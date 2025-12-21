# -*- coding: utf-8 -*-
"""
UI Components for the Presentation Controller App
"""
import customtkinter as ctk
from config import Colors, Fonts, Dims, Icons

class GestureGuideCard(ctk.CTkFrame):
    """Card showing gesture instructions"""
    
    GESTURES = [
        ("✊", "Fist", "Pause", Colors.DANGER),
        ("👆", "1 Finger", "Move", Colors.TEXT_MAIN),
        ("✌️", "2 Fingers", "Drag", Colors.INFO),
        ("🖐", "Open", "Swipe", Colors.SUCCESS),
    ]
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=Colors.BG_CARD, corner_radius=Dims.CORNER, **kwargs)
        
        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(12, 8))
        
        ctk.CTkLabel(
            title_frame,
            text="GESTURES",
            font=("Segoe UI Semibold", 11),
            text_color=Colors.TEXT_MUTED
        ).pack(side="left")
        
        # Gesture grid
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=(0, 12))
        
        for i, (icon, name, action, color) in enumerate(self.GESTURES):
            self._create_gesture_item(grid_frame, icon, name, action, color, i)
    
    def _create_gesture_item(self, parent, icon, name, action, color, col):
        """Create a single gesture item"""
        frame = ctk.CTkFrame(parent, fg_color=Colors.BG_HOVER, corner_radius=8, width=60, height=65)
        frame.pack(side="left", padx=3, expand=True, fill="x")
        frame.pack_propagate(False)
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(inner, text=icon, font=("Segoe UI", 18), text_color=color).pack()
        ctk.CTkLabel(inner, text=action, font=("Segoe UI", 9), text_color=Colors.TEXT_SUB).pack()


class StatusCard(ctk.CTkFrame):
    """Main status display card"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=Colors.BG_CARD, corner_radius=Dims.CORNER, **kwargs)
        
        # Status indicator dot
        self.indicator_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.indicator_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        self.indicator = ctk.CTkLabel(
            self.indicator_frame,
            text=Icons.CIRCLE,
            font=("Segoe UI", 10),
            text_color=Colors.TEXT_MUTED
        )
        self.indicator.pack(side="left")
        
        self.indicator_label = ctk.CTkLabel(
            self.indicator_frame,
            text="STANDBY",
            font=("Segoe UI Semibold", 10),
            text_color=Colors.TEXT_MUTED
        )
        self.indicator_label.pack(side="left", padx=(5, 0))
        
        # Main status text
        self.status_label = ctk.CTkLabel(
            self,
            text="READY",
            font=Fonts.STATUS_BIG,
            text_color=Colors.TEXT_SUB
        )
        self.status_label.pack(pady=(0, 2))
        
        # Sub status
        self.sub_label = ctk.CTkLabel(
            self,
            text="Camera off",
            font=Fonts.BODY,
            text_color=Colors.TEXT_MUTED
        )
        self.sub_label.pack(pady=(0, 15))
    
    def update_status(self, state: str, sub_text: str, color: str, is_active: bool = False):
        """Update the status display"""
        self.status_label.configure(text=state, text_color=color)
        self.sub_label.configure(text=sub_text)
        
        if is_active:
            self.indicator.configure(text_color=Colors.SUCCESS)
            self.indicator_label.configure(text="ACTIVE", text_color=Colors.SUCCESS)
        else:
            self.indicator.configure(text_color=Colors.TEXT_MUTED)
            self.indicator_label.configure(text="STANDBY", text_color=Colors.TEXT_MUTED)


class InfoBar(ctk.CTkFrame):
    """Bottom info bar with stats"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=Colors.BG_CARD, corner_radius=Dims.CORNER, height=40, **kwargs)
        self.pack_propagate(False)
        
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=15)
        
        # Confidence
        self.conf_label = ctk.CTkLabel(
            inner,
            text="Confidence: --",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self.conf_label.pack(side="left")
        
        # Smooth factor
        self.smooth_label = ctk.CTkLabel(
            inner,
            text="Smooth: --",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self.smooth_label.pack(side="right")
    
    def update_info(self, confidence: float, smooth: float):
        """Update info display"""
        conf_text = f"Confidence: {confidence:.0%}" if confidence > 0 else "Confidence: --"
        self.conf_label.configure(text=conf_text)
        self.smooth_label.configure(text=f"Smooth: {smooth:.1f}")
