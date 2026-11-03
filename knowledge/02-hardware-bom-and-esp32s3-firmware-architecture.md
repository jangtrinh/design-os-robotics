# 02 — Kiến trúc Phần cứng & Firmware ESP32-S3 (`RB5320XZ78AI`)

Tài liệu kỹ thuật tổng hợp kiến trúc phần cứng **ESP32-S3 (`N16R8` / `N8R8`)**, màn hình hiển thị SPI TFT và sơ đồ phân vùng bộ nhớ Flash chuẩn ESP-IDF.

## 1. Nền tảng Phần cứng (Hardware BOM)

### Vi điều khiển (MCU) & Bộ nhớ
- **Chip chính**: **ESP32-S3** (Dual-core Xtensa LX7 @ `240MHz`, hỗ trợ tập lệnh vector PIE 128-bit SIMD cho nhận diện wake word trên thiết bị và giải mã âm thanh Opus thời gian thực).
- **Module chuẩn**: **ESP32-S3-WROOM-1U-N16R8** (**16MB Flash** Quad SPI + **8MB PSRAM** Octal SPI).
- **Module tương thích khác**: **N8R2 / N8R8** (**8MB Flash** + 2MB/8MB PSRAM), ESP32-S3-CAM (`XH-S3E`).
- **Giao tiếp USB-UART**: Cổng USB-C tích hợp USB-Serial/JTAG hoặc qua chip cầu **WCH CH343 / CH340 / CP210x** (tốc độ nạp flash `921600` baud, tốc độ đọc log `115200` baud).

### Màn hình hiển thị (Displays) & Độ phân giải
Hệ thống hỗ trợ 3 nhóm cấu hình khung hình SPI TFT:
1. **TFT `1.54 inch` (Vuông `240×240`)**: Driver IC **ST7789**.
2. **TFT `2.4 / 2.8 / 3.2 inch` (`240×320` Dọc hoặc `320×240` Ngang)**:
   - Driver IC **ST7789** (chuẩn trên bo mạch `RB5320XZ78AI`).
   - Driver IC **ILI9341** (`240×320`).
3. **TFT `3.5 / 4.0 inch` (`320×480` Dọc hoặc `480×320` Ngang)**: Driver IC **ILI9488**.

## 2. Hai Kiến trúc Đóng gói Giao diện trên ESP32-S3

| Đặc điểm | Nhánh 1: **`esp_mmap_assets` (`Hi Telly / Xiaozhi v2.5.x`)** | Nhánh 2: **Idle `.pack` (`XiaoZhiVN`)** |
|---|---|---|
| **Wake Word** | **"Hi Telly"** (`wakenet9l_tts2h8v5_hitelly`) | Tùy theo gói model đi kèm |
| **Định dạng giao diện** | File `.bin` (`esp_mmap_assets`) ghi vào phân vùng **`assets`** (`0xAA0000` hoặc `0x800000`) | File **`.pack`** ghi vào offset `0xE80000` (16MB) hoặc `0x410000` (8MB) |
| **Cấu trúc hiển thị** | 21+1 bộ mặt biểu cảm động GIF + `index.json` + `srmodels.bin` + font DeepSeek | Màn hình chờ hiển thị đồng hồ số, thời tiết, lịch âm |

## 3. Sơ đồ Phân vùng Bộ nhớ Flash (ESP-IDF Partition Map)

Bảng phân vùng ESP-IDF nằm tại địa chỉ `0x8000` (`3,072 bytes`, mỗi mục `32 bytes` bắt đầu bằng magic `0x50AA` little-endian):

```text
+-----------------------------------------------------------------------+ 0x000000 (0 MB)
| Bootloader (0x0) + Partition Table (0x8000)                           |
+-----------------------------------------------------------------------+ 0x008000 (32 KB)
| Bảng phân vùng ESP-IDF (Partition Table - 0xC00 = 3072 bytes)         |
| -> Mỗi entry 32 bytes, bắt đầu bằng Magic 0x50AA (little-endian)      |
| -> Offset +4: uint32 partition offset | Offset +8: uint32 size        |
| -> Offset +12..27: Tên phân vùng ASCII ("nvs", "ota_0", "ota_1",      |
|    "assets")                                                          |
+-----------------------------------------------------------------------+ 0x009000 (36 KB)
| Phân vùng "nvs" (16 KB) - Cấu hình GPIO lcd_cfg, Wi-Fi, âm lượng      |
+-----------------------------------------------------------------------+ 0x020000 (128 KB)
| Phân vùng "ota_0" (5.25 MB) - Khe chứa firmware dự phòng              |
+-----------------------------------------------------------------------+ 0x560000 (5.38 MB)
| Phân vùng "ota_1" (5.25 MB) - Khe chứa firmware chính (v2.5.3)        |
+-----------------------------------------------------------------------+ 0xAA0000 (10.625 MB)
| Phân vùng "assets" (5.38 MB trên bo mạch 16MB N16R8)                  |
| -> Chứa dữ liệu Theme khuôn mặt + Wake word model + Font              |
+-----------------------------------------------------------------------+ 0x1000000 (16.0 MB)
```

> [!IMPORTANT]
> Luôn đọc bảng phân vùng tại `0x8000` để lấy địa chỉ chính xác của phân vùng `assets` (`0xAA0000` trên bản `ota_1 v2.5.3`, hoặc `0x800000` trên một số bản ROM đơn khe). Không bao giờ ghi cứng vào `0x800000` khi máy đang dùng bố cục 2 khe OTA (`ota_0` + `ota_1`).
