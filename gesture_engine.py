# -*- coding: utf-8 -*-
"""
Gesture Recognition Engine using MediaPipe
"""
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List

import mediapipe as mp

from config import AppConfig, Colors


@dataclass
class GestureResult:
    """Result from gesture detection"""
    
    state_name: str          # "PAUSED", "MOVING", "DRAGGING", "SWIPE", "WAITING", "SCANNING"
    sub_text: str            # Secondary description
    ui_color: str            # Color for UI elements
    roi_color: Tuple[int, int, int]  # RGB color for camera ROI
    normalized_pos: Optional[Tuple[float, float]] = None  # (x, y) for mouse
    swipe_feedback: str = ""  # Feedback text for swipe actions
    finger_count: int = 0     # Number of fingers detected
    confidence: float = 0.0   # Detection confidence
    is_paused: bool = False   # Whether system is paused


class HandGestureEngine:
    """
    Hand gesture recognition engine using MediaPipe.
    
    Flow: Any gesture -> PAUSE (fist) -> Any gesture works immediately
    
    Supports:
    - Fist (0 fingers): Pause - stops all commands temporarily
    - Open hand (4-5 fingers): Swipe gesture
    - One finger: Move cursor
    - Two fingers: Drag
    """
    
    # Finger tip and pip landmarks for each finger
    FINGER_TIPS = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
    FINGER_PIPS = [3, 6, 10, 14, 18]  # PIP joints
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            model_complexity=config.model_complexity,
            max_num_hands=config.max_num_hands,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence
        )
        
        # State tracking
        self._allow_drag = False
        self._last_fist_time = 0.0
        self._last_open_time = 0.0
        
        # Swipe detection state
        self._swipe_start_x: Optional[float] = None
        self._swipe_start_time = 0.0
        self._last_swipe_action_time = 0.0
        
        # Detection state
        self._last_detection_time = 0.0
        self._detection_confidence = 0.0

    def process(self, img_rgb, width: int, height: int) -> GestureResult:
        """
        Process an RGB image and return gesture detection result.
        """
        results = self.hands.process(img_rgb)
        now = time.time()
        margin = self.config.roi_margin
        
        # No hand detected
        if not results.multi_hand_landmarks:
            self._allow_drag = False
            self._swipe_start_x = None
            
            return GestureResult(
                state_name="SCANNING",
                sub_text="Looking for hand...",
                ui_color=Colors.TEXT_SUB,
                roi_color=Colors.state_color("SCANNING"),
                confidence=0.0,
                is_paused=False
            )
        
        # Get hand landmarks and confidence
        hand_landmarks = results.multi_hand_landmarks[0]
        landmarks = hand_landmarks.landmark
        
        # Determine handedness for thumb detection
        is_right_hand = True
        if results.multi_handedness:
            self._detection_confidence = results.multi_handedness[0].classification[0].score
            hand_label = results.multi_handedness[0].classification[0].label
            is_right_hand = (hand_label == "Right")
        
        self._last_detection_time = now
        
        # Count fingers with improved thumb detection
        fingers_up = self._count_fingers(landmarks, is_right_hand)
        total_fingers = sum(fingers_up)
        is_two_fingers = (fingers_up[1] == 1 and fingers_up[2] == 1 and 
                         fingers_up[3] == 0 and fingers_up[4] == 0)
        
        # Calculate normalized position from index finger tip
        palm_cx_norm = landmarks[9].x
        idx_x = landmarks[8].x * width
        idx_y = landmarks[8].y * height
        
        raw_x = (idx_x - margin) / (width - 2 * margin)
        raw_y = (idx_y - margin) / (height - 2 * margin)
        norm_pos = (raw_x, raw_y)
        
        return self._process_state(
            now, total_fingers, is_two_fingers,
            palm_cx_norm, norm_pos, fingers_up
        )

    def _count_fingers(self, landmarks, is_right_hand: bool) -> List[int]:
        """
        Count raised fingers with improved thumb detection.
        """
        fingers = [0] * 5
        
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        
        if is_right_hand:
            thumb_extended = thumb_tip.x < thumb_ip.x - 0.02
        else:
            thumb_extended = thumb_tip.x > thumb_ip.x + 0.02
        
        palm_center_x = landmarks[9].x
        thumb_away_from_palm = abs(thumb_tip.x - palm_center_x) > 0.08
        
        fingers[0] = 1 if (thumb_extended and thumb_away_from_palm) else 0
        
        for i in range(1, 5):
            tip_idx = self.FINGER_TIPS[i]
            pip_idx = self.FINGER_PIPS[i]
            
            tip_y = landmarks[tip_idx].y
            pip_y = landmarks[pip_idx].y
            
            fingers[i] = 1 if (pip_y - tip_y) > 0.02 else 0
        
        return fingers

    def _process_state(
        self, 
        now: float, 
        total_fingers: int,
        is_two_fingers: bool,
        palm_cx_norm: float,
        norm_pos: Tuple[float, float],
        fingers_up: List[int]
    ) -> GestureResult:
        """Process gesture state machine"""
        
        # Check for fist (no fingers excluding thumb)
        non_thumb_fingers = sum(fingers_up[1:])
        is_fist = (non_thumb_fingers == 0)
        
        # A. FIST -> PAUSE (no mouse action)
        if is_fist:
            self._allow_drag = False
            self._swipe_start_x = None
            self._last_fist_time = now
            
            return GestureResult(
                state_name="PAUSED",
                sub_text="Fist - Commands paused",
                ui_color=Colors.DANGER,
                roi_color=Colors.state_color("PAUSED"),
                finger_count=total_fingers,
                confidence=self._detection_confidence,
                is_paused=True
            )
        
        # B. OPEN HAND (4-5 fingers) -> SWIPE MODE
        if total_fingers >= 4:
            self._allow_drag = False
            self._last_open_time = now
            
            swipe_feedback = self._detect_swipe(now, palm_cx_norm)
            
            return GestureResult(
                state_name="SWIPE",
                sub_text="Swipe ready" if not swipe_feedback else swipe_feedback,
                ui_color=Colors.SUCCESS,
                roi_color=Colors.state_color("SWIPE"),
                swipe_feedback=swipe_feedback,
                finger_count=total_fingers,
                confidence=self._detection_confidence,
                is_paused=False
            )
        
        # C. TWO FINGERS -> DRAG MODE
        if is_two_fingers:
            self._swipe_start_x = None
            if self._allow_drag:
                return GestureResult(
                    state_name="DRAGGING",
                    sub_text="Drag active",
                    ui_color=Colors.INFO,
                    roi_color=Colors.state_color("DRAGGING"),
                    normalized_pos=norm_pos,
                    finger_count=2,
                    confidence=self._detection_confidence,
                    is_paused=False
                )
            else:
                return GestureResult(
                    state_name="LOCKED",
                    sub_text="Use 1 finger first to unlock",
                    ui_color=Colors.WARNING,
                    roi_color=Colors.state_color("LOCKED"),
                    normalized_pos=norm_pos,
                    finger_count=2,
                    confidence=self._detection_confidence,
                    is_paused=False
                )
        
        # D. ONE FINGER -> MOVE MODE
        self._swipe_start_x = None
        
        fist_delay_ok = (now - self._last_fist_time) > self.config.delay_after_fist
        open_delay_ok = (now - self._last_open_time) > self.config.delay_after_swipe
        
        if fist_delay_ok and open_delay_ok:
            self._allow_drag = True
            return GestureResult(
                state_name="MOVING",
                sub_text="Cursor active - Drag unlocked",
                ui_color=Colors.TEXT_MAIN,
                roi_color=Colors.state_color("MOVING"),
                normalized_pos=norm_pos,
                finger_count=total_fingers,
                confidence=self._detection_confidence,
                is_paused=False
            )
        else:
            return GestureResult(
                state_name="WAITING",
                sub_text="Stabilizing...",
                ui_color=Colors.WARNING,
                roi_color=Colors.state_color("WAITING"),
                finger_count=total_fingers,
                confidence=self._detection_confidence,
                is_paused=False
            )

    def _detect_swipe(self, now: float, palm_cx_norm: float) -> str:
        """Detect horizontal swipe gesture."""
        if self._swipe_start_x is None:
            self._swipe_start_x = palm_cx_norm
            self._swipe_start_time = now
            return ""
        
        dx = palm_cx_norm - self._swipe_start_x
        dt = now - self._swipe_start_time
        
        if dt > self.config.swipe_timeout:
            self._swipe_start_x = palm_cx_norm
            self._swipe_start_time = now
            return ""
        
        cooldown_ok = (now - self._last_swipe_action_time) > self.config.swipe_cooldown
        threshold_reached = abs(dx) > self.config.swipe_dist_threshold
        
        if threshold_reached and cooldown_ok:
            self._last_swipe_action_time = now
            self._swipe_start_x = None
            
            if dx > 0:
                return "NEXT >>"
            else:
                return "<< PREV"
        
        return ""

    def reset(self):
        """Reset all state"""
        self._allow_drag = False
        self._last_fist_time = 0.0
        self._last_open_time = 0.0
        self._swipe_start_x = None
        self._swipe_start_time = 0.0
        self._last_swipe_action_time = 0.0

    def release(self):
        """Release MediaPipe resources"""
        if self.hands:
            self.hands.close()