# Use Cases & Acceptance Criteria — Spec 03 (`03-xiaozhi-proactive-bridge`)

## 1. Use Cases

### UC-01: Kết xuất Thẻ Tamagotchi HUD `240x320` Bằng Code (`Procedural HUD Card`)
- **Actor**: `MochiProactiveBridge.render_hud_card(soul_state)`
- **Precondition**: Nhận đối tượng `SoulState` từ `MochiSoulEngine`.
- **Happy Path**:
  1. Dựng ảnh `240x320` nền `#000000` gồm: Header cấp độ tiến hóa (`Stage`), khung avatar Mochi ở biểu cảm hiện tại (`s.emotion`), 4 thanh tiến trình (`ENERGY`, `CURIOSITY`, `BOND`, `MOOD`), và nhật ký ký ức gần nhất.
  2. Xuất ra file PNG tối ưu bảng màu (`< 12 KB`) tại `plans/reports/mochi_hud_card_240x320.png` (và phục vụ qua HTTP nội bộ cho `self.screen.preview_image`).

### UC-02: Đóng gói & Kiểm chứng 5 Gói Giao thức Chủ động Khớp Mã Máy `ota_1`
- **Actor**: `FirmwareProtocolValidator.validate_incoming_json(payload)` (mô phỏng chính xác `0x4202c0c8..0x4202c711`)
- **Happy Path**:
  1. Gói `"notify"` có `"audio_url"` hợp lệ và mảng `"subtitles"` gồm các phần tử `{"start_ms": int >= 0, "text": str}`.
  2. Gói `"alert"` có đủ 3 chuỗi `"status"`, `"message"`, `"emotion"` (thuộc 21 trạng thái).
  3. Gói `"llm"` có `"emotion"` thuộc 21 trạng thái.
  4. Gói `"mcp"` có `"payload"` chuẩn JSON-RPC 2.0 gọi `self.screen.preview_image`!

---

## 2. Acceptance Criteria (Gherkin)

```gherkin
Scenario: AC-01 — Tuân thủ 100% hợp đồng mã máy Application::OnIncomingJson (0x4202c0c8..0x4202c711)
  Given bộ giả lập parser của firmware ota_1 (FirmwareProtocolValidator)
  When kiểm tra tất cả 21 gói "llm", 21 gói "alert", gói "notify", và gói "mcp" (self.screen.preview_image) do Bridge sinh ra
  Then 100% gói hợp lệ phải được chấp nhận với 0 lỗi
  And 100% gói cố tình thiếu trường bắt buộc (như notify thiếu audio_url hoặc alert thiếu status) phải bị phát hiện đúng mã lỗi của firmware

Scenario: AC-02 — Kết xuất thẻ Tamagotchi HUD 240x320 siêu nhẹ (< 15 KB) và siêu nhanh (< 5 ms)
  Given trạng thái hiện tại của MochiSoulEngine
  When gọi hàm render_hud_card_png()
  Then ảnh đầu ra phải có đúng kích thước 240x320 pixel
  And dung lượng file PNG phải < 15,000 bytes
  And thời gian render trung bình phải < 5.0 ms / thẻ

Scenario: AC-03 — Kiểm thử Loopback HTTP + WebSocket End-to-End (< 10 ms RTT)
  Given máy chủ HTTP/Loopback cục bộ đang chạy trong "bridge.py benchmark"
  When thực hiện chu trình đẩy Proactive Impulse + tải ảnh HUD 240x320 qua HTTP
  Then độ trễ toàn trình (End-to-End Loopback RTT) phải < 10.0 ms và khớp SHA-256 của ảnh HUD
```
