<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="./docs/assets/brand/hero-light.png">
    <img src="./docs/assets/brand/hero-dark.png" alt="design:os by Jang" width="100%">
  </picture>
</p>

# design-os-robotics

ESP32-S3 voice-robot toolchain: non-intrusive serial health, NVS control, code-drawn Procedural Mochi-21 avatar, Mochi-Soul engine.

FREE + source-available (PolyForm Shield 1.0.0)

[![Licence: PolyForm Shield 1.0.0](https://img.shields.io/badge/licence-PolyForm_Shield_1.0.0-202020?style=for-the-badge&labelColor=09090b)](./LICENSE)
[![Hardware: ESP32-S3](https://img.shields.io/badge/hardware-ESP32--S3-202020?style=for-the-badge&labelColor=09090b)](./knowledge/07-connected-robot-hardware-profile.md)
[![Avatar pack: 244.71 KB](https://img.shields.io/badge/avatar_pack-244.71_KB-202020?style=for-the-badge&labelColor=09090b)](./plans/reports/benchmark-avatar-perf.json)
[![Soul engine: 1.24 µs/tick host benchmark](https://img.shields.io/badge/soul_engine-1.24_us%2Ftick_host_benchmark-202020?style=for-the-badge&labelColor=09090b)](./plans/reports/benchmark-mochi-soul-engine.json)

![design:os by Jang](./docs/assets/brand/showcase.png)

Inspect USB-JTAG health, compile a 244.71 KB code-drawn face pack, and flash NVS at `0x9000`.
The Mochi-Soul engine holds a 4D state `S(t)=[E,V,B,C]` with a 60 Hz spring reflex.
Pin map and partition offsets are for `RB5320XZ78AI` (`ESP32-S3-WROOM-1U-N16R8`, ST7789 240×320).

## What you get

- **No-reset health audit.** Four layers in about 1.8 s.
- **NVS control.** `robotctl.py optimize --flash` writes the NVS partition at `0x9000` in 0.1 s.
- **Procedural Mochi-21 avatar.** 244.71 KB, −90.4% versus the default GIF pack.
- **Mochi-Soul engine.** 4D state `S(t)=[E,V,B,C]`, 1.24 µs/tick host benchmark, 0.81M ticks/s. SQLite WAL 2.52 µs/tx. Quiet hours 23:00-07:00. Proactive MCP/WebSocket bridge 1.22 ms HUD card. 60 Hz spring reflex 2.36 µs/frame.

Benchmarks are host-CPU numbers (Python 3 on a shared Linux x86 machine), not device speed. 1.24 µs/tick is the figure measured on 2026-11-03; repeat runs on an idle machine have given 0.73–0.76 µs, and the committed JSON in plans/reports/ comes from an earlier run (0.471 µs). Run `python3 tools/mochi-soul-engine/engine.py benchmark` to measure on your own machine.

## Quick start

Requires macOS or Linux, Python 3.10+, Pillow, esptool, and pyserial.

```bash
git clone https://github.com/jangtrinh/design-os-robotics.git
cd design-os-robotics
python3 -m pip install pillow esptool pyserial
```

1. **Health.** Run `./tools/robotctl.py health`.
2. **Compile.** Run `python3 tools/cook-procedural-avatar.py`.
3. **Verify.** Run the four benchmark suites.

```bash
python3 tools/benchmark-avatar-perf.py
python3 tools/mochi-soul-engine/engine.py benchmark
python3 tools/mochi-soul-engine/bridge.py benchmark
python3 tools/mochi-soul-engine/reflex_60fps.py
```

4. **Flash.** Run `./tools/robotctl.py optimize --flash`.

![Terminal health dashboard: four layers, no reset](./docs/assets/brand/health-dashboard.png)

## Supported hardware

| Item | Value |
|:---|:---|
| Board | RB5320XZ78AI |
| SoC | ESP32-S3-WROOM-1U-N16R8, 16 MB flash / 8 MB octal PSRAM |
| Display | ST7789 240×320 |
| DACs | MAX98357A + PCM5102A I2S |
| Microphone | INMP441 |
| Battery ADC | GPIO 17 |
| Charge detect | GPIO 38 |
| Assets partition | 0xAA0000 |
| NVS | 0x9000 |

## How it works

![Workflow: inspect, build, flash, verify](./docs/assets/brand/workflow.svg)

![Architecture of the toolchain, soul engine and board](./docs/assets/brand/architecture.svg)

`robotctl.py health` runs a four-layer audit without resetting the chip.

1. **Layer 1, physical and LAN.** USB-JTAG is opened with `~HUPCL` so DTR is never dropped. The tool resolves the device in the ARP table by its MAC and measures ping latency.
2. **Layer 2, cloud AI and weather.** TLS reachability to the voice server and Open-Meteo.
3. **Layer 3, NVS and assets.** NVS CRC32 plus the asset-partition checksum (`0x18AF` / `0x5867`).
4. **Layer 4, UART telemetry.** Passive 115200 baud logs for uptime, app state (`idle` / `listening` / `speaking`), and WARN/ERROR counters.

```bash
./tools/robotctl.py health
./tools/robotctl.py dashboard
./tools/robotctl.py status
./tools/robotctl.py optimize --flash
```

## Procedural Mochi-21 avatar

![21 code-drawn faces](./docs/assets/brand/faces-21.png)

Drawn entirely by code (`tools/cook-procedural-avatar.py`).
Full-bleed 240×240 on the 240×320 ST7789.
244.71 KB, 12-colour indexed LZW, checksum `0x5867`. Sources live in [./themes/procedural-mochi/](./themes/procedural-mochi/).

## Tools reference

| Tool | Role |
|:---|:---|
| `tools/robotctl.py` | NVS inspect and patch, OTA slot switch, four-layer health dashboard, and 240×320 theme flashing. |
| `tools/cook-assets-and-nvs.py` | Cooks a full-screen 240×320 `esp_mmap_assets` binary and a HUD-enabled NVS image. |
| `tools/cook-procedural-avatar.py` | Draws all 21 Procedural Mochi emotions in code and packs the 240×320 asset binary. |
| `tools/benchmark-avatar-perf.py` | Measures flash footprint, LZW/RLE, decode speed, and estimated SPI/CPU load for avatar packs. |
| `tools/voice-studio.py` | Extracts Ogg Opus streams from `ota_1`, builds studio reference audio, and writes custom wake-up responses. |
| `tools/patch-ota1-voice.py` | Synthesizes on-device voice prompts, encodes them as Ogg Opus, and patches them into the `ota_1` firmware with checksums. |
| `tools/xtensa-disasm.py` | Zero-dependency Xtensa LX7 disassembler and xref analyzer for ESP-IDF application partitions. |
| `tools/mochi-soul-engine/engine.py` | 4D homeostasis engine, 21-emotion router, SQLite WAL memory, and host benchmark suite. |
| `tools/mochi-soul-engine/bridge.py` | Proactive robot bridge, 240×320 HUD renderer, and `ota_1` protocol validator. |
| `tools/mochi-soul-engine/reflex_60fps.py` | 60 fps spring-damper face engine, audio RMS lip-sync, and C++17 header generator. |

## Repository map

```text
design-os-robotics/
├── README.md
├── CONTEXT.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── docs/                          GitHub Pages site and brand assets
├── plans/                         Specs, wayfinder map, and benchmark JSON
├── tools/                         Host CLI, compilers, and Mochi-Soul engine
├── themes/
│   ├── procedural-mochi/          21 code-drawn GIFs and contact sheet
│   └── procedural-mochi-fullvien-240x320.bin
├── knowledge/                     Hardware, NVS, MCP, Xtensa, and Mochi-Soul notes
└── profiles/
    └── example-esp32s3-n16r8/     Example board profile
```

## Safety and limits

Health checks are non-intrusive by design. The tools do not toggle DTR/RTS and do not reset the chip on a health run.

The pin map and partition offsets are calibrated for `RB5320XZ78AI` only. Back up NVS before flashing.

If you only need a browser reflash, or you are building firmware for a different board, you may not need this toolchain.

## Licence

Free to use, study and modify for personal, academic or internal commercial work. You may not resell it or offer a product that competes with it. See [PolyForm Shield 1.0.0](./LICENSE).

## Ecosystem

| Project | Domain | Link |
|:---|:---|:---|
| DESIGN:OS CLI | Multi-runtime design CLI for Claude Code, Codex and Antigravity | [jangtrinh.github.io/design-os](https://jangtrinh.github.io/design-os/) |
| OPAH ONE | 249g indoor drone showcase with scroll-scrub kinematics | [jangtrinh.github.io/design-os-drone-showcase](https://jangtrinh.github.io/design-os-drone-showcase/) |
| 3D Blender Agent | Mechanical parts generation with embedded Three.js CAD viewer | [jangtrinh.github.io/design-os-3d-blender](https://jangtrinh.github.io/design-os-3d-blender/) |
| SVG Animation Engine | Deterministic vector animation and 1080p 60fps video pipeline | [jangtrinh.github.io/design-os-svg-animation](https://jangtrinh.github.io/design-os-svg-animation/) |
| Knowledge Builder | Multimodal knowledge compiler with UKMC.v1 contract and epistemic gate | [jangtrinh.github.io/design-os-knowledge-builder](https://jangtrinh.github.io/design-os-knowledge-builder/) |
| Agent Teacher | Evidence-graded pedagogy library and curriculum tree runtime | [jangtrinh.github.io/design-os-pedagogy](https://jangtrinh.github.io/design-os-pedagogy/) |
| jang.work | Canonical portfolio, case studies and zero-chroma design language | [www.jang.work](https://www.jang.work/) |

## Support and contributing

If this toolchain saves you time on the board, you can support continued work.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-202020?style=for-the-badge&logo=buy-me-a-coffee&logoColor=white&labelColor=09090b)](https://www.buymeacoffee.com/jangtrinh)
