# Use Cases & Acceptance Criteria — Spec 04 (`04-embodied-reflex-and-native-60fps`)

## 1. Use Cases

### UC-01: Nội suy Vật lý Lò xo 60Hz Giữa 21x21 Trạng thái (`Spring-Damper Morphing`)
- **Actor**: `SpringFaceController.step_60hz(dt=1/60)`
- **Happy Path**:
  1. Mỗi trạng thái trong 21 biểu cảm được biểu diễn bằng một vector đích 12 chiều $\mathbf{X}_{\text{target}} \in \mathbb{R}^{12}$ (`gaze_x`, `gaze_y`, `open_l`, `open_r`, `scale_l`, `scale_r`, `slope_l`, `slope_r`, `happy_cheek`, `mouth_curve`, `mouth_open`, `blush_opa`).
  2. Khi đổi cảm xúc, hệ phương trình lò xo cập nhật vận tốc $\mathbf{V}$ và vị trí $\mathbf{X}$ mỗi `16.67 ms` (`60 FPS`).

### UC-02: Nhép Môi Thời Gian Thực (`Audio RMS Lip-Sync`) & Phản Xạ Khoảng Cách (`HC-SR04 Reflex`)
- **Actor**: `EmbodiedReflexEngine`
- **Happy Path**:
  1. Nhận khung mẫu âm thanh PCM `16kHz` (`266 samples` / frame `60Hz`), tính căn bậc hai trung bình bình phương (RMS) và lọc thông thấp bất đối xứng (`attack = 0.65`, `release = 0.25`) để điều khiển `mouth_open`.
  2. Nhận khoảng cách $d$ (`cm`) từ cảm biến siêu âm: khi người dùng tiến vào $< 45\text{ cm}$, hai mắt hơi hội tụ vào trong (`vergence`), mở to `scale=1.15`, tăng độ sáng màn hình lên `100%` (`self.screen.set_brightness`) và chuyển sang `happy` / `loving`.

---

## 2. Acceptance Criteria (Gherkin)

```gherkin
Scenario: AC-01 — Hiệu năng vật lý lò xo 60Hz (< 20 us/frame) và hội tụ ổn định trên toàn bộ 420 cặp chuyển trạng thái
  Given bộ điều khiển SpringFaceController với 21 vector trạng thái chuẩn
  When kiểm thử toàn bộ 21 x 20 = 420 cặp chuyển trạng thái cảm xúc ở 60 FPS
  Then 100% (420/420) cặp chuyển trạng thái phải hội tụ về sai số < 0.01 trong vòng <= 30 frames (500 ms)
  And độ vọt lố đàn hồi (overshoot) phải nằm trong dải tự nhiên [2.0%, 12.0%]
  And thời gian tính toán trung bình phải < 20.0 us / frame

Scenario: AC-02 — Đồng bộ nhép môi Audio RMS Lip-Sync (Correlation r > 0.95, Latency < 25 us)
  Given luồng âm thanh tiếng nói giả lập gồm 5 âm tiết xen kẽ khoảng lặng ở tần số 16kHz
  When chạy bộ giải mã RMS Lip-Sync ở 60Hz
  Then hệ số tương quan Pearson (r) giữa đường bao năng lượng âm thanh và độ mở miệng phải > 0.95
  And khi âm thanh im lặng (RMS = 0), mouth_open phải đóng về < 0.02 trong <= 6 frames (100 ms)

Scenario: AC-03 — Phản xạ khoảng cách HC-SR04 và sinh mã C++17 Header-Only hợp lệ
  Given khoảng cách người dùng giảm từ 150 cm xuống 30 cm
  When EmbodiedReflexEngine xử lý tín hiệu khoảng cách
  Then phản xạ phải kích hoạt trạng thái chào đón ("happy" / "loving") + gói MCP tăng độ sáng màn hình trong 1 chu kỳ (< 1 ms)
  And file "tools/mochi-soul-engine/mochi_face_60fps.hpp" phải được xuất ra đầy đủ cấu trúc 64-byte State Vector và hàm step_60hz()
```
