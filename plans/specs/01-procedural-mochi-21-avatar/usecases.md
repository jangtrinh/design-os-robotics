# Use Cases & Acceptance Criteria — Spec 01 (`01-procedural-mochi-21-avatar`)

## 1. Use Cases

### UC-01: Biên dịch 21 Trạng thái Cảm xúc Bằng Toán học (`Procedural Compile`)
- **Actor**: Developer / Build Pipeline (`tools/cook-procedural-avatar.py`)
- **Precondition**: Phân vùng gốc `profiles/example-esp32s3-n16r8/partitions/08-assets-0xAA0000.bin` tồn tại để trích xuất `srmodels.bin`, `font_puhui_deepseek_20_4.bin` và bảng ánh xạ 21 tên file `emoji_*.gif`.
- **Happy Path**:
  1. Chạy `python3 tools/cook-procedural-avatar.py`.
  2. Script render 21 chuỗi 16 khung hình `240x320` ở chế độ bảng màu 8 màu phẳng (`Palette Mode P`), xuất 21 file `.gif` vào `themes/procedural-mochi/` và bảng tổng hợp `procedural_mochi_21_preview.png`.
  3. Script ánh xạ chính xác từng tên cảm xúc trong `index.json["emoji_collection"]` vào đúng file `emoji_*.gif` tương ứng, thêm khóa dự phòng `"robot_2" -> "emoji_3ec1da35.gif"` (`neutral`), bật `"hide_subtitle": true` và màu nền `#000000`.
  4. Script đóng gói `themes/procedural-mochi-fullvien-240x320.bin` kèm tiền tố `ZZ` và checksum 16-bit.
- **Edge Cases**:
  - Firmware gọi cảm xúc mặc định `"robot_2"` không có trong 21 tên chuẩn $\rightarrow$ Đã có mục `"robot_2"` trỏ về `emoji_3ec1da35.gif`.

### UC-02: Nạp An toàn vào Phân vùng `0xAA0000` và Kiểm chứng Phần cứng
- **Actor**: Developer / `esptool` + `tools/robotctl.py`
- **Precondition**: `RoBot.5320` đang kết nối qua `/dev/cu.usbmodem*`.
- **Happy Path**:
  1. Kiểm tra kích thước file `themes/procedural-mochi-fullvien-240x320.bin` (`2,092,592 bytes` $\le 5,505,024 bytes` của phân vùng `0xAA0000`).
  2. Nạp file vào địa chỉ `0xAA0000` ở tốc độ `921600` baud bằng `esptool write-flash`.
  3. Khởi động lại robot và chạy `python3 tools/robotctl.py status`.
  4. Robot đạt `8/8 [  OK  ]`, màn hình `240x320` hiển thị khuôn mặt `Procedural Mochi-21` sắc nét tràn viền trên nền đen `#000000`.

---

## 2. Acceptance Criteria (Gherkin)

```gherkin
Scenario: AC-01 — Đủ 21 trạng thái cảm xúc độc lập và siêu nhẹ (< 300 KB)
  Given script "tools/cook-procedural-avatar.py" được thực thi
  When kiểm tra thư mục "themes/procedural-mochi/" và "themes/procedural-mochi-fullvien-240x320.bin"
  Then phải có đúng 21 file .gif riêng biệt có độ phân giải 240x320 và 16 khung hình mỗi file
  And tổng dung lượng của cả 21 file .gif phải nhỏ hơn 300,000 bytes (thực tế: 250,580 bytes)
  And cả 21 mục trong "index.json" phải trỏ tới 21 nội dung GIF khác nhau hoàn toàn

Scenario: AC-02 — Toàn vẹn cấu trúc esp_mmap_assets và tài nguyên hệ thống
  Given file đóng gói "themes/procedural-mochi-fullvien-240x320.bin"
  When phân tích header 12-byte và bảng 26 mục (44 bytes/mục)
  Then checksum 16-bit trong header phải khớp tuyệt đối với tổng byte của phần thân (0xef2a)
  And mỗi mục dữ liệu phải bắt đầu bằng 2 byte magic "ZZ" (0x5a5a)
  And "srmodels.bin" (291,039 bytes) cùng "font_puhui_deepseek_20_4.bin" (1,240,332 bytes) phải được giữ nguyên 100%

Scenario: AC-03 — Nạp xuống RoBot.5320 và vượt qua 8/8 bài kiểm tra sức khỏe
  Given RoBot.5320 đang kết nối tại "/dev/cu.usbmodem*"
  When nạp "themes/procedural-mochi-fullvien-240x320.bin" vào địa chỉ "0xAA0000"
  And chạy lệnh "python3 tools/robotctl.py status"
  Then kết quả phải đạt "8/8 checks [  OK  ]" (Active Slot = ota_1, Assets Partition valid, Wi-Fi LAN 192.0.2.10 reachable)
```
