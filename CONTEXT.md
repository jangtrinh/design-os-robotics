# CONTEXT.md — Domain Glossary (`design-os-robotics` & `Mochi-Soul`)

> Canonical domain vocabulary for `RoBot.5320` (`ESP32-S3` + `Otto Quadruped`) and **Project Mochi-Soul**. Every spec in `plans/specs/` and every commit must use these exact terms and avoid rejected synonyms.

**`RoBot.5320` (Hardware Target)**:
The physical quadruped desktop robot based on `ESP32-S3` (`QFN56`, `16MB` Flash, `8MB` Octal PSRAM), `ST7789` `240x320` IPS LCD, dual `MAX98357A + PCM5102A` / `ES8311` I2S audio pipeline, `HC-SR04` ultrasonic sensor (`GPIO 11/12`), and 6 servo channels (`LF, RF, LH, RH, LW, RW`).
_Avoid_: generic board, ESP32 toy, speaker box.

**`Active Firmware Slot (ota_1)`**:
The production firmware image at flash offset `0x560000` (`xingzhi-cube-1.54tft-wifi v2.5.3`) booted via `otadata` (`0x00d000`) with full 6-servo quadruped support, `HC-SR04` driver, and `esp_mmap_assets` (`240x320`).
_Avoid_: `ota_0` (`0x020000`, legacy `v2.2.2` 4-servo build — never boot).

**`Assets Partition (mmap_assets)`**:
The `5.25 MB` flash partition at `0xAA0000` (`08-assets-0xAA0000.bin`) formatted with a 12-byte header (`num_files, checksum, total_data_len`), 44-byte file table entries (`32s` name + `<IIHH` `size, offset, width, height`), and `ZZ`-prefixed payloads containing `srmodels.bin`, `font_puhui_deepseek_20_4.bin`, `index.json`, and 21 `emoji_*.gif` files.
_Avoid_: SPIFFS theme, SD card assets.

**`Procedural Mochi-21`**:
The 21-state code-drawn `240x320` avatar pack (`250,580 bytes` / `244.71 KB` total across 21 unique 16-frame GIFs) generated deterministically by `tools/cook-procedural-avatar.py` using parametric geometry, boolean eyelid masking, and harmonic motion in an 8-color flat palette (`Mode P`).
_Avoid_: video-ripped GIFs, 6-state duplicated theme.

**`Mochi-Soul Engine`**:
The host-side autonomous digital lifeform daemon (`tools/mochi-soul-engine/`) that computes continuous biological state transitions, stores episodic memories in SQLite, and drives proactive behavior on `RoBot.5320`.
_Avoid_: chatbot wrapper, cron voice script.

**`Homeostasis Vector (4D State)`**:
The 4 continuous biological variables governing Mochi's internal life: `Energy` ($E \in [0, 100]$), `Hunger/Curiosity` ($H \in [0, 100]$), `Bond/Affection` ($B \in [0, 100]$), and `Mood Valence/Arousal` ($M \in [-1, +1]^2$).
_Avoid_: random mood picker, static emotion state.

**`Proactive Impulse`**:
An autonomous action initiated by `Mochi-Soul Engine` without a user wake word when an internal drive crosses a threshold (outside `Quiet Hours 23:00–07:30`), delivered via `"type": "notify"` (`0x4202c0fc`), `"type": "alert"` (`0x4202c683`), or `self.screen.preview_image` (`0x3c27852f`).
_Avoid_: spam notification, push alert.
