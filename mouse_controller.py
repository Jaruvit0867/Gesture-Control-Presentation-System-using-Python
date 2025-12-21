# -*- coding: utf-8 -*-
"""
Mouse Controller with adaptive smoothing
"""
import time
import threading
from typing import Optional, Tuple

import pyautogui

from config import AppConfig


# PyAutoGUI settings
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class MouseController:
    """
    Mouse controller with adaptive smoothing based on frame rate.
    
    Features:
    - Adaptive smoothing factor based on actual FPS
    - Thread-safe drag operations
    - Screen boundary handling
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.screen_w, self.screen_h = pyautogui.size()
        
        # Position tracking
        self._prev_x = 0.0
        self._prev_y = 0.0
        self._curr_x = 0.0
        self._curr_y = 0.0
        
        # Drag state with lock for thread safety
        self._is_dragging = False
        self._drag_lock = threading.Lock()
        
        # FPS tracking for adaptive smoothing
        self._last_move_time = 0.0
        self._frame_times: list = []
        self._max_frame_samples = 10
        
        # Current adaptive smooth factor
        self._current_smooth = config.smooth_factor

    def move(self, raw_x_norm: float, raw_y_norm: float) -> None:
        """
        Move mouse to normalized position with adaptive smoothing.
        
        Args:
            raw_x_norm: X position (0.0 to 1.0) from camera ROI
            raw_y_norm: Y position (0.0 to 1.0) from camera ROI
        """
        now = time.time()
        
        # Update FPS tracking
        if self._last_move_time > 0:
            frame_time = now - self._last_move_time
            self._frame_times.append(frame_time)
            if len(self._frame_times) > self._max_frame_samples:
                self._frame_times.pop(0)
            
            # Calculate adaptive smooth factor
            self._update_smooth_factor()
        
        self._last_move_time = now
        
        # Clamp and map coordinates
        clamped_x = max(0.0, min(1.0, raw_x_norm))
        clamped_y = max(0.0, min(1.0, raw_y_norm))
        
        target_x = self.screen_w * clamped_x
        target_y = self.screen_h * clamped_y
        
        # Apply smoothing
        smooth = self._current_smooth
        self._curr_x = self._prev_x + (target_x - self._prev_x) / smooth
        self._curr_y = self._prev_y + (target_y - self._prev_y) / smooth
        
        # Move mouse
        try:
            pyautogui.moveTo(int(self._curr_x), int(self._curr_y))
        except Exception:
            pass  # Ignore pyautogui errors
        
        self._prev_x, self._prev_y = self._curr_x, self._curr_y

    def _update_smooth_factor(self) -> None:
        """Update smooth factor based on actual FPS"""
        if len(self._frame_times) < 3:
            return
        
        avg_frame_time = sum(self._frame_times) / len(self._frame_times)
        current_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 30
        
        # Target FPS is 30, adjust smooth factor proportionally
        target_fps = self.config.target_fps
        fps_ratio = current_fps / target_fps
        
        # Adjust smooth factor: higher FPS = higher smooth, lower FPS = lower smooth
        base_smooth = self.config.smooth_factor
        adjusted = base_smooth * fps_ratio
        
        # Clamp to configured range
        self._current_smooth = max(
            self.config.min_smooth_factor,
            min(self.config.max_smooth_factor, adjusted)
        )

    def drag_start(self) -> None:
        """Start mouse drag (left button down)"""
        with self._drag_lock:
            if not self._is_dragging:
                try:
                    pyautogui.mouseDown()
                    self._is_dragging = True
                except Exception:
                    pass

    def drag_end(self) -> None:
        """End mouse drag (left button up)"""
        with self._drag_lock:
            if self._is_dragging:
                try:
                    pyautogui.mouseUp()
                    self._is_dragging = False
                except Exception:
                    pass

    def trigger_swipe(self, direction: str) -> None:
        """
        Trigger keyboard arrow for swipe gesture.
        
        Args:
            direction: "left" or "right"
        """
        try:
            if direction == "left":
                pyautogui.press("left")
            elif direction == "right":
                pyautogui.press("right")
        except Exception:
            pass

    def click(self) -> None:
        """Perform a single click"""
        try:
            pyautogui.click()
        except Exception:
            pass

    def get_position(self) -> Tuple[float, float]:
        """Get current mouse position"""
        return (self._curr_x, self._curr_y)

    def get_current_smooth_factor(self) -> float:
        """Get the current adaptive smooth factor"""
        return self._current_smooth

    def reset_state(self) -> None:
        """Reset all state - safety function"""
        self.drag_end()
        self._prev_x = 0.0
        self._prev_y = 0.0
        self._curr_x = 0.0
        self._curr_y = 0.0
        self._frame_times.clear()
        self._current_smooth = self.config.smooth_factor

    @property
    def is_dragging(self) -> bool:
        """Check if currently dragging"""
        with self._drag_lock:
            return self._is_dragging
