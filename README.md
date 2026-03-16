# Gesture-based Presentation Controller

A vision-based hand gesture control system for mouse manipulation and presentations.

## Installation

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Supported Gestures

| Gesture | Action |
|---------|--------|
| **1 Finger** | Move Cursor |
| **2 Fingers** | Drag |
| **5 Fingers** | Swipe Left/Right |
| **Fist** | Pause / Standby |

## Improvements from the Previous Version

### 1. Thread Safety
- Added `threading.Lock` for the `running` state.
- Implemented `queue.Queue` for inter-thread data communication instead of direct access.
- Added lock mechanisms for drag operations.

### 2. Memory Management
- Resolved memory leaks caused by lambda closures.
- Stored `tk_image` references in instance variables to prevent garbage collection issues.
- Added `reset()` methods for proper cleanup.

### 3. Gesture Engine
- **Thumb Detection:** Evaluates X-axis coordinates instead of Y-axis for accurate thumb counting.
- Added `confidence` score evaluation in the results.
- Added `finger_count` evaluation in the results.
- Improved state machine logic for gesture transitions.

### 4. Mouse Controller
- **Adaptive Smoothing:** Dynamically adjusts the smoothing factor based on actual FPS.
- Introduced `min_smooth_factor` and `max_smooth_factor` configurations.
- Ensured thread-safe drag operations.

### 5. UI/UX
- Fixed Unicode escape sequence encoding issues.
- Implemented a loading state during camera initialization.
- Added an error dialog for camera access failures.
- Displayed a finger count indicator directly on the screen.
- Added a state indicator at the top of the interface.
- Included a real-time smooth factor display in the sidebar.

### 6. Performance
- Utilized a frame queue (maxsize=2) to prevent processing backlogs.
- Reduced the camera buffer size for lower latency.
- Implemented automatic frame skipping for outdated frames.

### 7. Code Quality
- Added comprehensive docstrings to all classes and methods.
- Enforced strict type hinting throughout the codebase.
- Refactored constants into dedicated classes.
- Included `# -*- coding: utf-8 -*-` headers.

## File Structure

```
gesture_app/
├── config.py           # Configuration, colors, fonts, dimensions
├── gesture_engine.py   # MediaPipe hand gesture recognition
├── mouse_controller.py # PyAutoGUI mouse control with smoothing
├── ui_renderer.py      # OpenCV/PIL image rendering
├── main.py             # Main application with CustomTkinter UI
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## Configuration

Adjust the parameters in `config.py` to customize the system:

```python
@dataclass
class AppConfig:
    cam_index: int = 0                  # Camera index
    cam_width: int = 1280               # Resolution
    cam_height: int = 720
    
    swipe_dist_threshold: float = 0.15  # Swipe sensitivity
    smooth_factor: float = 5.0          # Mouse smoothing (higher = smoother)
    roi_margin: int = 120               # Working area margin
```

## Known Issues

1. On certain Linux distributions, you may need to install `python3-tk` separately.
2. The `cam_index` might need to be modified depending on the connected camera hardware.

## License

MIT License
