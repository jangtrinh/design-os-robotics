# Use Cases & Gherkin Acceptance Criteria — Spec 05 (`05-mochi-soul-live-companion-app`)

## UC-01: End-to-End Unified Soul Tick & Workspace Symbiosis Event
- **Actor**: Developer / CI Hook / Companion UI
- **Preconditions**: `MochiCompanionApp` initialized with SQLite WAL database (`engine.py`), `XiaozhiProactiveBridge` (`bridge.py`), and `EmbodiedReflexEngine` (`reflex_60fps.py`).
- **Flow**:
  1. Actor triggers an interaction (`feed`, `pet`, `play`, `wake`, `sleep`, `dream`) or a Workspace Symbiosis event (`git_commit`, `test_pass`, `test_fail`, `pomodoro_complete`, `agent_approval_needed`).
  2. `MochiCompanionApp` updates the 4D Homeostasis vector $S(t) = [E, V, B, C]^T$, steps the 10-DOF spring target to the resulting 21-emotion keyframe, synthesizes the corresponding `ota_1` `OnIncomingJson` packet list (`notify`, `alert`, `llm`, `mcp` servo/LED choreography), and appends the packet trace to the live ring buffer.

### Gherkin `AC-01` (Unified Pipeline Latency & Workspace Symbiosis Completeness)
```gherkin
Given a running MochiCompanionApp instance combining Spec 02, Spec 03, and Spec 04
When 500 mixed user interactions and Workspace Symbiosis events (git_commit, test_pass, test_fail, pomodoro_complete, agent_approval_needed) are dispatched
Then 100% of events must mutate the 4D state vector, update the 10-DOF spring target, and emit 100% schema-valid ota_1 JSON packets
And the mean end-to-end processing time per unified event must be < 250 microseconds (> 4,000 events/sec).
```

---

## UC-02: Local `ota_1` (`v2.5.3`) OTA Discovery & HTTP Loopback API Performance
- **Actor**: `RoBot.5320` Firmware (`POST /ota`) or Browser Companion Studio (`/api/*`)
- **Flow**:
  1. `POST /ota` receives device MAC / board metadata headers (`Device-Id`, `Client-Id`) and returns the exact `Xiaozhi v2.5.3` OTA JSON structure (`websocket.url`, `websocket.token`, `server_time`, `firmware`).
  2. `GET /api/status`, `POST /api/interact`, `POST /api/workspace-event`, `POST /api/reflex`, `POST /api/mcp`, `GET /api/hud.png`, and `GET /api/hardware` serve live JSON/PNG responses.

### Gherkin `AC-02` (HTTP API & Local OTA Discovery Benchmark)
```gherkin
Given the Mochi-Soul Live Companion HTTP server listening on localhost
When benchmarked across GET /api/status, POST /api/interact, POST /api/workspace-event, POST /api/reflex, POST /ota, and GET /api/hud.png
Then 100% of responses must return HTTP 200 with valid JSON or PNG payloads
And mean HTTP loopback round-trip latency for JSON endpoints must be < 2.0 ms (and < 5.0 ms for dynamic 240x320 PNG HUD rendering).
```

---

## UC-03: Real-Time `60fps` Ultrasonic Reflex, Lip-Sync & 32-Tool MCP Dispatch
- **Actor**: Ultrasonic Sensor (`HC-SR04`) / Audio Stream / Companion UI
- **Flow**:
  1. Submitting distance (`cm`) and audio RMS frame via `POST /api/reflex` steps the 10-DOF spring physics at `60Hz`, computes lip-sync jaw aperture, and triggers autonomous proximity reflexes (`startled_back` at `< 8 cm`, `curious_greet` at `< 25 cm`).
  2. Submitting any of the 32 reverse-engineered MCP tools (`self.Otto.*`, `self.led.*`, `self.screen.*`, `self.audio_speaker.*`) via `POST /api/mcp` generates a spec-compliant JSON-RPC 2.0 packet and updates simulated actuator state.

### Gherkin `AC-03` (Reflex & 32-Tool MCP Dispatcher Integrity)
```gherkin
Given the Embodied Reflex and MCP Dispatcher endpoints (/api/reflex and /api/mcp)
When swept across HC-SR04 distances (3 cm to 150 cm), 16kHz audio RMS envelopes, and all 6 Otto quadruped & peripheral MCP tool families
Then proximity reflexes (< 8 cm startled, < 25 cm curious) and JSON-RPC 2.0 MCP packets must be 100% deterministic with zero invalid payloads.
```

---

## UC-04: Interactive Browser Companion Cockpit & Hardware Link (`http://localhost` on port `4185`)
- **Actor**: Remote or Local Engineer via Web Browser
- **Flow**:
  1. Opening `http://localhost` on port `4185` renders the Mochi-Soul Companion Studio with:
     - Live `240×240` Procedural Mochi-21 OLED GIF + `60 FPS` `240×320` ST7789 LCD simulator (`#lcd-canvas`) + toggleable HUD card preview
     - 4D Homeostasis bars (`Energy`, `Satiety`, `Bond`, `Mood Valence`) + Evolution Stage badge
     - 21 Emotion buttons + 6 Workspace Symbiosis buttons + 6-DOF Otto & LED MCP deck + HC-SR04 distance slider
     - Live Physical Hardware Link banner (`USB-JTAG` + `Wi-Fi LAN` from `robotctl.py`) & Outbound `ota_1` Packet Inspector.

### Gherkin `AC-04` (Headless Browser E2E Verification)
```gherkin
Given the Mochi-Soul Companion Studio running on localhost port 4185
When inspected via headless Chromium (Playwright) across 375px, 768px, and 1440px
Then there must be 0 page errors, 0 broken images, all 21 emotion triggers and Workspace Symbiosis controls must interactively update the 4D gauges and packet log in real time, and live hardware status must be displayed.
```
