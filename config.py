# -*- coding: utf-8 -*-
"""
Configuration module for AI Control Pro
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass
class AppConfig:
    """Application configuration with sensible defaults"""
    
    # Camera Settings
    cam_index: int = 0
    cam_width: int = 1280
    cam_height: int = 720
    target_fps: int = 30
    
    # Gesture Detection Thresholds
    swipe_dist_threshold: float = 0.15
    swipe_timeout: float = 0.5
    swipe_cooldown: float = 0.6
    
    # Timing Delays (seconds)
    delay_after_fist: float = 0.6
    delay_after_swipe: float = 0.5
    
    # Mouse Control
    smooth_factor: float = 5.0
    min_smooth_factor: float = 2.0
    max_smooth_factor: float = 10.0
    
    # Region of Interest
    roi_margin: int = 120
    
    # UI Feedback
    swipe_feedback_frames: int = 15
    
    # MediaPipe Settings
    model_complexity: int = 0
    max_num_hands: int = 1
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.6


class Colors:
    """UI Color palette - Modern Dark Theme"""
    
    # Backgrounds
    BG_MAIN = "#0f0f1a"
    BG_SIDEBAR = "#161625"
    BG_CARD = "#1e1e32"
    BG_CARD_HOVER = "#282845"
    BG_HOVER = "#2a2a4a"
    
    # Accent Colors
    ACCENT = "#6c5ce7"
    ACCENT_LIGHT = "#a29bfe"
    SUCCESS = "#00b894"
    SUCCESS_LIGHT = "#55efc4"
    WARNING = "#fdcb6e"
    DANGER = "#ff7675"
    DANGER_LIGHT = "#fab1a0"
    INFO = "#74b9ff"
    CYAN = "#00cec9"
    ORANGE = "#e17055"
    
    # Text Colors
    TEXT_MAIN = "#ffffff"
    TEXT_SUB = "#a0a0b8"
    TEXT_MUTED = "#6c6c80"
    TEXT_DARK = "#0f0f1a"
    
    # State Colors (RGB for OpenCV)
    @staticmethod
    def state_color(state: str) -> Tuple[int, int, int]:
        """Get RGB color tuple for gesture state"""
        colors = {
            "SCANNING": (108, 92, 231),
            "PAUSED": (255, 118, 117),
            "DRAGGING": (253, 203, 110),
            "LOCKED": (116, 185, 255),
            "SWIPE": (0, 184, 148),
            "MOVING": (255, 255, 255),
            "WAITING": (160, 160, 184),
        }
        return colors.get(state, (128, 128, 128))


class Fonts:
    """Font definitions for UI"""
    
    HEADER = ("Segoe UI Black", 20)
    SUBHEADER = ("Segoe UI", 13)
    BODY = ("Segoe UI", 11)
    BODY_BOLD = ("Segoe UI Semibold", 11)
    SMALL = ("Segoe UI", 10)
    STATUS_BIG = ("Segoe UI Black", 32)
    STATUS_COMPACT = ("Segoe UI Bold", 20)
    BUTTON = ("Segoe UI Semibold", 12)
    GESTURE_ICON = ("Segoe UI", 18)
    GESTURE_TEXT = ("Segoe UI", 10)


class Dims:
    """UI Dimensions"""
    
    # Main Window
    WIDTH = 960
    HEIGHT = 640
    SIDEBAR_WIDTH = 300
    CORNER = 12
    STATUS_H = 100
    
    # Compact Mode
    COMPACT_W = 300
    COMPACT_H = 180
    
    # Overlay
    OVERLAY_ALPHA = 0.6
    
    # Drawing
    BRACKET_LENGTH = 30
    BRACKET_THICKNESS = 3


class Icons:
    """Unicode icons"""
    
    PIN = "📌"
    ARROW_EXPAND = "↗"
    ARROW_COMPACT = "↙"
    CAMERA = "🎥"
    HAND = "✋"
    CHECK = "✓"
    CROSS = "✗"
    CIRCLE = "●"