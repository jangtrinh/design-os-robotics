# Implementation Plan — Spec 04: Embodied Reflex & 60FPS Spring Engine (`04-embodied-reflex-and-native-60fps`)

## 1. Kiến trúc & File Phạm vi (Scope)
- **60FPS Spring-Damper, Lip-Sync & Reflex Engine**: [`tools/mochi-soul-engine/reflex_60fps.py`](file:///Users/jangtrinh/Products/design-os-robotics/tools/mochi-soul-engine/reflex_60fps.py)
- **Generated ESP-IDF C++17 Header**: [`tools/mochi-soul-engine/mochi_face_60fps.hpp`](file:///Users/jangtrinh/Products/design-os-robotics/tools/mochi-soul-engine/mochi_face_60fps.hpp) (`3,898 bytes`, `alignas(64) MochiFaceState`)
- **Generated 60FPS Morphing + Lip-Sync Demo GIF**: `/Users/jangtrinh/.gemini/antigravity/brain/32f1ac36-6292-41f1-ae0c-a80ad0e02a34/mochi_60fps_spring_transition.gif` (`21.66 KB`, 48 frames)
- **Benchmark Report Output**: [`plans/reports/benchmark-reflex-60fps.json`](file:///Users/jangtrinh/Products/design-os-robotics/plans/reports/benchmark-reflex-60fps.json)

## 2. Danh sách Công việc Nguyên tử (Atomic Checklist)

- [x] **Task 4.1**: Hiện thực hóa `SpringFaceController` (12-DOF Spring-Damper Physics ở `60 Hz`, `2.36 µs/frame`), `AudioRmsLipSync` (`16kHz` PCM envelope follower, $r = 0.9592$), và `ProximityReflexRouter` (`HC-SR04` distance + MCP actuator hooks, `1.01 µs/eval`) trong [`tools/mochi-soul-engine/reflex_60fps.py`](file:///Users/jangtrinh/Products/design-os-robotics/tools/mochi-soul-engine/reflex_60fps.py).
- [x] **Task 4.2**: Sinh tự động file [`tools/mochi-soul-engine/mochi_face_60fps.hpp`](file:///Users/jangtrinh/Products/design-os-robotics/tools/mochi-soul-engine/mochi_face_60fps.hpp) (`C++17` `constexpr` 21-emotion parameter table + `64-byte` `MochiFaceState` struct) và render ảnh động minh họa `mochi_60fps_spring_transition.gif`.
- [x] **Task 4.3 (Verification Gate)**: Chạy `python3 tools/mochi-soul-engine/reflex_60fps.py benchmark` kiểm thử toàn bộ `420/420` cặp chuyển trạng thái (`21x20`, overshoot `6.77%`), đo hệ số tương quan nhép môi $r = 0.9592$, và nghiệm thu `AC-01 PASS`, `AC-02 PASS`, `AC-03 PASS`.
