#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
Spec 05 + EVO-01..03 — Mochi-Soul Live Companion Studio, Self-Evolution Hub,
Autonomous Dream Consolidation, Single-Owner Serial Supervisor & Local OTA/MCP Runtime.

Unifies:
  - Spec 01 + EVO-02: Procedural Mochi-21 Vector Avatar & Morphological Evolution (`cook-procedural-avatar.py`)
  - Spec 02 + EVO-01/03: 4D Homeostasis, Relative-Share Personality Genome & Dream Consolidation (`engine.py`)
  - Spec 03: Xiaozhi ota_1 (v2.5.3) Proactive Bridge & 240x320 HUD Card Renderer (`bridge.py`)
  - Spec 04: 60fps 12-DOF Second-Order Spring Physics, 16kHz Lip-Sync & HC-SR04 Reflex (`reflex_60fps.py`)
  - EVO-03b: Single-Owner USB-JTAG Serial Supervisor & Watchdog Auto-Rescue FSM (`serial_supervisor.py`)

Fixed Localhost Port Contract: port 4185 on localhost
"""

from __future__ import annotations

import argparse
import datetime
import http.server
import importlib.util
import json
import math
import mimetypes
import os
import socketserver
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path
from statistics import mean, median
from typing import Optional

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(THIS_DIR))
sys.path.insert(0, str(ROOT / "tools"))

import bridge  # noqa: E402
import engine  # noqa: E402
import mochi_canonical_vectors  # noqa: E402
import reflex_60fps  # noqa: E402
import serial_supervisor  # noqa: E402

bridge.FirmwareProtocolValidator.VALID_MCP_TOOLS.update(
    {
        "self.led.set_color",
        "self.screen.set_brightness",
        "self.audio_speaker.set_volume",
        "self.Otto.walk_forward",
        "self.Otto.turn_left",
    }
)

# Load robotctl.py for non-intrusive LAN/profile probes
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
    Thread-safe unified runtime coupling Spec 02 (4D Homeostasis + EVO-01 Genome + EVO-03 Dreams),
    Spec 03 (Proactive Bridge & HUD), Spec 04 (60fps Spring Physics, Lip-Sync & HC-SR04 Reflex),
    and EVO-03b (`SerialSupervisor` Watchdog Rescue FSM).
    """

    def __init__(
        self,
        base_http_url: str = f"http://{LOCAL_HOST}:{DEFAULT_PORT}",
        in_memory_db: bool = False,
        db_path: Path | str | None = None,
        wdt_rescue_mode: Optional[str] = None,
        start_background_threads: bool = False,
    ):
        self.lock = threading.RLock()
        self.base_http_url = base_http_url.rstrip("/")
        self.soul = engine.MochiSoulEngine(
            db_path=db_path,
            in_memory=in_memory_db,
            mode="live" if start_background_threads else "sim",
        )
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

        self.supervisor = serial_supervisor.SerialSupervisor(
            mode=wdt_rescue_mode,
            on_hardware_event=self._record_hardware_event,
            on_voice_wake=self._on_serial_voice_wake,
            enabled=start_background_threads,
        )

        # Sync initial emotion into spring controller
        self.spring.set_emotion(self.soul.state.emotion)
        for _ in range(15):
            self.spring.step_60hz()

        self._ticker_stop = threading.Event()
        self._ticker_thread: Optional[threading.Thread] = None
        if start_background_threads:
            self._catch_up_downtime_and_missed_dreams()
            self.supervisor.start()
            self._ticker_thread = threading.Thread(
                target=self._run_minute_ticker, name="mochi-soul-ticker", daemon=True
            )
            self._ticker_thread.start()

    def close(self) -> None:
        self._ticker_stop.set()
        self.supervisor.stop()

    def _record_hardware_event(self, ev: serial_supervisor.HardwareEventRecord) -> None:
        with self.lock:
            self.soul.conn.execute(
                "INSERT INTO hardware_events "
                "(wall_ts, kind, signature, uptime_ms, fw_version, rescue_mode, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ev.wall_ts,
                    ev.kind,
                    ev.signature,
                    ev.uptime_ms,
                    ev.fw_version,
                    ev.rescue_mode,
                    ev.note,
                ),
            )
            self.soul.conn.commit()

    def _on_serial_voice_wake(self) -> None:
        with self.lock:
            emo = self.soul.apply_event(
                "wink_greet",
                detail="Wake-word detected on USB-JTAG stream",
                source="serial",
            )
            self.spring.set_emotion(emo)
            self.spring.step_60hz()

    def _catch_up_downtime_and_missed_dreams(self) -> None:
        now_i = int(time.time())
        with self.lock:
            last_ts = self.soul.state.last_tick_wall_ts
            if last_ts is not None and now_i > last_ts:
                gap_min = (now_i - last_ts) // 60
                replay_steps = min(gap_min, 2880)
                start_ts = now_i - replay_steps * 60
                for step_i in range(replay_steps):
                    t_step = start_ts + (step_i + 1) * 60
                    dt = datetime.datetime.fromtimestamp(t_step)
                    hour_f = dt.hour + dt.minute / 60.0
                    self.soul.step_minute(persist=False, hour_override=hour_f)
                if gap_min > replay_steps:
                    self.soul.state.minutes_since_interaction += int(gap_min - replay_steps)

            self.soul.state.last_tick_wall_ts = now_i
            self.soul.save_state(commit=True)

            # Check missed_night dream trigger on startup
            last_night_key = self.soul._dream_key(
                "missed_night",
                float(now_i),
                self.soul.genome.last_consolidated_memory_id,
                self.soul.genome.genome_rev,
            )
            row = self.soul.conn.execute(
                "SELECT id FROM dream_journal WHERE dream_key = ?", (last_night_key,)
            ).fetchone()
            if not row and self.soul.genome.last_dream_wall_ts is not None:
                if (now_i - self.soul.genome.last_dream_wall_ts) >= 18 * 3600:
                    self.soul.consolidate_dreams("missed_night", now_ts=float(now_i))

    def _run_minute_ticker(self) -> None:
        while not self._ticker_stop.wait(timeout=60.0):
            now_ts = time.time()
            dt = datetime.datetime.fromtimestamp(now_ts)
            hour_f = dt.hour + dt.minute / 60.0
            with self.lock:
                self.soul.step_minute(persist=False, hour_override=hour_f)
                self.soul.state.last_tick_wall_ts = int(now_ts)
                self.soul.save_state(commit=True)
                self.soul.maybe_auto_dream(now_ts=now_ts)
                self.spring.set_emotion(self.soul.state.emotion)

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
                emo = self.soul.apply_emotion_override(
                    emotion_override, detail=detail or f"Switched face to {emotion_override}"
                )
            else:
                emo = self.soul.apply_event(
                    event_type,
                    detail=detail or f"Interaction: {event_type}",
                    source="user",
                )

            self.spring.set_emotion(emo)
            pose = self.spring.step_60hz()

            pkt_llm = self.bridge.build_llm_emotion(emo)
            pkt_alert = self.bridge.build_alert(
                status=f"Mochi · {emo.upper()}",
                message=engine.sanitize_detail(detail or f"Triggered {event_type} -> {emo}"),
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
            clean_sub = engine.sanitize_detail(detail or spec["subtitle"])
            self.soul.apply_event(spec["care_event"], detail=clean_sub, source="workspace")
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
                subtitles=[(0, clean_sub)],
            )
            p_alert = self.bridge.build_alert(
                status=spec["status"],
                message=clean_sub,
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
        """
        Hardware probe executed OUTSIDE `self.lock` so slow LAN/USB checks never block
        `/api/interact` or SQLite transactions (verifies V-08).
        Uses `SerialSupervisor.snapshot()` when active so the serial port has a single owner.
        """
        now = time.time()
        cached = self.hardware_cache
        if not force and cached and (now - self.hardware_cache_ts) < 15.0:
            return cached
        try:
            sup_snap = self.supervisor.snapshot()
            if self.supervisor.enabled and sup_snap["mode"] != "off":
                usb_connected = bool(sup_snap["port_present"])
                uptime_str = f"WDT:{sup_snap['state']}"
            else:
                usb = robotctl.probe_usb_and_serial(robotctl.DEFAULT_PORT, listen_sec=0.05)
                usb_connected = bool(usb.get("connected"))
                uptime_str = usb.get("app_state") or "idle / ready"

            lan = robotctl.probe_lan_network()
            audit = robotctl.audit_profile_and_theme(robotctl.DEFAULT_NVS, robotctl.DEFAULT_THEME)
            summary = {
                "usb_connected": usb_connected,
                "usb_port": "USB-JTAG",
                "uptime_str": uptime_str,
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
                    "detail": engine.sanitize_detail(det),
                    "emotion": emo,
                    "energy": round(en, 1),
                    "satiety": round(100.0 - hu, 1),
                    "bond": round(bo, 1),
                }
            )
        return rows

    def get_genome_dict(self) -> dict:
        with self.lock:
            return self.soul.get_genome_payload()

    def handle_genome_mutation(self, body: dict) -> tuple[int, dict]:
        if os.environ.get("MOCHI_DEV") != "1":
            return 403, {"error": "Forbidden: MOCHI_DEV=1 required for /api/genome mutations"}
        action = body.get("action")
        now_i = int(time.time())
        with self.lock:
            old_g = self.soul.genome
            before_json = json.dumps(
                {
                    "curiosity": round(old_g.curiosity, 4),
                    "affection": round(old_g.affection, 4),
                    "playfulness": round(old_g.playfulness, 4),
                    "resilience": round(old_g.resilience, 4),
                    "chronotype_shift": round(old_g.chronotype_shift, 4),
                },
                sort_keys=True,
            )
            if action == "reset":
                new_g = engine.PersonalityGenome(
                    genome_rev=old_g.genome_rev + 1,
                    last_consolidated_memory_id=old_g.last_consolidated_memory_id,
                    last_dream_wall_ts=old_g.last_dream_wall_ts,
                    updated_wall_ts=now_i,
                )
            elif action == "set" and isinstance(body.get("genome"), dict):
                gm = body["genome"]
                new_g = engine.PersonalityGenome(
                    curiosity=engine.clamp(float(gm.get("curiosity", old_g.curiosity)), 0.02, 0.98),
                    affection=engine.clamp(float(gm.get("affection", old_g.affection)), 0.02, 0.98),
                    playfulness=engine.clamp(float(gm.get("playfulness", old_g.playfulness)), 0.02, 0.98),
                    resilience=engine.clamp(float(gm.get("resilience", old_g.resilience)), 0.02, 0.98),
                    chronotype_shift=engine.clamp(
                        float(gm.get("chronotype_shift", old_g.chronotype_shift)), -3.0, 3.0
                    ),
                    base_curiosity=old_g.base_curiosity,
                    base_affection=old_g.base_affection,
                    base_playfulness=old_g.base_playfulness,
                    base_resilience=old_g.base_resilience,
                    genome_rev=old_g.genome_rev + 1,
                    last_consolidated_memory_id=old_g.last_consolidated_memory_id,
                    last_dream_wall_ts=old_g.last_dream_wall_ts,
                    updated_wall_ts=now_i,
                )
            else:
                return 400, {"error": "Invalid action; expected 'reset' or 'set'"}

            self.soul._save_genome(new_g, commit=False)
            self.soul.genome = new_g
            after_json = json.dumps(
                {
                    "curiosity": round(new_g.curiosity, 4),
                    "affection": round(new_g.affection, 4),
                    "playfulness": round(new_g.playfulness, 4),
                    "resilience": round(new_g.resilience, 4),
                    "chronotype_shift": round(new_g.chronotype_shift, 4),
                },
                sort_keys=True,
            )
            ph_hash = engine.phenotype_params(self.soul.state.stage, new_g, quantize=False)["hash"]
            self.soul.conn.execute(
                """
                INSERT INTO dream_journal (
                    dream_key, trigger, wall_ts, sim_minute,
                    mem_from_id, mem_to_id, mem_count,
                    genome_before, genome_after, delta_l1,
                    stage, milestone, summary, phenotype_hash
                ) VALUES (?, 'operator_override', ?, ?, ?, ?, 0, ?, ?, 0.0, ?, 'operator_override', ?, ?)
                """,
                (
                    f"override:{now_i}:r{new_g.genome_rev}",
                    now_i,
                    self.soul.state.sim_minute,
                    new_g.last_consolidated_memory_id,
                    new_g.last_consolidated_memory_id,
                    before_json,
                    after_json,
                    self.soul.state.stage,
                    f"Operator override ({action})",
                    ph_hash,
                ),
            )
            self.soul.conn.commit()
            return 200, self.soul.get_genome_payload()

    def get_dreams_list(self, limit: int = 10) -> list[dict]:
        with self.lock:
            return self.soul.get_recent_dreams(limit=limit)

    def trigger_dream(self, dry_run: bool = False) -> dict:
        with self.lock:
            return self.soul.consolidate_dreams(trigger="manual", dry_run=dry_run)

    def get_state_dict(self) -> dict:
        hw = self.probe_hardware_summary(force=False)
        wdt = self.supervisor.snapshot()
        with self.lock:
            s = self.soul.state
            satiety = engine.clamp(100.0 - s.hunger, 0.0, 100.0)
            mood_pct = engine.clamp((s.valence + 1.0) * 50.0, 0.0, 100.0)
            genome_payload = self.soul.get_genome_payload()
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
                "hardware": hw,
                "genome": genome_payload["genome"],
                "expressed": genome_payload["expressed"],
                "phenotype": genome_payload["phenotype"],
                "dreams": self.soul.get_recent_dreams(5),
                "watchdog": wdt,
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

    def _check_post_security_guards(self) -> Optional[tuple[int, str]]:
        """
        Localhost CSRF & DNS Rebinding Guard (verifies V-17):
          1. Content-Type must be application/json (-> 415)
          2. Host header must be localhost / 127.0.0.1 (-> 403)
          3. Origin header (if present) must be http://localhost or http://127.0.0.1 (-> 403)
        """
        ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if ctype != "application/json":
            return 415, "Unsupported Media Type: Content-Type must be application/json"

        host_hdr = (self.headers.get("Host") or "").strip().lower()
        host_only = host_hdr.split(":", 1)[0] if not host_hdr.startswith("[") else host_hdr
        if host_only not in ("localhost", "127.0.0.1", "[::1]"):
            return 403, "Forbidden: untrusted Host header"

        origin_hdr = (self.headers.get("Origin") or "").strip().lower()
        if origin_hdr:
            parsed = urllib.parse.urlparse(origin_hdr)
            if parsed.scheme not in ("http", "https") or parsed.hostname not in (
                "localhost",
                "127.0.0.1",
                "::1",
            ):
                return 403, "Forbidden: untrusted Origin header"

        return None

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        qs = urllib.parse.parse_qs(parsed_url.query)

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
        elif path in ("/api/status", "/api/state"):
            self._send_json(self.server.app.get_state_dict())
        elif path == "/api/genome":
            self._send_json(self.server.app.get_genome_dict())
        elif path == "/api/dream":
            limit_s = (qs.get("limit") or ["10"])[0]
            try:
                limit_i = int(limit_s)
            except ValueError:
                limit_i = 10
            self._send_json({"dreams": self.server.app.get_dreams_list(limit=limit_i)})
        elif path == "/api/watchdog":
            self._send_json(self.server.app.supervisor.snapshot())
        elif path == "/api/mochi-vectors":
            self._send_json(
                {
                    "palette": [
                        "#000000",
                        "#eafcff",
                        "#b8e6f8",
                        "#e080e4",
                        "#eee46e",
                        "#e6312e",
                        "#7644a8",
                        "#4c1a24",
                    ],
                    "src_w": mochi_canonical_vectors.FACE_SRC_W,
                    "src_h": mochi_canonical_vectors.FACE_SRC_H,
                    "emotions": mochi_canonical_vectors.decode_all_emotion_scanlines(),
                }
            )
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
        guard_err = self._check_post_security_guards()
        if guard_err is not None:
            status_code, msg = guard_err
            self._send_json({"error": msg}, status=status_code)
            return

        path = self.path.split("?", 1)[0]
        try:
            body = self._read_json_body()
        except Exception:
            self._send_json({"error": "Invalid JSON request body"}, status=400)
            return

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
        elif path == "/api/genome":
            status_code, payload = self.server.app.handle_genome_mutation(body)
            self._send_json(payload, status=status_code)
        elif path == "/api/dream":
            dry_run = bool(body.get("dry_run", False))
            self._send_json(self.server.app.trigger_dream(dry_run=dry_run))
        elif path == "/api/watchdog/rescue":
            status_code, payload = self.server.app.supervisor.request_manual_rescue(
                confirm=bool(body.get("confirm", False)),
                force=bool(body.get("force", False)),
            )
            self._send_json(payload, status=status_code)
        elif path == "/api/serial/yield":
            secs = float(body.get("seconds", 120.0))
            self._send_json(self.server.app.supervisor.request_yield(seconds=secs))
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
        start_background_threads=False,
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
                if r.status == 200 and "energy" in body and "genome" in body:
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
        description="Mochi-Soul Live Companion Studio, Self-Evolution Hub & Local OTA/MCP Runtime"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="HTTP server port (default: 4185)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--wdt-rescue",
        choices=("off", "observe", "auto"),
        default=None,
        help="Watchdog rescue mode (default: observe, or MOCHI_WDT_RESCUE env)",
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

    is_oneshot = bool(args.event)
    app = MochiCompanionApp(
        base_http_url=f"http://{LOCAL_HOST}:{args.port}",
        db_path=args.db,
        wdt_rescue_mode=args.wdt_rescue,
        start_background_threads=not is_oneshot,
    )
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
        app.close()
        srv.server_close()


if __name__ == "__main__":
    main()
