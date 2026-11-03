# Brainstorm — Spec 04: Embodied Reflex, Lip-Sync & 60FPS Spring-Damper Engine (`04-embodied-reflex-and-native-60fps`)

## 1. Press Release (Amazon Method)
**Hôm nay, `Mochi-Soul Embodied Reflex & 60FPS Spring Engine` hoàn thiện mảnh ghép cuối cùng của dự án Tamagotchi AI trên `RoBot.5320` — biến 21 trạng thái cảm xúc rời rạc thành một cơ thể sống động liên tục ở `60 FPS` với vật lý lò xo (`Spring-Damper Physics`), nhép môi theo biên độ âm thanh thời gian thực (`Real-Time Audio RMS Lip-Sync`), phản xạ ánh nhìn theo khoảng cách (`HC-SR04 Proximity Gaze`) và xuất mã nguồn `C++17 Header-Only` (`mochi_face_60fps.hpp`) cho `ESP32-S3`.**
Thay vì chuyển đột ngột (hard-cut) khi đổi từ `neutral` sang `shocked` hay `loving`, hệ phương trình dao động điều hòa có cản ($\omega_0 = 18\text{ rad/s}, \zeta = 0.65$) nội suy mượt mà cả 12 tham số khuôn mặt ở `60 Hz` với độ nảy đàn hồi tự nhiên (`~6% overshoot`) như hoạt họa Pixar/Anki Cozmo. Đồng thời, bộ phân tích năng lượng âm thanh RMS điều khiển độ mở miệng khớp từng âm tiết tiếng nói với độ trễ chỉ `< 10 µs/frame`.

## 2. User Stories
- **US-01 (60Hz Spring-Damper Transition across 21x21 States)**: Là người quan sát Mochi, tôi muốn mọi chuyển đổi giữa 21 trạng thái cảm xúc (`420` cặp chuyển trạng thái) đều tuân theo vật lý lò xo $\omega_0 = 18, \zeta = 0.65$, hội tụ trong `< 450 ms` với độ nảy tự nhiên mà chỉ tốn `< 10 µs/frame` tính toán.
- **US-02 (Real-Time Audio RMS Lip-Sync)**: Là người trò chuyện với Mochi, tôi muốn độ mở miệng (`mouth_open` $\in [0.0, 1.0]$) bám sát đường bao biên độ âm thanh PCM 16kHz (hệ số tương quan $r > 0.95$) để Mochi nhép môi khớp từng từ khi nói.
- **US-03 (Proximity Gaze Reflex & Native C++17 Header)**: Là kỹ sư firmware, tôi muốn có phản xạ khoảng cách từ `HC-SR04` ($d \in [10, 200]\text{ cm}$ điều khiển hội tụ 2 đồng tử + độ sáng màn hình `self.screen.set_brightness` + xung loa/LED `self.loudspeaker.pulse` / `self.led_visualizer`) VÀ một file `mochi_face_60fps.hpp` (`0 KB` Flash asset overhead, `64 bytes` RAM) sẵn sàng nhúng vào ESP-IDF.

## 3. MoSCoW Prioritization

| Priority | Item | Rationale |
|---|---|---|
| **Must (P0)** | Động cơ vật lý lò xo 12 chiều (`60 Hz Spring-Damper`) nội suy giữa toàn bộ 21 trạng thái cảm xúc | Xóa bỏ hoàn toàn hiện tượng cắt cảnh đột ngột giữa các cảm xúc |
| **Must (P0)** | Bộ đồng bộ nhép môi theo năng lượng âm thanh (`Audio RMS Lip-Sync`) + Phản xạ khoảng cách (`Proximity Gaze Reflex`) | Tạo cảm giác sinh vật sống phản ứng tức thời với giọng nói và khoảng cách |
| **Must (P0)** | Xuất module `C++17 Header-Only` (`tools/mochi-soul-engine/mochi_face_60fps.hpp`) + Công cụ đo hiệu năng định lượng (`reflex_60fps.py benchmark`) | Kiểm chứng 100% bằng số liệu và sẵn sàng cho cả chế độ Bridge lẫn Native Firmware |
| **Should (P1)** | Xuất animation mẫu `mochi_60fps_spring_transition.gif` minh họa chuyển cảnh vật lý lò xo + nhép môi | Giúp kiểm chứng trực quan từ xa |
