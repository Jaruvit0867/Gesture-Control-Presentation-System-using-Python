# -*- coding: utf-8 -*-
"""
Presentation Controller - Gesture-based Presentation Controller
"""
import threading
import time
import queue
from typing import Optional

import customtkinter as ctk
import cv2

from config import AppConfig, Colors, Fonts, Dims, Icons
from gesture_engine import HandGestureEngine, GestureResult
from mouse_controller import MouseController
from ui_renderer import UIRenderer


from ui_components import GestureGuideCard, StatusCard, InfoBar


class PresentationMouseApp(ctk.CTk):
    """Main application class"""
    
    def __init__(self):
        super().__init__()
        
        self.config = AppConfig()
        self.engine = HandGestureEngine(self.config)
        self.mouse = MouseController(self.config)
        self.renderer = UIRenderer(self.config)
        
        self._running = False
        self._running_lock = threading.Lock()
        self._pinned = False
        self._compact_mode = False
        
        self._cap: Optional[cv2.VideoCapture] = None
        self._camera_thread: Optional[threading.Thread] = None
        self._frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._current_tk_image = None
        
        self._setup_window()
        self._init_ui()
        self._show_full_mode()
        self._schedule_frame_update()

    def _setup_window(self) -> None:
        """Configure main window"""
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("Presentation Controller")
        self.geometry(f"{Dims.WIDTH}x{Dims.HEIGHT}")
        self.configure(fg_color=Colors.BG_MAIN)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _init_ui(self) -> None:
        """Initialize all UI components"""
        self._init_full_mode_ui()
        self._init_compact_mode_ui()

    def _init_full_mode_ui(self) -> None:
        """Create full mode UI layout"""
        self.full_container = ctk.CTkFrame(self, fg_color="transparent")
        
        # === SIDEBAR ===
        self.sidebar = ctk.CTkFrame(
            self.full_container,
            width=Dims.SIDEBAR_WIDTH,
            fg_color=Colors.BG_SIDEBAR,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Logo/Header
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(25, 20))
        
        ctk.CTkLabel(
            header_frame,
            text="Presentation Controller",
            font=Fonts.HEADER,
            text_color=Colors.ACCENT
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            header_frame,
            text="Gesture Control System",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w")
        
        # Status Card
        self.status_card = StatusCard(self.sidebar)
        self.status_card.pack(padx=15, pady=(0, 10), fill="x")
        
        # Gesture Guide
        self.gesture_guide = GestureGuideCard(self.sidebar)
        self.gesture_guide.pack(padx=15, pady=(0, 10), fill="x")
        
        # Control Buttons
        btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        self.btn_start = ctk.CTkButton(
            btn_frame,
            text="▶  START CAMERA",
            font=Fonts.BUTTON,
            height=45,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_LIGHT,
            text_color=Colors.TEXT_MAIN,
            corner_radius=10,
            command=self._toggle_camera
        )
        self.btn_start.pack(fill="x", pady=(0, 8))
        
        # Secondary buttons row
        sec_btn_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        sec_btn_frame.pack(fill="x")
        
        self.btn_pin = ctk.CTkButton(
            sec_btn_frame,
            text=f"{Icons.PIN} Pin",
            font=Fonts.BUTTON,
            height=38,
            width=100,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_HOVER,
            corner_radius=8,
            command=self._toggle_pin
        )
        self.btn_pin.pack(side="left", expand=True, fill="x", padx=(0, 4))
        
        self.btn_mode = ctk.CTkButton(
            sec_btn_frame,
            text=f"{Icons.ARROW_COMPACT} Compact",
            font=Fonts.BUTTON,
            height=38,
            width=100,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_HOVER,
            corner_radius=8,
            command=self._toggle_mode
        )
        self.btn_mode.pack(side="right", expand=True, fill="x", padx=(4, 0))
        
        # Info Bar at bottom
        self.info_bar = InfoBar(self.sidebar)
        self.info_bar.pack(side="bottom", fill="x", padx=15, pady=15)
        
        # === CAMERA AREA ===
        cam_container = ctk.CTkFrame(self.full_container, fg_color="transparent")
        cam_container.pack(side="right", expand=True, fill="both", padx=15, pady=15)
        
        # Camera frame with border effect
        self.cam_frame = ctk.CTkFrame(
            cam_container,
            fg_color=Colors.BG_CARD,
            corner_radius=Dims.CORNER
        )
        self.cam_frame.pack(expand=True, fill="both")
        
        self._create_cam_label()

    def _create_cam_label(self) -> None:
        """Create or recreate the camera display label"""
        if hasattr(self, 'cam_label') and self.cam_label:
            try:
                self.cam_label.destroy()
            except Exception:
                pass
                
        self.cam_label = ctk.CTkLabel(
            self.cam_frame,
            text="📷\n\nCamera Off\nClick 'START CAMERA' to begin",
            font=Fonts.SUBHEADER,
            text_color=Colors.TEXT_MUTED
        )
        self.cam_label.place(relx=0.5, rely=0.5, anchor="center")

    def _init_compact_mode_ui(self) -> None:
        """Create compact mode UI layout"""
        self.compact_container = ctk.CTkFrame(self, fg_color=Colors.BG_MAIN)
        
        # Status area
        self.c_status_frame = ctk.CTkFrame(
            self.compact_container,
            fg_color=Colors.BG_CARD,
            corner_radius=Dims.CORNER,
            height=80
        )
        self.c_status_frame.pack(padx=12, pady=12, fill="x")
        self.c_status_frame.pack_propagate(False)
        
        c_inner = ctk.CTkFrame(self.c_status_frame, fg_color="transparent")
        c_inner.place(relx=0.5, rely=0.5, anchor="center")
        
        self.lbl_c_indicator = ctk.CTkLabel(
            c_inner,
            text=Icons.CIRCLE,
            font=("Segoe UI", 8),
            text_color=Colors.TEXT_MUTED
        )
        self.lbl_c_indicator.pack()
        
        self.lbl_c_status = ctk.CTkLabel(
            c_inner,
            text="READY",
            font=Fonts.STATUS_COMPACT,
            text_color=Colors.TEXT_SUB
        )
        self.lbl_c_status.pack()
        
        self.lbl_c_sub = ctk.CTkLabel(
            c_inner,
            text="Camera off",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self.lbl_c_sub.pack()
        
        # Control buttons
        self.c_ctrl = ctk.CTkFrame(self.compact_container, fg_color="transparent")
        self.c_ctrl.pack(fill="x", padx=12, pady=(0, 12))
        
        self.btn_c_start = ctk.CTkButton(
            self.c_ctrl,
            text="▶ START",
            font=Fonts.BUTTON,
            height=40,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_LIGHT,
            corner_radius=8,
            command=self._toggle_camera
        )
        self.btn_c_start.pack(side="left", expand=True, fill="x", padx=(0, 4))
        
        self.btn_c_pin = ctk.CTkButton(
            self.c_ctrl,
            text=Icons.PIN,
            font=Fonts.BUTTON,
            width=40,
            height=40,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_HOVER,
            corner_radius=8,
            command=self._toggle_pin
        )
        self.btn_c_pin.pack(side="left", padx=4)
        
        self.btn_c_mode = ctk.CTkButton(
            self.c_ctrl,
            text=Icons.ARROW_EXPAND,
            font=Fonts.BUTTON,
            width=40,
            height=40,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_HOVER,
            corner_radius=8,
            command=self._toggle_mode
        )
        self.btn_c_mode.pack(side="left")

    def _show_full_mode(self) -> None:
        """Switch to full mode UI"""
        self.compact_container.pack_forget()
        self.geometry(f"{Dims.WIDTH}x{Dims.HEIGHT}")
        self.full_container.pack(fill="both", expand=True)
        self._compact_mode = False

    def _show_compact_mode(self) -> None:
        """Switch to compact mode UI"""
        self.full_container.pack_forget()
        self.geometry(f"{Dims.COMPACT_W}x{Dims.COMPACT_H}")
        self.compact_container.pack(fill="both", expand=True)
        self._compact_mode = True

    def _toggle_mode(self) -> None:
        """Toggle between full and compact mode"""
        if self._compact_mode:
            self._show_full_mode()
        else:
            self._show_compact_mode()

    def _toggle_pin(self) -> None:
        """Toggle window always-on-top"""
        self._pinned = not self._pinned
        self.attributes('-topmost', self._pinned)
        
        if self._pinned:
            self.btn_pin.configure(fg_color=Colors.WARNING, text_color=Colors.TEXT_DARK)
            self.btn_c_pin.configure(fg_color=Colors.WARNING, text_color=Colors.TEXT_DARK)
        else:
            self.btn_pin.configure(fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN)
            self.btn_c_pin.configure(fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN)

    def _toggle_camera(self) -> None:
        """Toggle camera on/off"""
        if self._running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self) -> None:
        """Start camera capture"""
        self.btn_start.configure(state="disabled", text="⏳ Starting...")
        self.btn_c_start.configure(state="disabled", text="⏳")
        self.update()
        
        self._cap = cv2.VideoCapture(self.config.cam_index)
        
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(1)
        
        if not self._cap.isOpened():
            self._show_error("Camera Error", "Could not open camera")
            self.btn_start.configure(state="normal", text="▶  START CAMERA")
            self.btn_c_start.configure(state="normal", text="▶ START")
            return
        
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.cam_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.cam_height)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        with self._running_lock:
            self._running = True
        
        # Clear any existing image before starting
        self._current_tk_image = None
        self.cam_label.configure(image=None, text="")
        
        self._camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._camera_thread.start()
        
        self._update_button_state()

    def _stop_camera(self) -> None:
        """Stop camera capture"""
        # Signal thread to stop
        with self._running_lock:
            self._running = False
        
        # Wait for thread to finish (outside of lock)
        if self._camera_thread and self._camera_thread.is_alive():
            self._camera_thread.join(timeout=2.0)
        
        # Release camera
            self._cap.release()
            self._cap = None
            # Give the OS a moment to fully release the resource
            time.sleep(0.2)
        
        # Clear UI image by RECREATING the label
        # This prevents TclError where the widget holds onto dead image references
        self._create_cam_label()

        # Then reset state and references
        self._current_tk_image = None
        self._camera_thread = None
        self.mouse.reset_state()
        self.engine.reset()
        self.renderer.reset()

        # Clear frame queue to prevent zombie frames
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break
        self.status_card.update_status("READY", "Camera off", Colors.TEXT_SUB, False)
        self.lbl_c_status.configure(text="READY", text_color=Colors.TEXT_SUB)
        self.lbl_c_sub.configure(text="Camera off")
        self.lbl_c_indicator.configure(text_color=Colors.TEXT_MUTED)
        self.info_bar.update_info(0, self.config.smooth_factor)
        self._update_button_state()

    def _camera_loop(self) -> None:
        """Camera capture and processing loop"""
        while True:
            with self._running_lock:
                if not self._running:
                    break
            
            # Additional safety: if this thread is no longer the active camera thread, stop
            if threading.current_thread() is not self._camera_thread:
                break
            
            if not self._cap or not self._cap.isOpened():
                break
            
            success, frame = self._cap.read()
            if not success:
                continue
            
            frame = cv2.flip(frame, 1)
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame.shape[:2]
            
            result = self.engine.process(img_rgb, w, h)
            self._handle_gesture(result)
            
            if not self._compact_mode:
                img_drawn = self.renderer.draw(img_rgb, result, self._compact_mode)
            else:
                img_drawn = None
            
            try:
                self._frame_queue.put_nowait((result, img_drawn))
            except queue.Full:
                pass

    def _handle_gesture(self, result: GestureResult) -> None:
        """Handle gesture actions"""
        if result.is_paused:
            self.mouse.drag_end()
            return
        
        if result.state_name == "DRAGGING" and result.normalized_pos:
            self.mouse.drag_start()
            self.mouse.move(*result.normalized_pos)
        elif result.state_name == "MOVING" and result.normalized_pos:
            self.mouse.drag_end()
            self.mouse.move(*result.normalized_pos)
        elif result.state_name == "SWIPE" and result.swipe_feedback:
            self.mouse.drag_end()
            direction = "right" if "NEXT" in result.swipe_feedback else "left"
            self.mouse.trigger_swipe(direction)
        else:
            self.mouse.drag_end()

    def _schedule_frame_update(self) -> None:
        """Schedule periodic frame updates"""
        self._process_frame_queue()
        self.after(16, self._schedule_frame_update)

    def _process_frame_queue(self) -> None:
        """Process frames from queue and update UI"""
        try:
            result, img_drawn = self._frame_queue.get_nowait()
            
            # Update status card
            is_active = result.state_name not in ["SCANNING", "PAUSED"]
            self.status_card.update_status(
                result.state_name,
                result.sub_text,
                result.ui_color,
                is_active
            )
            
            # Update compact mode
            self.lbl_c_status.configure(text=result.state_name, text_color=result.ui_color)
            self.lbl_c_sub.configure(text=result.sub_text)
            self.lbl_c_indicator.configure(
                text_color=Colors.SUCCESS if is_active else Colors.TEXT_MUTED
            )
            
            # Update info bar
            smooth = self.mouse.get_current_smooth_factor()
            self.info_bar.update_info(result.confidence, smooth)
            
            # Update camera image
            if img_drawn is not None and not self._compact_mode:
                display_w = self.cam_frame.winfo_width() - 4
                display_h = self.cam_frame.winfo_height() - 4
                
                tk_img = self.renderer.get_tk_image(img_drawn, display_w, display_h)
                if tk_img:
                    self._current_tk_image = tk_img
                    self.cam_label.configure(image=tk_img)
                    
        except queue.Empty:
            pass

    def _update_button_state(self) -> None:
        """Update button appearance"""
        if self._running:
            self.btn_start.configure(
                text="⏹  STOP CAMERA",
                fg_color=Colors.DANGER,
                hover_color=Colors.DANGER_LIGHT,
                state="normal"
            )
            self.btn_c_start.configure(
                text="⏹ STOP",
                fg_color=Colors.DANGER,
                hover_color=Colors.DANGER_LIGHT,
                state="normal"
            )
        else:
            self.btn_start.configure(
                text="▶  START CAMERA",
                fg_color=Colors.ACCENT,
                hover_color=Colors.ACCENT_LIGHT,
                state="normal"
            )
            self.btn_c_start.configure(
                text="▶ START",
                fg_color=Colors.ACCENT,
                hover_color=Colors.ACCENT_LIGHT,
                state="normal"
            )

    def _show_error(self, title: str, message: str) -> None:
        """Show error dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("320x160")
        dialog.configure(fg_color=Colors.BG_MAIN)
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text="⚠️",
            font=("Segoe UI", 32)
        ).pack(pady=(20, 5))
        
        ctk.CTkLabel(
            dialog,
            text=message,
            font=Fonts.BODY,
            text_color=Colors.TEXT_SUB
        ).pack(pady=5)
        
        ctk.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy,
            fg_color=Colors.ACCENT,
            corner_radius=8,
            width=100
        ).pack(pady=15)

    def _on_closing(self) -> None:
        """Handle window close"""
        with self._running_lock:
            self._running = False
        
        if self._cap:
            self._cap.release()
        
        self.engine.release()
        self.destroy()


def main():
    """Application entry point"""
    app = PresentationMouseApp()
    app.mainloop()


if __name__ == "__main__":
    main()