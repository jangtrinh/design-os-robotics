# Implementation Plan — Spec 02: Mochi-Soul Engine Core (`02-mochi-soul-engine-core`)

## 1. Kiến trúc & File Phạm vi (Scope)
- **Core Engine & CLI**: [`tools/mochi-soul-engine/engine.py`](../../../tools/mochi-soul-engine/engine.py)
- **Database File**: `profiles/example-esp32s3-n16r8/mochi_soul.db` (`SQLite WAL`)
- **Benchmark Report Output**: [`plans/reports/benchmark-mochi-soul-engine.json`](../../reports/benchmark-mochi-soul-engine.json)

## 2. Danh sách Công việc Nguyên tử (Atomic Checklist)

- [x] **Task 2.1**: Hiện thực hóa lớp `MochiSoulEngine` trong [`tools/mochi-soul-engine/engine.py`](../../../tools/mochi-soul-engine/engine.py) với phương trình cân bằng nội môi 4D (`Energy`, `Hunger`, `Bond`, `Valence/Arousal`), bộ định tuyến đủ **21 trạng thái cảm xúc `Procedural Mochi-21`**, và hệ thống cấp độ tiến hóa (`Stage 1 -> Stage 4`).
- [x] **Task 2.2**: Tích hợp lớp lưu trữ bền vững `SQLite` (`WAL mode`) lưu bảng `soul_state`, `episodic_memories`, và `proactive_impulses`.
- [x] **Task 2.3 (Verification Gate)**: Xây dựng chế độ kiểm thử & đo hiệu năng định lượng (`python3 tools/mochi-soul-engine/engine.py benchmark`) kiểm chứng toàn bộ `AC-01` (`21/21` emotions, `0` bounds violations), `AC-02` (`0` Quiet Hours violations, `0` Cooldown violations), `AC-03` (`0.47 µs/tick` math, `2.52 µs/tx` SQLite WAL).
