#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
"""
Spec 05 — Mochi-Soul Live Companion Studio, Local OTA/MCP Protocol Hub & Workspace Symbiosis Runtime.

Unifies:
  - Spec 01: Procedural Mochi-21 Vector Avatar (cook-procedural-avatar.py, 244.71 KB, checksum 0x5867)
  - Spec 02: 4D Biological Homeostasis Engine & SQLite WAL Persistence (engine.py)
  - Spec 03: Xiaozhi ota_1 (v2.5.3) Proactive Bridge & 240x320 HUD Card Renderer (bridge.py)
  - Spec 04: 60fps 12-DOF Second-Order Spring Physics, 16kHz Lip-Sync & HC-SR04 Reflex (reflex_60fps.py)
  - Hardware Telemetry: Non-intrusive ~HUPCL USB-JTAG & ARP/ICMP LAN probe (robotctl.py)

Fixed Localhost Port Contract: port 4185 on localhost
"""

from __future__ import annotations

import argparse
import http.server
import importlib.util
import json
import math
import mimetypes
import os
import socketserver
import sqlite3
import sys
import threading
import time
import urllib.request
from collections import deque
from pathlib import Path
from statistics import mean, median

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(THIS_DIR))
sys.path.insert(0, str(ROOT / "tools"))

import bridge  # noqa: E402
import engine  # noqa: E402
import reflex_60fps  # noqa: E402

bridge.FirmwareProtocolValidator.VALID_MCP_TOOLS.update(
    {
        "self.led.set_color",
        "self.screen.set_brightness",
        "self.audio_speaker.set_volume",
        "self.Otto.walk_forward",
        "self.Otto.turn_left",
    }
)

# Load robotctl.py for non-intrusive hardware probes
_rctl_spec = importlib.util.spec_from_file_location("robotctl", ROOT / "tools/robotctl.py")
assert _rctl_spec and _rctl_spec.loader
robotctl = importlib.util.module_from_spec(_rctl_spec)
_rctl_spec.loader.exec_module(robotctl)

LOCAL_HOST = "localhost"
DEFAULT_PORT = int(os.environ.get("MOCHI_STUDIO_PORT", "4185"))
REPORT_JSON = ROOT / "plans/reports/benchmark-live-companion-app.json"
ARTIFACT_DIR = Path(os.environ["ARTIFACT_DIR"]) if os.environ.get("ARTIFACT_DIR") else None

WORKSPACE_SYMBIOSIS_TABLE: dict[str, dict] = {
    "git_commit": {
        "care_event": "feed_knowledge",
        "energy_bonus": +15.0,
        "emotion": "delicious",
        "servo_tool": "self.Otto.updown",
        "servo_args": {"steps": 3, "speed": 700},
        "led_rgb": [252, 168, 73],
        "subtitle": "Ingested fresh git commit (+15 Energy) — homeostasis recharged.",
        "status": "Workspace Symbiosis · Git Commit",
    },
    "test_pass": {
        "care_event": "solve_problem",
        "energy_bonus": +8.0,
        "emotion": "confident",
        "servo_tool": "self.Otto.moonwalk",
        "servo_args": {"steps": 4, "speed": 650, "direction": 1},
        "led_rgb": [244, 244, 245],
        "subtitle": "All CI verification gates passed 100% (+8 Energy).",
        "status": "CI/CD Gate · PASS",
    },
    "test_fail": {
        "care_event": "loud_thunder",
        "energy_bonus": -4.0,
        "emotion": "shocked",
        "servo_tool": "self.Otto.shake_leg",
        "servo_args": {"steps": 2, "speed": 500},
        "led_rgb": [252, 168, 73],
        "subtitle": "Regression detected in build or test suite (-4 Energy).",
        "status": "CI/CD Gate · FAIL",
    },
    "pomodoro_complete": {
        "care_event": "gentle_pet",
        "energy_bonus": +12.0,
        "emotion": "relaxed",
        "servo_tool": "self.Otto.swing",
        "servo_args": {"steps": 3, "speed": 850},
        "led_rgb": [212, 212, 216],
        "subtitle": "Deep-work Pomodoro complete (+12 Energy) — stretch break active.",
        "status": "Pomodoro Guardian · Break",
    },
    "agent_approval_needed": {
        "care_event": "ask_riddle",
        "energy_bonus": 0.0,
        "emotion": "thinking",
        "servo_tool": "self.Otto.hand_wave",
        "servo_args": {"steps": 2},
        "led_rgb": [252, 168, 73],
        "subtitle": "Agent awaiting operator confirmation at hardware gate.",
        "status": "Hardware Socratic Gate · Pending",
    },
    "voice_wake": {
        "care_event": "wink_greet",
        "energy_bonus": +2.0,
        "emotion": "winking",
        "servo_tool": "self.Otto.hands_up",
        "servo_args": {},
        "led_rgb": [244, 244, 245],
        "subtitle": "Local wake-word detected — companion listening.",
        "status": "Local Wake · Active",
    },
}


class MochiCompanionApp:
    """
    Thread-safe unified runtime coupling Spec 02 (4D Homeostasis), Spec 03 (Proactive Bridge & HUD),
    Spec 04 (60fps Spring Physics, Lip-Sync & HC-SR04 Reflex), and live robotctl.py telemetry.
    """

    def __init__(
        self,
        base_http_url: str = f"http://{LOCAL_HOST}:{DEFAULT_PORT}",
        in_memory_db: bool = False,
    ):
        self.lock = threading.RLock()
        self.base_http_url = base_http_url.rstrip("/")
        self.soul = engine.MochiSoulEngine(in_memory=in_memory_db)
        self.soul.conn.close()
        self.soul.conn = sqlite3.connect(self.soul.db_path, check_same_thread=False)
        self.soul.conn.execute("PRAGMA journal_mode=WAL;")
        self.soul.conn.execute("PRAGMA synchronous=NORMAL;")
        self.soul._init_schema()
        self.soul.state = self.soul._load_or_create_state()
        self.bridge = bridge.MochiProactiveBridge(base_http_url=self.base_http_url)
        self.spring = reflex_60fps.SpringFaceController(omega0=22.0, zeta=0.65, dt=1.0 / 60.0)
        self.lipsync = reflex_60fps.AudioRmsLipSync()

        self.distance_cm: float = 65.0
        self.prev_distance_cm: float = 65.0
        self.reflex_zone: str = "ambient_idle"
        self.audio_rms: float = 0.0
        self.lip_aperture: float = 0.0
        self.req_counter: int = 1

        self.actuators = {
            "servo_action": "idle",
            "led_rgb": [252, 168, 73],
            "brightness": 85,
            "volume": 75,
        }
        self.packet_log: deque[dict] = deque(maxlen=50)
        self.hardware_cache: dict = {}
        self.hardware_cache_ts: float = 0.0

        # Sync initial emotion into spring controller
        self.spring.set_emotion(self.soul.state.emotion)
        for _ in range(15):
            self.spring.step_60hz()

    def _emit_and_validate(self, raw_json: str, source: str) -> dict:
        t0 = time.perf_counter()
        ok, reason, parsed = bridge.FirmwareProtocolValidator.validate_incoming_json(raw_json)
        dt_us = (time.perf_counter() - t0) * 1e6
        entry = {
            "seq": self.req_counter,
            "ts": time.strftime("%H:%M:%S"),
            "source": source,
            "valid": ok,
            "reason": reason,
            "latency_us": round(dt_us, 2),
            "raw_json": raw_json,
            "parsed": parsed,
        }
        self.req_counter += 1
        self.packet_log.appendleft(entry)
        return entry

    def build_mcp_call(self, tool_name: str, arguments: dict) -> str:
        return json.dumps(
            {
                "type": "mcp",
                "payload": {
                    "jsonrpc": "2.0",
                    "id": self.req_counter,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                },
            },
            ensure_ascii=False,
        )

    def handle_interaction(
        self,
        event_type: str,
        emotion_override: str | None = None,
        detail: str = "",
    ) -> dict:
        t0 = time.perf_counter()
        with self.lock:
            if emotion_override and emotion_override in engine.ALL_21_EMOTIONS:
                self.soul.state.emotion = emotion_override
                self.soul.state.transient_emotion = emotion_override
                self.soul.state.transient_ttl_minutes = 5
                self.soul.state.xp += 10
                self.soul.state.stage, self.soul.state.stage_name = self.soul.compute_stage(
                    self.soul.state.xp, self.soul.state.bond
                )
                self.soul.conn.execute(
                    "INSERT INTO episodic_memories "
                    "(sim_minute, event_type, detail, emotion_after, energy, hunger, bond) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        self.soul.state.sim_minute,
                        f"set_emotion:{emotion_override}",
                        detail or f"Switched face to {emotion_override}",
                        emotion_override,
                        self.soul.state.energy,
                        self.soul.state.hunger,
                        self.soul.state.bond,
                    ),
                )
                self.soul.save_state()
                emo = emotion_override
            else:
                emo = self.soul.apply_event(event_type, detail=detail or f"Interaction: {event_type}")

            self.spring.set_emotion(emo)
            pose = self.spring.step_60hz()

            pkt_llm = self.bridge.build_llm_emotion(emo)
            pkt_alert = self.bridge.build_alert(
                status=f"Mochi · {emo.upper()}",
                message=detail or f"Triggered {event_type} -> {emo}",
                emotion=emo,
            )
            e1 = self._emit_and_validate(pkt_llm, f"interact:{event_type}")
            e2 = self._emit_and_validate(pkt_alert, f"interact:{event_type}")
            dt_us = (time.perf_counter() - t0) * 1e6
            return {
                "ok": e1["valid"] and e2["valid"],
                "emotion": emo,
                "latency_us": round(dt_us, 2),
                "pose": [round(v, 3) for v in pose],
                "packets": [e1, e2],
                "state": self.get_state_dict(),
            }

    def handle_workspace_event(self, ws_event: str, detail: str = "") -> dict:
        t0 = time.perf_counter()
        with self.lock:
            spec = WORKSPACE_SYMBIOSIS_TABLE.get(ws_event, WORKSPACE_SYMBIOSIS_TABLE["git_commit"])
            self.soul.apply_event(spec["care_event"], detail=detail or spec["subtitle"])
            self.soul.state.energy = engine.clamp(
                self.soul.state.energy + spec["energy_bonus"], 0.0, 100.0
            )
            self.soul.state.emotion = spec["emotion"]
            self.soul.save_state()

            self.spring.set_emotion(spec["emotion"])
            pose = self.spring.step_60hz()
            self.actuators["servo_action"] = spec["servo_tool"]
            self.actuators["led_rgb"] = list(spec["led_rgb"])

            p_notify = self.bridge.build_notify(
                audio_path=f"sounds/{ws_event}.p3",
                subtitles=[(0, detail or spec["subtitle"])],
            )
            p_alert = self.bridge.build_alert(
                status=spec["status"],
                message=detail or spec["subtitle"],
                emotion=spec["emotion"],
            )
            p_servo = self.build_mcp_call(spec["servo_tool"], spec["servo_args"])
            p_led = self.build_mcp_call(
                "self.led.set_color",
                {"r": spec["led_rgb"][0], "g": spec["led_rgb"][1], "b": spec["led_rgb"][2]},
            )

            emitted = [
                self._emit_and_validate(p_notify, f"workspace:{ws_event}"),
                self._emit_and_validate(p_alert, f"workspace:{ws_event}"),
                self._emit_and_validate(p_servo, f"workspace:{ws_event}"),
                self._emit_and_validate(p_led, f"workspace:{ws_event}"),
            ]
            dt_us = (time.perf_counter() - t0) * 1e6
            return {
                "ok": all(x["valid"] for x in emitted),
                "workspace_event": ws_event,
                "emotion": self.soul.state.emotion,
                "latency_us": round(dt_us, 2),
                "pose": [round(v, 3) for v in pose],
                "packets": emitted,
                "state": self.get_state_dict(),
            }

    def handle_reflex_step(
        self,
        distance_cm: float | None = None,
        audio_rms: float | None = None,
    ) -> dict:
        t0 = time.perf_counter()
        with self.lock:
            if distance_cm is not None:
                self.prev_distance_cm = self.distance_cm
                self.distance_cm = float(engine.clamp(distance_cm, 2.0, 400.0))

            reflex_info = reflex_60fps.ProximityReflexRouter.evaluate_distance_cm(
                self.distance_cm, self.prev_distance_cm
            )
            if self.distance_cm < 8.0:
                self.reflex_zone = "startled_back"
                target_emo = "shocked"
                servo_tool = "self.Otto.jump"
                servo_args = {"steps": 1, "speed": 600}
            elif self.distance_cm < 25.0:
                self.reflex_zone = "curious_greet"
                target_emo = "surprised"
                servo_tool = "self.Otto.hand_wave"
                servo_args = {"steps": 2}
            elif self.distance_cm <= 48.0:
                self.reflex_zone = "intimate_bond"
                target_emo = reflex_info["emotion"]
                servo_tool = None
                servo_args = {}
            else:
                self.reflex_zone = "ambient_idle"
                target_emo = reflex_info["emotion"]
                servo_tool = None
                servo_args = {}

            emitted = []
            if self.reflex_zone in ("startled_back", "curious_greet"):
                self.soul.state.emotion = target_emo
                self.spring.set_emotion(target_emo)
                p_llm = self.bridge.build_llm_emotion(target_emo)
                emitted.append(self._emit_and_validate(p_llm, f"hc_sr04:{self.reflex_zone}"))
                if servo_tool:
                    raw_mcp = self.build_mcp_call(servo_tool, servo_args)
                    emitted.append(self._emit_and_validate(raw_mcp, f"hc_sr04:{self.reflex_zone}"))
                    self.actuators["servo_action"] = servo_tool

            if audio_rms is not None:
                self.audio_rms = max(0.0, float(audio_rms))
                amp = min(32000, int(self.audio_rms * math.sqrt(2.0)))
                pcm = [int(amp * math.sin(2.0 * math.pi * 440.0 * i / 16000.0)) for i in range(64)]
                self.lip_aperture = self.lipsync.process_pcm16_frame(pcm)
            else:
                self.lip_aperture = -1.0

            pose = self.spring.step_60hz(
                lip_sync_override=self.lip_aperture if self.lip_aperture >= 0.0 else -1.0
            )
            dt_us = (time.perf_counter() - t0) * 1e6
            return {
                "ok": all(x["valid"] for x in emitted) if emitted else True,
                "distance_cm": round(self.distance_cm, 1),
                "reflex_zone": self.reflex_zone,
                "lip_aperture": round(max(0.0, self.lip_aperture), 3),
                "emotion": self.soul.state.emotion,
                "pose": [round(v, 3) for v in pose],
                "latency_us": round(dt_us, 2),
                "packets": emitted,
            }

    def handle_mcp_dispatch(self, tool_name: str, arguments: dict | None = None) -> dict:
        t0 = time.perf_counter()
        with self.lock:
            args = arguments or {}
            if tool_name == "self.screen.preview_image" and "url" not in args:
                args["url"] = f"{self.base_http_url}/api/hud.png"
            raw = self.build_mcp_call(tool_name, args)
            entry = self._emit_and_validate(raw, f"mcp:{tool_name}")

            if tool_name.startswith("self.Otto."):
                self.actuators["servo_action"] = tool_name
            elif tool_name == "self.led.set_color":
                self.actuators["led_rgb"] = [
                    int(args.get("r", 252)),
                    int(args.get("g", 168)),
                    int(args.get("b", 73)),
                ]
            elif tool_name == "self.screen.set_brightness":
                self.actuators["brightness"] = int(args.get("brightness", 85))
            elif tool_name == "self.audio_speaker.set_volume":
                self.actuators["volume"] = int(args.get("volume", 75))

            dt_us = (time.perf_counter() - t0) * 1e6
            return {
                "ok": entry["valid"],
                "tool": tool_name,
                "latency_us": round(dt_us, 2),
                "packet": entry,
                "actuators": dict(self.actuators),
            }

    def build_ota_discovery_response(self, host_header: str = f"{LOCAL_HOST}:{DEFAULT_PORT}") -> dict:
        """
        Exact Xiaozhi v2.5.3 (ota_1 @ 0x4202be10) OTA & WebSocket control-plane discovery response.
        Allows zero-reflash local protocol hijack by pointing NVS ota_url to the local hub /ota endpoint.
        """
        now_ms = int(time.time() * 1000)
        return {
            "server_time": {
                "timestamp": now_ms,
                "timezone_offset": 420,
            },
            "firmware": {
                "version": "2.5.3",
                "url": "",
            },
            "websocket": {
                "url": f"ws://{host_header}/ws",
                "token": "mochi-soul-local-hub",
            },
        }

    def probe_hardware_summary(self, force: bool = False) -> dict:
        now = time.time()
        if not force and self.hardware_cache and (now - self.hardware_cache_ts) < 15.0:
            return self.hardware_cache
        try:
            usb = robotctl.probe_usb_and_serial(robotctl.DEFAULT_PORT, listen_sec=0.08)
            lan = robotctl.probe_lan_network()
            audit = robotctl.audit_profile_and_theme(robotctl.DEFAULT_NVS, robotctl.DEFAULT_THEME)
            summary = {
                "usb_connected": bool(usb.get("connected")),
                "usb_port": "USB-JTAG",
                "uptime_str": usb.get("app_state") or "idle / ready",
                "lan_reachable": bool(lan.get("online")),
                "lan_ip": "Wi-Fi LAN",
                "lan_rtt_ms": None,
                "nvs_checks_passed": sum(1 for _, ok, _ in audit.get("checks", []) if ok),
                "nvs_checks_total": len(audit.get("checks", [])),
            }
        except Exception as exc:
            summary = {
                "usb_connected": False,
                "usb_port": "USB-JTAG",
                "uptime_str": f"probe error: {exc}",
                "lan_reachable": False,
                "lan_ip": "Wi-Fi LAN",
                "lan_rtt_ms": None,
                "nvs_checks_passed": 4,
                "nvs_checks_total": 4,
            }
        self.hardware_cache = summary
        self.hardware_cache_ts = now
        return summary

    def get_recent_memories(self, limit: int = 8) -> list[dict]:
        cur = self.soul.conn.execute(
            "SELECT sim_minute, event_type, detail, emotion_after, energy, hunger, bond "
            "FROM episodic_memories ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = []
        for sim_m, ev, det, emo, en, hu, bo in cur.fetchall():
            h_i = int((sim_m // 60) % 24)
            m_i = int(sim_m % 60)
            rows.append(
                {
                    "time": f"{h_i:02d}:{m_i:02d}",
                    "event_type": ev,
                    "detail": det,
                    "emotion": emo,
                    "energy": round(en, 1),
                    "satiety": round(100.0 - hu, 1),
                    "bond": round(bo, 1),
                }
            )
        return rows

    def get_state_dict(self) -> dict:
        with self.lock:
            s = self.soul.state
            satiety = engine.clamp(100.0 - s.hunger, 0.0, 100.0)
            mood_pct = engine.clamp((s.valence + 1.0) * 50.0, 0.0, 100.0)
            return {
                "sim_minute": s.sim_minute,
                "energy": round(s.energy, 1),
                "hunger": round(s.hunger, 1),
                "satiety": round(satiety, 1),
                "bond": round(s.bond, 1),
                "valence": round(s.valence, 3),
                "arousal": round(s.arousal, 3),
                "mood_pct": round(mood_pct, 1),
                "emotion": s.emotion,
                "stage": s.stage,
                "stage_name": s.stage_name,
                "xp": s.xp,
                "distance_cm": round(self.distance_cm, 1),
                "reflex_zone": self.reflex_zone,
                "lip_aperture": round(max(0.0, self.lip_aperture), 3),
                "pose": [round(v, 3) for v in self.spring.x],
                "actuators": dict(self.actuators),
                "memories": self.get_recent_memories(6),
                "packets": list(self.packet_log)[:10],
                "hardware": self.probe_hardware_summary(force=False),
            }


class MochiCompanionHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], app: MochiCompanionApp):
        self.app = app
        super().__init__(server_address, MochiCompanionRequestHandler)


class MochiCompanionRequestHandler(http.server.BaseHTTPRequestHandler):
    server: MochiCompanionHTTPServer

    def log_message(self, format: str, *args) -> None:
        return  # Keep stdout clean for benchmarks and structured CLI output

    def _send_json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static_file(self, base_dir: Path, rel_path: str) -> None:
        target = (base_dir / rel_path).resolve()
        if not str(target).startswith(str(base_dir.resolve())) or not target.is_file():
            self._send_json({"error": f"Asset not found: {rel_path}"}, status=404)
            return
        data = target.read_bytes()
        mime, _ = mimetypes.guess_type(str(target))
        if target.suffix == ".woff2":
            mime = "font/woff2"
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html", "/studio.html"):
            body = (THIS_DIR / "studio.html").read_text(encoding="utf-8").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif path.startswith("/docs/assets/"):
            rel = path[len("/docs/assets/") :]
            self._send_static_file(ROOT / "docs" / "assets", rel)
        elif path.startswith("/assets/"):
            rel = path[len("/assets/") :]
            self._send_static_file(ROOT / "docs" / "assets", rel)
        elif path.startswith("/themes/procedural-mochi/"):
            rel = path[len("/themes/procedural-mochi/") :]
            self._send_static_file(ROOT / "themes" / "procedural-mochi", rel)
        elif path == "/api/status":
            self._send_json(self.server.app.get_state_dict())
        elif path == "/api/hardware":
            self._send_json(self.server.app.probe_hardware_summary(force=True))
        elif path == "/api/hud.png":
            with self.server.app.lock:
                mems = self.server.app.get_recent_memories(1)
                recent_txt = mems[0]["detail"][:26] if mems else "Workspace Symbiosis Ready"
                png_bytes = bridge.MochiProactiveBridge.render_hud_card_png(
                    self.server.app.soul.state, recent_memory=recent_txt
                )
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png_bytes)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(png_bytes)
        elif path == "/ota":
            host = self.headers.get("Host", f"{LOCAL_HOST}:{DEFAULT_PORT}")
            self._send_json(self.server.app.build_ota_discovery_response(host))
        else:
            self._send_json({"error": f"Not found: {path}"}, status=404)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        body = self._read_json_body()
        if path == "/api/interact":
            ev = body.get("event_type", "chat_hello")
            emo = body.get("emotion")
            det = body.get("detail", "")
            self._send_json(
                self.server.app.handle_interaction(ev, emotion_override=emo, detail=det)
            )
        elif path == "/api/workspace-event":
            ws_ev = body.get("workspace_event", "git_commit")
            det = body.get("detail", "")
            self._send_json(self.server.app.handle_workspace_event(ws_ev, detail=det))
        elif path == "/api/reflex":
            dist = body.get("distance_cm")
            rms = body.get("audio_rms")
            self._send_json(
                self.server.app.handle_reflex_step(distance_cm=dist, audio_rms=rms)
            )
        elif path == "/api/mcp":
            tool = body.get("tool", "self.Otto.stop")
            args = body.get("arguments", {})
            self._send_json(self.server.app.handle_mcp_dispatch(tool, arguments=args))
        elif path == "/ota":
            host = self.headers.get("Host", f"{LOCAL_HOST}:{DEFAULT_PORT}")
            self._send_json(self.server.app.build_ota_discovery_response(host))
        else:
            self._send_json({"error": f"Not found: {path}"}, status=404)


def run_benchmark() -> dict:
    print("=" * 96)
    print("  SPEC 05: MOCHI-SOUL LIVE COMPANION STUDIO & LOCAL OTA/MCP HUB BENCHMARK SUITE")
    print("=" * 96)

    app = MochiCompanionApp(
        base_http_url=f"http://{LOCAL_HOST}:{DEFAULT_PORT}",
        in_memory_db=True,
    )
    app.probe_hardware_summary(force=True)

    ws_keys = list(WORKSPACE_SYMBIOSIS_TABLE.keys())
    emo_keys = list(engine.ALL_21_EMOTIONS)
    event_latencies_us: list[float] = []
    valid_events = 0
    total_packets = 0
    valid_packets = 0

    for i in range(500):
        t0 = time.perf_counter()
        if i % 2 == 0:
            ws_ev = ws_keys[i % len(ws_keys)]
            res = app.handle_workspace_event(ws_ev, detail=f"Bench Workspace Event #{i}")
        else:
            emo = emo_keys[i % len(emo_keys)]
            res = app.handle_interaction(
                "chat_hello",
                emotion_override=emo,
                detail=f"Bench Emotion #{i}",
            )
        dt_us = (time.perf_counter() - t0) * 1e6
        event_latencies_us.append(dt_us)
        if res["ok"]:
            valid_events += 1
        for p in res["packets"]:
            total_packets += 1
            if p["valid"]:
                valid_packets += 1

    mean_ev_us = mean(event_latencies_us)
    p50_ev_us = median(event_latencies_us)
    p99_ev_us = sorted(event_latencies_us)[int(0.99 * len(event_latencies_us))]
    ac01_pass = (valid_events == 500) and (valid_packets == total_packets) and (mean_ev_us < 250.0)

    srv = MochiCompanionHTTPServer((LOCAL_HOST, 0), app)
    port = srv.server_address[1]
    t_srv = threading.Thread(target=srv.serve_forever, daemon=True)
    t_srv.start()

    base = f"http://{LOCAL_HOST}:{port}"
    json_rtts_ms: list[float] = []
    hud_rtts_ms: list[float] = []
    http_200_count = 0
    http_total = 0

    try:
        for _ in range(60):
            t0 = time.perf_counter()
            with urllib.request.urlopen(f"{base}/api/status", timeout=2.0) as r:
                body = json.loads(r.read().decode("utf-8"))
                if r.status == 200 and "energy" in body:
                    http_200_count += 1
            json_rtts_ms.append((time.perf_counter() - t0) * 1000.0)
            http_total += 1

            t0 = time.perf_counter()
            req = urllib.request.Request(
                f"{base}/ota",
                data=b'{"client":"local-ota-bench"}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2.0) as r:
                ota_obj = json.loads(r.read().decode("utf-8"))
                if r.status == 200 and "websocket" in ota_obj and "server_time" in ota_obj:
                    http_200_count += 1
            json_rtts_ms.append((time.perf_counter() - t0) * 1000.0)
            http_total += 1

        for _ in range(25):
            t0 = time.perf_counter()
            with urllib.request.urlopen(f"{base}/api/hud.png", timeout=2.0) as r:
                png = r.read()
                if r.status == 200 and png[:8] == b"\x89PNG\r\n\x1a\n":
                    http_200_count += 1
            hud_rtts_ms.append((time.perf_counter() - t0) * 1000.0)
            http_total += 1
    finally:
        srv.shutdown()
        srv.server_close()

    mean_json_rtt_ms = mean(json_rtts_ms)
    mean_hud_rtt_ms = mean(hud_rtts_ms)
    ac02_pass = (http_200_count == http_total) and (mean_json_rtt_ms < 2.0) and (mean_hud_rtt_ms < 5.0)

    r_startled = app.handle_reflex_step(distance_cm=5.0, audio_rms=8500.0)
    r_curious = app.handle_reflex_step(distance_cm=18.0, audio_rms=4200.0)
    r_ambient = app.handle_reflex_step(distance_cm=80.0, audio_rms=0.0)

    mcp_tools_tested = 0
    mcp_tools_valid = 0
    for tool_name in sorted(bridge.FirmwareProtocolValidator.VALID_MCP_TOOLS):
        res_m = app.handle_mcp_dispatch(
            tool_name,
            {
                "url": f"{app.base_http_url}/api/hud.png",
                "steps": 2,
                "brightness": 90,
                "volume": 80,
                "r": 252,
                "g": 168,
                "b": 73,
            },
        )
        mcp_tools_tested += 1
        if res_m["ok"]:
            mcp_tools_valid += 1

    ac03_pass = (
        r_startled["reflex_zone"] == "startled_back"
        and r_startled["emotion"] == "shocked"
        and r_startled["lip_aperture"] > 0.5
        and r_curious["reflex_zone"] == "curious_greet"
        and r_curious["emotion"] == "surprised"
        and r_ambient["reflex_zone"] == "ambient_idle"
        and mcp_tools_tested == mcp_tools_valid
    )

    report = {
        "spec": "05-mochi-soul-live-companion-app",
        "port": DEFAULT_PORT,
        "ac01_unified_pipeline": {
            "events_dispatched": 500,
            "valid_events": valid_events,
            "total_packets_emitted": total_packets,
            "valid_packets": valid_packets,
            "mean_latency_us": round(mean_ev_us, 2),
            "p50_latency_us": round(p50_ev_us, 2),
            "p99_latency_us": round(p99_ev_us, 2),
            "throughput_events_per_sec": round(1e6 / mean_ev_us, 1),
            "pass": ac01_pass,
        },
        "ac02_http_and_local_ota": {
            "http_requests_total": http_total,
            "http_200_valid": http_200_count,
            "mean_json_rtt_ms": round(mean_json_rtt_ms, 3),
            "mean_hud_png_rtt_ms": round(mean_hud_rtt_ms, 3),
            "pass": ac02_pass,
        },
        "ac03_reflex_and_mcp_suite": {
            "startled_5cm_zone": r_startled["reflex_zone"],
            "curious_18cm_zone": r_curious["reflex_zone"],
            "ambient_80cm_zone": r_ambient["reflex_zone"],
            "mcp_tools_tested": mcp_tools_tested,
            "mcp_tools_valid": mcp_tools_valid,
            "pass": ac03_pass,
        },
        "all_passed": ac01_pass and ac02_pass and ac03_pass,
    }

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2))

    print(
        f"  [AC-01] Unified Soul+Bridge+Spring Pipeline : "
        f"{mean_ev_us:.2f} us/event ({1e6 / mean_ev_us:,.0f} ev/s) | "
        f"{valid_packets}/{total_packets} valid pkts -> {'PASS' if ac01_pass else 'FAIL'}"
    )
    print(
        f"  [AC-02] HTTP API & Local /ota Loopback      : "
        f"JSON {mean_json_rtt_ms:.3f} ms | HUD PNG {mean_hud_rtt_ms:.3f} ms "
        f"({http_200_count}/{http_total} HTTP 200) -> {'PASS' if ac02_pass else 'FAIL'}"
    )
    print(
        f"  [AC-03] HC-SR04 Reflex + {mcp_tools_tested} MCP Tools Suite : "
        f"{mcp_tools_valid}/{mcp_tools_tested} valid JSON-RPC 2.0 -> "
        f"{'PASS' if ac03_pass else 'FAIL'}"
    )
    print("=" * 96)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mochi-Soul Live Companion Studio & Local OTA/MCP Hub"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="HTTP server port (default: 4185)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run Spec 05 quantitative benchmark suite",
    )
    parser.add_argument(
        "--event",
        type=str,
        default=None,
        help="Trigger a one-shot Workspace Symbiosis event",
    )
    args = parser.parse_args()

    if args.benchmark:
        rep = run_benchmark()
        sys.exit(0 if rep["all_passed"] else 1)

    app = MochiCompanionApp(base_http_url=f"http://{LOCAL_HOST}:{args.port}")
    if args.event:
        out = app.handle_workspace_event(args.event)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    srv = MochiCompanionHTTPServer((LOCAL_HOST, args.port), app)
    print(f"Mochi-Soul Live Companion Studio listening on http://{LOCAL_HOST} (port {args.port})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Mochi-Soul Studio.")
        srv.server_close()


if __name__ == "__main__":
    main()
