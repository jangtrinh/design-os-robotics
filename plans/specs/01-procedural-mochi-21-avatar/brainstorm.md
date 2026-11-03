# Brainstorm — Spec 01: Procedural Mochi-21 Avatar Pack (`01-procedural-mochi-21-avatar`)

## 1. Press Release (Amazon Method)
**Hôm nay, `RoBot.5320` chính thức sở hữu bộ mặt `Procedural Mochi-21` — đầy đủ 21 trạng thái cảm xúc riêng biệt 100% ở độ phân giải tràn viền `240x320`, được vẽ hoàn toàn bằng toán học với tổng dung lượng chỉ `244.71 KB` (nhẹ hơn 90.4% so với ảnh GIF truyền thống).**
Trước đây, để nhét vừa phân vùng Flash `0xAA0000` và tránh tràn bộ nhớ, bộ giao diện `Procedural Mochi-21` cắt từ video phải gom 21 trạng thái cảm xúc của Xiaozhi vào chỉ 6 file GIF lặp đi lặp lại (nặng `782.46 KB`), khiến robot biểu lộ cùng một khuôn mặt cho cả `happy`, `winking`, `cool`, `delicious` và `kissy`. Với trình biên dịch hình học tham số [`tools/cook-procedural-avatar.py`](../../../tools/cook-procedural-avatar.py), mỗi cảm xúc trong 21 trạng thái nay có một hoạt cảnh 16 khung hình độc bản (từ kính râm `cool`, mắt trái tim `loving`, thác nước mắt `crying`, mắt lác thè lưỡi `silly` đến bong bóng ngủ `sleepy`) mà tổng dung lượng chỉ bằng 1/3 bộ 6 GIF cũ và giải mã nhanh gấp 4 lần trên CPU `ESP32-S3`.

## 2. User Stories
- **US-01**: Là chủ nhân của `RoBot.5320`, tôi muốn cả 21 trạng thái cảm xúc mà AI trả về (`neutral`, `happy`, `laughing`, `funny`, `sad`, `angry`, `crying`, `loving`, `embarrassed`, `surprised`, `shocked`, `thinking`, `winking`, `cool`, `relaxed`, `delicious`, `kissy`, `confident`, `sleepy`, `silly`, `confused`) đều hiển thị thành **21 khuôn mặt hoạt họa khác nhau hoàn toàn** trên màn hình `240x320` để Mochi biểu cảm tinh tế như một sinh vật sống thực thụ.
- **US-02**: Là kỹ sư hệ thống nhúng, tôi muốn toàn bộ 21 animation `240x320` chiếm dưới `300 KB` Flash và sử dụng bảng màu phẳng 8 màu (`Mode P`) không hạt nhiễu (`dithering = NONE`) để bộ giải mã `lv_gif` trên `ESP32-S3` tốn `< 12%` CPU, không bao giờ làm khựng luồng âm thanh TTS.
- **US-03**: Là người phát triển `Mochi-Soul`, tôi muốn mọi biểu cảm được định nghĩa bằng hàm toán học trong 1 file Python duy nhất (`tools/cook-procedural-avatar.py`) để có thể chỉnh sửa hình dáng mắt/miệng/hiệu ứng và đóng gói lại file `.bin` trong `< 2 giây`.

## 3. MoSCoW Prioritization

| Priority | Item | Rationale |
|---|---|---|
| **Must (P0)** | 21 file GIF `240x240` (12–16 frames/file, hiển thị tràn viền trên màn hình `240x320`) vẽ bằng toán học, mỗi cảm xúc có nét mặt riêng biệt 100% | Xóa bỏ hoàn toàn hiện tượng 15/21 cảm xúc bị dùng chung hình ảnh |
| **Must (P0)** | Bảo toàn nguyên vẹn `srmodels.bin` (`291 KB` WakeNet9), `font_puhui_deepseek_20_4.bin` (`1.24 MB` tiếng Việt) và khóa dự phòng `robot_2` trong `index.json` | Đảm bảo Wake Word và phụ đề tiếng Việt hoạt động bình thường |
| **Must (P0)** | Kiểm tra chữ ký `esp_mmap_assets` (`ZZ` prefix + 16-bit checksum `0xef2a`) và xác nhận `8/8` health checks qua `tools/robotctl.py status` sau khi nạp | Đảm bảo an toàn tuyệt đối khi ghi vào phân vùng `0xAA0000` |
| **Should (P1)** | Tạo bảng xem trước tổng thể `7x3` (`procedural_mochi_21_preview.png`) trước khi nạp | Giúp kiểm duyệt thị giác toàn bộ 21 mặt trong 1 cái nhìn |
| **Won't (This Spec)** | Sửa mã máy C++ của `ota_1` (`0x560000`) | Thuộc phạm vi **Spec 04** (`04-embodied-reflex-and-native-60fps`) |

## 4. Appetite & No-Gos (Shape Up)
- **Appetite**: 1 phiên thực thi ngắn (Compile $\rightarrow$ Verify Checksum $\rightarrow$ Flash `0xAA0000` $\rightarrow$ Run `robotctl.py status`).
- **No-Gos**:
  1. Không bao giờ ghi đè vào phân vùng `ota_1` (`0x560000`) hoặc `otadata` (`0x00d000`) trong Spec 01.
  2. Không dùng ảnh cắt từ video hoặc ảnh có hạt nhiễu dithering (làm phình dung lượng LZW gấp 10 lần).
