# AI Control Pro - Gesture-based Presentation Controller

ระบบควบคุมเมาส์และนำเสนอด้วยท่าทางมือผ่านกล้อง

## 🚀 การติดตั้ง

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## ✋ ท่าทางที่รองรับ

| ท่าทาง | การทำงาน |
|--------|----------|
| ☝️ **1 นิ้ว** | เลื่อนเมาส์ |
| ✌️ **2 นิ้ว** | ลาก (Drag) |
| 🖐️ **5 นิ้ว** | Swipe ซ้าย/ขวา |
| ✊ **กำปั้น** | หยุดชั่วคราว |

## 🔧 สิ่งที่ปรับปรุงจากเวอร์ชันเดิม

### 1. Thread Safety
- เพิ่ม `threading.Lock` สำหรับ `running` state
- ใช้ `queue.Queue` สำหรับส่งข้อมูลระหว่าง threads แทน direct access
- เพิ่ม lock สำหรับ drag operations

### 2. Memory Management
- แก้ไข memory leak จาก lambda closures
- เก็บ reference ของ `tk_image` ไว้ใน instance variable
- เพิ่ม `reset()` methods สำหรับ cleanup

### 3. Gesture Engine
- **เพิ่มการนับนิ้วโป้ง** - ตรวจจับแกน X แทน Y
- เพิ่ม `confidence` score ใน result
- เพิ่ม `finger_count` ใน result
- ปรับปรุง state machine logic

### 4. Mouse Controller
- **Adaptive Smoothing** - ปรับค่า smooth ตาม FPS จริง
- เพิ่ม `min_smooth_factor` และ `max_smooth_factor`
- Thread-safe drag operations

### 5. UI/UX
- แก้ไข **Emoji encoding** ใช้ Unicode escape sequences
- เพิ่ม **Loading state** ขณะเปิดกล้อง
- เพิ่ม **Error dialog** เมื่อเปิดกล้องไม่ได้
- แสดง **Finger count indicator** บนหน้าจอ
- แสดง **State indicator** ที่ด้านบน
- เพิ่ม **Smooth factor display** ใน sidebar

### 6. Performance
- ใช้ frame queue (maxsize=2) ป้องกัน backlog
- ลดขนาด buffer ของกล้อง
- Skip frame เก่าอัตโนมัติ

### 7. Code Quality
- เพิ่ม docstrings ทุก class และ method
- ใช้ type hints
- แยก constants ออกมาเป็น classes
- ใช้ `# -*- coding: utf-8 -*-` header

## 📁 โครงสร้างไฟล์

```
gesture_app/
├── config.py          # Configuration, colors, fonts, dimensions
├── gesture_engine.py  # MediaPipe hand gesture recognition
├── mouse_controller.py # PyAutoGUI mouse control with smoothing
├── ui_renderer.py     # OpenCV/PIL image rendering
├── main.py           # Main application with CustomTkinter UI
├── requirements.txt  # Dependencies
└── README.md         # This file
```

## ⚙️ Configuration

แก้ไขค่าใน `config.py`:

```python
@dataclass
class AppConfig:
    cam_index: int = 0              # Camera index
    cam_width: int = 1280           # Resolution
    cam_height: int = 720
    
    swipe_dist_threshold: float = 0.15  # Swipe sensitivity
    smooth_factor: float = 5.0          # Mouse smoothing (higher = smoother)
    roi_margin: int = 120               # Working area margin
```

## 🐛 Known Issues

1. บนบาง Linux distro อาจต้องติดตั้ง `python3-tk` แยก
2. กล้องบางตัวอาจต้องเปลี่ยน `cam_index`

## 📜 License

MIT License
