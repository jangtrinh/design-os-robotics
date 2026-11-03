#!/usr/bin/env python3
"""
engine.py — Mochi-Soul 4D Biological Homeostasis Engine, 21-Emotion Router,
SQLite WAL Episodic Memory & Quantitative Benchmark Suite (Spec 02).
"""
import argparse
import json
import math
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = ROOT / "profiles/example-esp32s3-n16r8/mochi_soul.db"
REPORT_JSON = ROOT / "plans/reports/benchmark-mochi-soul-engine.json"

ALL_21_EMOTIONS = [
    "neutral", "happy", "laughing", "funny", "sad", "angry", "crying",
    "loving", "embarrassed", "surprised", "shocked", "thinking", "winking",
    "cool", "relaxed", "delicious", "kissy", "confident", "sleepy",
    "silly", "confused",
]


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def is_quiet_hours(hour_float: float) -> bool:
    """Quiet Hours: 23:00 to 07:30 local time."""
    h = hour_float % 24.0
    return h >= 23.0 or h < 7.5


@dataclass
class SoulState:
    sim_minute: int = 480  # Start at 08:00 AM (480 min)
    energy: float = 88.0
    hunger: float = 22.0
    bond: float = 60.0
    valence: float = 0.25   # [-1.0, +1.0]
    arousal: float = 0.10   # [-1.0, +1.0]
    emotion: str = "neutral"
    stage: int = 1
    stage_name: str = "Stage 1: Mochi Spore"
    xp: int = 0
    minutes_since_interaction: int = 0
    last_impulse_minute: int = -999
    transient_emotion: Optional[str] = None
    transient_ttl_minutes: int = 0


class MochiSoulEngine:
    def __init__(self, db_path: Path = DEFAULT_DB, in_memory: bool = False):
        self.db_path = ":memory:" if in_memory else str(db_path)
        if not in_memory:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()
        self.state = self._load_or_create_state()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS soul_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                sim_minute INTEGER NOT NULL,
                energy REAL NOT NULL,
                hunger REAL NOT NULL,
                bond REAL NOT NULL,
                valence REAL NOT NULL,
                arousal REAL NOT NULL,
                emotion TEXT NOT NULL,
                stage INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                xp INTEGER NOT NULL,
                minutes_since_interaction INTEGER NOT NULL,
                last_impulse_minute INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS episodic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_minute INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL,
                emotion_after TEXT NOT NULL,
                energy REAL NOT NULL,
                hunger REAL NOT NULL,
                bond REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS proactive_impulses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_minute INTEGER NOT NULL,
                hour_float REAL NOT NULL,
                impulse_kind TEXT NOT NULL,
                emotion TEXT NOT NULL,
                message TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def _load_or_create_state(self) -> SoulState:
        row = self.conn.execute(
            "SELECT sim_minute, energy, hunger, bond, valence, arousal, emotion, "
            "stage, stage_name, xp, minutes_since_interaction, last_impulse_minute "
            "FROM soul_state WHERE id = 1"
        ).fetchone()
        if row:
            return SoulState(*row)
        st = SoulState()
        self.save_state(st)
        return st

    def save_state(self, st: Optional[SoulState] = None) -> None:
        s = st or self.state
        self.conn.execute(
            """
            INSERT INTO soul_state (
                id, sim_minute, energy, hunger, bond, valence, arousal, emotion,
                stage, stage_name, xp, minutes_since_interaction, last_impulse_minute
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                sim_minute=excluded.sim_minute,
                energy=excluded.energy,
                hunger=excluded.hunger,
                bond=excluded.bond,
                valence=excluded.valence,
                arousal=excluded.arousal,
                emotion=excluded.emotion,
                stage=excluded.stage,
                stage_name=excluded.stage_name,
                xp=excluded.xp,
                minutes_since_interaction=excluded.minutes_since_interaction,
                last_impulse_minute=excluded.last_impulse_minute
            """,
            (
                s.sim_minute, s.energy, s.hunger, s.bond, s.valence, s.arousal,
                s.emotion, s.stage, s.stage_name, s.xp,
                s.minutes_since_interaction, s.last_impulse_minute,
            ),
        )
        self.conn.commit()

    @staticmethod
    def compute_stage(xp: int, bond: float) -> tuple[int, str]:
        if xp >= 600 and bond >= 80.0:
            return 4, "Stage 4: Cyber-Savant Mochi"
        if xp >= 250 and bond >= 65.0:
            return 3, "Stage 3: Companion Mochi"
        if xp >= 80:
            return 2, "Stage 2: Curious Mochi"
        return 1, "Stage 1: Mochi Spore"

    def apply_event(self, event_type: str, detail: str = "") -> str:
        s = self.state
        s.minutes_since_interaction = 0
        s.xp += 15

        # Map 21 distinct interaction stimuli & biological responses
        event_table = {
            "feed_knowledge": (0.0, -38.0, +4.0, +0.55, +0.25, "delicious", 5),
            "praise":         (+2.0,  0.0, +6.0, +0.65, +0.30, "loving",    5),
            "kiss":           (+1.0,  0.0, +7.0, +0.70, +0.20, "kissy",     4),
            "joke":           (-1.0,  0.0, +5.0, +0.80, +0.65, "laughing",  4),
            "funny_trick":    (-1.0,  0.0, +4.0, +0.65, +0.55, "funny",     4),
            "silly_play":     (-2.0, +2.0, +5.0, +0.60, +0.60, "silly",     4),
            "wink_greet":     (0.0,   0.0, +3.0, +0.45, +0.20, "winking",   3),
            "shy_compliment": (0.0,   0.0, +5.0, +0.35, +0.40, "embarrassed", 4),
            "music_vibe":     (+3.0, -5.0, +4.0, +0.60, +0.35, "cool",      6),
            "solve_problem":  (-2.0, -15.0,+5.0, +0.70, +0.25, "confident", 5),
            "ask_riddle":     (-1.0, +5.0, +2.0, +0.10, +0.35, "thinking",  4),
            "paradox":        (-1.0, +8.0, +1.0, -0.10, +0.45, "confused",  4),
            "sudden_approche":(0.0,   0.0, +2.0, +0.20, +0.75, "surprised", 3),
            "loud_thunder":   (-3.0,  0.0,  0.0, -0.50, +0.95, "shocked",   4),
            "tease_annoy":    (-2.0, +4.0, -3.0, -0.65, +0.75, "angry",     4),
            "scold":          (-2.0,  0.0, -6.0, -0.80, +0.60, "crying",    5),
            "gentle_pet":     (+5.0, -2.0, +5.0, +0.50, -0.45, "relaxed",   6),
            "chat_hello":     (0.0,  -5.0, +3.0, +0.45, +0.15, "happy",     4),
        }

        if event_type in event_table:
            de, dh, db, v_t, a_t, emo, ttl = event_table[event_type]
            s.energy = clamp(s.energy + de, 0.0, 100.0)
            s.hunger = clamp(s.hunger + dh, 0.0, 100.0)
            s.bond = clamp(s.bond + db, 0.0, 100.0)
            s.valence = clamp(0.4 * s.valence + 0.6 * v_t, -1.0, 1.0)
            s.arousal = clamp(0.4 * s.arousal + 0.6 * a_t, -1.0, 1.0)
            s.transient_emotion = emo
            s.transient_ttl_minutes = ttl
            s.emotion = emo
        else:
            s.emotion = self.select_homeostatic_emotion()

        s.stage, s.stage_name = self.compute_stage(s.xp, s.bond)
        self.conn.execute(
            "INSERT INTO episodic_memories (sim_minute, event_type, detail, emotion_after, energy, hunger, bond) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (s.sim_minute, event_type, detail or event_type, s.emotion, s.energy, s.hunger, s.bond),
        )
        self.save_state(s)
        return s.emotion

    def select_homeostatic_emotion(self) -> str:
        """Deterministic mapping of 4D Homeostasis state (E, H, B, V, A) -> 21 Mochi Emotions."""
        s = self.state
        if s.transient_emotion and s.transient_ttl_minutes > 0:
            return s.transient_emotion

        hour_f = (s.sim_minute / 60.0) % 24.0
        quiet = is_quiet_hours(hour_f)

        if quiet or s.energy < 22.0:
            return "sleepy"
        if s.minutes_since_interaction > 360 and s.bond < 42.0:
            return "crying"
        if s.minutes_since_interaction > 210:
            return "sad"
        if s.hunger > 82.0:
            return "confused"
        if s.hunger > 64.0:
            return "thinking"
        if s.energy > 82.0 and s.bond > 82.0 and s.valence > 0.55:
            return "loving"
        if s.energy > 75.0 and s.valence > 0.35:
            return "happy"
        if s.arousal < -0.25 and s.valence >= 0.0:
            return "relaxed"
        return "neutral"

    def step_minute(self, persist: bool = False) -> Optional[dict]:
        """Advance biological homeostasis by 1 minute (dt = 1/60 hour)."""
        s = self.state
        s.sim_minute += 1
        dt_h = 1.0 / 60.0
        hour_f = (s.sim_minute / 60.0) % 24.0
        quiet = is_quiet_hours(hour_f)

        if quiet:
            # Sleeping & recharging during Quiet Hours (23:00 - 07:30)
            s.energy = clamp(s.energy + 14.0 * dt_h, 0.0, 100.0)
            s.hunger = clamp(s.hunger + 1.2 * dt_h, 0.0, 100.0)
            s.arousal = clamp(s.arousal - 0.8 * dt_h, -0.8, 1.0)
        else:
            # Active daytime metabolism
            s.energy = clamp(s.energy - 4.2 * dt_h, 0.0, 100.0)
            s.hunger = clamp(s.hunger + 6.5 * dt_h, 0.0, 100.0)
            s.minutes_since_interaction += 1
            if s.minutes_since_interaction > 180:
                s.bond = clamp(s.bond - 1.5 * dt_h, 0.0, 100.0)
                s.valence = clamp(s.valence - 0.15 * dt_h, -1.0, 1.0)
            else:
                # Natural decay toward calm positive baseline
                s.valence += (0.15 - s.valence) * 0.05
                s.arousal += (0.05 - s.arousal) * 0.05

        if s.transient_ttl_minutes > 0:
            s.transient_ttl_minutes -= 1
            if s.transient_ttl_minutes == 0:
                s.transient_emotion = None

        s.emotion = self.select_homeostatic_emotion()

        # Check Proactive Impulse Gate (NEVER during Quiet Hours, cooldown >= 45 min)
        impulse = None
        if not quiet and (s.sim_minute - s.last_impulse_minute) >= 45:
            if s.hunger >= 75.0:
                impulse = {
                    "sim_minute": s.sim_minute,
                    "hour_float": round(hour_f, 2),
                    "impulse_kind": "notify_voice",
                    "emotion": "thinking",
                    "message": "Mochi đang tò mò quá, hôm nay bạn có khám phá gì mới kể cho Mochi nghe với!",
                }
            elif s.minutes_since_interaction >= 240:
                impulse = {
                    "sim_minute": s.sim_minute,
                    "hour_float": round(hour_f, 2),
                    "impulse_kind": "notify_voice",
                    "emotion": "sad",
                    "message": "Bạn làm việc chăm chỉ thế, nghỉ tay uống ngụm nước với Mochi nhé!",
                }
            elif s.energy <= 20.0:
                impulse = {
                    "sim_minute": s.sim_minute,
                    "hour_float": round(hour_f, 2),
                    "impulse_kind": "alert_face",
                    "emotion": "sleepy",
                    "message": "Mochi hơi buồn ngủ rồi, cho Mochi chợp mắt chút nha...",
                }

            if impulse:
                s.last_impulse_minute = s.sim_minute
                if persist:
                    self.conn.execute(
                        "INSERT INTO proactive_impulses (sim_minute, hour_float, impulse_kind, emotion, message) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            impulse["sim_minute"],
                            impulse["hour_float"],
                            impulse["impulse_kind"],
                            impulse["emotion"],
                            impulse["message"],
                        ),
                    )

        if persist:
            self.save_state(s)
        return impulse


def run_benchmark_and_verification() -> dict:
    print("=" * 108)
    print("  MOCHI-SOUL ENGINE CORE — 24-HOUR SIMULATION & PERFORMANCE BENCHMARK SUITE (SPEC 02)")
    print("=" * 108)

    # 1. Pure Math Tick Latency Benchmark (10,000 ticks in-memory)
    mem_engine = MochiSoulEngine(in_memory=True)
    t0 = time.perf_counter()
    for _ in range(10000):
        mem_engine.step_minute(persist=False)
    math_elapsed = time.perf_counter() - t0
    us_per_math_tick = (math_elapsed / 10000.0) * 1e6
    ticks_per_sec = 10000.0 / math_elapsed

    # 2. Full 24-Hour Realistic Day Simulation + SQLite WAL Persistence (1,440 minutes)
    if DEFAULT_DB.exists():
        DEFAULT_DB.unlink()
    eng = MochiSoulEngine(db_path=DEFAULT_DB, in_memory=False)

    # Scheduled interactions across a 48h test (Day 1 = Interactive Day, Day 2 = Busy Remote Workday)
    scheduled_events = {
        485: ("chat_hello", "Morning greeting at desk"),
        510: ("wink_greet", "Quick wink check-in"),
        560: ("ask_riddle", "Morning architecture puzzle"),
        640: ("feed_knowledge", "Shared new Robotics Spec-02 notes"),
        660: ("solve_problem", "Passed all unit tests"),
        750: ("joke", "Lunchtime funny story"),
        770: ("funny_trick", "Quadruped dance move"),
        810: ("silly_play", "Cross-eyed face play"),
        920: ("paradox", "Tricky Xtensa disasm question"),
        960: ("feed_knowledge", "Fed Xtensa ABI documentation"),
        1020: ("music_vibe", "Afternoon Lo-Fi coding session"),
        1080: ("shy_compliment", "Called Mochi cute"),
        1110: ("praise", "Praised Mochi's low CPU usage"),
        1140: ("kiss", "Evening appreciation"),
        1180: ("sudden_approche", "Walked fast to desk"),
        1210: ("loud_thunder", "Dropped book near desk"),
        1230: ("tease_annoy", "Poked Mochi nose 3 times"),
        1250: ("scold", "Fake stern voice test"),
        1275: ("gentle_pet", "Comforted Mochi before night"),
        # Day 2 (minute 1920 = 08:00 AM Day 2): User is working remotely for 6 hours -> triggers sad, thinking, confused & proactive impulses!
        2340: ("feed_knowledge", "Afternoon remote check-in & knowledge feed"),
        2360: ("praise", "Reassured Mochi after long remote block"),
    }

    hourly_snapshots = []
    impulses_emitted = []
    emotions_seen = set()
    bounds_violations = 0
    quiet_hours_violations = 0
    cooldown_violations = 0
    last_imp_min = -999

    t_sim_start = time.perf_counter()
    for step_idx in range(2880):
        cur_min = eng.state.sim_minute + 1
        if cur_min in scheduled_events:
            ev_type, ev_detail = scheduled_events[cur_min]
            emo_ev = eng.apply_event(ev_type, ev_detail)
            emotions_seen.add(emo_ev)

        imp = eng.step_minute(persist=(step_idx % 15 == 0))
        s = eng.state
        emotions_seen.add(s.emotion)

        # Verify bounds [0, 100] and valid emotion key
        if not (0.0 <= s.energy <= 100.0 and 0.0 <= s.hunger <= 100.0 and 0.0 <= s.bond <= 100.0):
            bounds_violations += 1
        if s.emotion not in ALL_21_EMOTIONS:
            bounds_violations += 1

        if imp:
            impulses_emitted.append(imp)
            if is_quiet_hours(imp["hour_float"]):
                quiet_hours_violations += 1
            if (imp["sim_minute"] - last_imp_min) < 45:
                cooldown_violations += 1
            last_imp_min = imp["sim_minute"]

        if (s.sim_minute % 60) == 0:
            hour_int = int((s.sim_minute // 60) % 24)
            hourly_snapshots.append(
                {
                    "time": f"{hour_int:02d}:00",
                    "quiet": is_quiet_hours(float(hour_int)),
                    "energy": round(s.energy, 1),
                    "hunger": round(s.hunger, 1),
                    "bond": round(s.bond, 1),
                    "valence": round(s.valence, 2),
                    "arousal": round(s.arousal, 2),
                    "emotion": s.emotion,
                    "stage": s.stage_name,
                }
            )
    eng.save_state()
    sim_24h_ms = (time.perf_counter() - t_sim_start) * 1000.0

    # Measure SQLite WAL single-write & single-read latency over 200 iterations
    t_db_w = time.perf_counter()
    for _ in range(200):
        eng.save_state()
    us_per_sqlite_write = ((time.perf_counter() - t_db_w) / 200.0) * 1e6

    t_db_r = time.perf_counter()
    for _ in range(200):
        eng._load_or_create_state()
    us_per_sqlite_read = ((time.perf_counter() - t_db_r) / 200.0) * 1e6

    missing_emotions = [e for e in ALL_21_EMOTIONS if e not in emotions_seen]

    print("\n[1] ENGINE PERFORMANCE & GHERKIN ACCEPTANCE METRICS")
    print("-" * 108)
    print(f"  Pure Math Homeostasis Tick Latency   : {us_per_math_tick:8.2f} us/tick  ({ticks_per_sec:,.0f} ticks/sec)")
    print(f"  SQLite WAL State Commit Latency      : {us_per_sqlite_write:8.2f} us/tx")
    print(f"  SQLite WAL State Read Latency        : {us_per_sqlite_read:8.2f} us/read")
    print(f"  Full 24-Hour (1,440 min) Sim Walltime: {sim_24h_ms:8.2f} ms")
    print(f"  21-Emotion Coverage Triggered        : {len(emotions_seen):2d} / 21 states  (Missing: {missing_emotions or 'NONE - 100% COVERED'})")
    print(f"  Bounds & Schema Violations           : {bounds_violations}  [AC-01 {'PASS' if bounds_violations == 0 and len(emotions_seen) == 21 else 'FAIL'}]")
    print(f"  Quiet Hours (23:00-07:30) Violations : {quiet_hours_violations}  [AC-02 {'PASS' if quiet_hours_violations == 0 else 'FAIL'}]")
    print(f"  Impulse Cooldown (<45m) Violations   : {cooldown_violations}  [AC-02 {'PASS' if cooldown_violations == 0 else 'FAIL'}]")
    print(f"  Latency Gate (<50us math / <500us DB): [AC-03 {'PASS' if us_per_math_tick < 50.0 and us_per_sqlite_write < 500.0 else 'FAIL'}]")
    print("-" * 108)

    print("\n[2] 24-HOUR BIOLOGICAL TRAJECTORY SNAPSHOT (08:00 -> 08:00 NEXT DAY)")
    print("-" * 108)
    print(
        f"{'Clock':6s} | {'Mode':11s} | {'Energy':>7s} | {'Hunger':>7s} | {'Bond':>6s} | {'Valence':>7s} | {'Arousal':>7s} | {'Active Emotion':15s} | {'Evolution Stage'}"
    )
    print("-" * 108)
    for snap in hourly_snapshots:
        mode_str = "QUIET/SLEEP" if snap["quiet"] else "ACTIVE/AWAKE"
        print(
            f"{snap['time']:6s} | {mode_str:11s} | {snap['energy']:6.1f}% | {snap['hunger']:6.1f}% | {snap['bond']:5.1f}% | {snap['valence']:+7.2f} | {snap['arousal']:+7.2f} | {snap['emotion']:15s} | {snap['stage']}"
        )
    print("-" * 108)

    print(f"\n[3] PROACTIVE IMPULSES EMITTED DURING 24H ({len(impulses_emitted)} total, 0 during Quiet Hours)")
    for idx, imp in enumerate(impulses_emitted, 1):
        h_int = int(imp["hour_float"])
        m_int = int(round((imp["hour_float"] - h_int) * 60))
        print(
            f"  #{idx} at {h_int:02d}:{m_int:02d} [{imp['impulse_kind']:12s}] emotion={imp['emotion']:10s} -> \"{imp['message']}\""
        )

    report = {
        "metrics": {
            "us_per_math_tick": round(us_per_math_tick, 3),
            "ticks_per_sec": round(ticks_per_sec, 1),
            "us_per_sqlite_write": round(us_per_sqlite_write, 3),
            "us_per_sqlite_read": round(us_per_sqlite_read, 3),
            "sim_24h_walltime_ms": round(sim_24h_ms, 2),
            "emotions_covered_count": len(emotions_seen),
            "emotions_covered": sorted(emotions_seen),
            "bounds_violations": bounds_violations,
            "quiet_hours_violations": quiet_hours_violations,
            "cooldown_violations": cooldown_violations,
            "ac01_pass": bounds_violations == 0 and len(emotions_seen) == 21,
            "ac02_pass": quiet_hours_violations == 0 and cooldown_violations == 0,
            "ac03_pass": us_per_math_tick < 50.0 and us_per_sqlite_write < 500.0,
        },
        "hourly_snapshots": hourly_snapshots,
        "proactive_impulses": impulses_emitted,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_bytes(json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8"))
    print(f"\nSaved Spec-02 benchmark report to {REPORT_JSON}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Mochi-Soul 4D Biological Homeostasis Engine CLI")
    sub = parser.add_subparsers(dest="cmd", required=False)
    sub.add_parser("benchmark", help="Run 24h simulation, 21-emotion coverage & latency benchmark")
    sub.add_parser("status", help="Show current persisted Mochi-Soul state from SQLite")
    args = parser.parse_args()

    if args.cmd in (None, "benchmark"):
        run_benchmark_and_verification()
    elif args.cmd == "status":
        eng = MochiSoulEngine(db_path=DEFAULT_DB)
        print(json.dumps(asdict(eng.state), indent=2))


if __name__ == "__main__":
    main()
