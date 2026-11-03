# 07 — Hồ sơ Phần cứng & Cấu trúc Phân vùng Bo mạch `RB5320XZ78AI`

Tài liệu này ghi lại cấu hình phần cứng, ánh xạ chân GPIO trong NVS (`0x9000`) và cấu trúc nhị phân của phân vùng `esp_mmap_assets` (`0xAA0000`) trên bo mạch **`RB5320XZ78AI` (`ESP32-S3-WROOM-1U-N16R8`)**.

## 1. Định danh Phần cứng & Vi điều khiển (`FACT`)

- **Cổng kết nối trên macOS**: `/dev/cu.usbmodem*` (Chip cầu USB-UART: **WCH CH343** `USB Single Serial`, `idVendor=0x1a86`, `idProduct=0x55d3`).
- **SoC / Module**: **ESP32-S3 (QFN56) revision v0.2** — Dual Core Xtensa LX7 @ `240MHz`, thạch anh `40MHz`.
- **Bộ nhớ**:
  - **Flash**: **16MB Quad SPI** (`Manufacturer: 0x68`, `Device: 0x4018`, `3.3V`).
  - **PSRAM**: **8MB Octal PSRAM** (`AP_3v3`) → Chuẩn module **ESP32-S3-WROOM-1U-N16R8**.
- **Màn hình**: **TFT 2.8 inch (`240×320` Dọc, driver `ST7789`, xoay `180°`)** trên bo mạch mở rộng **`RB5320XZ78AI`**.

### 1.1. Giải phẫu Bo mạch Mặt sau & Kiến trúc Âm thanh Kép (`MAX98357A` + `PCM5102A`)

Từ ảnh chụp mặt sau bo mạch [04-rb5320xz78ai-st7789-schematic.png](../docs/assets/hardware/04-rb5320xz78ai-st7789-schematic.png), bo mạch chủ `RB5320XZ78AI` tích hợp **5 cụm phần cứng**:

| Cụm linh kiện trên PCB | Module thực tế | Vai trò kỹ thuật |
|---|---|---|
| **1. Vi điều khiển trung tâm** | **ESP32-S3-WROOM-1 N16R8 DevKitC-1** (2 cổng USB-C `USB` & `UART`, đèn RGB `WS2812` tại `GPIO 48`) | Xử lý giọng nói WakeNet9l (`Hi Telly`), giải mã âm thanh Opus, kết nối Wi-Fi/WebSocket và dựng hình LVGL lên màn TFT |
| **2. Khuếch đại Loa trong** | **MAX98357A I2S Class-D Amp** (module tím vuông `HW-792` ở giữa) + **Loa hộp cộng hưởng lớn** | Nhận tín hiệu I2S (`DOUT=7, BCLK=15, LRCK=16`) phát trực tiếp ra loa ngoài công suất 3W |
| **3. Giải mã Âm thanh Hi-Fi Rời** | **PCM5102A 32-bit I2S Stereo DAC** (module tím chữ nhật bên phải, có **cổng 3.5mm Audio Out**) | Cho phép cắm tai nghe IEM hoặc loa ngoài qua cổng 3.5mm, chuyển đổi bằng **công tắc trượt `PCM`** cạnh công tắc nguồn `PWR ON` |
| **4. Nguồn & Quản lý Pin** | **Pin Li-ion 18650** + **Mạch sạc & bảo vệ TP4056 USB-C** (module xanh dương góc dưới trái) | Cấp nguồn độc lập cho robot (`OUT+`/`OUT-` qua công tắc `PWR ON` vào chân `5V0`/`GND` kèm tụ lọc `1000µF 25V`) |
| **5. Cụm Nút bấm Vật lý** | **3 nút nhấn sườn trái** (`VOL+` `GPIO 40`, `BOOT` `GPIO 0`, `VOL-` `GPIO 39`) + **2 công tắc gạt đỉnh** (`PWR ON`, `PCM`) | Tăng/giảm âm lượng, bấm gọi/ngắt giọng nói, chuyển đổi ngõ ra âm thanh Loa trong / DAC 3.5mm |

## 2. Bảng Phân vùng Thực tế @ `0x00008000` (`FACT`)

> [!IMPORTANT]
> Trên bố cục 2 khe OTA (`ota_0` + `ota_1`), phân vùng `assets` nằm tại **`0x00AA0000` (10.625 MB)** chứ không phải `0x00800000` (8.0 MB).

| Tên phân vùng | Type / Subtype | Offset bắt đầu | Dung lượng | Trạng thái / Nội dung |
|---|---|---|---|---|
| `nvs` | `0x01` / `0x02` | `0x00009000` (`36 KB`) | `16.0 KB` (`0x4000`) | Chứa cấu hình chân GPIO (`lcd_cfg`), Wi-Fi, MQTT, WebSocket, âm lượng |
| `otadata` | `0x01` / `0x00` | `0x0000D000` (`52 KB`) | `8.0 KB` (`0x2000`) | `slot0 seq=1`, **`slot1 seq=2` (Boot từ `ota_1`)** |
| `phy_init` | `0x01` / `0x01` | `0x0000F000` (`60 KB`) | `4.0 KB` (`0x1000`) | Dữ liệu hiệu chuẩn RF Wi-Fi/BLE |
| `ota_0` | `0x00` / `0x10` | `0x00020000` (`128 KB`) | `5,376.0 KB` (`5.25 MB`) | Project `xiaozhi` **v2.4.2** |
| `ota_1` *(Active)* | `0x00` / `0x11` | `0x00560000` (`5.38 MB`) | `5,376.0 KB` (`5.25 MB`) | Project `xiaozhi` **v2.5.3** |
| `assets` | `0x01` / `0x82` | **`0x00AA0000`** (`10.62 MB`) | `5,504.0 KB` (`5.38 MB`) | Gói 26 file: Font DeepSeek, `srmodels.bin`, 21+1 GIF biểu cảm, 2 ảnh nền `.raw` |

## 3. Sơ đồ Chân GPIO & Cấu hình trong NVS (`0x9000`)

Firmware `xiaozhi v2.5.3` đọc động ánh xạ chân từ namespace **`lcd_cfg`** trong NVS:

| Nhóm chức năng | Khóa NVS (`lcd_cfg`) | Giá trị chuẩn | Ý nghĩa kỹ thuật |
|---|---|---|---|
| **Màn hình TFT SPI** | `drv`, `scr_type`, `w`, `h`, `rot` | `drv=0`, `w=240`, `h=320`, `rot=180` | Màn TFT `240×320` `ST7789`, xoay `180°`, `rgb_ord=0`, `inv_col=0` |
| **Chân SPI Màn hình** | `p_mosi`, `p_clk`, `p_dc`, `p_rst`, `p_cs`, `p_bl` | `MOSI=10`, `CLK=9`, `DC=8`, `RST=18`, `CS=14`, `BL=13` | Đấu nối chuẩn SPI cho màn hình TFT |
| **Micro I2S (`INMP441`)** | `mic_ws`, `mic_sck`, `mic_din` | `WS=4`, `SCK=5`, `DIN=6` | Ngõ vào thu âm giọng nói I2S |
| **Loa I2S (`MAX98357A`)** | `spk_dout`, `spk_bclk`, `spk_lrck` | `DOUT=7`, `BCLK=15`, `LRCK=16` | Ngõ ra khuếch đại âm thanh I2S (`audio.output_volume = 60`) |
| **Nút nhấn & LED RGB** | `p_boot`, `p_vol_up`, `p_vol_dn`, `p_led`, `led_count` | `BOOT=0`, `VOL+=40`, `VOL-=39`, `LED=48` (`1` bóng) | Nút chức năng + LED WS2812 tích hợp tại `GPIO 48` |
| **Chế độ Giao diện** | `u_wch` | `0` (Full-viền) / `1` (Widget nhỏ) | `u_wch=0` hiển thị biểu cảm tràn viền `240×320`; `u_wch=1` bật bong bóng hội thoại |

## 4. Cấu trúc Nhị phân của Phân vùng `assets` (`0x00AA0000`)

Định dạng gói `.bin` của Theme (`esp_mmap_assets`):
1. **Header 12 bytes đầu (`0x00..0x0B`)**:
   - `num_files` (`uint32 LE`): Số lượng tệp trong gói (`26` hoặc `27`).
   - `checksum` (`uint32 LE`): Tổng byte 16-bit (`sum(data) & 0xFFFF`) của toàn bộ vùng dữ liệu ghép nối.
   - `data_len` (`uint32 LE`): Tổng độ dài vùng dữ liệu tính bằng byte.
2. **Bảng Mục lục (`num_files × 44 bytes`, bắt đầu từ `0x0C`)**:
   - Mỗi mục 44 bytes gồm: `name[32]` (ASCII null-terminated), `size` (`uint32 LE`), `offset` (`uint32 LE`), `width` (`uint16 LE`), `height` (`uint16 LE`).
3. **Vùng Dữ liệu**:
   - Trước mỗi file có 2 byte magic **`0x5A 0x5A` (`"ZZ"`)**.
   - Gồm `font_puhui_deepseek_20_4.bin`, `srmodels.bin`, 21+1 file `emoji_<hash>.gif`, `index.json`, và `background_dark.raw` / `background_light.raw` (`28 B` header + `240 × 320 × 2 B` ảnh nền RGB565).
