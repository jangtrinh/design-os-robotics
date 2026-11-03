# Use Cases & Acceptance Criteria — Spec 02 (`02-mochi-soul-engine-core`)

## 1. Use Cases

### UC-01: Vòng lặp Sinh học 4D & Ánh xạ Đủ 21 Biểu cảm (`Homeostasis & 21-State Emotion Router`)
- **Actor**: `MochiSoulEngine.step(dt_minutes, current_hour, event=None)`
- **Precondition**: Khởi tạo hoặc đọc trạng thái từ `profiles/example-esp32s3-n16r8/mochi_soul.db`.
- **Happy Path**:
  1. Cập nhật `Energy` ($E \in [0, 100]$): Giảm `-3.5 / giờ` khi thức, tăng `+18.0 / giờ` khi trong `Quiet Hours (23:00–07:30)` hoặc sự kiện `rest`.
  2. Cập nhật `Hunger/Curiosity` ($H \in [0, 100]$): Tăng `+5.5 / giờ` khi thức; giảm `-35.0` khi nhận sự kiện `feed_knowledge` (kèm biểu cảm `delicious` $\rightarrow$ `happy`).
  3. Cập nhật `Bond` ($B \in [0, 100]$): Tăng khi có tương tác (`chat`, `praise`, `play`), giảm nhẹ `-1.2 / giờ` nếu bị bỏ rơi liên tục $> 4\text{ giờ}$.
  4. Tính toán вектор cảm xúc `(Valence, Arousal)` và chọn chính xác 1 trong **21 biểu cảm `Procedural Mochi-21`**.

### UC-02: Giả lập 24 Giờ & Đo Hiệu năng Định lượng Từ Xa (`Remote Simulation & Perf Benchmark`)
- **Actor**: Developer (Remote) chạy `python3 tools/mochi-soul-engine/engine.py benchmark`
- **Happy Path**:
  1. Chạy giả lập `1,440 ticks` (`24 giờ` sinh học) kết hợp kịch bản tương tác mẫu trong ngày.
  2. Đo thời gian xử lý trung bình mỗi tick (`µs/tick`), thời gian ghi đọc `SQLite` (`µs/tx`), mức bao phủ biểu cảm (số trạng thái được kích hoạt trong 21 trạng thái), và kiểm chứng `0` lần phát âm thanh chủ động trong khung giờ `23:00–07:30`.

---

## 2. Acceptance Criteria (Gherkin)

```gherkin
Scenario: AC-01 — Bảo toàn miền giá trị [0, 100] và ánh xạ hợp lệ sang 21 trạng thái Procedural Mochi-21
  Given động cơ MochiSoulEngine chạy qua 1,440 bước thời gian (24 giờ) với các sự kiện ngẫu nhiên và định sẵn
  When kiểm tra đầu ra của mọi bước thời gian
  Then Energy, Hunger, và Bond phải luôn nằm trong đoạn [0.0, 100.0]
  And tên biểu cảm trả về phải luôn thuộc tập 21 tên chuẩn của Procedural Mochi-21
  And tối thiểu 15/21 trạng thái cảm xúc khác nhau phải được kích hoạt khi chạy qua bộ kịch bản kiểm thử toàn diện

Scenario: AC-02 — Tuân thủ tuyệt đối Quiet Hours (23:00 - 07:30) và Cooldown (>= 45 phút)
  Given MochiSoulEngine đang chạy trong khoảng thời gian từ 23:00 đến 07:30 sáng hôm sau
  When bất kỳ chỉ số Hunger hoặc Lonely nào vượt ngưỡng
  Then số lần phát Proactive Impulse có âm thanh (notify_voice) trong khung 23:00-07:30 phải bằng 0 tuyệt đối
  And khoảng cách giữa 2 lần Proactive Impulse liên tiếp ban ngày phải >= 45 phút

Scenario: AC-03 — Hiệu năng xử lý siêu nhanh (< 500 us / tick) và lưu trữ SQLite bền vững
  Given công cụ benchmark "python3 tools/mochi-soul-engine/engine.py benchmark" được thực thi
  When đo 1,440 bước tính toán + ghi SQLite WAL
  Then độ trễ tính toán toán học trung bình phải < 50 us/tick (và < 500 us/tick khi có ghi SQLite)
```
