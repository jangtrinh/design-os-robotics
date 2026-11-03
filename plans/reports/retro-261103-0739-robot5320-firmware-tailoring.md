# Session Retro — `RoBot.5320` Firmware Reverse Engineering, Mochi Theme & Hardware Tailoring

- **Date**: `2026-11-03 07:39 +07:00`
- **Project**: `design-os-robotics` (`RoBot.5320`, ESP32-S3 `AA:BB:CC:DD:EE:FF`, Xiaozhi `v2.5.3` `ota_1`)
- **Trajectory span**: `1,607` steps · `562` `run_command` calls · `39` user messages · `13` flash cycles

---

## 1. Measure First (FACT Table)

| Cost bucket | Count | Root cause (one clause) |
|---|---:|---|
| Repeated scans / inline disassemblers before mutation | **51** | No standalone Xtensa LX7 disassembler script existed in `tools/`, so a 90-line inline `python3 -c` decoder was re-pasted 51 times. |
| Reruns caused by guessed firmware/hardware anatomy | **13** | Flashed NVS/assets on hypotheses (`ota_0` vs `ota_1`, `u_wch`, `0%` battery) before disassembling `07-ota1-v2.5.3-0x560000.bin` (`0x42023ce8` & `0x4201b724`). |
| Command / shell escaping errors (`code 1`) | **59** | Multi-line `python3 -c '...'` scripts hit bash quote escaping (`SyntaxError`) and unbounded C-string slicing (`data.find(b"\x00")` returning `-1` -> 21MB stdout). |
| USB-Serial probe side-effects (`serial_calls`) | **47** | Opening `/dev/cu.usbmodem*` on macOS defaulted to `9600` baud (`Vwkkog` garbage) and dropping `DTR` before `RTS` (`pyserial` `s.dtr=False; s.rts=False` or missing `~HUPCL`) pulled `EN=LOW` and reset the ESP32-S3. |
| Fix rounds found only on physical device | **5** | Theme state jitter, local wake chime vs cloud TTS mismatch, acoustic echo cut-off, `0%` ghost battery (`p_bat=1` floating ADC), and `arp -a` DNS timeout. |
| Owner questions / corrections — changed outcome | **8 / 8** | Every owner intervention redirected from symptom-patching to root-cause architecture (cloning Mochi's 6-group state table, separating local wake chime from cloud TTS, disabling `p_bat`/`p_chg`). |

---

## 2. Edit-Rows Table (Harness² Reflector Discipline)

| Component | Change | Observed | Verdict |
|---|---|---|---|
| `tools/cook-assets-and-nvs.py` | Cloned exact 6-group emotion mapping from original Mochi theme into Shouto Mochi (`26` assets) + `0000.p3` | Eliminated rapid emotion state jitter during speech/idle transitions | `helped` |
| `profiles/example-esp32s3-n16r8/nvs-hud-enabled.bin` | Patched `board_cfg` NVS slots 113–114: `p_bat = -1`, `p_chg = -1` (instead of `GPIO 1` / `GPIO 14`) | Disassembly at `0x42023ce8` proved `p_bat < 0` skips `adc_oneshot`; removed `0%` ghost battery permanently | `helped` |
| `tools/robotctl.py#probe_usb_and_serial` | Forced raw `115200 8N1` + `~HUPCL` on `os.open` without separate `DTR`/`RTS` ioctl calls | Stopped accidental ESP32-S3 reboots and `9600`-baud garbled serial logs during `health`/`watch` | `helped` |
| `tools/robotctl.py#_lookup_arp` | Replaced `arp -a` with `arp -an` + automatic ICMP ARP refresh to `192.0.2.10` | Eliminated 2.0s reverse-DNS timeout and false `[ FAIL ] Wi-Fi LAN` after macOS ARP cache expiry | `helped` |
| `tools/xtensa-disasm.py` | Extracted permanent CLI disassembler (`disasm`, `strings`, `xrefs`, `vtable`) with bounded C-string slicing | Replaces 51 inline `python3 -c` disassembler invocations and prevents `find() == -1` 21MB stdout explosions | `helped` |

---

## 3. Debate Table (Keep / Drop & Routing)

| # | Proposal | Scope | Form | For (evidence count) | Against | Verdict | Destination |
|---|---|---|---|---|---|---|---|
| **A** | Extract standalone `tools/xtensa-disasm.py` CLI (`disasm`, `xrefs`, `vtable`, bounded C-strings) | `INV` | `script` | **51** inline disasm runs + **1** 21MB stdout hang (`step 1526`) | None — deterministic zero-dependency Python tool | **Do** | `tools/xtensa-disasm.py` |
| **B** | Enforce macOS ESP32-S3 USB-Serial no-reset contract (`115200 8N1`, `~HUPCL`, never set `DTR=0` while `RTS=1`) | `DOM` | `script` | **47** serial probes; `pyserial` `s.dtr=False; s.rts=False` caused unintended reset at `step 1432` | None | **Do** | `tools/robotctl.py` + `knowledge/08-system-optimization-and-complete-mastery.md` |
| **C** | Disassemble active OTA partition (`otadata` -> `ota_0`/`ota_1`) BEFORE flashing any NVS key hypothesis | `INV` | `skill` / doc | **13** flash cycles; guessing `u_wch` wasted 3 rounds before `0x42023ce8` revealed `p_bat = -1` | Adds ~30s static analysis before first flash | **Do** | `.project-agent.md` + `knowledge/08-system-optimization-and-complete-mastery.md` |
| **D** | Document 2-layer Voice Architecture (ESP32 `0000.p3` local wake chime vs `xiaozhi.me` server TTS/Voice Clone) | `DOM` | `script` / doc | **4** rounds spent debugging why changing `0000.p3` didn't change AI conversational voice (`step 940`) | None | **Do** | `knowledge/08-system-optimization-and-complete-mastery.md` |
| **E** | Always use `arp -an` (never `arp -a`) on macOS LAN probes | `INV` | `script` | `arp -a` blocked >2.0s on reverse DNS (`step 1585`), causing false LAN failure | None | **Do** | `tools/robotctl.py` |

---

## 4. Behaviour Changes (Agent Operating Discipline)

1. **When investigating ESP32 firmware behavior** → First check `otadata` (`0xd000`) to identify the active slot (`ota_0` vs `ota_1`), then run `python3 tools/xtensa-disasm.py` on that partition before modifying NVS or assets → Saves ~8–10 flash cycles and ~30k tokens per bug.
2. **When opening `/dev/cu.usbmodem*` on macOS** → Never use `pyserial` `s.dtr = False; s.rts = False` (which issues two separate `TIOCMBIC` ioctls and transiently sets `DTR=0, RTS=1` -> `EN=LOW` reset); always use `os.open()` with raw `115200 8N1` + `~HUPCL` via `tools/robotctl.py` → Zero unintended reboots.
3. **When the owner flags a repeat error loop (`step 758`)** → Stop mutating immediately, switch to static binary disassembly (`L32R` string -> function -> NVS key), and falsify the hypothesis before touching flash.

---

## 5. Đã lưu ở đâu (Persisted Artifacts)

- **Retro Report**: [`plans/reports/retro-261103-0739-robot5320-firmware-tailoring.md`](file:///Users/jangtrinh/Products/design-os-robotics/plans/reports/retro-261103-0739-robot5320-firmware-tailoring.md)
- **Standalone Xtensa Disassembler CLI**: [`tools/xtensa-disasm.py`](file:///Users/jangtrinh/Products/design-os-robotics/tools/xtensa-disasm.py)
- **Non-Intrusive Health & Telemetry CLI**: [`tools/robotctl.py`](file:///Users/jangtrinh/Products/design-os-robotics/tools/robotctl.py)
- **Deterministic Asset & NVS Cooker**: [`tools/cook-assets-and-nvs.py`](file:///Users/jangtrinh/Products/design-os-robotics/tools/cook-assets-and-nvs.py)
- **Hardware & Firmware Mastery Guide**: [`knowledge/08-system-optimization-and-complete-mastery.md`](file:///Users/jangtrinh/Products/design-os-robotics/knowledge/08-system-optimization-and-complete-mastery.md) & [`knowledge/07-connected-robot-hardware-profile.md`](file:///Users/jangtrinh/Products/design-os-robotics/knowledge/07-connected-robot-hardware-profile.md)
- **Project Agent Contract**: [`.project-agent.md`](file:///Users/jangtrinh/Products/design-os-robotics/.project-agent.md)
