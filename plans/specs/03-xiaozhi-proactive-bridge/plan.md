# Implementation Plan — Spec 03: Xiaozhi Proactive Robot Bridge (`03-xiaozhi-proactive-bridge`)

## 1. Kiến trúc & File Phạm vi (Scope)
- **Proactive Bridge, HUD Renderer & Loopback Benchmark**: [`tools/mochi-soul-engine/bridge.py`](../../../tools/mochi-soul-engine/bridge.py)
- **Generated HUD Preview Artifact**: `plans/reports/mochi_hud_card_240x320.png`
- **Benchmark Report Output**: [`plans/reports/benchmark-proactive-bridge.json`](../../reports/benchmark-proactive-bridge.json)

## 2. Danh sách Công việc Nguyên tử (Atomic Checklist)

- [x] **Task 3.1**: Xây dựng bộ dựng thẻ **Tamagotchi HUD Card `240x320`** (`render_hud_card_png` vẽ trực tiếp trên `Mode P` 8-bit) kết hợp khuôn mặt `Procedural Mochi-21` với 4 thanh chỉ số sinh học (`Energy`, `Curiosity`, `Bond`, `Mood`) và nhật ký ký ức (`0.88 ms/card`, `2,723 bytes` / `2.66 KB`).
- [x] **Task 3.2**: Hiện thực hóa bộ đóng gói giao thức `MochiProactiveBridge` và bộ kiểm chứng hợp ngữ `FirmwareProtocolValidator` (mô phỏng chính xác `0x4202c0c8..0x4202c711` của `ota_1`, `1.01 µs/packet`).
- [x] **Task 3.3 (Verification Gate)**: Chạy `python3 tools/mochi-soul-engine/bridge.py benchmark` kiểm thử Loopback HTTP (`0.54 ms` RTT), xác nhận `AC-01 PASS`, `AC-02 PASS`, `AC-03 PASS`.
