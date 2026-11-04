#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
serial_supervisor.py — Single-Owner Non-Intrusive USB-JTAG Serial Supervisor & Watchdog Auto-Rescue FSM (EVO-03).

Features:
  - Pure deterministic `WdtRescueFSM` with injected clock and zero I/O for 100% replayable testing (`--selftest`).
  - Recognizes the exact `ota_1` (v2.5.3) LVGL `_lv_inv_area` infinite loop (`0x4214E041:`) and generic `IDLE0` WDT.
  - Yields immediately (< 1s) when `esptool`/`idf.py`/`espflash` runs, when the advisory flash lock is held,
    or when `/api/serial/yield` is requested.
  - Never pulses in `DOWNLOAD_MODE`, during `BOOT_GRACE` (90s), or when `LOCKED_OUT` (>= 3 rescues/hour).
  - Atomic `TIOCMSET` RTS soft-reset pulse (`DTR=0, RTS=0` -> `DTR=0, RTS=1` 120ms -> `DTR=0, RTS=0` with `~HUPCL`).
"""
from __future__ import annotations

import argparse
import fcntl
import glob
import json
import os
import re
import select
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

RE_WDT = re.compile(r"task_wdt: Task watchdog got triggered")
RE_IDLE0 = re.compile(r"task_wdt:\s+-\s+IDLE0 \(CPU 0\)")
RE_MAIN = re.compile(r"task_wdt: CPU 0: main")
RE_LVGL = re.compile(r"Backtrace:.*\b0x4214[eE]041:")
RE_BOOT = re.compile(r"(?:ESP-ROM:|rst:0x[0-9a-fA-F]+|boot:0x[0-9a-fA-F]+)")
RE_DL = re.compile(r"waiting for download", re.IGNORECASE)
RE_VER = re.compile(r"App version:\s+(\S+)")
RE_ELF = re.compile(r"ELF file SHA256:\s+([0-9a-f]{8,})")
RE_UPTIME = re.compile(r"\((\d+)\)\s+[A-Za-z0-9_]+:")
RE_VOICE_WAKE = re.compile(
    r"(?:Wake word detected|Command \d+:\s*(?:HEY|HELLO|HI)\s+J)", re.IGNORECASE
)

TIOCMSET = 0x8004746D
TIOCM_DTR = 0x002
TIOCM_RTS = 0x004


def get_flash_lock_path() -> Path:
    runtime_dir = os.environ.get("MOCHI_RUNTIME_DIR", "").strip()
    base = Path(runtime_dir) if runtime_dir else Path(tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    return base / "mochi-serial-flash.lock"


def is_flash_lock_held() -> bool:
    lock_path = get_flash_lock_path()
    if not lock_path.exists():
        return False
    fd = None
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def is_flasher_process_running() -> bool:
    try:
        res = subprocess.run(
            ["pgrep", "-f", "esptool|idf\\.py|espflash"],
            capture_output=True,
            text=True,
            timeout=0.5,
            check=False,
        )
        my_pid = str(os.getpid())
        pids = [p.strip() for p in res.stdout.splitlines() if p.strip() and p.strip() != my_pid]
        return len(pids) > 0
    except Exception:
        return False


@dataclass
class HardwareEventRecord:
    wall_ts: int
    kind: str
    signature: Optional[str] = None
    uptime_ms: Optional[int] = None
    fw_version: Optional[str] = None
    rescue_mode: str = "observe"
    note: Optional[str] = None


@dataclass
class WdtRescueFSM:
    """
    Pure, deterministic Watchdog Detection & Auto-Rescue State Machine (zero I/O).
    Modes: 'off' | 'observe' | 'auto' (default: 'observe').
    """

    mode: str = "observe"
    now_fn: Callable[[], float] = time.time
    state: str = "DISCONNECTED"
    port_present: bool = False
    fw_version: Optional[str] = None
    elf_sha256: Optional[str] = None
    last_uptime_ms: Optional[int] = None
    last_signature: Optional[str] = None

    boot_grace_until: float = 0.0
    cooldown_until: float = 0.0
    yield_until: float = 0.0
    lock_release_resume_at: float = 0.0
    capture_deadline: float = 0.0
    verify_deadline: float = 0.0

    capture_saw_idle0: bool = False
    capture_saw_main: bool = False
    capture_saw_lvgl: bool = False
    last_suspect_ts: Optional[float] = None
    suspect_count: int = 0
    last_voice_wake_ts: float = 0.0

    rescue_timestamps: deque[float] = field(default_factory=lambda: deque(maxlen=16))
    events_emitted: list[HardwareEventRecord] = field(default_factory=list)
    pulse_requests: int = 0

    def _emit(self, kind: str, signature: Optional[str] = None, note: Optional[str] = None) -> None:
        self.events_emitted.append(
            HardwareEventRecord(
                wall_ts=int(self.now_fn()),
                kind=kind,
                signature=signature or self.last_signature,
                uptime_ms=self.last_uptime_ms,
                fw_version=self.fw_version,
                rescue_mode=self.mode,
                note=note,
            )
        )

    def _prune_rescue_window(self, now: float) -> None:
        while self.rescue_timestamps and (now - self.rescue_timestamps[0]) > 3600.0:
            self.rescue_timestamps.popleft()

    def rescues_last_hour(self, now: Optional[float] = None) -> int:
        t = float(now if now is not None else self.now_fn())
        self._prune_rescue_window(t)
        return len(self.rescue_timestamps)

    def set_external_status(self, port_present: bool, flash_lock_or_flasher: bool) -> None:
        now = float(self.now_fn())
        self.port_present = port_present

        if flash_lock_or_flasher:
            self.lock_release_resume_at = now + 120.0
            if self.state != "YIELDED":
                self.state = "YIELDED"
                self._emit("serial_yield", note="External flash lock or flasher detected")
            return

        if now < self.yield_until or now < self.lock_release_resume_at:
            if self.state != "YIELDED":
                self.state = "YIELDED"
            return

        if self.state == "YIELDED":
            self.state = "MONITORING" if port_present else "DISCONNECTED"
            return

        if not port_present and self.state not in ("PULSING", "VERIFYING", "LOCKED_OUT"):
            self.state = "DISCONNECTED"
        elif port_present and self.state == "DISCONNECTED":
            self.state = "MONITORING"

    def request_yield(self, seconds: float) -> dict:
        now = float(self.now_fn())
        dur = max(1.0, min(600.0, float(seconds)))
        self.yield_until = now + dur
        self.state = "YIELDED"
        self._emit("serial_yield", note=f"Yield requested for {int(dur)}s")
        return {
            "ok": True,
            "state": self.state,
            "yield_remaining_s": round(dur, 1),
        }

    def _confirm_crash(self, signature: str, now: float) -> None:
        self.last_signature = signature
        self.state = "CONFIRMED"
        self._emit("wdt_detected", signature=signature)

        if self.mode != "auto":
            self.state = "COOLDOWN"
            self.cooldown_until = now + 300.0
            return

        self._prune_rescue_window(now)
        if len(self.rescue_timestamps) >= 3:
            self.state = "LOCKED_OUT"
            self._emit("locked_out", signature=signature, note=">=3 rescues in rolling hour")
            return

        self._start_pulse(now, signature=signature)

    def _start_pulse(self, now: float, signature: str) -> None:
        self.rescue_timestamps.append(now)
        self.pulse_requests += 1
        self.state = "PULSING"
        self._emit("wdt_rescue_pulse", signature=signature)

    def complete_pulse_io(self) -> None:
        now = float(self.now_fn())
        if self.state == "PULSING":
            self.state = "VERIFYING"
            self.verify_deadline = now + 20.0

    def request_manual_rescue(
        self,
        confirm: bool = False,
        force: bool = False,
        flash_lock_held: bool = False,
    ) -> tuple[int, dict]:
        now = float(self.now_fn())
        if not confirm:
            return 400, {"accepted": False, "refused": "confirm_required"}
        if self.mode == "off":
            return 409, {"accepted": False, "refused": "mode_off"}
        if flash_lock_held or now < self.lock_release_resume_at:
            return 409, {"accepted": False, "refused": "flash_lock_held"}
        if self.state == "DOWNLOAD_MODE":
            return 409, {"accepted": False, "refused": "download_mode"}
        if self.state == "YIELDED" or now < self.yield_until:
            return 409, {"accepted": False, "refused": "yielded"}
        if not self.port_present:
            return 409, {"accepted": False, "refused": "port_absent"}
        if now < self.boot_grace_until:
            return 409, {"accepted": False, "refused": "boot_grace"}

        if not force:
            if now < self.cooldown_until:
                return 409, {"accepted": False, "refused": "cooldown"}
            self._prune_rescue_window(now)
            if len(self.rescue_timestamps) >= 3 or self.state == "LOCKED_OUT":
                return 409, {"accepted": False, "refused": "rate_limited"}

        self._start_pulse(now, signature=self.last_signature or "manual_operator")
        return 202, {"accepted": True, "state": self.state}

    def feed_line(self, line: str) -> Optional[str]:
        """
        Feed one UART log line into the FSM.
        Returns `"voice_wake"` if a debounced wake-word activation was observed, else `None`.
        """
        now = float(self.now_fn())
        clean = line.strip()
        if not clean:
            return None

        if self.state == "YIELDED":
            return None

        # 1. Check Download Mode first (highest safety invariant)
        if RE_DL.search(clean):
            self.state = "DOWNLOAD_MODE"
            self._emit("download_mode", note=clean[:80])
            return None

        # 2. Extract metadata (firmware version, ELF hash, uptime_ms)
        m_ver = RE_VER.search(clean)
        if m_ver:
            self.fw_version = m_ver.group(1)
        m_elf = RE_ELF.search(clean)
        if m_elf:
            self.elf_sha256 = m_elf.group(1)
        m_up = RE_UPTIME.search(clean)
        if m_up:
            try:
                self.last_uptime_ms = int(m_up.group(1))
            except ValueError:
                pass

        # 3. Check Boot Banner
        if RE_BOOT.search(clean):
            if self.state == "VERIFYING":
                self.state = "COOLDOWN"
                self.cooldown_until = now + 300.0
                self.boot_grace_until = now + 90.0
                self._emit("wdt_rescue_ok", note="Verified clean reboot banner")
                return None
            self.boot_grace_until = now + 90.0
            if self.state not in ("LOCKED_OUT", "DOWNLOAD_MODE"):
                self.state = "BOOT_GRACE"
            self._emit("boot_banner", note=clean[:80])
            return None

        # 4. If in VERIFYING, check if uptime_ms < 30000 confirms reboot
        if self.state == "VERIFYING" and self.last_uptime_ms is not None and self.last_uptime_ms < 30000:
            self.state = "COOLDOWN"
            self.cooldown_until = now + 300.0
            self.boot_grace_until = now + 90.0
            self._emit("wdt_rescue_ok", note=f"Verified uptime {self.last_uptime_ms}ms < 30000ms")
            return None

        # 5. Ignore WDT triggers during BOOT_GRACE
        if now < self.boot_grace_until:
            if self.state not in ("COOLDOWN", "LOCKED_OUT", "DOWNLOAD_MODE"):
                self.state = "BOOT_GRACE"
            return None
        elif self.state == "BOOT_GRACE":
            self.state = "MONITORING"

        # 6. Check Watchdog Trigger & Capture Window
        if RE_WDT.search(clean):
            if self.state in ("MONITORING", "SUSPECT", "COOLDOWN"):
                self.state = "CAPTURE"
                self.capture_deadline = now + 2.0
                self.capture_saw_idle0 = False
                self.capture_saw_main = False
                self.capture_saw_lvgl = False
            return None

        if self.state == "CAPTURE":
            if RE_IDLE0.search(clean):
                self.capture_saw_idle0 = True
            if RE_MAIN.search(clean):
                self.capture_saw_main = True
            if RE_LVGL.search(clean):
                self.capture_saw_lvgl = True

            fw_ok = self.fw_version in (None, "", "2.5.3", "v2.5.3")
            if self.capture_saw_idle0 and self.capture_saw_lvgl and fw_ok:
                self._confirm_crash("lvgl_0x4214e041", now)
                return None

        # 7. Optional debounced voice wake detection
        if RE_VOICE_WAKE.search(clean) and (now - self.last_voice_wake_ts) >= 60.0:
            self.last_voice_wake_ts = now
            return "voice_wake"

        return None

    def step_clock(self) -> None:
        """Advance time-dependent transitions (`CAPTURE` window end, `VERIFYING` timeout, `SUSPECT` expiry)."""
        now = float(self.now_fn())

        if self.state == "YIELDED":
            if now >= self.yield_until and now >= self.lock_release_resume_at:
                self.state = "MONITORING" if self.port_present else "DISCONNECTED"
            return

        if self.state == "BOOT_GRACE" and now >= self.boot_grace_until:
            self.state = "MONITORING"

        if self.state == "COOLDOWN" and now >= self.cooldown_until:
            self.state = "MONITORING" if self.port_present else "DISCONNECTED"

        if self.state == "CAPTURE" and now >= self.capture_deadline:
            fw_ok = self.fw_version in (None, "", "2.5.3", "v2.5.3")
            if self.capture_saw_idle0 and self.capture_saw_lvgl and fw_ok:
                self._confirm_crash("lvgl_0x4214e041", now)
            elif self.capture_saw_idle0:
                if (
                    self.last_suspect_ts is not None
                    and 120.0 <= (now - self.last_suspect_ts) <= 180.0
                ):
                    self._confirm_crash("generic_idle0_x2", now)
                else:
                    self.state = "SUSPECT"
                    self.last_suspect_ts = now
                    self.suspect_count = 1
            else:
                self.state = "MONITORING"

        if self.state == "SUSPECT" and self.last_suspect_ts is not None:
            if (now - self.last_suspect_ts) > 200.0:
                self.state = "MONITORING"
                self.last_suspect_ts = None
                self.suspect_count = 0

        if self.state == "VERIFYING" and now >= self.verify_deadline:
            self.state = "COOLDOWN"
            self.cooldown_until = now + 300.0
            self._emit("wdt_rescue_failed", note="Reboot verification timed out after 20s")

    def snapshot(self) -> dict:
        now = float(self.now_fn())
        cd_rem = max(0.0, self.cooldown_until - now)
        yd_rem = max(0.0, max(self.yield_until, self.lock_release_resume_at) - now)
        return {
            "mode": self.mode,
            "state": self.state,
            "port_present": self.port_present,
            "fw_version": self.fw_version or "2.5.3",
            "last_signature": self.last_signature,
            "rescues_last_hour": self.rescues_last_hour(now),
            "cooldown_remaining_s": round(cd_rem, 1),
            "yield_remaining_s": round(yd_rem, 1),
        }


class SerialSupervisor:
    """
    Single-owner background thread managing `/dev/cu.usbmodem*` (`~HUPCL`, 115200 8N1)
    and driving `WdtRescueFSM`. Never exposes port paths or serial numbers in API payloads.
    """

    def __init__(
        self,
        mode: Optional[str] = None,
        on_hardware_event: Optional[Callable[[HardwareEventRecord], None]] = None,
        on_voice_wake: Optional[Callable[[], None]] = None,
        enabled: bool = True,
    ):
        resolved_mode = (mode or os.environ.get("MOCHI_WDT_RESCUE", "observe")).strip().lower()
        if resolved_mode not in ("off", "observe", "auto"):
            resolved_mode = "observe"
        self.lock = threading.RLock()
        self.fsm = WdtRescueFSM(mode=resolved_mode)
        self.on_hardware_event = on_hardware_event
        self.on_voice_wake = on_voice_wake
        self.enabled = enabled
        self._fd: Optional[int] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_proc_check: float = 0.0
        self._flash_active_cached: bool = False

    def start(self) -> None:
        if not self.enabled or self.fsm.mode == "off":
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="mochi-serial-supervisor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._close_fd()

    def _close_fd(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    @staticmethod
    def _discover_port() -> Optional[str]:
        env_p = os.environ.get("ESPPORT", "").strip()
        if env_p and os.path.exists(env_p):
            return env_p
        candidates = sorted(glob.glob("/dev/cu.usbmodem*"))
        return candidates[0] if candidates else None

    def _open_port_nonintrusive(self, port_path: str) -> Optional[int]:
        try:
            fd = os.open(port_path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            attrs = termios.tcgetattr(fd)
            attrs[0] = 0
            attrs[1] = 0
            attrs[2] = (
                attrs[2] & ~(termios.CSIZE | termios.PARENB | termios.CSTOPB | termios.HUPCL)
            ) | termios.CS8 | termios.CREAD | termios.CLOCAL
            attrs[3] = 0
            attrs[4] = termios.B115200
            attrs[5] = termios.B115200
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            return fd
        except OSError:
            return None

    def _execute_atomic_rts_pulse(self) -> None:
        fd = self._fd
        if fd is None:
            port = self._discover_port()
            if port:
                fd = self._open_port_nonintrusive(port)
                self._fd = fd
        if fd is None:
            return
        try:
            fcntl.ioctl(fd, TIOCMSET, struct.pack("I", 0))
            time.sleep(0.05)
            fcntl.ioctl(fd, TIOCMSET, struct.pack("I", TIOCM_RTS))
            time.sleep(0.12)
            fcntl.ioctl(fd, TIOCMSET, struct.pack("I", 0))
        except OSError:
            self._close_fd()

    def _flush_emitted_events(self) -> None:
        while self.fsm.events_emitted:
            ev = self.fsm.events_emitted.pop(0)
            if self.on_hardware_event:
                try:
                    self.on_hardware_event(ev)
                except Exception:
                    pass

    def _run_loop(self) -> None:
        line_buf = ""
        while not self._stop_event.is_set():
            now = time.time()
            if (now - self._last_proc_check) >= 1.0:
                self._flash_active_cached = is_flash_lock_held() or is_flasher_process_running()
                self._last_proc_check = now

            port_path = self._discover_port()
            with self.lock:
                self.fsm.set_external_status(
                    port_present=bool(port_path),
                    flash_lock_or_flasher=self._flash_active_cached,
                )
                if self.fsm.state == "YIELDED":
                    self._close_fd()
                    self._flush_emitted_events()

            if self.fsm.state == "YIELDED":
                time.sleep(0.25)
                continue

            if self._fd is None and port_path:
                self._fd = self._open_port_nonintrusive(port_path)

            if self._fd is not None:
                try:
                    r, _, _ = select.select([self._fd], [], [], 0.2)
                    if r:
                        chunk = os.read(self._fd, 4096)
                        if not chunk:
                            self._close_fd()
                        else:
                            line_buf += chunk.decode("utf-8", errors="replace")
                            while "\n" in line_buf:
                                line, line_buf = line_buf.split("\n", 1)
                                wake_sig = None
                                with self.lock:
                                    wake_sig = self.fsm.feed_line(line)
                                    if self.fsm.state == "PULSING":
                                        self._execute_atomic_rts_pulse()
                                        self.fsm.complete_pulse_io()
                                    self._flush_emitted_events()
                                if wake_sig == "voice_wake" and self.on_voice_wake:
                                    try:
                                        self.on_voice_wake()
                                    except Exception:
                                        pass
                except BlockingIOError:
                    pass
                except OSError:
                    self._close_fd()
            else:
                time.sleep(0.5)

            with self.lock:
                self.fsm.step_clock()
                if self.fsm.state == "PULSING":
                    self._execute_atomic_rts_pulse()
                    self.fsm.complete_pulse_io()
                self._flush_emitted_events()

    def snapshot(self) -> dict:
        with self.lock:
            port_path = self._discover_port()
            self.fsm.port_present = bool(port_path)
            self.fsm.step_clock()
            return self.fsm.snapshot()

    def request_yield(self, seconds: float = 120.0) -> dict:
        with self.lock:
            self._close_fd()
            res = self.fsm.request_yield(seconds)
            self._flush_emitted_events()
            return res

    def request_manual_rescue(self, confirm: bool = False, force: bool = False) -> tuple[int, dict]:
        flash_busy = is_flash_lock_held() or is_flasher_process_running()
        with self.lock:
            port_path = self._discover_port()
            self.fsm.port_present = bool(port_path)
            status, payload = self.fsm.request_manual_rescue(
                confirm=confirm, force=force, flash_lock_held=flash_busy
            )
            if self.fsm.state == "PULSING":
                self._execute_atomic_rts_pulse()
                self.fsm.complete_pulse_io()
            self._flush_emitted_events()
            return status, payload


def run_selftest() -> bool:
    """
    Deterministic replay suite verifying V-15 across all 8 required fixtures:
      1. LVGL `0x4214E041:` crash -> CONFIRMED immediately (and PULSING in auto mode)
      2. Generic IDLE0 WDT x1 -> SUSPECT
      3. Generic IDLE0 WDT x2 at +150s -> CONFIRMED
      4. Boot banner + WDT within 90s -> ignored (BOOT_GRACE)
      5. Download mode (`waiting for download`) -> DOWNLOAD_MODE, 0 pulses even on force
      6. Flash lock held -> YIELDED within <1s, 0 pulses
      7. 4th rescue in 1 rolling hour -> LOCKED_OUT, 0 pulses
      8. Observe mode on LVGL crash -> COOLDOWN, logs `wdt_detected`, 0 pulses
    """
    now = [1000.0]

    def clock() -> float:
        return now[0]

    # 1. LVGL 0x4214E041 in auto mode -> immediate CONFIRMED -> PULSING
    fsm1 = WdtRescueFSM(mode="auto", now_fn=clock)
    fsm1.set_external_status(port_present=True, flash_lock_or_flasher=False)
    fsm1.feed_line("E (24931609) task_wdt: Task watchdog got triggered. The following tasks/users did not reset the watchdog in time:")
    fsm1.feed_line("E (24931609) task_wdt:  - IDLE0 (CPU 0)")
    fsm1.feed_line("E (24931609) task_wdt: CPU 0: main")
    fsm1.feed_line("Backtrace: 0x4214E041:0x3fc9b120 0x4202CACE:0x3fc9b140")
    assert fsm1.state == "PULSING" and fsm1.pulse_requests == 1, f"Fixture 1 failed: {fsm1.state}"

    # 2 & 3. Generic IDLE0 x1 -> SUSPECT; x2 at +150s -> CONFIRMED (PULSING)
    now[0] = 2000.0
    fsm2 = WdtRescueFSM(mode="auto", now_fn=clock)
    fsm2.set_external_status(port_present=True, flash_lock_or_flasher=False)
    fsm2.feed_line("E (100000) task_wdt: Task watchdog got triggered.")
    fsm2.feed_line("E (100000) task_wdt:  - IDLE0 (CPU 0)")
    now[0] += 2.5
    fsm2.step_clock()
    assert fsm2.state == "SUSPECT" and fsm2.pulse_requests == 0, f"Fixture 2 failed: {fsm2.state}"

    now[0] += 150.0
    fsm2.feed_line("E (250000) task_wdt: Task watchdog got triggered.")
    fsm2.feed_line("E (250000) task_wdt:  - IDLE0 (CPU 0)")
    now[0] += 2.5
    fsm2.step_clock()
    assert fsm2.state == "PULSING" and fsm2.pulse_requests == 1, f"Fixture 3 failed: {fsm2.state}"

    # 4. Boot banner + WDT within 90s -> ignored in BOOT_GRACE
    now[0] = 3000.0
    fsm4 = WdtRescueFSM(mode="auto", now_fn=clock)
    fsm4.set_external_status(port_present=True, flash_lock_or_flasher=False)
    fsm4.feed_line("ESP-ROM:esp32s3-20210327")
    now[0] += 30.0
    fsm4.feed_line("E (30000) task_wdt: Task watchdog got triggered.")
    fsm4.feed_line("E (30000) task_wdt:  - IDLE0 (CPU 0)")
    fsm4.feed_line("Backtrace: 0x4214E041:0x3fc9b120")
    assert fsm4.state == "BOOT_GRACE" and fsm4.pulse_requests == 0, f"Fixture 4 failed: {fsm4.state}"

    # 5. Download mode -> DOWNLOAD_MODE, 0 pulses even on manual force=True
    now[0] = 4000.0
    fsm5 = WdtRescueFSM(mode="auto", now_fn=clock)
    fsm5.set_external_status(port_present=True, flash_lock_or_flasher=False)
    fsm5.feed_line("rst:0x1 (POWERON),boot:0x0 (DOWNLOAD(USB/UART0))")
    fsm5.feed_line("waiting for download")
    code5, body5 = fsm5.request_manual_rescue(confirm=True, force=True, flash_lock_held=False)
    assert fsm5.state == "DOWNLOAD_MODE" and code5 == 409 and fsm5.pulse_requests == 0, (
        f"Fixture 5 failed: {fsm5.state} {code5} {body5}"
    )

    # 6. Flash lock held -> YIELDED immediately, 0 pulses
    now[0] = 5000.0
    fsm6 = WdtRescueFSM(mode="auto", now_fn=clock)
    fsm6.set_external_status(port_present=True, flash_lock_or_flasher=True)
    code6, _ = fsm6.request_manual_rescue(confirm=True, force=True, flash_lock_held=True)
    assert fsm6.state == "YIELDED" and code6 == 409 and fsm6.pulse_requests == 0, (
        f"Fixture 6 failed: {fsm6.state}"
    )

    # 7. 4th rescue in a rolling hour -> LOCKED_OUT, 0 additional pulses
    now[0] = 6000.0
    fsm7 = WdtRescueFSM(mode="auto", now_fn=clock)
    fsm7.set_external_status(port_present=True, flash_lock_or_flasher=False)
    for i in range(3):
        now[0] += 400.0
        fsm7.feed_line("E (99999) task_wdt: Task watchdog got triggered.")
        fsm7.feed_line("E (99999) task_wdt:  - IDLE0 (CPU 0)")
        fsm7.feed_line("Backtrace: 0x4214E041:0x3fc9b120")
        fsm7.complete_pulse_io()
        fsm7.feed_line("rst:0x1 (POWERON),boot:0x8 (SPI_FAST_FLASH_BOOT)")
        now[0] += 310.0
        fsm7.step_clock()
    assert fsm7.pulse_requests == 3, f"Expected 3 pulses before lockout, got {fsm7.pulse_requests}"
    now[0] += 10.0
    fsm7.feed_line("E (99999) task_wdt: Task watchdog got triggered.")
    fsm7.feed_line("E (99999) task_wdt:  - IDLE0 (CPU 0)")
    fsm7.feed_line("Backtrace: 0x4214E041:0x3fc9b120")
    assert fsm7.state == "LOCKED_OUT" and fsm7.pulse_requests == 3, f"Fixture 7 failed: {fsm7.state}"

    # 8. Observe mode on LVGL crash -> COOLDOWN, logs wdt_detected, 0 pulses
    now[0] = 10000.0
    fsm8 = WdtRescueFSM(mode="observe", now_fn=clock)
    fsm8.set_external_status(port_present=True, flash_lock_or_flasher=False)
    fsm8.feed_line("E (24931609) task_wdt: Task watchdog got triggered.")
    fsm8.feed_line("E (24931609) task_wdt:  - IDLE0 (CPU 0)")
    fsm8.feed_line("Backtrace: 0x4214E041:0x3fc9b120")
    assert fsm8.state == "COOLDOWN" and fsm8.pulse_requests == 0, f"Fixture 8 failed: {fsm8.state}"
    assert any(e.kind == "wdt_detected" for e in fsm8.events_emitted), "Fixture 8 missing wdt_detected"

    print("PASS: WdtRescueFSM --selftest (8/8 fixtures verified)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mochi-Soul Single-Owner USB-JTAG Serial Supervisor & Watchdog Rescue FSM"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run deterministic 8-fixture WdtRescueFSM replay verification (V-15)",
    )
    parser.add_argument(
        "--mode",
        choices=("off", "observe", "auto"),
        default="observe",
        help="Watchdog rescue mode (default: observe)",
    )
    args = parser.parse_args()
    if args.selftest:
        ok = run_selftest()
        sys.exit(0 if ok else 1)
    sup = SerialSupervisor(mode=args.mode, enabled=False)
    print(json.dumps(sup.snapshot(), indent=2))


if __name__ == "__main__":
    main()
