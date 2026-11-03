# 08 — System Optimization, Reverse-Engineered Firmware Laws & Session Mastery

> **Status**: Verified on physical `RoBot.5320` (`ESP32-S3-WROOM-1 N16R8`, MAC `AA:BB:CC:DD:EE:FF`, LAN IP `192.0.2.10`, active slot `ota_1` = Xiaozhi `v2.5.3`).

---

## 1. Hard Invariants Discovered in This Session (Never Repeat)

| # | Invariant | Root Cause / Hardware Proof | Enforced By |
|---|---|---|---|
| **1** | **Check `otadata` (`0xd000`) BEFORE analyzing or patching firmware** | `RoBot.5320` has dual OTA slots: `ota_0` (`0x20000`, `v2.0.5`) and `ota_1` (`0x560000`, Xiaozhi `v2.5.3`). `seq=1` in `otadata` boots `ota_1`. Guessing based on `ota_0` wastes flash cycles. | `tools/robotctl.py` + `tools/xtensa-disasm.py` |
| **2** | **Disable Ghost `0%` Battery via `p_bat = -1`, `p_chg = -1` in `board_cfg`** | Physical `RoBot.5320` uses a standalone TP4056 charger with NO battery voltage divider wired to `GPIO 1` (`ADC1_CH0`). In `ota_1` (`0x42023ce8`), `p_bat = 1` reads `0 mV` (`0%`) and renders a permanent `0%` icon. Only `p_bat < 0` (`-1`) skips `adc_oneshot`. | `tools/cook-assets-and-nvs.py` + `robotctl.py health` |
| **3** | **Never toggle `DTR` and `RTS` separately when opening `/dev/cu.usbmodem*` on macOS** | The ESP32-S3 dual-transistor auto-reset circuit pulls `EN = LOW` (reboot) whenever `(DTR=0, RTS=1)`. In `pyserial`, setting `s.dtr = False; s.rts = False` issues two separate `TIOCMBIC` ioctls, briefly creating `(DTR=0, RTS=1)` and resetting the chip. Opening with `os.open()` + raw `115200 8N1` + `~HUPCL` keeps `DTR == RTS` (`EN = HIGH`). | `tools/robotctl.py#probe_usb_and_serial` |
| **4** | **Always configure `B115200` (`8N1`, `~HUPCL`) on macOS USB-Serial open** | macOS `AppleUSBCDCACMData` defaults to `9600` baud on open, turning `115200`-baud ESP-IDF logs into `Vwkkog` / `wgkG` garbage. | `tools/robotctl.py#probe_usb_and_serial` |
| **5** | **Clone the exact 6-group Mochi emotion state table for full-bleed themes** | Mapping custom per-frame curves across 21 emotion keys causes rapid facial jitter during TTS/STT transitions. Grouping into the 6 canonical Mochi states (`neutral`, `happy`, `laughing`/`funny`/`wink`, `sad`/`crying`, `angry`/`shocked`, `sleepy`/`thinking`/`confused`) keeps transitions smooth. | `tools/cook-assets-and-nvs.py` |
| **6** | **Separate Local Wake Chime (`0000.p3`) from Cloud Conversational TTS (`xiaozhi.me`)** | `0000.p3` in the `assets` partition (`0x900000`) ONLY plays locally when `WakeNet9` detects the wake word (`"Hi, Tell me"` / `"Hello"`). The AI's conversational reply voice is streamed via Opus packets over `wss://api.tenclass.net/xiaozhi/v1/` and must be configured on the `xiaozhi.me` console (or self-hosted server). | `knowledge/07-connected-robot-hardware-profile.md` |
| **7** | **Always use `arp -an` (never `arp -a`) on macOS LAN probes** | `arp -a` blocks >2.0s on reverse DNS lookups for local LAN peers; `arp -an` resolves in <5ms. Combine with a 1-packet ICMP ping (`192.0.2.10`) to refresh expired macOS ARP entries. | `tools/robotctl.py#_lookup_arp` |

---

## 2. Reverse-Engineered `ota_1` (`v2.5.3` @ `0x560000`) Code Map

Use [`tools/xtensa-disasm.py`](file:///Users/jangtrinh/Products/design-os-robotics/tools/xtensa-disasm.py) on [`profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-0x560000.bin`](file:///Users/jangtrinh/Products/design-os-robotics/profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-0x560000.bin):

| Symbol / Method | Virtual Address (`IROM` / `DROM`) | Behavior & NVS Keys |
|---|---|---|
| `LcdDisplay` vtable | `0x3c294808` (`DROM`) | `[5]=0x42019338` (`SetEmotion`), `[8]=0x42016dd4` (`ClearChatMessages`), `[11]=0x4201b724` (`UpdateStatusBar`), `[38]=0x42016244` (`ShowIdleWeather`), `[39]=0x42016164` (`HideIdleWeather`) |
| `LcdDisplay::UpdateStatusBar` | `0x4201b724..0x4201bb40` | Reads battery level via board vtable (`+64`), updates battery icon (`0x4201b7bc`), checks `tm_year >= 125` (`2025`), and handles `enable_weather` idle transition. |
| `Board::InitBatteryMonitor` | `0x42023c6c..0x4202400c` | Reads `p_bat` and `p_chg` from NVS namespace `board_cfg`. If `p_bat >= 0`, initializes `adc_oneshot` on `GPIO 1` and logs `Battery monitor on ADC GPIO %d`. If `p_bat < 0` (`-1`), disables battery ADC completely (`GetBatteryLevel` returns `false`). |
| `Application::UpdateIdleWeather` | `0x4202b5a8..0x4202b99c` | Fetches Open-Meteo (`api.open-meteo.com`) and calls `LcdDisplay::ShowIdleWeather()` (`WeatherUI::Create` at `0x42048248`). |
| `Application::CheckNewVersion` | `0x4202bcb8..0x4202be86` | Queries `https://xiaozhi-api.tandev282.workers.dev/ota` with exponential backoff (`10s -> 20s -> 40s ...`, up to 10 retries) before calling `InitializeProtocol` (`0x4202bed4`). |

---

## 3. Standard Tooling Commands

```bash
# 1. Non-intrusive health check (USB-Serial + LAN + Cloud + NVS + Assets)
python3 tools/robotctl.py health

# 2. Live telemetry dashboard (2s refresh)
python3 tools/robotctl.py watch

# 3. Rebuild & verify Shouto Mochi assets + NVS image
python3 tools/cook-assets-and-nvs.py

# 4. Disassemble or search xrefs in ota_1 firmware
python3 tools/xtensa-disasm.py strings profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-0x560000.bin "Battery"
python3 tools/xtensa-disasm.py xrefs profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-0x560000.bin 0x3c278cf2
python3 tools/xtensa-disasm.py disasm profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-0x560000.bin 0x42023c6c 0x42023f00
```

## See Also
- [`knowledge/07-connected-robot-hardware-profile.md`](file:///Users/jangtrinh/Products/design-os-robotics/knowledge/07-connected-robot-hardware-profile.md)
- [`plans/reports/retro-261103-0739-robot5320-firmware-tailoring.md`](file:///Users/jangtrinh/Products/design-os-robotics/plans/reports/retro-261103-0739-robot5320-firmware-tailoring.md)
