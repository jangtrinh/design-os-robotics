# Implementation Plan — Spec 01: Procedural Mochi-21 Avatar Pack (`01-procedural-mochi-21-avatar`)

## 1. Kiến trúc & File Phạm vi (Scope)
- **Generator & Packer**: [`tools/cook-procedural-avatar.py`](../../../tools/cook-procedural-avatar.py)
- **Performance Benchmark Suite**: [`tools/benchmark-avatar-perf.py`](../../../tools/benchmark-avatar-perf.py) & [`plans/reports/benchmark-avatar-perf.json`](../../reports/benchmark-avatar-perf.json)
- **Generated Assets**:
  - 21 file GIF (`240x240` viewport-matched trên nền `#000000` `240x320`, 12–16 frames mỗi file): `themes/procedural-mochi/{emotion}.gif` (`250,580 bytes` / `244.71 KB` tổng cộng)
  - Bảng xem trước `7x3`: `themes/procedural-mochi/procedural_mochi_21_preview.png`
  - Image nạp Flash (`0xAA0000`): `themes/procedural-mochi-fullvien-240x320.bin` (built locally, git-ignored) (`2,092,592 bytes`, `1.04 MB` compressed, checksum `0x5867`, `background_dark.raw` & `background_light.raw` zeroed to `#000000`)
- **Hardware Verifier**: [`tools/robotctl.py`](../../../tools/robotctl.py)

## 2. Danh sách Công việc Nguyên tử (Atomic Checklist)

- [x] **Task 1.1**: Xây dựng bộ dựng hình học tham số 2D (`draw_mochi_face` + boolean eyelid masks + particle FX) cho toàn bộ 21 trạng thái cảm xúc trong [`tools/cook-procedural-avatar.py`](../../../tools/cook-procedural-avatar.py).
- [x] **Task 1.2**: Biên dịch ra 21 file `.gif` (`250,580 bytes` / `244.71 KB` tổng cộng) và xuất bảng preview `7x3` (`procedural_mochi_21_preview.png`).
- [x] **Task 1.3**: Đóng gói `themes/procedural-mochi-fullvien-240x320.bin` (built locally, git-ignored) giữ nguyên `srmodels.bin`, `font_puhui_deepseek_20_4.bin`, xóa sạch `background_dark.raw` / `background_light.raw` về `#000000` (`nonzero_pixel_bytes = 0`), ánh xạ đủ 21 file GIF riêng biệt + khóa `robot_2`, kiểm chứng checksum `0x5867`.
- [x] **Task 1.4**: Xây dựng bộ công cụ đo hiệu năng định lượng [`tools/benchmark-avatar-perf.py`](../../../tools/benchmark-avatar-perf.py) và nạp `themes/procedural-mochi-fullvien-240x320.bin` (built locally, git-ignored) vào địa chỉ `0xAA0000` trên `RoBot.5320` (`/dev/cu.usbmodem*`).
- [x] **Task 1.5 (Verification Gate)**: Chạy `python3 tools/robotctl.py health` xác nhận `8/8 [  OK  ]` và xuất báo cáo định lượng [`plans/reports/benchmark-avatar-perf.json`](../../reports/benchmark-avatar-perf.json).
