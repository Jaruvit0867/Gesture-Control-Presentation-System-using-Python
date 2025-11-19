# Gesture Control Presentation System using Python

This project provides a gesture‑based presentation controller using OpenCV, Mediapipe, PyAutoGUI, and Tkinter. You can control slides, move the cursor, and zoom on screen using hand gestures through a webcam.

GitHub Repository: [https://github.com/Jaruvit0867/Gesture-Control-Presentation-System-using-Python](https://github.com/Jaruvit0867/Gesture-Control-Presentation-System-using-Python)

## Installation

### 1. Clone the Repository

```
git clone https://github.com/Jaruvit0867/Gesture-Control-Presentation-System-using-Python.git
cd Gesture-Control-Presentation-System-using-Python
```

### 2. Install Dependencies

Recommended Python version: 3.9–3.11

```
pip install -r requirements.txt
```

If `requirements.txt` is not provided, install manually:

```
pip install opencv-python mediapipe pyautogui pillow
```

## Run the Program

```
python hand_gesture_presentation_control_clean.py
```

## Usage

### Cursor Mode

* Make a fist to activate mouse control.
* Index finger only → left click.
* Index + middle finger → drag.

### Slide Mode

* Swipe left/right to change slides.
* Make a fist to pause slide gestures.

### Zoom Mode

* Thumb + index finger → zoom in.
* Thumb + middle finger → zoom out.

### Quick Mode Switching

* Hold both hands open for about 0.5 seconds to cycle between modes: Cursor → Slide → Zoom

## Notes

* Works best in good lighting conditions.
* Zoom mode uses Windows Magnifier, so this feature is specific to Windows.

## License

MIT License
