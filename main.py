import cv2
import mediapipe as mp
import pyautogui
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import time
import math
from collections import deque
from queue import SimpleQueue, Queue, Empty
import ctypes

# ====== Config ======
CAM_WIDTH = 640
CAM_HEIGHT = 480
TARGET_FPS = 30
PREVIEW_FPS = 30
SMOOTH_WINDOW = 3
LERP_ALPHA = 0.35
SLEEP_NO_HAND = 0.05
DEBUG_DRAW = False
SHOW_FPS_ON_STATUS = True
PREVIEW_W, PREVIEW_H = 400, 300
MARGIN = 5

# ====== Mediapipe hands ======
cap = None
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.6)
mp_draw = mp.solutions.drawing_utils

# ====== Helpers ======
def is_finger_extended(lm, tip_id):
    return lm[tip_id].y < lm[tip_id - 2].y

def count_fingers_up(lm):
    return sum(is_finger_extended(lm, i) for i in (8, 12, 16, 20))

def lerp(a, b, alpha):
    return a + (b - a) * alpha

# ====== State ======
running = False
preview_on = False
status_text = "Idle"
control_mode = False
pin_on = False
preview_win = None
preview_label = None
preview_pin_on = False
preview_pin_btn = None
x_min, x_max, y_min, y_max = 0.2, 0.8, 0.2, 0.8

# Gesture state
last_cx, last_time = None, None
open_start = None
slide_active = True
last_swipe_time = 0
swipe_cooldown = 0.8
last_zoom_time = 0
zoom_cooldown = 0.5
last_click_time = 0
click_cooldown = 0.8
dragging = False
last_cursor_pos = None
cursor_hist = deque(maxlen=SMOOTH_WINDOW)

two_hand_open_start = None
two_hand_hold_time = 0.5
mode_order = ["Cursor", "Slide", "Zoom"]
prev_mode = "Cursor"

# Queues & threads
ui_queue = SimpleQueue()
frame_queue = Queue(maxsize=1)
cursor_queue = SimpleQueue()
zoom_queue = SimpleQueue()

cam_thread = None
det_thread = None
cur_thread = None
cursor_running = False

# ====== Threads ======
def zoom_thread():
    while running:
        try:
            cmd = zoom_queue.get(timeout=0.1)
            if cmd == "in":
                try:
                    pyautogui.hotkey("win", "=")
                except:
                    pass
                try:
                    pyautogui.hotkey("win", "add")
                except:
                    pass
            elif cmd == "out":
                try:
                    pyautogui.hotkey("win", "-")
                except:
                    pass
                try:
                    pyautogui.hotkey("win", "subtract")
                except:
                    pass
            elif cmd == "close":
                try:
                    pyautogui.hotkey("win", "esc")
                except:
                    pass
        except:
            pass

def fast_move(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))

def cursor_thread():
    global cursor_running
    cursor_running = True
    while cursor_running:
        last = None
        try:
            while True:
                last = cursor_queue.get_nowait()
        except Empty:
            pass
        if last is not None:
            x, y = last
            fast_move(x, y)
        time.sleep(0.016)

# ====== UI helpers ======
def push_status(text):
    ui_queue.put(("status", text))

def push_frame(frame_bgr):
    ui_queue.put(("frame", frame_bgr))

def set_status(text):
    global status_text
    status_text = text
    status_label.config(text=text)

def set_debug(val: bool):
    global DEBUG_DRAW
    DEBUG_DRAW = val

# ====== Camera reader ======
def camera_reader():
    global cap, running
    push_status("Camera reader started")
    while running and cap is not None and cap.isOpened():
        success, frame = cap.read()
        if not success or frame is None:
            time.sleep(0.003)
            continue
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except Empty:
                pass
        frame_queue.put(frame)
    push_status("Camera reader stopped")

# ====== Main detection loop ======
def run_detection():
    global running, control_mode, last_cx, last_time, open_start
    global slide_active, last_swipe_time, last_zoom_time, last_click_time
    global last_cursor_pos, cursor_hist, two_hand_open_start, dragging

    screen_w, screen_h = pyautogui.size()
    frame_interval = 1.0 / float(TARGET_FPS) if TARGET_FPS > 0 else 0.0333
    fps_avg = deque(maxlen=60)
    next_tick = time.perf_counter()
    last_preview_frame = None

    push_status("Starting detection...")

    while running:
        loop_start = time.perf_counter()
        now = time.perf_counter()
        if now < next_tick:
            time.sleep(next_tick - now)
        next_tick += frame_interval
        if next_tick - now > 2 * frame_interval:
            next_tick = now + frame_interval

        try:
            img = frame_queue.get_nowait()
            last_preview_frame = img
        except Empty:
            if last_preview_frame is None:
                push_status("No camera frame")
                time.sleep(0.005)
                continue
            img = last_preview_frame

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = hands.process(img_rgb)

        # Two-hand cycle
        if result.multi_hand_landmarks and len(result.multi_hand_landmarks) >= 2:
            h1, h2 = result.multi_hand_landmarks[0], result.multi_hand_landmarks[1]
            if count_fingers_up(h1.landmark) == 4 and count_fingers_up(h2.landmark) == 4:
                if two_hand_open_start is None:
                    two_hand_open_start = now
                elif now - two_hand_open_start >= two_hand_hold_time:
                    current = current_mode.get()
                    idx = mode_order.index(current) if current in mode_order else 0
                    new_mode = mode_order[(idx + 1) % len(mode_order)]
                    current_mode.set(new_mode)
                    push_status(f"Cycle → {new_mode} Mode")
                    two_hand_open_start = None
            else:
                two_hand_open_start = None
        else:
            two_hand_open_start = None

        if result.multi_hand_landmarks:
            for handLms in result.multi_hand_landmarks:
                lm = handLms.landmark
                if DEBUG_DRAW:
                    mp_draw.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)

                wrist = lm[0]
                cx, cy = wrist.x, wrist.y
                now2 = time.perf_counter()

                idx_ext = is_finger_extended(lm, 8)
                mid_ext = is_finger_extended(lm, 12)
                ring_ext = is_finger_extended(lm, 16)
                pink_ext = is_finger_extended(lm, 20)
                fingers_up_count = (1 if idx_ext else 0) + (1 if mid_ext else 0) + (1 if ring_ext else 0) + (1 if pink_ext else 0)

                index_only = idx_ext and not (mid_ext or ring_ext or pink_ext)
                two_fingers_drag = idx_ext and mid_ext and not (ring_ext or pink_ext)
                fist = (fingers_up_count == 0)
                open4 = (fingers_up_count == 4)

                if open4:
                    if open_start is None:
                        open_start = now2
                    elif now2 - open_start > 2:
                        control_mode = False
                        push_status("Reset")
                else:
                    open_start = None

                mode = current_mode.get()

                if mode == "Slide":
                    if fist:
                        if slide_active:
                            slide_active = False
                            push_status("Slide Paused")
                    else:
                        if not slide_active and fingers_up_count > 0:
                            slide_active = True
                            push_status("Slide Active")

                    if slide_active:
                        if last_cx is not None and last_time is not None:
                            dt = now2 - last_time
                            dx = cx - last_cx
                            speed = dx / dt if dt > 0 else 0
                            if abs(speed) > 1.5 and (now2 - last_swipe_time) > swipe_cooldown:
                                if speed > 0:
                                    pyautogui.press("right")
                                    push_status("Next Slide")
                                else:
                                    pyautogui.press("left")
                                    push_status("Prev Slide")
                                last_swipe_time = now2
                                last_cx, last_time = None, None
                            else:
                                last_cx, last_time = cx, now2
                        else:
                            last_cx, last_time = cx, now2

                elif mode == "Cursor":
                    if two_fingers_drag:
                        if not dragging:
                            try:
                                pyautogui.mouseDown(button="left")
                                dragging = True
                                push_status("Left Drag")
                            except:
                                pass
                        nx = (cx - x_min) / (x_max - x_min)
                        ny = (cy - y_min) / (y_max - y_min)
                        nx = min(max(nx, 0), 1)
                        ny = min(max(ny, 0), 1)
                        x, y = int(nx * screen_w), int(ny * screen_h)
                        x = min(max(x, MARGIN), screen_w - MARGIN)
                        y = min(max(y, MARGIN), screen_h - MARGIN)

                        cursor_hist.append((x, y))
                        avg_x = int(sum(px for px, _ in cursor_hist) / len(cursor_hist))
                        avg_y = int(sum(py for _, py in cursor_hist) / len(cursor_hist))

                        if last_cursor_pos:
                            sm_x = lerp(last_cursor_pos[0], avg_x, LERP_ALPHA)
                            sm_y = lerp(last_cursor_pos[1], avg_y, LERP_ALPHA)
                            cursor_queue.put((sm_x, sm_y))
                            last_cursor_pos = (sm_x, sm_y)
                        else:
                            cursor_queue.put((avg_x, avg_y))
                            last_cursor_pos = (avg_x, avg_y)

                    else:
                        if dragging:
                            try:
                                pyautogui.mouseUp(button="left")
                            except:
                                pass
                            dragging = False
                            push_status("Drag End")

                        if index_only and (time.perf_counter() - last_click_time) > click_cooldown:
                            if last_cursor_pos:
                                pyautogui.click(int(last_cursor_pos[0]), int(last_cursor_pos[1]))
                            else:
                                pyautogui.click()
                            push_status("Left Click")
                            last_click_time = time.perf_counter()
                        else:
                            if fist and not control_mode:
                                control_mode = True
                                push_status("Mouse Control")
                            elif (not fist) and control_mode and not index_only:
                                control_mode = False
                                push_status("Released")

                            if control_mode and not index_only:
                                nx = (cx - x_min) / (x_max - x_min)
                                ny = (cy - y_min) / (y_max - y_min)
                                nx = min(max(nx, 0), 1)
                                ny = min(max(ny, 0), 1)
                                x, y = int(nx * screen_w), int(ny * screen_h)
                                x = min(max(x, MARGIN), screen_w - MARGIN)
                                y = min(max(y, MARGIN), screen_h - MARGIN)

                                cursor_hist.append((x, y))
                                avg_x = int(sum(px for px, _ in cursor_hist) / len(cursor_hist))
                                avg_y = int(sum(py for _, py in cursor_hist) / len(cursor_hist))

                                if last_cursor_pos:
                                    sm_x = lerp(last_cursor_pos[0], avg_x, LERP_ALPHA)
                                    sm_y = lerp(last_cursor_pos[1], avg_y, LERP_ALPHA)
                                    cursor_queue.put((sm_x, sm_y))
                                    last_cursor_pos = (sm_x, sm_y)
                                else:
                                    cursor_queue.put((avg_x, avg_y))
                                    last_cursor_pos = (avg_x, avg_y)

                elif mode == "Zoom":
                    thumb_tip = lm[4]
                    index_tip = lm[8]
                    middle_tip = lm[12]

                    dist_index = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
                    dist_middle = math.hypot(thumb_tip.x - middle_tip.x, thumb_tip.y - middle_tip.y)
                    pinch_threshold = 0.05

                    if fist:
                        nx = (cx - x_min) / (x_max - x_min)
                        ny = (cy - y_min) / (y_max - y_min)
                        nx = min(max(nx, 0), 1)
                        ny = min(max(ny, 0), 1)
                        x, y = int(nx * screen_w), int(ny * screen_h)
                        x = min(max(x, MARGIN), screen_w - MARGIN)
                        y = min(max(y, MARGIN), screen_h - MARGIN)

                        cursor_hist.append((x, y))
                        avg_x = int(sum(px for px, _ in cursor_hist) / len(cursor_hist))
                        avg_y = int(sum(py for _, py in cursor_hist) / len(cursor_hist))

                        if last_cursor_pos:
                            sm_x = lerp(last_cursor_pos[0], avg_x, LERP_ALPHA)
                            sm_y = lerp(last_cursor_pos[1], avg_y, LERP_ALPHA)
                            cursor_queue.put((sm_x, sm_y))
                            last_cursor_pos = (sm_x, sm_y)
                        else:
                            cursor_queue.put((avg_x, avg_y))
                            last_cursor_pos = (avg_x, avg_y)

                        push_status("Cursor Control")

                    elif dist_index < pinch_threshold and (time.perf_counter() - last_zoom_time) > zoom_cooldown and not fist:
                        zoom_queue.put("in")
                        push_status("Zoom In")
                        last_zoom_time = time.perf_counter()

                    elif dist_middle < pinch_threshold and (time.perf_counter() - last_zoom_time) > zoom_cooldown and not fist:
                        zoom_queue.put("out")
                        push_status("Zoom Out")
                        last_zoom_time = time.perf_counter()

                    elif count_fingers_up(lm) == 4:
                        push_status("Zoom Paused")

        else:
            push_status("No Hand Detected")
            time.sleep(SLEEP_NO_HAND)

        if preview_on:
            disp = cv2.resize(img, (PREVIEW_W, PREVIEW_H))
            h, w, _ = disp.shape
            x1, y1 = int(x_min * w), int(y_min * h)
            x2, y2 = int(x_max * w), int(y_max * h)
            overlay = disp.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (255, 0, 0), -1)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
            disp = cv2.addWeighted(overlay, 0.18, disp, 0.82, 0)
            cv2.rectangle(disp, (x1, y1), (x2, y2), (255, 0, 0), 2)
            push_frame(disp)

        dt = time.perf_counter() - loop_start
        fps = 1.0 / dt if dt > 0 else 0.0
        fps_avg.append(fps)
        if SHOW_FPS_ON_STATUS and len(fps_avg) >= 10:
            ui_queue.put(("fps", sum(fps_avg) / len(fps_avg)))

    push_status("Stopped")

# ====== GUI ======
def start_detection():
    global running, cap, cam_thread, det_thread, cur_thread, cursor_running
    if not running:
        if cap is None or not cap.isOpened():
            try:
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            except:
                cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

        with frame_queue.mutex:
            frame_queue.queue.clear()
        while not cursor_queue.empty():
            try:
                cursor_queue.get_nowait()
            except Empty:
                break

        running = True

        if not cursor_running:
            cur_thread = threading.Thread(target=cursor_thread, daemon=True)
            cur_thread.start()

        threading.Thread(target=zoom_thread, daemon=True).start()

        cam_thread = threading.Thread(target=camera_reader, daemon=True)
        cam_thread.start()

        det_thread = threading.Thread(target=run_detection, daemon=True)
        det_thread.start()

        set_status("Starting...")

def stop_detection():
    global running, cursor_running, dragging
    running = False
    cursor_running = False
    try:
        if current_mode.get() == "Zoom":
            zoom_queue.put("close")
    except:
        pass
    if dragging:
        try:
            pyautogui.mouseUp(button="left")
        except:
            pass
        dragging = False
    set_status("Stopped")

# Preview window helpers
def create_preview_window():
    global preview_win, preview_label, preview_pin_btn
    if preview_win is not None:
        return
    preview_win = tk.Toplevel(root)
    preview_win.title("Camera Preview")
    preview_win.configure(bg="#1E1E1E")
    preview_win.geometry(f"{PREVIEW_W+40}x{PREVIEW_H+100}")
    preview_win.wm_attributes("-topmost", preview_pin_on)

    header = tk.Frame(preview_win, bg="#1E1E1E")
    header.pack(fill="x", pady=6)
    title = tk.Label(header, text="Live Preview", font=("Segoe UI", 12, "bold"), bg="#1E1E1E", fg="white")
    title.pack(side="left", padx=10)

    def toggle_preview_pin():
        global preview_pin_on
        preview_pin_on = not preview_pin_on
        if preview_win is not None:
            preview_win.wm_attributes("-topmost", preview_pin_on)
        preview_pin_btn.config(text="Unpin" if preview_pin_on else "Pin Top")

    preview_pin_btn = ttk.Button(header, text="Unpin" if preview_pin_on else "Pin Top", style="Rounded.TButton", command=toggle_preview_pin, width=12)
    preview_pin_btn.pack(side="right", padx=8)

    preview_label = tk.Label(preview_win, bg="#1E1E1E")
    preview_label.pack(padx=10, pady=10)

    def on_close():
        global preview_on
        preview_on = False
        close_preview_window()
        preview_btn.config(text="Show Preview")
    preview_win.protocol("WM_DELETE_WINDOW", on_close)

def close_preview_window():
    global preview_win, preview_label
    try:
        if preview_win is not None:
            preview_win.destroy()
    except:
        pass
    preview_win = None
    preview_label = None

def toggle_preview():
    global preview_on
    preview_on = not preview_on
    if preview_on:
        create_preview_window()
        preview_btn.config(text="Hide Preview")
    else:
        close_preview_window()
        preview_btn.config(text="Show Preview")

def toggle_pin():
    global pin_on
    pin_on = not pin_on
    root.wm_attributes("-topmost", pin_on)
    pin_btn.config(text="Unpin" if pin_on else "Pin Top")

def show_help():
    help_text = """
Global:
- Two open hands ~0.5s -> cycle mode
Slide Mode:
- Swipe -> change slide
Cursor Mode:
- Fist -> control cursor
- Index only -> click
- Index+Middle -> drag
Zoom Mode:
- Uses Windows Magnifier
- Thumb+Index -> Zoom In
- Thumb+Middle -> Zoom Out
"""
    messagebox.showinfo("Help", help_text)

def finalize_window_size():
    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    root.geometry(f"{w}x{h}")
    root.minsize(w, h)
    root.maxsize(w, h)
    root.resizable(False, False)

# UI pump
last_fps = None

def set_last_fps(v):
    global last_fps
    last_fps = v
    if SHOW_FPS_ON_STATUS:
        txt = status_label.cget("text").split("|")[0].strip()
        status_label.config(text=f"{txt}  |  Det FPS ~ {last_fps:.1f}")

def ui_pump():
    try:
        while True:
            kind, payload = ui_queue.get_nowait()
            if kind == "status":
                if SHOW_FPS_ON_STATUS and last_fps is not None:
                    status_label.config(text=f"{payload}  |  Det FPS ~ {last_fps:.1f}")
                else:
                    status_label.config(text=payload)
            elif kind == "frame":
                if preview_on and preview_label is not None and preview_win is not None:
                    frame_bgr = payload
                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    img_tk = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
                    preview_label.config(image=img_tk)
                    preview_label.image = img_tk
            elif kind == "fps":
                set_last_fps(payload)
    except:
        pass
    finally:
        interval_ms = int(1000 / PREVIEW_FPS) if PREVIEW_FPS > 0 else 33
        root.after(interval_ms, ui_pump)

def on_exit():
    global cap, running, cursor_running, dragging, preview_on
    try:
        running = False
        cursor_running = False
        time.sleep(0.1)
        if cap is not None:
            try:
                cap.release()
            except:
                pass
        try:
            zoom_queue.put("close")
        except:
            pass
        if dragging:
            try:
                pyautogui.mouseUp(button="left")
            except:
                pass
            dragging = False
        preview_on = False
        try:
            close_preview_window()
        except:
            pass
    finally:
        try:
            root.destroy()
        except:
            pass

# ====== Tkinter UI setup ======
root = tk.Tk()
root.title("Hand Gesture Presentation Control")
root.configure(bg="#1E1E1E")

current_mode = tk.StringVar(value="Cursor")
current_mode.trace("w", lambda *args: on_mode_change())

style = ttk.Style()
style.theme_use("clam")
style.configure("Rounded.TButton", font=("Segoe UI", 12), padding=10, relief="flat", background="#2D2D2D", foreground="white")
style.map("Rounded.TButton", background=[("active", "#3E3E3E")], relief=[("pressed", "sunken")])

content = tk.Frame(root, bg="#1E1E1E")
content.pack(side="top", fill="both", padx=10, pady=8)

title_label = tk.Label(content, text="Hand Gesture Presentation Control", font=("Segoe UI", 16, "bold"), bg="#1E1E1E", fg="white")
title_label.pack(pady=(2, 6))

status_label = tk.Label(content, text="Idle", font=("Segoe UI", 13), bg="#1E1E1E", fg="#00FFAA")
status_label.pack(pady=(0, 6))

debug_frame = tk.Frame(content, bg="#1E1E1E")
debug_frame.pack(pady=4)
debug_var = tk.IntVar(value=1 if DEBUG_DRAW else 0)
debug_chk = ttk.Checkbutton(debug_frame, text="Debug landmarks", command=lambda: set_debug(bool(debug_var.get())), variable=debug_var)
debug_chk.pack(side=tk.LEFT, padx=5)

btn_frame = tk.Frame(content, bg="#1E1E1E")
btn_frame.pack(pady=6)

start_btn = ttk.Button(btn_frame, text="Start", style="Rounded.TButton", command=start_detection, width=12)
start_btn.grid(row=0, column=0, padx=6, pady=4)

stop_btn = ttk.Button(btn_frame, text="Stop", style="Rounded.TButton", command=stop_detection, width=12)
stop_btn.grid(row=0, column=1, padx=6, pady=4)

preview_btn = ttk.Button(btn_frame, text="Show Preview", style="Rounded.TButton", command=toggle_preview, width=26)
preview_btn.grid(row=1, column=0, padx=6, pady=4, columnspan=2)

pin_btn = ttk.Button(btn_frame, text="Pin Top", style="Rounded.TButton", command=toggle_pin, width=26)
pin_btn.grid(row=2, column=0, padx=6, pady=4, columnspan=2)

help_btn = ttk.Button(btn_frame, text="Help", style="Rounded.TButton", command=show_help, width=26)
help_btn.grid(row=3, column=0, padx=6, pady=4, columnspan=2)

exit_btn = ttk.Button(btn_frame, text="Exit", style="Rounded.TButton", command=on_exit, width=26)
exit_btn.grid(row=4, column=0, padx=6, pady=4, columnspan=2)

roi_label = tk.Label(content, text="ROI (Control Area %)", font=("Segoe UI", 11), bg="#1E1E1E", fg="white")
roi_label.pack(pady=(6, 2))

roi_slider = tk.Scale(content, from_=30, to=100, orient="horizontal", length=360, command=lambda v: update_roi(), bg="#1E1E1E", fg="white", troughcolor="#2D2D2D", highlightthickness=0)
roi_slider.set(60)
roi_slider.pack(pady=(0, 4))

mode_bar = tk.Frame(root, bg="#1E1E1E")
mode_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

mode_buttons = {}

def _apply_mode_button_styles(active):
    for m, btn in mode_buttons.items():
        if m == active:
            btn.state(["pressed"])
        else:
            btn.state(["!pressed"])

def set_mode(new_mode: str):
    if current_mode.get() != new_mode:
        current_mode.set(new_mode)
    else:
        _apply_mode_button_styles(new_mode)
    set_status(f"Switched to {new_mode} Mode")

def _make_mode_button(text, mode_name):
    btn = ttk.Button(mode_bar, text=text, style="Rounded.TButton", command=lambda: set_mode(mode_name), width=12)
    btn.pack(side=tk.LEFT, padx=6)
    mode_buttons[mode_name] = btn

_make_mode_button("Cursor", "Cursor")
_make_mode_button("Slide", "Slide")
_make_mode_button("Zoom", "Zoom")

def on_mode_change():
    global control_mode, last_cx, last_time, open_start, slide_active, cursor_hist, prev_mode, dragging
    new_mode = current_mode.get()

    if prev_mode == "Zoom" and new_mode != "Zoom":
        try:
            zoom_queue.put("close")
        except:
            pass
    if new_mode == "Zoom":
        try:
            zoom_queue.put("in")
        except:
            pass

    control_mode = False
    last_cx, last_time, open_start = None, None, None
    slide_active = True
    cursor_hist.clear()

    if dragging:
        try:
            pyautogui.mouseUp(button="left")
        except:
            pass
        dragging = False

    prev_mode = new_mode
    _apply_mode_button_styles(new_mode)

_apply_mode_button_styles("Cursor")
root.after(int(1000 / PREVIEW_FPS), ui_pump)
finalize_window_size()
root.protocol("WM_DELETE_WINDOW", on_exit)
root.mainloop()
