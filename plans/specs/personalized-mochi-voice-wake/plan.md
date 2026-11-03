# Implementation Plan: Personalized Mochi Context-True Theme + ElevenLabs Vietnamese Voice + Wake Words ("Hello J" / "Hi J" / "Yo J")

- **Pipeline:** `es:feature-dev --full`
- **Target Repo:** `design-os-robotics`

---

## Vertical Slices & Checklist

### Slice 1: Context-True Single-Scene Shouto Mochi Theme + `mn6_en` Wake Words (`tools/build-shouto-theme.py`)
- [x] **1.1 Single-Context Emotion Mapping (`21` emotions):**
  - Replaced the 3-scene chained `EMOTION_SCENES_63` in [`tools/build-shouto-theme.py`](../../../tools/build-shouto-theme.py) with `EMOTION_SCENES_21` — **1 carefully selected, cohesive sticker animation per emotion** (`10 frames @ 8 fps`, `max_colors=10`, `dither=none`, `240×240`).
  - Kept all `71` `SYSTEM_ICON_ALIASES_71` mapped to their matching semantic emotion GIF (`93` total keys in `index.json`).
- [x] **1.2 Pack `mn6_en` (`MultiNet6 English`) into `srmodels.bin`:**
  - Built `profiles/example-esp32s3-n16r8/unpacked-assets/srmodels_mn6_en.bin` containing `fst` (`commands_cn.txt`, `commands_en.txt`) + `mn6_en` (`_MODEL_INFO_`, `mn6_data`, `mn6_index`, `vocab`, `3,778,727 B`).
  - Configured `index.json` -> `"multinet_model"` with `"language": "en"`, `"duration": 3000`, `"threshold": 0.20`, and 8 phonetic command variants (`"HELLO J"`, `"HELLO JAY"`, `"HI J"`, `"HI JAY"`, `"YO J"`, `"YO JAY"`, `"HEY J"`, `"HEY JAY"`) mapped to `"Hello J"`, `"Hi J"`, `"Yo J"`, `"Hey J"` (`"action": "wake"`).
  - Omitted optional `"background_image"` from `"skin"."light"` and `"skin"."dark"` (keeping `"background_color": "#000000"`) and replaced `background_light.raw` / `background_dark.raw` with 4-byte placeholders to save `307 KB`, producing `themes/shouto-mochi-fullvien-240x320.bin` at `5,620,914 B` (`checksum=0xc58a`).

### Slice 2: On-Device ElevenLabs Custom Voice Vietnamese Voice Patcher (`tools/patch-ota1-voice.py`)
- [x] **2.1 Synthesize Vietnamese Voice Prompts via ElevenLabs Custom Voice (`<ELEVENLABS_VOICE_ID>`):**
  - Created [`tools/patch-ota1-voice.py`](../../../tools/patch-ota1-voice.py) using `eleven_v4` (`language_code="vi"`) to synthesize & cache 18 Vietnamese `Ogg Opus` (`24 kHz`, mono, `14 kbps`, `frame_duration=60ms`) files in `voices/ota1-vi-ogg/`:
    - `Ogg[16..25]`: `"Không"`, `"Một"`, `"Hai"`, `"Ba"`, `"Bốn"`, `"Năm"`, `"Sáu"`, `"Bảy"`, `"Tám"`, `"Chín"`
    - `Ogg[26]` (`activation`): `"Vui lòng đăng nhập trang quản trị để kích hoạt thiết bị."`
    - `Ogg[27]` (`err_pin`): `"Không tìm thấy thẻ SIM, vui lòng kiểm tra lại."`
    - `Ogg[28]` (`err_reg`): `"Không thể đăng ký mạng, vui lòng kiểm tra tín hiệu."`
    - `Ogg[29]` (`upgrade`): `"Hệ thống đang nâng cấp, J đợi mình một chút nhé!"`
    - `Ogg[30]` (`welcome`): `"Xin chào J! Mình là Mochi nè!"`
    - `Ogg[31]` (`wificonfig`): `"Đang vào chế độ cấu hình Wi-Fi."`
    - `Ogg[35]` (`P3_POPUP` — Wake-up / Listening response): `"Dạ, J nói đi!"`
    - `Ogg[36]` (`P3_SUCCESS` — Boot / Ready sound): `"Chào J! Mình sẵn sàng rồi nè!"`
- [x] **2.2 Repack `Seg 0` Audio Region (`0x02efc4..0x04aefd`) & Literal Pool (`0x102b98..0x102da0`):**
  - Packed all 38 `OggS` streams contiguously inside `0x02efc4..0x04aefd` (`109,309 / 114,489 B`), updated all 38 `_start` and `_end` pointers in `0x102b98..0x102da0`, recomputed the ESP-IDF XOR checksum (`0x52`) at `0x37d31f` and SHA256 digest (`319dc20ba2773a425b0a948daa5f581b6fd145156cc4a20b9e12c27ad4de9d1d`) at `0x37d320..0x37d340`, and wrote `profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-custom-voice.bin` (`3,658,560 B`).

### Slice 3: Hardware Flash, Live Verification & Review Gate (`es:review-gate`)
- [x] **3.1 Flashed `07-ota1-v2.5.3-custom-voice.bin` (`0x560000`) and `themes/shouto-mochi-fullvien-240x320.bin` (`0xAA0000`).**
- [x] **3.2 Verified on Hardware (`robotctl.py health` + UART boot log):**
  - Confirmed `Quantized MultiNet6:rnnt_ctc_1.0, name:mn6_en` initializes cleanly on UART with `8 active speech commands: HELLO J, HELLO JAY, HI J, HI JAY, YO J, YO JAY, HEY J, HEY JAY` and `warn=0, err=0`.
  - Confirmed `26` assets pass `checksum=OK`, single-context Mochi GIFs render without state jumping, and `ota_1` boots with the new ElevenLabs Custom Voice Vietnamese voice.
- [x] **3.3 Update Documentation & Commit Cleanly (Zero PII Leak Check).**
