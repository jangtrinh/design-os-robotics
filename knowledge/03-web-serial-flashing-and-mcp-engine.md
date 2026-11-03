# 03 — Giao thức Nạp Web Serial (`esptool-js`), Phân vùng `0x8000` & Cổng MCP WebSocket

Tài liệu kỹ thuật về quy trình nạp phân vùng `esp_mmap_assets` qua Web Serial / `esptool`, giải mã bảng phân vùng `0x8000`, đọc log UART không gây khởi động lại chip và giao thức MCP WebSocket.

## 1. Quy trình Dò Phân vùng `assets` Tự động (`0x8000`)

Khi nạp gói giao diện `.bin` (`esp_mmap_assets`) mà không ghi đè firmware chính, trình nạp cần đọc bảng phân vùng ESP-IDF tại `0x8000`:

1. **Đọc `3,072 bytes` (`0xC00`) tại địa chỉ `0x8000`**:
   - Quét từng khung `32 bytes`.
   - Kiểm tra 2 byte đầu là magic `0x50AA` (`buf[i] === 0xAA && buf[i+1] === 0x50`).
   - Đọc `offset` (`uint32 LE` tại `+4`), `size` (`uint32 LE` tại `+8`), và tên phân vùng ASCII (`+12..27`, cắt tại byte `0x00`).
2. **Xác thực dung lượng**:
   - Tìm phân vùng có tên `"assets"`.
   - Kiểm tra `theme_bin.length <= assetsPart.size` trước khi gọi `writeFlash`.
   - Trên bo mạch `RB5320XZ78AI` (`16MB` Flash, 2 khe OTA), `assets` bắt đầu tại `0xAA0000` với kích thước `5,636,096 bytes` (`5.38 MB`).

## 2. Cơ chế Mở Cổng Serial Không Gây Reset (`~HUPCL`)

Mạch tự động nạp (Auto-Reset) trên hầu hết các bo ESP32-S3 sử dụng cặp transistor kết nối với hai đường điều khiển `DTR` và `RTS`:

| `DTR` | `RTS` | `EN (RST)` | `IO0 (BOOT)` | Hệ quả |
|:---:|:---:|:---:|:---:|:---|
| `1` | `1` | `1` | `1` | Hoạt động bình thường |
| `0` | `0` | `1` | `1` | Hoạt động bình thường |
| `1` | `0` | `1` | `0` | Giữ chân `BOOT = LOW` |
| `0` | `1` | **`0`** | `1` | **Kéo chân `EN = LOW` → Reset cứng chip!** |

- Trong Python trên macOS/Linux, nếu dùng `pyserial` và gán `s.dtr = False; s.rts = False`, hệ điều hành thực thi 2 lệnh `ioctl(TIOCMBIC)` nối tiếp nhau, tạo ra trạng thái quá độ `(DTR=0, RTS=1)` trong vài micro-giây và làm khởi động lại ESP32-S3.
- Để đọc log hoặc kiểm tra sức khỏe mà **không làm gián đoạn cuộc hội thoại**, [`tools/robotctl.py`](../tools/robotctl.py) mở trực tiếp file descriptor `/dev/cu.usbmodem*` bằng `os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)` và tắt cờ `termios.HUPCL` (`attrs[2] &= ~termios.HUPCL`) trước khi đóng cổng.

## 3. Giao thức Điều khiển MCP qua WebSocket (`JSON-RPC 2.0`)

Firmware `xiaozhi v2.5.3` tích hợp máy chủ MCP nội bộ gồm 32 công cụ (`self.get_device_status`, `self.screen.set_theme`, `self.screen.set_brightness`, `self.screen.preview_image`, `self.audio_speaker.set_volume`, `self.led.set_color`, `self.Otto.*`...):

- Mọi lệnh MCP được bọc trong gói tin WebSocket `"type": "mcp"` với phần thân `"payload"` tuân thủ chuẩn **JSON-RPC 2.0** (`"jsonrpc": "2.0"`, `"id"`, `"method": "tools/call"`, `"params": { "name": ..., "arguments": ... }`).
- Xem chi tiết cài đặt trong [`tools/mochi-soul-engine/bridge.py`](../tools/mochi-soul-engine/bridge.py).
