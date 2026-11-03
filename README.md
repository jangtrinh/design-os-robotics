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
![Hardware: ESP32-S3](https://img.shields.io/badge/hardware-ESP32--S3-202020?style=for-the-badge&labelColor=09090b)
![Avatar pack: 244.71 KB](https://img.shields.io/badge/avatar_pack-244.71_KB-202020?style=for-the-badge&labelColor=09090b)
![Soul engine: ~0.76 µs/tick median, measured idle](https://img.shields.io/badge/soul_engine-%7E0.76_us%2Ftick_median_idle-202020?style=for-the-badge&labelColor=09090b)

Inspect USB-JTAG health, compile a 244.71 KB code-drawn face pack, and flash NVS at `0x9000`.
The Mochi-Soul engine holds a 4D state `S(t)=[energy, hunger, bond, mood]` (mood = valence and arousal) with a 60 Hz spring reflex.
Pin map and partition offsets are for `RB5320XZ78AI` (`ESP32-S3-WROOM-1U-N16R8`, ST7789 240×320).

## What you get

- **No-reset health audit.** Four non-intrusive layers via `robotctl.py health`.
- **NVS control.** `robotctl.py optimize --flash` writes the NVS partition at `0x9000` (needs your own NVS dump).
- **Procedural Mochi-21 avatar.** 21 faces in 244.71 KB of GIFs, −90.4% versus the default pack's 21 GIFs.
- **Mochi-Soul engine.** 4D state `S(t)=[energy, hunger, bond, mood]` (mood = valence and arousal), ~0.76 µs/tick (median of 12 runs, measured idle), 1.31M ticks/s. SQLite WAL ~4.0 µs/tx (median of 12 runs). Quiet hours 23:00–07:30. Proactive MCP/WebSocket bridge 1.22 ms HUD card (single run). 60 Hz spring reflex 2.36 µs/frame (single run).

Benchmark sources and caveats are listed under [Benchmarks](#benchmarks).

## Quick start

Requires macOS or Linux and Python 3.10+, with Pillow for the image tools and pyserial for the serial probe. These five commands run and exit 0 on a clean clone:

```bash
git clone https://github.com/jangtrinh/design-os-robotics.git
cd design-os-robotics
python3 -m pip install pillow pyserial
python3 tools/robotctl.py health
python3 tools/mochi-soul-engine/engine.py benchmark
```

`health` exits 0 with or without a board. With no board connected, the USB-JTAG, Wi-Fi and some NVS rows show FAIL. It contacts the voice server and Open-Meteo over the network. `engine.py benchmark` overwrites the committed `plans/reports/benchmark-mochi-soul-engine.json`; restore it with `git checkout plans/reports`.

### Flashing and NVS backup

> **Back up NVS before you flash.** `optimize --flash` writes the NVS partition at `0x9000`, which holds the board's saved settings, Wi-Fi included. Read that partition back from the board with esptool first, using the partition size from your own partition table, and keep the file.

The avatar build and the flash step read your own device dumps. Dumps and built `.bin` files are gitignored and are not in the repository:

- `python3 tools/cook-procedural-avatar.py` needs your dump of the assets partition at `profiles/example-esp32s3-n16r8/partitions/08-assets-0xAA0000.bin` (or pass `--base-bin`). Without it the script prints an error and exits with status 2. It builds `themes/procedural-mochi-fullvien-240x320.bin` locally; that file is not tracked. The finished GIFs are already committed in `themes/procedural-mochi/`.
- `robotctl.py status`, `optimize` and `optimize --flash` read your own dump of the NVS partition at `profiles/example-esp32s3-n16r8/partitions/03-nvs-0x009000.bin` (`--nvs` for `status`, `--base-nvs` for `optimize`). Without it they print how to read the partition from your board and exit with status 2. `--flash` then writes only NVS at `0x9000`, through `uvx esptool`, so it needs [uv](https://docs.astral.sh/uv/).

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

## Real hardware

Photos of the physical RB5320XZ78AI build, taken by the repository owner. The network name, setup address, serial prints and QR codes are blurred or covered by a solid bar. Third-party silkscreen art (a ring logo, a poster and a lion drawing, on the board edge and in the line-art drawings shown on the screen) is blurred in every photo where it appears. Photo 05 (back of the board) shows none, and the files carry no metadata. Select a photo for the full-size version.

<table>
<tr>
<td align="center" width="33%"><a href="./docs/assets/hardware/real/01-face-listening.webp"><img src="./docs/assets/hardware/real/01-face-listening-thumb.webp" alt="design:os by Jang. Real hardware: the robot board on a wooden desk, its 240x320 screen showing a white Mochi face with closed smiling eyes and the Vietnamese status text Đang lắng nghe (listening), with USB cables and earphones around it" width="240"></a><br><sub>design:os by Jang · Listening face</sub></td>
<td align="center" width="33%"><a href="./docs/assets/hardware/real/02-face-bokeh.webp"><img src="./docs/assets/hardware/real/02-face-bokeh-thumb.webp" alt="design:os by Jang. Real hardware: close, low-angle view of the same board with a shallow depth of field, the screen showing a calm white Mochi face with closed eyes, a USB-C cable plugged in below" width="240"></a><br><sub>design:os by Jang · Calm face, close view</sub></td>
<td align="center" width="33%"><a href="./docs/assets/hardware/real/03-uwu-board-bg.webp"><img src="./docs/assets/hardware/real/03-uwu-board-bg-thumb.webp" alt="design:os by Jang. Real hardware: the board held upright on a desk, the screen showing a dark interface with two green U-shaped eyes above a line-art board drawing" width="240"></a><br><sub>design:os by Jang · Dark interface on the screen</sub></td>
</tr>
<tr>
<td align="center" width="33%"><a href="./docs/assets/hardware/real/04-chat-bubble.webp"><img src="./docs/assets/hardware/real/04-chat-bubble-thumb.webp" alt="design:os by Jang. Real hardware: the board on a desk with a chat bubble of Vietnamese text across the bottom of the screen, a face and line art above it" width="240"></a><br><sub>design:os by Jang · Chat bubble on the screen</sub></td>
<td align="center" width="33%"><a href="./docs/assets/hardware/real/05-back-hardware.webp"><img src="./docs/assets/hardware/real/05-back-hardware-thumb.webp" alt="design:os by Jang. Real hardware: the back of the robot held in a hand, showing an ESP32-S3 module with two USB-C ports, a round speaker, three push buttons, two purple I2S audio breakout boards and a blue charging board" width="240"></a><br><sub>design:os by Jang · Back of the board</sub></td>
<td align="center" width="33%"><a href="./docs/assets/hardware/real/06-wifi-setup.webp"><img src="./docs/assets/hardware/real/06-wifi-setup-thumb.webp" alt="design:os by Jang. Real hardware: the board held in a hand, the screen showing the Wi-Fi setup page titled Chế độ cấu hình Wi-Fi; the network name and setup address are covered by a black bar" width="240"></a><br><sub>design:os by Jang · Wi-Fi setup screen (details covered)</sub></td>
</tr>
</table>

## How it works

![Workflow: inspect, build, flash, verify](./docs/assets/brand/workflow.svg)

![Architecture of the toolchain, soul engine and board](./docs/assets/brand/architecture.svg)

`robotctl.py health` runs a four-layer audit without resetting the chip.

1. **Layer 1, physical and LAN.** USB-JTAG is opened with `~HUPCL` so DTR is never dropped. The tool resolves the device in the ARP table by its MAC and measures ping latency.
2. **Layer 2, cloud AI and weather.** TLS reachability to the voice server and Open-Meteo.
3. **Layer 3, NVS and assets.** NVS CRC32 plus the asset-partition checksum (`0x5867`).
4. **Layer 4, UART telemetry.** Passive 115200 baud logs for uptime, app state (`idle` / `listening` / `speaking`), and WARN/ERROR counters.

```bash
python3 tools/robotctl.py health
python3 tools/robotctl.py dashboard
```

`dashboard` refreshes the same audit live until you press Ctrl+C. `status` and `optimize` need the NVS dump described under [Flashing and NVS backup](#flashing-and-nvs-backup).

## Procedural Mochi-21 avatar

![21 code-drawn faces](./docs/assets/brand/faces-21.png)

Drawn entirely by code. The GIFs in `themes/procedural-mochi/` come from `tools/cook-procedural-avatar.py`; running that script needs your own assets dump (see [Flashing and NVS backup](#flashing-and-nvs-backup)). The packed `.bin` is built locally and is not tracked.
Full-bleed 240×240 on the 240×320 ST7789. 8-colour indexed LZW, checksum `0x5867`.

Size: **250,580 bytes = 244.71 KiB** (this repo writes KiB as "KB"). That is the 21 unique emotion GIFs added together, and it is the `total_gif_bytes` value in `plans/reports/benchmark-avatar-perf.json`. Running `tools/cook-procedural-avatar.py` on the committed sources reproduces all 21 GIFs byte for byte. Two other numbers measure different things:

- `themes/procedural-mochi/` holds 272,760 bytes in 22 GIFs: the 21 emotion GIFs (250,580 bytes) plus `mochi_60fps_spring_transition.gif` (22,180 bytes), a demo written by `tools/mochi-soul-engine/reflex_60fps.py`.
- The packed assets `.bin` was 2,092,592 bytes in the benchmark run. It holds the GIFs and everything else packed with them, and lists `robot_2` as a second entry that reuses the neutral GIF. It is built locally and not tracked.

## Benchmarks

Benchmarks are host-CPU numbers (Python 3 on a Linux x86 VM), not device speed. The JSON reports are in this repository:

- `plans/reports/benchmark-avatar-perf.json`: total size of the 21 emotion GIFs, 244.71 KB versus 2,560.27 KB for the 21 GIFs of the default pack.
- `plans/reports/benchmark-mochi-soul-engine.json`: a single run, 0.765 µs/tick, 1.31M ticks/s, 3.84 µs per SQLite WAL write.
- `plans/reports/benchmark-mochi-soul-engine-idle-runs.json`: 12 repeated runs with machine spec, per-run load and the outlier rule.

The repeated-run figures (ticks and SQLite writes) use one method: the median of all 12 runs. Ticks: 0.76 µs/tick (range 0.70–1.50). Writes: ~4.0 µs/tx (range 3.6–6.6). Outliers stay in and are disclosed: runs 8 and 9 for ticks (about 1.5 µs/tick), runs 5 and 9 for writes (about 6.5 µs). Without the two tick outliers the tick median is 0.754. The outlier rule (above 1.5× the all-12 median) was set after the data had been seen, and its threshold comes from the same data, so it describes the runs; it is not a pre-registered test. The recorded load average does not explain the outliers. The VM was not dedicated, so "idle" means no heavy work was competing for the benchmark core. The other figures on this page, 2.36 µs/frame (`benchmark-reflex-60fps.json`) and 1.22 ms per HUD card (`benchmark-proactive-bridge.json`), are single runs, not medians.

Four suites run and exit 0 on a clean clone:

```bash
python3 tools/mochi-soul-engine/engine.py benchmark
python3 tools/mochi-soul-engine/reflex_60fps.py
python3 tools/mochi-soul-engine/bridge.py benchmark
python3 tools/benchmark-avatar-perf.py
```

`tools/benchmark-avatar-perf.py` needs no `.bin` pack: when none is present it benchmarks the committed GIFs in `themes/procedural-mochi/` and shows `n/a` for the flash-image rows. With a locally built pack it also reports flash footprint. The first three suites overwrite their committed JSON reports (and `bridge.py benchmark` the HUD card PNG in `plans/reports/`); restore them with `git checkout plans/reports`.

## Voice

The voice pipeline itself is not part of this repository: there is no speech recognition, text-to-speech or voice-cloning code here. What the repository touches:

- **Audio hardware.** INMP441 microphone, MAX98357A and PCM5102A I2S DACs (see [Supported hardware](#supported-hardware)).
- **Health checks.** `robotctl.py health` checks TLS reachability to the voice server and never toggles DTR/RTS, so a health run does not reset the chip during a voice conversation.
- **Lip-sync.** `tools/mochi-soul-engine/reflex_60fps.py` turns an audio RMS value into the mouth-open channel of the face.
- **Bridge.** `tools/mochi-soul-engine/bridge.py` validates the `notify`, `alert`, `llm`, `tts` and `mcp` JSON messages.

## Tools reference

| Tool | Role |
|:---|:---|
| `tools/robotctl.py` | NVS inspect and patch, OTA slot switch, four-layer health dashboard, and 240×320 theme flashing. |
| `tools/cook-assets-and-nvs.py` | Cooks a full-screen 240×320 `esp_mmap_assets` binary and a HUD-enabled NVS image. Takes no options: it reads fixed paths under `themes/` and `profiles/`, and any extra argument is rejected with exit code 2 (`--help` prints this). |
| `tools/cook-procedural-avatar.py` | Draws all 21 Procedural Mochi emotions in code and packs the 240×320 asset binary. Needs your own assets dump; the `.bin` it builds is local and not tracked. |
| `tools/benchmark-avatar-perf.py` | Measures flash footprint, LZW/RLE, decode speed, and estimated SPI/CPU load for avatar packs. Runs without a `.bin` by reading the committed GIFs. |
| `tools/xtensa-disasm.py` | Zero-dependency Xtensa LX7 disassembler and xref analyzer for ESP-IDF application partitions. |
| `tools/mochi-soul-engine/engine.py` | 4D homeostasis engine, 21-emotion router, SQLite WAL memory, and benchmark suite. |
| `tools/mochi-soul-engine/bridge.py` | Proactive robot bridge, 240×320 HUD renderer, and `ota_1` protocol validator. |
| `tools/mochi-soul-engine/reflex_60fps.py` | 60 fps spring-damper face engine, audio RMS lip-sync, and C++17 header generator. |
| `tools/mochi-soul-engine/app.py` | Spec 05 Live Companion Studio server, local `ota_1` / MCP protocol hub, workspace symbiosis runtime, and `--benchmark` suite (`plans/reports/benchmark-live-companion-app.json`, single run). |
| `tools/mochi-soul-engine/studio.html` | Operate-mode browser companion studio for the 240×240 Mochi-21 OLED face, 4D homeostasis register, custom DS sensor scrubbers, and 6-DOF Otto MCP deck. |

## Repository map

```text
design-os-robotics/
├── README.md
├── CONTEXT.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── docs/                          GitHub Pages site, brand assets, ART-DIRECTION.md
├── plans/                         Internal notes; benchmark JSON in plans/reports/
├── tools/                         Host CLI, compilers, and Mochi-Soul engine
├── themes/
│   ├── procedural-mochi/          22 GIFs: 21 code-drawn faces and a spring transition
│   └── (procedural-mochi-fullvien-240x320.bin: built locally by tools/cook-procedural-avatar.py, not tracked)
├── knowledge/                     Internal research notes
└── profiles/
    └── example-esp32s3-n16r8/     Example board profile
```

## Safety and limits

Health checks are non-intrusive by design. The tools do not toggle DTR/RTS and do not reset the chip on a health run.

The pin map and partition offsets are calibrated for `RB5320XZ78AI` only. Back up NVS before flashing (see [Flashing and NVS backup](#flashing-and-nvs-backup)).

If you only need a browser reflash, or you are building firmware for a different board, you may not need this toolchain.

## Licence

PolyForm Shield 1.0.0, source-available. Any purpose is permitted except providing a product that competes with this software, or with a product the licensor provides using it. You may use, study, modify and distribute it if you keep the licence terms (or their URL) and the `Required Notice:` line. The [LICENSE](./LICENSE) text is the only binding statement; this paragraph is a summary.

Third-party works in this repository keep their own licences: the Be Vietnam Pro typeface (SIL OFL 1.1) and three.js r186 (MIT). The one hardware wiring image is the owner's own material and is covered by the licence above. See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).

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

## Credits

- Design and code: Jang Trinh ([@jangtrinh](https://github.com/jangtrinh)).
- Be Vietnam Pro typeface, © The Be Vietnam Pro Project Authors, SIL Open Font License 1.1, self-hosted under `docs/assets/fonts/`.
- three.js (MIT) powers the 3D viewer on the docs site.
- Badges are rendered by [shields.io](https://shields.io/).
- Making an image, diagram, promo or motion? Follow [docs/ART-DIRECTION.md](./docs/ART-DIRECTION.md): colour and type tokens, logo, faces, asset specs, data and privacy rules.

Full third-party details: [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
