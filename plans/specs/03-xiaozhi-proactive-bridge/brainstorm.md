# Brainstorm — Spec 03: Xiaozhi Proactive Robot Bridge & HUD Renderer (`03-xiaozhi-proactive-bridge`)

## 1. Press Release (Amazon Method)
**Hôm nay, `Mochi-Soul Proactive Bridge` chính thức kết nối não bộ sinh học 4D với phần cứng `RoBot.5320` thông qua 5 giao thức chủ động có sẵn trong firmware `ota_1` (`v2.5.3`) — kèm bộ dựng thẻ HUD Tamagotchi `240x320` (`< 8 KB`) và bộ giả lập máy chủ/thiết bị Loopback đo hiệu năng hoàn toàn tự động.**
Bằng cách dịch ngược chính xác hàm `Application::OnIncomingJson` tại địa chỉ `0x4202c0c8..0x4202c711` của `07-ota1-v2.5.3-0x560000.bin`, cầu nối `tools/mochi-soul-engine/bridge.py` tạo ra các gói tin chuẩn xác tuyệt đối tới từng trường `cJSON`:
- `"type": "alert"` (`0x4202c683`: bắt buộc đủ 3 trường `"status"`, `"message"`, `"emotion"`)
- `"type": "notify"` (`0x4202c0fc`: bắt buộc `"audio_url"` + mảng `"subtitles": [{"start_ms": 0, "text": "..."}]`)
- `"type": "llm"` (`0x4202c569`: đổi ngay lập tức 1 trong 21 biểu cảm `Procedural Mochi-21` qua `"emotion"`)
- `"type": "mcp"` (`0x4202c5de` $\rightarrow$ `0x42026b68`: gọi `self.screen.preview_image` để hiển thị thẻ chỉ số **Tamagotchi HUD `240x320`** trực tiếp lên màn hình LCD!)

## 2. User Stories
- **US-01 (Disassembly-Exact Protocol Contract)**: Là kỹ sư giao thức, tôi muốn mọi gói JSON gửi xuống `RoBot.5320` được kiểm tra hợp lệ theo đúng tập lệnh hợp ngữ `0x4202c0c8..0x4202c711` của `ota_1` trước khi phát đi để không bao giờ gặp cảnh báo `W: Alert command requires status, message and emotion` hay `W: Notify message requires audio_url`.
- **US-02 (Procedural Tamagotchi HUD `240x320`)**: Là người nuôi Mochi, tôi muốn có một thẻ giao diện **Tamagotchi Status Card `240x320`** hiển thị 4 thanh chỉ số (`Energy`, `Hunger`, `Bond`, `Mood`), cấp độ tiến hóa (`Stage 1..4`) và gương mặt Mochi hiện tại để đẩy sang màn hình robot qua `self.screen.preview_image` trong `< 3 ms`.
- **US-03 (Remote Loopback & Latency Benchmark)**: Là người phát triển đang làm việc từ xa, tôi muốn chạy `python3 tools/mochi-soul-engine/bridge.py benchmark` để kiểm thử toàn bộ luồng `Engine -> Bridge -> HTTP Asset Server -> Simulated ota_1 Firmware Parser` và đo độ trễ từng bước (`µs` / `ms`) bằng con số cụ thể.

## 3. MoSCoW Prioritization

| Priority | Item | Rationale |
|---|---|---|
| **Must (P0)** | Bộ đóng gói & kiểm tra hợp đồng giao thức `ota_1` (`notify`, `alert`, `llm`, `mcp:preview_image`, `mcp:Otto`) | Khớp 100% với mã máy tại `0x4202c0c8..0x4202c711` |
| **Must (P0)** | Bộ vẽ thẻ **Tamagotchi HUD Card `240x320`** bằng code (`< 10 KB` PNG, `< 5 ms` render) | Cho phép xem toàn bộ chỉ số sinh học của Mochi trên màn hình `240x320` hoặc từ xa |
| **Must (P0)** | Máy chủ HTTP nội bộ + Bộ giả lập `ota_1` (`OnIncomingJson` emulator) & Benchmark đo latency end-to-end | Kiểm chứng 100% bằng chương trình và số liệu khi làm việc remote |
| **Won't (This Spec)** | Đọc cảm biến khoảng cách `HC-SR04` và chuỗi vũ đạo 6 servo | Thuộc phạm vi **Spec 04 (`04-embodied-reflex-and-native-60fps`)** |
