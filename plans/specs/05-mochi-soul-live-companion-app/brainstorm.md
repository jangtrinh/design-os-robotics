# Brainstorm — Spec 05: Mochi-Soul Live Companion Studio & Local Protocol Hub (`05-mochi-soul-live-companion-app`)

## 1. Press Release (Working Backwards)
**FOR IMMEDIATE RELEASE** — **DESIGN:OS Robotics Ships `Mochi-Soul Studio` (`app.py`), Unifying 4D Biological Homeostasis, 60fps Spring Reflex, Local Xiaozhi OTA/MCP Protocol Hub, and Live `RB5320XZ78AI` Hardware Telemetry into a Single Zero-Dependency Application on Port `4185`.**

Previously, developers working with the `RB5320XZ78AI` (`ESP32-S3 N16R8` + `ST7789 240×320`) had four high-speed standalone modules (`cook-procedural-avatar.py`, `engine.py`, `bridge.py`, and `reflex_60fps.py`), but lacked a unified runtime daemon and interactive control studio that connected them to live developer workflows (`git commit`, test runs, Pomodoro focus) and live USB/LAN hardware telemetry (`robotctl.py`)—especially when working remotely.

With **Spec 05 (`tools/mochi-soul-engine/app.py`)**, running a single command launches:
1. **A Unified Full-Stack Soul Runtime**: Couples the 4D Homeostasis ODE solver (`engine.py`), 10-DOF `60fps` spring physics & lip-sync engine (`reflex_60fps.py`), and `ota_1` (`v2.5.3`) Proactive Bridge + 32-tool MCP dispatcher (`bridge.py`) with sub-millisecond end-to-end latency.
2. **A Local OTA & Workspace Symbiosis API (`http://localhost` on port `4185`)**: Serves the exact `Xiaozhi v2.5.3` `POST /ota` discovery contract for local protocol hijack alongside REST endpoints (`/api/status`, `/api/interact`, `/api/reflex`, `/api/workspace-event`, `/api/mcp`, `/api/hud.png`, `/api/hardware`) for feeding Mochi via real `git commit`, CI/CD test results, or Pomodoro events.
3. **An Interactive Browser Companion Cockpit & `60fps` `240×320` ST7789 Simulator**: Lets the developer see Mochi's live `240×320` screen, trigger all 21 procedural emotions, test HC-SR04 ultrasonic proximity (`2–200 cm`) and 16kHz audio lip-sync, dispatch 6-DOF Otto quadruped servo choreographies, inspect live outbound `OnIncomingJson` packets, and monitor physical USB-JTAG / Wi-Fi LAN hardware health in real time.

---

## 2. User Stories & MoSCoW Prioritization

| ID | User Story | Priority | Target Metric |
|---|---|---|---|
| **US-01** | As a remote or deskside hardware engineer, I want a single daemon (`app.py`) that integrates `engine.py`, `bridge.py`, `reflex_60fps.py`, and `robotctl.py` behind a clean HTTP/JSON + OTA server on port `4185`. | **MUST** | Full-stack tick + packet synthesis `< 0.25 ms` (`> 4,000 Hz` throughput) |
| **US-02** | As a developer practicing Workspace Symbiosis, I want `git commit`, test pass/fail, and Pomodoro events to feed/stimulate Mochi's 4D homeostasis and emit valid `ota_1` (`notify`, `alert`, `llm`, `mcp`) packets. | **MUST** | `100%` valid `OnIncomingJson` packets + SQLite WAL persistence |
| **US-03** | As a remote developer without physical eye contact with the LCD, I want a real-time browser Companion Studio (`GET /` on port `4185`) with a `60fps` `240×320` ST7789 canvas, 4D gauges, 21 emotion triggers, HC-SR04 slider, 6-DOF Otto servo deck, and live `robotctl.py` hardware telemetry. | **MUST** | `0` console/page errors, `< 2 ms` API RTT on loopback |
| **US-04** | As an engineer reverse-engineering `ota_1` (`v2.5.3`), I want `POST /ota` to return a spec-compliant local WebSocket/MQTT discovery payload so `RoBot.5320` can be redirected to the local Mac hub. | **SHOULD** | Valid JSON matching `0x4202be10` OTA parser |
