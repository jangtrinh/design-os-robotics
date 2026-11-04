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
The 21-state code-reconstructed canonical Mochi avatar pack (`222,892 bytes` / `217.67 KB` in total, `-91.3%` vs the `2,560.27 KB` default pack; the sum of 21 unique GIFs of `240x240` px with 10 frames each, shown full-bleed on the `240x320` display; the demo `mochi_60fps_spring_transition.gif` is not counted) generated deterministically by `tools/cook-procedural-avatar.py` and `tools/mochi_canonical_vectors.py` (`108,522` Structure-of-Arrays scanline spans `(y, x0, w, color)` across 210 frames in an 8-color `MOCHI_PALETTE_8` Global Color Table with `LZW min_code_size = 3`), plus optional `EVO-02` phenotype traits and `ESP-SR MultiNet6` (`"Mochi / Hey Mochi / Hi Mochi"`) wake-word model packing.
_Avoid_: video-ripped GIFs, 6-state duplicated theme.

**`Mochi-Soul Engine`**:
The host-side autonomous digital lifeform daemon (`tools/mochi-soul-engine/`) that computes continuous biological state transitions, evolves a bounded Relative-Share Personality Genome (`EVO-01`), renders Dual-Track Morphological Phenotype traits (`EVO-02`), performs idempotent SQLite WAL Dream Consolidation (`EVO-03`), supervises USB-JTAG hardware health via a 12-state Watchdog Auto-Rescue FSM (`EVO-03b`, `tools/mochi-soul-engine/serial_supervisor.py`), and drives proactive behavior on `RoBot.5320`.
_Avoid_: chatbot wrapper, cron voice script.

**`Homeostasis Vector (4D State)` & `Personality Genome (EVO-01)`**:
The 4 continuous biological variables governing Mochi's internal life: `Energy` ($E \in [0, 100]$), `Hunger` ($H \in [0, 100]$, rises with time and drops when fed), `Bond` ($B \in [0, 100]$), and `Mood`, which is two axes: `Valence` and `Arousal` ($V, A \in [-1, +1]$). Alongside the 4D state, `SoulState` in `tools/mochi-soul-engine/engine.py` maintains a persistent **Personality Genome** (`curiosity`, `affection`, `playfulness`, `resilience`, `chronotype_shift`) evolved via Relative-Share (`RS_k - 0.25`) zero-sum drift and bounded homeostatic set-point plasticity (`energy_setpoint`, `hunger_drift_scale`, `bond_retention`).
_Avoid_: random mood picker, static emotion state, unbounded runaway drift.

**`Proactive Impulse`**:
An autonomous action initiated by `Mochi-Soul Engine` without a user wake word when an internal drive crosses a threshold (outside `Quiet Hours 23:00–07:30`), delivered via `"type": "notify"` (`0x4202c0fc`), `"type": "alert"` (`0x4202c683`), or `self.screen.preview_image` (`0x3c27852f`).
_Avoid_: spam notification, push alert.
