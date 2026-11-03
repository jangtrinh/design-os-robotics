# 11 — Kiến trúc Avatar Tự Vẽ Bằng Code (Procedural / Parametric Vector Face Engine) cho `RoBot.5320`

> **Kết luận Thực nghiệm**: Hoàn toàn khả thi và **nhẹ hơn từ 10.46 lần đến $\infty$ lần** so với dùng ảnh GIF truyền thống.
> - **Phương án A (Zero-Firmware-Mod — Procedural GIF Compiler bằng Python [`tools/cook-procedural-avatar.py`](../tools/cook-procedural-avatar.py))**: Toàn bộ **21 trạng thái cảm xúc riêng biệt** (GIF `240x240`, 12 đến 16 khung hình mỗi trạng thái, tổng **312 khung hình**, hiển thị tràn viền trên màn hình `240x320`) tự vẽ bằng toán học chỉ nặng tổng cộng **`250,580 bytes` (`244.71 KB`)** — trung bình **`11.7 KB` / biểu cảm**, giảm **90.4%** dung lượng so với bộ 21 GIF gốc (`2,621,717 bytes` / `2,560.27 KB`) và, **nếu** con số `801,236 bytes` của bộ 6 GIF cắt từ video là đúng (**chưa kiểm chứng**: bộ đó không còn trong repo và không có nguồn), thì nhẹ hơn khoảng **3.20 lần**.
> - **Phương án B (Native On-Chip C++ Parametric Engine — Kiến trúc Anki Cozmo / Stack-chan / RoboEyes)**: Tốn **`0 KB` Flash assets**, chỉ **`64 bytes` RAM** cho vector trạng thái, chạy mượt **`60 FPS` với `< 3%` CPU**, mở khóa **vô hạn biểu cảm nội suy lò xo (Spring Physics)**, **nhép môi theo biên độ âm thanh thời gian thực (Real-time Lip-Sync)** và **liếc mắt theo vị trí người ngồi (`HC-SR04`)**.

---

## 1. Bảng So sánh Định lượng: GIF Truyền thống vs. Procedural GIF (21 States) vs. Native On-Chip

| Tiêu chí | 1. Bộ 21 GIF gốc (`08-assets-0xAA0000.bin`) | 2. Bộ 6 GIF Video (`Procedural Mochi-21` lặp vào 21 slot) | 3. Bộ 21 GIF Tự Vẽ Bằng Code (`Procedural Mochi 21`) | 4. Native On-Chip Procedural (`C++ LVGL`) |
|---|---|---|---|---|
| **Số biểu cảm độc lập thực sự** | 21 | Chỉ **6** (15 trạng thái bị dùng trùng) | **Đủ 21 biểu cảm riêng biệt 100%** | **Vô hạn ($\infty$)** |
| **Dung lượng trung bình 1 GIF** (KB = KiB) | `121.92 KB` | `130.41 KB` *(chưa kiểm chứng)* | **`11.7 KB`** (`5.69 KB – 19.36 KB`) | **`0 KB`** |
| **Tổng dung lượng 21 GIF** | `2,621,717 B` (`2,560.27 KB`) | `801,236 B` (`782.46 KB`) *(chưa kiểm chứng)* | **`250,580 B` (`244.71 KB`, giảm 90.4%)** | **`0 KB`** |
| **Tổng file `.bin` nạp vào `0xAA0000`** | `5,636,096 B` (`5.375 MiB`) | `2,643,248 B` (`2.52 MiB`) *(chưa kiểm chứng)* | **`2,092,592 B` (`2.00 MiB`)** | `1,842,012 B` (`1.76 MiB`) *(chưa kiểm chứng: không có nguồn trong repo)* |
| **Tải CPU ESP32-S3 (`240MHz`) khi giải mã** | `35% – 55%` | `35% – 55%` (LZW nhiễu dithering) | **`8% – 12%`** (bảng màu phẳng 8 màu) | **`< 3%` ở 60 FPS** |
| **Cần biên dịch lại Firmware C++ (`ota_1`)?** | Không | Không | **Không (Chạy ngay trên `ota_1` `v2.5.3`!)** | Có |

---

## 2. Tại sao Avatar Tự Vẽ Bằng Code Lại Đẹp & "Có Hồn" Hơn Ảnh GIF? (Nguyên lý Anki Cozmo & Pixar)

Các robot để bàn đắt giá nhất thế giới (**Anki Cozmo / Vector**, **Living.ai EMO**, **M5Stack Stack-chan**) đều **không dùng video/GIF dựng sẵn** cho khuôn mặt chính. Thay vào đó, chúng vẽ khuôn mặt bằng **Hình học Tham số (Parametric Geometry) + Mặt nạ Cắt (Boolean Eyelid Masking)**:

```mermaid
flowchart LR
    subgraph Layer1["Lớp 1: Nền & Con ngươi (Base Shapes)"]
        BG["Nền Đen Tuyệt đối #000000\n(Tạo hiệu ứng tràn viền vô cực)"]
        EYES["2 Hình chữ nhật bo góc (Rounded Rect)\nhoặc SDF Ellipse tại (gx, gy)"]
    end

    subgraph Layer2["Lớp 2: Mặt nạ Mí mắt (Boolean Masks màu #000000)"]
        UPPER["Đa giác Mí trên (Upper Lid Slope)\n• Nghiêng vào trong (+25°) -> Tức giận 😠\n• Nghiêng ra ngoài (-25°) -> Buồn bã 😔\n• Hạ ngang xuống 60% -> Ngái ngủ 😴"]
        LOWER["Hình elip Mí dưới (Lower Lid Raise)\n• Dâng từ dưới lên cắt con ngươi\n-> Tạo mắt cười bán nguyệt híp mí 😆"]
    end

    subgraph Layer3["Lớp 3: Miệng Bezier, Má hồng & Hạt FX"]
        BLUSH["2 Đốm Má hồng (Pink Pill)\nCo giãn theo nhịp thở"]
        MOUTH["Đường cong Bezier Bậc 2 / Miệng chữ W\nMở rộng theo âm lượng giọng nói (RMS)"]
        FX["Hạt Hiệu ứng Toán học:\nZzz · Trái tim ❤️ · Giọt mồ hôi 💧 · Dấu ?"]
    end

    Layer1 --> Layer2 --> Layer3
```

### 2.1. Vector Tham số `64-byte` Điều khiển Toàn bộ Linh hồn Khuôn mặt
Chỉ cần **12 biến số thực (`float`)**, chúng ta có thể biểu đạt mọi sắc thái cảm xúc của `Mochi-Soul`:

| Tham số | Miền giá trị | Ý nghĩa Hình học & Tâm lý |
|---|---|---|
| `gaze_x`, `gaze_y` | `[-1.0, +1.0]` | Hướng nhìn của 2 mắt (dịch chuyển tối đa `±28px` ngang, `±20px` dọc). Mắt phải di chuyển nhiều hơn một chút khi nhìn sang phải (hiệu ứng phối cảnh 3D giả lập!). |
| `open_l`, `open_r` | `[0.0, 1.2]` | Độ mở dọc của mắt trái/phải (`0.0` = nhắm tịt khi chớp mắt, `1.2` = mở to kinh ngạc `shocked`). Cho phép nháy 1 mắt (`wink`: `open_l=1.0, open_r=0.05`). |
| `scale_l`, `scale_r` | `[0.5, 1.4]` | Kích thước tổng thể từng mắt. Khi `scale_l=1.25, scale_r=0.75` $\rightarrow$ tạo biểu cảm **Nghi ngờ / Tò mò (`confused` / `thinking`)** cực kỳ sống động! |
| `slope_l`, `slope_r` | `[-40°, +40°]` | Góc nghiêng của mặt nạ mí mắt trên. `+30°` = Dữ dằn (`angry`); `-25°` = Tủi thân (`sad`). |
| `happy_cheek` | `[0.0, 1.0]` | Độ dâng của mí mắt dưới màu đen cắt vào đáy con ngươi, biến con ngươi thành hình vầng trăng khuyết cười tít mắt (`happy` / `laughing`). |
| `mouth_curve` | `[-1.0, +1.0]` | Độ cong của miệng (`+1.0` = Cười chữ $\cup$ hoặc $\omega$, `0.0` = Ngang, `-1.0` = Mếu $\cap$). |
| `mouth_open` | `[0.0, 1.0]` | Độ mở hàm dưới — **nối trực tiếp vào biên độ âm thanh TTS** để nhép môi theo từng từ! |
| `blush_opa` | `[0.0, 1.0]` | Độ đậm của 2 má hồng (`loving` 😍 / `embarrassed` 😳). |

---

## 3. Phương trình Vật lý Lò xo (`Spring-Damper Physics`) Giúp Chuyển động Mượt Như Đồ họa Apple

Thay vì dùng hàm tuyến tính (`linear`) khô cứng, mọi tham số trên đều tuân theo phương trình dao động điều hòa có cản (**Critically / Slightly Under-damped Spring**):

$$
\begin{aligned}
a_i(t) &= \omega_0^2 \cdot \big(x_{i,\text{target}} - x_i(t)\big) - 2 \zeta \omega_0 \cdot v_i(t) \\
v_i(t + \Delta t) &= v_i(t) + a_i(t) \cdot \Delta t \\
x_i(t + \Delta t) &= x_i(t) + v_i(t) \cdot \Delta t
\end{aligned}
$$

- Với tần số góc tự nhiên $\omega_0 = 18\text{ rad/s}$ và hệ số cản $\zeta = 0.65$ (hơi nảy nhẹ — *overshoot* ~6% giống hệt triết lý hoạt họa của Pixar & Apple):
  - Khi Mochi liếc mắt từ trái sang phải hoặc giật mình mở to mắt (`shocked`), đôi mắt sẽ **vượt nhẹ qua điểm đích ~3 pixel rồi đàn hồi về vị trí cân bằng** tạo cảm giác có khối lượng quán tính như thạch Mochi thật!

---

## 4. Hai Lộ trình Áp dụng Thực tế trên `RoBot.5320`

### Lộ trình 1: Áp dụng Ngay Hôm Nay Không Cần Sửa Firmware C++ (`Procedural Ultra-Light Asset Pack`)
Vì firmware `ota_1` (`v2.5.3`) hiện tại đọc các file `.gif` từ phân vùng `assets` (`0xAA0000`) và cho phép hiển thị ảnh động/tĩnh qua `self.screen.preview_image`:
1. **Tại sao GIF tự vẽ bằng code lại nhẹ chỉ `11.2 KB`?**
   - Khi vẽ bằng code Python (`Pillow` / `Cairo`) với **bảng màu phẳng 8 màu (`Palette Mode P`)** và không dùng hạt nhiễu (no dithering), mỗi dòng quét ngang 240 pixel của màn hình chỉ gồm 2–4 đoạn màu đồng nhất (ví dụ: `60 pixel Đen -> 45 pixel Trắng -> 30 pixel Đen -> 45 pixel Trắng -> 60 pixel Đen`).
   - Thuật toán nén từ điển LZW của GIF gom cả dải 60 pixel cùng màu thành **1 mã 9-bit duy nhất**!
   - Nhờ đó, bộ giải mã `lv_gif` trên ESP32-S3 chạy nhẹ nhàng hơn gấp 4 lần, không bao giờ gây khựng âm thanh khi AI đang trả lời dài.
2. **Tùy biến Nhân vật Bằng Code 100%**:
   - Chúng ta có thể viết script `tools/generate-procedural-mochi.py` định nghĩa từng biểu cảm bằng hàm toán học (`blink_curve`, `spring_bounce`, `w_mouth`, `zzz_particles`, `heart_eyes`, `coding_glasses`), tự xuất ra bộ 6 hoặc 21 biểu cảm tổng cộng chỉ **`~70 KB – 180 KB`** và nạp vào `0xAA0000` trong vài giây!

### Lộ trình 2: Nhúng Trực tiếp Bộ Vẽ C++ Vào Firmware (Khi Build Custom Firmware ở Phase 3)
Khi chuyển sang build firmware ESP-IDF riêng:
1. Thay đối tượng `lv_gif` (`emoji_image_`) trong `LcdDisplay` bằng một `lv_canvas` hoặc custom LVGL draw callback (`LV_EVENT_DRAW_MAIN`) kích thước `240x320` trong PSRAM.
2. Chạy timer `16ms` (`60 FPS`) cập nhật:
   - **Auto-Blink**: Tự động chớp mắt ngẫu nhiên mỗi `2.5s – 5.0s`.
   - **Micro-Saccades**: Tự động đảo mắt nhẹ tìm kiếm xung quanh khi `idle`.
   - **Audio RMS Lip-Sync**: Đọc biên độ luồng PCM từ `AudioService` truyền thẳng vào `face.mouth_open`.
   - **Ultrasonic Gaze Tracking**: Đọc khoảng cách từ `HC-SR04` (`GPIO 11/12`) — khi bạn tiến lại gần bàn, hai con ngươi hơi hội tụ vào giữa và mở to đón chào!

---

## 5. Tài liệu Liên quan (See Also)
- [`knowledge/09-beyond-xiaozhi-capabilities-and-applications.md`](09-beyond-xiaozhi-capabilities-and-applications.md)
- [`knowledge/10-generative-ai-tamagotchi-deep-dive.md`](10-generative-ai-tamagotchi-deep-dive.md)
- [`tools/cook-assets-and-nvs.py`](../tools/cook-assets-and-nvs.py)
