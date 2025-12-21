# -*- coding: utf-8 -*-
"""
UI Renderer for camera overlay and image processing
"""
import cv2
import numpy as np
from typing import Optional, Tuple

from PIL import Image
import customtkinter as ctk

from config import AppConfig, Dims, Colors
from gesture_engine import GestureResult


class UIRenderer:
    """
    Renders camera overlay with gesture visualization.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        self._last_img_w = 0
        self._last_img_h = 0
        self._ctk_image_ref: Optional[ctk.CTkImage] = None
        
        self._swipe_msg = ""
        self._swipe_timer = 0
        
        self._font = cv2.FONT_HERSHEY_SIMPLEX

    def draw(self, img_rgb: np.ndarray, gesture_result: GestureResult, 
             compact_mode: bool = False) -> np.ndarray:
        """Draw gesture visualization overlay on image."""
        if compact_mode:
            return img_rgb
        
        h, w = img_rgb.shape[:2]
        margin = self.config.roi_margin
        
        # Create dimmed background
        final_img = self._create_dimmed_overlay(img_rgb, margin)
        
        # Draw ROI brackets
        self._draw_brackets(
            final_img,
            margin, margin,
            w - margin, h - margin,
            gesture_result.roi_color
        )
        
        # Draw finger count indicator
        self._draw_finger_count(final_img, gesture_result, w, h, margin)
        
        # Draw state indicator
        self._draw_state_indicator(final_img, gesture_result, w, margin)
        
        # Handle swipe feedback
        if gesture_result.swipe_feedback:
            self._swipe_msg = gesture_result.swipe_feedback
            self._swipe_timer = self.config.swipe_feedback_frames
        
        if self._swipe_timer > 0:
            self._draw_swipe_feedback(final_img, w, h)
            self._swipe_timer -= 1
        
        return final_img

    def _create_dimmed_overlay(self, img_rgb: np.ndarray, margin: int) -> np.ndarray:
        """Create image with dimmed border and bright ROI center"""
        h, w = img_rgb.shape[:2]
        
        dimmed = (img_rgb * (1 - Dims.OVERLAY_ALPHA)).astype(np.uint8)
        dimmed[margin:h-margin, margin:w-margin] = img_rgb[margin:h-margin, margin:w-margin]
        
        return dimmed

    def _draw_brackets(self, img: np.ndarray, x1: int, y1: int, 
                       x2: int, y2: int, color: Tuple[int, int, int]) -> None:
        """Draw corner brackets around ROI"""
        length = Dims.BRACKET_LENGTH
        thick = Dims.BRACKET_THICKNESS
        
        # Top-Left
        cv2.line(img, (x1, y1), (x1 + length, y1), color, thick)
        cv2.line(img, (x1, y1), (x1, y1 + length), color, thick)
        
        # Top-Right
        cv2.line(img, (x2, y1), (x2 - length, y1), color, thick)
        cv2.line(img, (x2, y1), (x2, y1 + length), color, thick)
        
        # Bottom-Left
        cv2.line(img, (x1, y2), (x1 + length, y2), color, thick)
        cv2.line(img, (x1, y2), (x1, y2 - length), color, thick)
        
        # Bottom-Right
        cv2.line(img, (x2, y2), (x2 - length, y2), color, thick)
        cv2.line(img, (x2, y2), (x2, y2 - length), color, thick)

    def _draw_finger_count(self, img: np.ndarray, result: GestureResult,
                           w: int, h: int, margin: int) -> None:
        """Draw finger count indicator in corner"""
        if result.finger_count > 0:
            text = f"{result.finger_count}"
            
            x = w - margin - 50
            y = h - margin - 20
            
            # Draw background circle with glow effect
            cv2.circle(img, (x + 10, y - 10), 28, (20, 20, 30), -1)
            cv2.circle(img, (x + 10, y - 10), 25, result.roi_color, 2)
            
            cv2.putText(img, text, (x, y), self._font, 1.0, (255, 255, 255), 2)

    def _draw_state_indicator(self, img: np.ndarray, result: GestureResult,
                              w: int, margin: int) -> None:
        """Draw current state text at top"""
        text = result.state_name
        text_size = cv2.getTextSize(text, self._font, 0.7, 2)[0]
        
        x = (w - text_size[0]) // 2
        y = margin + 25
        
        # Draw pill background
        padding_x = 15
        padding_y = 8
        cv2.rectangle(
            img,
            (x - padding_x, y - text_size[1] - padding_y),
            (x + text_size[0] + padding_x, y + padding_y),
            (20, 20, 30),
            -1
        )
        cv2.rectangle(
            img,
            (x - padding_x, y - text_size[1] - padding_y),
            (x + text_size[0] + padding_x, y + padding_y),
            result.roi_color,
            2
        )
        
        cv2.putText(img, text, (x, y), self._font, 0.7, result.roi_color, 2)

    def _draw_swipe_feedback(self, img: np.ndarray, w: int, h: int) -> None:
        """Draw swipe feedback text in center"""
        text = self._swipe_msg
        text_size = cv2.getTextSize(text, self._font, 1.5, 3)[0]
        
        x = (w - text_size[0]) // 2
        y = h // 2
        
        # Draw with glow effect
        cv2.putText(img, text, (x + 2, y + 2), self._font, 1.5, (0, 0, 0), 5)
        cv2.putText(img, text, (x, y), self._font, 1.5, (0, 255, 200), 3)

    def get_tk_image(self, img_rgb: np.ndarray, display_w: int, 
                     display_h: int) -> Optional[ctk.CTkImage]:
        """Convert RGB array to CTkImage for proper HiDPI support"""
        if display_w < 10 or display_h < 10:
            return None
        
        img_h, img_w = img_rgb.shape[:2]
        
        img_ratio = img_w / img_h
        frame_ratio = display_w / display_h
        
        if frame_ratio > img_ratio:
            new_h = display_h
            new_w = int(new_h * img_ratio)
        else:
            new_w = display_w
            new_h = int(new_w / img_ratio)
        
        # Ensure minimum size
        new_w = max(new_w, 100)
        new_h = max(new_h, 100)
        
        # Convert to PIL Image
        pil_img = Image.fromarray(img_rgb)
        
        # Create CTkImage (handles HiDPI automatically)
        self._ctk_image_ref = ctk.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=(new_w, new_h)
        )
        
        return self._ctk_image_ref

    def reset(self) -> None:
        """Reset renderer state"""
        self._swipe_msg = ""
        self._swipe_timer = 0
        self._ctk_image_ref = None