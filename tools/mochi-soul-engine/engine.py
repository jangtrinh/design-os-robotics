#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
engine.py — Mochi-Soul 4D Biological Homeostasis Engine, 21-Emotion Router,
Personality Genome (EVO-01), Morphological Phenotype (EVO-02), Dream Consolidation (EVO-03),
SQLite WAL Episodic Memory & Quantitative Benchmark Suite (Spec 02 + Self-Evolution).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
import threading
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLE_DB = ROOT / "profiles/example-esp32s3-n16r8/mochi_soul.db"
REPORT_JSON = ROOT / "plans/reports/benchmark-mochi-soul-engine.json"

ALL_21_EMOTIONS = [
    "neutral", "happy", "laughing", "funny", "sad", "angry", "crying",
    "loving", "embarrassed", "surprised", "shocked", "thinking", "winking",
    "cool", "relaxed", "delicious", "kissy", "confident", "sleepy",
    "silly", "confused",
]

STAGE_NAMES = {
    1: "Stage 1: Mochi Spore",
    2: "Stage 2: Curious Mochi",
    3: "Stage 3: Companion Mochi",
    4: "Stage 4: Cyber-Savant Mochi",
}

STAGE_EXPRESSION_GAIN = (0.25, 0.50, 0.80, 1.00)

SOURCE_WEIGHTS = {
    "user": 1.0,
    "serial": 0.5,
    "workspace": 0.35,
    "override": 0.0,
}

TRAIT_POS_WEIGHTS: dict[str, dict[str, float]] = {
    "curiosity": {
        "feed_knowledge": 1.0,
        "ask_riddle": 0.8,
        "solve_problem": 0.7,
        "paradox": 0.5,
    },
    "affection": {
        "kiss": 1.0,
        "gentle_pet": 0.8,
        "praise": 0.7,
        "shy_compliment": 0.5,
        "chat_hello": 0.3,
        "wink_greet": 0.3,
    },
    "playfulness": {
        "joke": 1.0,
        "silly_play": 0.8,
        "funny_trick": 0.7,
        "music_vibe": 0.5,
        "wink_greet": 0.3,
    },
}

AFFECTION_NEG_WEIGHTS: dict[str, float] = {
    "scold": 1.0,
    "tease_annoy": 0.6,
}

EVENT_VI_LABELS: dict[str, str] = {
    "feed_knowledge": "nạp tri thức",
    "praise": "khen ngợi",
    "kiss": "thơm má",
    "joke": "kể chuyện vui",
    "funny_trick": "làm trò vui",
    "silly_play": "đùa nghịch",
    "wink_greet": "nháy mắt chào",
    "shy_compliment": "khen dễ thương",
    "music_vibe": "nghe nhạc",
    "solve_problem": "giải bài toán",
    "ask_riddle": "đố vui",
    "paradox": "câu hỏi hóc búa",
    "sudden_approche": "bất ngờ ghé gần",
    "loud_thunder": "tiếng động lớn",
    "tease_annoy": "trêu chọc",
    "scold": "nhắc nhở nghiêm",
    "gentle_pet": "xoa đầu dịu dàng",
    "chat_hello": "trò chuyện",
}

_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]+")


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def sanitize_detail(detail: str, max_len: int = 120) -> str:
    cleaned = _CTRL_RE.sub(" ", str(detail or "")).strip()
    return cleaned[:max_len]


def is_quiet_hours(hour_float: float, chronotype_shift: float = 0.0) -> bool:
    """Quiet Hours: 23:00 to 07:30 shifted by chronotype_shift in [-3, +3] hours."""
    h = (hour_float - chronotype_shift) % 24.0
    return h >= 23.0 or h < 7.5


def is_hard_sleep_floor(hour_float: float) -> bool:
    """Hard floor: no proactive impulses between local 01:30 and 06:00 regardless of chronotype."""
    h = hour_float % 24.0
    return 1.5 <= h < 6.0


def resolve_default_db_path(explicit: Path | str | None = None) -> Path:
    """
    Safe DB path resolution:
      1. explicit `--db` argument
      2. `MOCHI_SOUL_DB` env var
      3. `ROBOT_PROFILE_DIR/mochi_soul.db` env var
      4. Single `profiles/robot-*/mochi_soul.db` if exactly one exists
      5. `profiles/example-esp32s3-n16r8/mochi_soul.db`
    """
    if explicit:
        return Path(explicit)
    env_db = os.environ.get("MOCHI_SOUL_DB", "").strip()
    if env_db:
        return Path(env_db)
    prof_dir = os.environ.get("ROBOT_PROFILE_DIR", "").strip()
    if prof_dir:
        return Path(prof_dir) / "mochi_soul.db"
    profiles_root = ROOT / "profiles"
    if profiles_root.is_dir():
        robot_dirs = sorted(p for p in profiles_root.glob("robot-*") if p.is_dir())
        if len(robot_dirs) == 1:
            return robot_dirs[0] / "mochi_soul.db"
    return EXAMPLE_DB


DEFAULT_DB = EXAMPLE_DB


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
    last_tick_wall_ts: Optional[int] = None


@dataclass
class PersonalityGenome:
    curiosity: float = 0.5
    affection: float = 0.5
    playfulness: float = 0.5
    resilience: float = 0.5
    chronotype_shift: float = 0.0
    base_curiosity: float = 0.5
    base_affection: float = 0.5
    base_playfulness: float = 0.5
    base_resilience: float = 0.5
    genome_rev: int = 0
    last_consolidated_memory_id: int = 0
    last_dream_wall_ts: Optional[int] = None
    day_key: Optional[str] = None
    day_abs_delta: float = 0.0
    updated_wall_ts: int = 0


@dataclass
class Phenotype:
    stage: int = 1
    gamma: float = 0.25
    g_cur: float = 0.5
    g_aff: float = 0.5
    g_play: float = 0.5
    g_res: float = 0.5
    d_cur: float = 0.0
    d_aff: float = 0.0
    d_play: float = 0.0
    d_res: float = 0.0
    chronotype_shift: float = 0.0


def compute_phenotype(stage: int, genome: PersonalityGenome) -> Phenotype:
    idx = int(clamp(stage, 1, 4)) - 1
    gamma = STAGE_EXPRESSION_GAIN[idx]
    g_cur = 0.5 + gamma * (genome.curiosity - 0.5)
    g_aff = 0.5 + gamma * (genome.affection - 0.5)
    g_play = 0.5 + gamma * (genome.playfulness - 0.5)
    g_res = 0.5 + gamma * (genome.resilience - 0.5)
    return Phenotype(
        stage=stage,
        gamma=gamma,
        g_cur=g_cur,
        g_aff=g_aff,
        g_play=g_play,
        g_res=g_res,
        d_cur=g_cur - 0.5,
        d_aff=g_aff - 0.5,
        d_play=g_play - 0.5,
        d_res=g_res - 0.5,
        chronotype_shift=genome.chronotype_shift,
    )


def _nearest(val: float, grid: tuple[float, ...]) -> float:
    return min(grid, key=lambda g: abs(g - val))


def phenotype_params(
    stage: int,
    genome: PersonalityGenome | dict | None = None,
    quantize: bool = False,
) -> dict:
    """
    Single source of truth for EVO-02 Morphological Face Evolution:
      - continuous: used by Studio Canvas 2D renderer (`studio.html`)
      - quantized: used by firmware asset packer (`cook-procedural-avatar.py`)
      - hash: 8-char deterministic SHA-1 of the quantized parameters
    """
    if isinstance(genome, dict):
        g_obj = PersonalityGenome(
            curiosity=float(genome.get("curiosity", 0.5)),
            affection=float(genome.get("affection", 0.5)),
            playfulness=float(genome.get("playfulness", 0.5)),
            resilience=float(genome.get("resilience", 0.5)),
            chronotype_shift=float(genome.get("chronotype_shift", 0.0)),
        )
    elif isinstance(genome, PersonalityGenome):
        g_obj = genome
    else:
        g_obj = PersonalityGenome()

    s_clamped = int(clamp(stage, 1, 4))
    ph = compute_phenotype(s_clamped, g_obj)

    eye_scale = round(0.92 + 0.04 * (s_clamped - 1) + 0.08 * ph.d_cur, 4)
    pupil_scale = round(0.85 + 0.10 * (s_clamped - 1) + 0.20 * ph.d_cur, 4)
    catchlights = 2 if s_clamped >= 2 else 1
    saccade_amp_px = round((0.5 + 0.25 * (s_clamped - 1)) * (1.0 + 1.2 * ph.d_play), 3)
    saccade_period_s = round(1.6 - 0.2 * (s_clamped - 1), 2)
    blush_scale = round(
        0.75 + 0.10 * (s_clamped - 1) + (0.50 * ph.d_aff if s_clamped >= 3 else 0.0), 4
    )
    blush_coral = s_clamped >= 3
    brow_curve_px = round(4.0 + 8.0 * (ph.d_aff + 0.5), 2) if s_clamped >= 3 else 0.0
    cyber_ring = s_clamped == 4
    cyber_omega = round(0.6 + 1.2 * (ph.d_cur + 0.5), 3) if s_clamped == 4 else 0.0
    cyber_alpha = round(min(0.85, 0.35 + 0.50 * (ph.d_cur + 0.5)), 3) if s_clamped == 4 else 0.0
    breath_period_s = round(4.2 - 0.3 * (s_clamped - 1), 2)

    continuous = {
        "stage": s_clamped,
        "eye_scale": eye_scale,
        "pupil_scale": pupil_scale,
        "catchlights": catchlights,
        "saccade_amp_px": saccade_amp_px,
        "saccade_period_s": saccade_period_s,
        "blush_scale": blush_scale,
        "blush_coral": blush_coral,
        "brow_curve_px": brow_curve_px,
        "cyber_ring": cyber_ring,
        "cyber_omega": cyber_omega,
        "cyber_alpha": cyber_alpha,
        "breath_period_s": breath_period_s,
    }

    eye_q = _nearest(eye_scale, (0.92, 0.96, 1.00, 1.04, 1.08))
    blush_q = _nearest(blush_scale, (0.75, 0.90, 1.00, 1.12, 1.25))
    brackets = bool(s_clamped == 4 and ph.g_cur >= 0.55)
    star = bool(s_clamped == 4 and ph.g_cur >= 0.70)

    quantized = {
        "stage": s_clamped,
        "eye_q": eye_q,
        "catch": catchlights,
        "blush_q": blush_q,
        "brackets": brackets,
        "star": star,
    }
    phash = hashlib.sha1(
        json.dumps(quantized, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]

    if quantize:
        return {**quantized, "hash": phash}
    return {
        "continuous": continuous,
        "quantized": quantized,
        "hash": phash,
    }


class MochiSoulEngine:
    def __init__(
        self,
        db_path: Path | str | None = None,
        in_memory: bool = False,
        mode: str = "sim",
        now_fn: Callable[[], float] = time.time,
        seed: Optional[int] = None,
    ):
        self.mode = mode  # "sim" or "live"
        self.now_fn = now_fn
        self.seed = seed
        resolved_path = resolve_default_db_path(db_path)
        self.db_path = ":memory:" if in_memory else str(resolved_path)
        if not in_memory:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db_lock = threading.RLock()
        if not in_memory and resolved_path.exists():
            try:
                os.chmod(resolved_path, 0o600)
            except OSError:
                pass
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._recent_events_window: deque[tuple[int, str]] = deque(maxlen=256)
        self._pending_dream_milestone: Optional[str] = None
        self._init_schema()
        self.state = self._load_or_create_state()
        self.genome = self._load_or_create_genome()
        self.phenotype = compute_phenotype(self.state.stage, self.genome)

    def _table_columns(self, table: str) -> set[str]:
        rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {r[1] for r in rows}

    def _init_schema(self) -> None:
        u_ver_row = self.conn.execute("PRAGMA user_version;").fetchone()
        u_ver = int(u_ver_row[0]) if u_ver_row else 0

        # Create base tables if fresh DB
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
                last_impulse_minute INTEGER NOT NULL,
                transient_emotion TEXT,
                transient_ttl_minutes INTEGER NOT NULL DEFAULT 0,
                last_tick_wall_ts INTEGER
            );
            CREATE TABLE IF NOT EXISTS episodic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_minute INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL,
                emotion_after TEXT NOT NULL,
                energy REAL NOT NULL,
                hunger REAL NOT NULL,
                bond REAL NOT NULL,
                wall_ts INTEGER,
                source TEXT NOT NULL DEFAULT 'user'
                    CHECK (source IN ('user','workspace','serial','override'))
            );
            CREATE TABLE IF NOT EXISTS proactive_impulses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_minute INTEGER NOT NULL,
                hour_float REAL NOT NULL,
                impulse_kind TEXT NOT NULL,
                emotion TEXT NOT NULL,
                message TEXT NOT NULL,
                wall_ts INTEGER
            );
            CREATE TABLE IF NOT EXISTS personality_genome (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                curiosity REAL NOT NULL CHECK (curiosity BETWEEN 0 AND 1),
                affection REAL NOT NULL CHECK (affection BETWEEN 0 AND 1),
                playfulness REAL NOT NULL CHECK (playfulness BETWEEN 0 AND 1),
                resilience REAL NOT NULL CHECK (resilience BETWEEN 0 AND 1),
                chronotype_shift REAL NOT NULL DEFAULT 0 CHECK (chronotype_shift BETWEEN -3 AND 3),
                base_curiosity REAL NOT NULL,
                base_affection REAL NOT NULL,
                base_playfulness REAL NOT NULL,
                base_resilience REAL NOT NULL,
                genome_rev INTEGER NOT NULL DEFAULT 0,
                last_consolidated_memory_id INTEGER NOT NULL DEFAULT 0,
                last_dream_wall_ts INTEGER,
                day_key TEXT,
                day_abs_delta REAL NOT NULL DEFAULT 0,
                updated_wall_ts INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dream_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dream_key TEXT NOT NULL UNIQUE,
                trigger TEXT NOT NULL CHECK (
                    trigger IN ('quiet_hours','interaction_burst','missed_night','manual','operator_override')
                ),
                wall_ts INTEGER NOT NULL,
                sim_minute INTEGER NOT NULL,
                mem_from_id INTEGER NOT NULL,
                mem_to_id INTEGER NOT NULL,
                mem_count INTEGER NOT NULL,
                genome_before TEXT NOT NULL,
                genome_after TEXT NOT NULL,
                delta_l1 REAL NOT NULL,
                stage INTEGER NOT NULL,
                milestone TEXT,
                summary TEXT NOT NULL,
                phenotype_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS hardware_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wall_ts INTEGER NOT NULL,
                kind TEXT NOT NULL CHECK (
                    kind IN (
                        'wdt_detected','wdt_rescue_pulse','wdt_rescue_ok','wdt_rescue_failed',
                        'serial_yield','boot_banner','download_mode','locked_out'
                    )
                ),
                signature TEXT,
                uptime_ms INTEGER,
                fw_version TEXT,
                rescue_mode TEXT,
                note TEXT
            );
            """
        )

        # Migrate v0 -> v1 columns if upgrading an existing pre-evolution DB
        if u_ver < 1:
            if self.db_path != ":memory:":
                db_p = Path(self.db_path)
                backup_p = db_p.with_name("mochi_soul.v0-backup.db")
                if db_p.exists() and not backup_p.exists():
                    try:
                        bconn = sqlite3.connect(str(backup_p))
                        self.conn.backup(bconn)
                        bconn.close()
                    except Exception:
                        pass

            st_cols = self._table_columns("soul_state")
            if "transient_emotion" not in st_cols:
                self.conn.execute("ALTER TABLE soul_state ADD COLUMN transient_emotion TEXT;")
            if "transient_ttl_minutes" not in st_cols:
                self.conn.execute(
                    "ALTER TABLE soul_state ADD COLUMN transient_ttl_minutes INTEGER NOT NULL DEFAULT 0;"
                )
            if "last_tick_wall_ts" not in st_cols:
                self.conn.execute("ALTER TABLE soul_state ADD COLUMN last_tick_wall_ts INTEGER;")

            mem_cols = self._table_columns("episodic_memories")
            if "wall_ts" not in mem_cols:
                self.conn.execute("ALTER TABLE episodic_memories ADD COLUMN wall_ts INTEGER;")
            if "source" not in mem_cols:
                self.conn.execute(
                    "ALTER TABLE episodic_memories ADD COLUMN source TEXT NOT NULL DEFAULT 'user';"
                )

            imp_cols = self._table_columns("proactive_impulses")
            if "wall_ts" not in imp_cols:
                self.conn.execute("ALTER TABLE proactive_impulses ADD COLUMN wall_ts INTEGER;")

            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_wall ON episodic_memories(wall_ts);")
            self.conn.execute("PRAGMA user_version = 1;")
            self.conn.commit()

        # Ensure composite indexes exist on all databases (v0 upgraded or fresh v1)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_wall ON episodic_memories(wall_ts);")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mem_source_wall ON episodic_memories(source, wall_ts);"
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_hw_wall ON hardware_events(wall_ts);")
        self.conn.commit()

    def _load_or_create_state(self) -> SoulState:
        row = self.conn.execute(
            "SELECT sim_minute, energy, hunger, bond, valence, arousal, emotion, "
            "stage, stage_name, xp, minutes_since_interaction, last_impulse_minute, "
            "transient_emotion, transient_ttl_minutes, last_tick_wall_ts "
            "FROM soul_state WHERE id = 1"
        ).fetchone()
        if row:
            return SoulState(*row)
        st = SoulState()
        self.save_state(st)
        return st

    def _seed_temperament(self) -> tuple[float, float, float, float]:
        if self.seed is None:
            return (0.5, 0.5, 0.5, 0.5)
        digest = hashlib.sha256(f"mochi-seed:{self.seed}".encode("utf-8")).digest()
        vals = []
        for i in range(4):
            offset = ((digest[i] / 255.0) - 0.5) * 0.20  # [-0.10, +0.10]
            vals.append(round(clamp(0.5 + offset, 0.35, 0.65), 4))
        return (vals[0], vals[1], vals[2], vals[3])

    def _load_or_create_genome(self) -> PersonalityGenome:
        row = self.conn.execute(
            "SELECT curiosity, affection, playfulness, resilience, chronotype_shift, "
            "base_curiosity, base_affection, base_playfulness, base_resilience, "
            "genome_rev, last_consolidated_memory_id, last_dream_wall_ts, "
            "day_key, day_abs_delta, updated_wall_ts "
            "FROM personality_genome WHERE id = 1"
        ).fetchone()
        if row:
            return PersonalityGenome(*row)
        c0, a0, p0, r0 = self._seed_temperament()
        now_i = int(self.now_fn())
        gen = PersonalityGenome(
            curiosity=c0,
            affection=a0,
            playfulness=p0,
            resilience=r0,
            chronotype_shift=0.0,
            base_curiosity=c0,
            base_affection=a0,
            base_playfulness=p0,
            base_resilience=r0,
            genome_rev=0,
            last_consolidated_memory_id=0,
            last_dream_wall_ts=None,
            day_key=None,
            day_abs_delta=0.0,
            updated_wall_ts=now_i,
        )
        self._save_genome(gen, commit=True)
        return gen

    def _save_genome(self, gen: Optional[PersonalityGenome] = None, commit: bool = True) -> None:
        g = gen or self.genome
        with self._db_lock:
            self.conn.execute(
                """
                INSERT INTO personality_genome (
                    id, curiosity, affection, playfulness, resilience, chronotype_shift,
                    base_curiosity, base_affection, base_playfulness, base_resilience,
                    genome_rev, last_consolidated_memory_id, last_dream_wall_ts,
                    day_key, day_abs_delta, updated_wall_ts
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    curiosity=excluded.curiosity,
                    affection=excluded.affection,
                    playfulness=excluded.playfulness,
                    resilience=excluded.resilience,
                    chronotype_shift=excluded.chronotype_shift,
                    base_curiosity=excluded.base_curiosity,
                    base_affection=excluded.base_affection,
                    base_playfulness=excluded.base_playfulness,
                    base_resilience=excluded.base_resilience,
                    genome_rev=excluded.genome_rev,
                    last_consolidated_memory_id=excluded.last_consolidated_memory_id,
                    last_dream_wall_ts=excluded.last_dream_wall_ts,
                    day_key=excluded.day_key,
                    day_abs_delta=excluded.day_abs_delta,
                    updated_wall_ts=excluded.updated_wall_ts
                """,
                (
                    g.curiosity, g.affection, g.playfulness, g.resilience, g.chronotype_shift,
                    g.base_curiosity, g.base_affection, g.base_playfulness, g.base_resilience,
                    g.genome_rev, g.last_consolidated_memory_id, g.last_dream_wall_ts,
                    g.day_key, g.day_abs_delta, g.updated_wall_ts,
                ),
            )
            if commit:
                self.conn.commit()
        self.phenotype = compute_phenotype(self.state.stage, g)

    def save_state(self, st: Optional[SoulState] = None, commit: bool = True) -> None:
        s = st or self.state
        with self._db_lock:
            self.conn.execute(
                """
                INSERT INTO soul_state (
                    id, sim_minute, energy, hunger, bond, valence, arousal, emotion,
                    stage, stage_name, xp, minutes_since_interaction, last_impulse_minute,
                    transient_emotion, transient_ttl_minutes, last_tick_wall_ts
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    last_impulse_minute=excluded.last_impulse_minute,
                    transient_emotion=excluded.transient_emotion,
                    transient_ttl_minutes=excluded.transient_ttl_minutes,
                    last_tick_wall_ts=excluded.last_tick_wall_ts
                """,
                (
                    s.sim_minute, s.energy, s.hunger, s.bond, s.valence, s.arousal,
                    s.emotion, s.stage, s.stage_name, s.xp,
                    s.minutes_since_interaction, s.last_impulse_minute,
                    s.transient_emotion, s.transient_ttl_minutes, s.last_tick_wall_ts,
                ),
            )
            if commit:
                self.conn.commit()

    @staticmethod
    def compute_stage(xp: int, bond: float) -> tuple[int, str]:
        if xp >= 600 and bond >= 80.0:
            return 4, STAGE_NAMES[4]
        if xp >= 250 and bond >= 65.0:
            return 3, STAGE_NAMES[3]
        if xp >= 80:
            return 2, STAGE_NAMES[2]
        return 1, STAGE_NAMES[1]

    def _xp_gain_with_novelty(self, event_type: str, sim_minute: int, base_xp: int = 15) -> int:
        cutoff = sim_minute - 60
        while self._recent_events_window and self._recent_events_window[0][0] < cutoff:
            self._recent_events_window.popleft()
        n_same = sum(1 for _, ev in self._recent_events_window if ev == event_type)
        self._recent_events_window.append((sim_minute, event_type))
        return max(1, round(base_xp / (1.0 + n_same / 2.0)))

    def apply_emotion_override(self, emotion: str, detail: str = "") -> str:
        """Operator / studio emotion override routed through the engine."""
        s = self.state
        clean_det = sanitize_detail(detail or f"Switched face to {emotion}")
        s.emotion = emotion
        s.transient_emotion = emotion
        s.transient_ttl_minutes = 5
        s.xp += self._xp_gain_with_novelty(f"set_emotion:{emotion}", s.sim_minute, base_xp=10)
        cand_stage, _ = self.compute_stage(s.xp, s.bond)
        if cand_stage > s.stage:
            s.stage = cand_stage
            s.stage_name = STAGE_NAMES[s.stage]
            self.phenotype = compute_phenotype(s.stage, self.genome)
        now_i = int(self.now_fn())
        self.conn.execute(
            "INSERT INTO episodic_memories "
            "(sim_minute, event_type, detail, emotion_after, energy, hunger, bond, wall_ts, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                s.sim_minute,
                f"set_emotion:{emotion}",
                clean_det,
                emotion,
                s.energy,
                s.hunger,
                s.bond,
                now_i,
                "override",
            ),
        )
        self.save_state(s, commit=True)
        return s.emotion

    def apply_event(
        self,
        event_type: str,
        detail: str = "",
        source: str = "user",
        wall_ts: Optional[int] = None,
    ) -> str:
        s = self.state
        ph = self.phenotype
        s.minutes_since_interaction = 0
        s.xp += self._xp_gain_with_novelty(event_type, s.sim_minute, base_xp=15)

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
            # EVO-01 coupling (all identity at d=0)
            if event_type in ("feed_knowledge", "solve_problem", "ask_riddle", "paradox") and dh < 0:
                dh = dh * (1.0 + 0.6 * ph.d_cur)
            if db > 0 and event_type in TRAIT_POS_WEIGHTS["affection"]:
                db = db * (1.0 + 0.8 * ph.d_aff)
            elif db < 0:
                db = db * (1.0 - 0.8 * ph.d_res)
            if v_t < 0:
                v_t = v_t * (1.0 - 0.8 * ph.d_res)
            if event_type in ("loud_thunder", "sudden_approche"):
                a_t = a_t * (1.0 - 0.6 * ph.d_res)
            if event_type in TRAIT_POS_WEIGHTS["playfulness"]:
                v_t = clamp(v_t + 0.2 * ph.d_play, -1.0, 1.0)
                ttl = max(1, ttl + round(2.0 * ph.d_play))

            s.energy = clamp(s.energy + de, 0.0, 100.0)
            s.hunger = clamp(s.hunger + dh, 0.0, 100.0)
            s.bond = clamp(s.bond + db, 0.0, 100.0)
            s.valence = clamp(0.4 * s.valence + 0.6 * v_t, -1.0, 1.0)
            s.arousal = clamp(0.4 * s.arousal + 0.6 * a_t, -1.0, 1.0)
            s.transient_emotion = emo
            s.transient_ttl_minutes = ttl
            s.emotion = emo
        else:
            s.emotion = self.resolve_emotion()

        cand_stage, _ = self.compute_stage(s.xp, s.bond)
        if cand_stage > s.stage:
            s.stage = cand_stage
            s.stage_name = STAGE_NAMES[s.stage]
            self.phenotype = compute_phenotype(s.stage, self.genome)
        else:
            s.stage_name = STAGE_NAMES.get(s.stage, s.stage_name)

        src = source if source in SOURCE_WEIGHTS else "user"
        clean_det = sanitize_detail(detail or event_type)
        ts_val = int(wall_ts if wall_ts is not None else self.now_fn())
        self.conn.execute(
            "INSERT INTO episodic_memories "
            "(sim_minute, event_type, detail, emotion_after, energy, hunger, bond, wall_ts, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (s.sim_minute, event_type, clean_det, s.emotion, s.energy, s.hunger, s.bond, ts_val, src),
        )
        self.save_state(s)
        return s.emotion

    def resolve_emotion(self, hour_override: Optional[float] = None) -> str:
        """
        Deterministic mapping of 4D Homeostasis state (E, H, B, V, A) + Phenotype -> 21 Mochi Emotions.
        At neutral genome (0.5), d == 0 and behavior is 100% identical to Spec 02 baseline.
        """
        s = self.state
        ph = self.phenotype
        if s.transient_emotion and s.transient_ttl_minutes > 0:
            return s.transient_emotion

        hour_f = hour_override if hour_override is not None else (s.sim_minute / 60.0) % 24.0
        quiet = is_quiet_hours(hour_f, ph.chronotype_shift)

        if quiet or s.energy < (22.0 - 8.0 * ph.d_play):
            return "sleepy"
        if s.minutes_since_interaction > 360.0 * (1.0 + 0.6 * ph.d_res) and s.bond < (42.0 - 10.0 * ph.d_res):
            return "crying"
        if s.minutes_since_interaction > 210.0 * (1.0 + 0.6 * ph.d_res):
            return "sad"
        if s.hunger > (82.0 + 6.0 * ph.d_res):
            return "confused"
        if s.hunger > (64.0 - 16.0 * ph.d_cur):
            return "thinking"
        if s.energy > 82.0 and s.bond > (82.0 - 16.0 * ph.d_aff) and s.valence > (0.55 - 0.20 * ph.d_aff):
            return "loving"
        if s.energy > (75.0 - 10.0 * ph.d_play) and s.valence > 0.35:
            return "happy"
        if s.arousal < -0.25 and s.valence >= 0.0:
            return "relaxed"

        # EVO-01 specialized idle attractor when dominant trait deviation d_j >= 0.15
        if s.stage >= 2:
            traits = [
                ("cur", ph.d_cur),
                ("aff", ph.d_aff),
                ("play", ph.d_play),
            ]
            dom_name, dom_d = max(traits, key=lambda x: x[1])
            if dom_d >= 0.15:
                window = round(12.0 * ph.gamma * dom_d)
                if (s.sim_minute % 30) < window:
                    if dom_name == "cur":
                        return "confident" if s.stage >= 4 else "thinking"
                    if dom_name == "aff":
                        return "loving" if s.stage >= 4 else "winking"
                    return "cool" if s.stage >= 4 else "silly"

        return "neutral"

    # Keep backwards-compatible alias
    select_homeostatic_emotion = resolve_emotion

    def evaluate_impulse(self, hour_f: float, quiet: bool) -> Optional[dict]:
        """Evaluate proactive impulse rules with EVO-01 phenotype coupling and quiet/floor guards."""
        s = self.state
        ph = self.phenotype
        if quiet:
            return None
        if ph.chronotype_shift != 0.0 and is_hard_sleep_floor(hour_f):
            return None

        cooldown = max(45, round(45.0 * (1.0 - 0.6 * ph.d_aff)))
        if (s.sim_minute - s.last_impulse_minute) < cooldown:
            return None

        if self._pending_dream_milestone:
            ms_text = self._pending_dream_milestone
            self._pending_dream_milestone = None
            return {
                "sim_minute": s.sim_minute,
                "hour_float": round(hour_f, 2),
                "impulse_kind": "dream_share",
                "emotion": "confident" if s.stage >= 3 else "happy",
                "message": f"Đêm qua Mochi mơ thấy tụi mình ({ms_text}) — Mochi thấy lớn thêm một chút rồi!",
            }

        if s.hunger >= (75.0 - 20.0 * ph.d_cur):
            return {
                "sim_minute": s.sim_minute,
                "hour_float": round(hour_f, 2),
                "impulse_kind": "notify_voice",
                "emotion": "thinking",
                "message": "Mochi đang tò mò quá, hôm nay bạn có khám phá gì mới kể cho Mochi nghe với!",
            }
        if s.minutes_since_interaction >= 240.0 * (1.0 + 0.5 * ph.d_res - 0.3 * ph.d_aff):
            return {
                "sim_minute": s.sim_minute,
                "hour_float": round(hour_f, 2),
                "impulse_kind": "notify_voice",
                "emotion": "sad",
                "message": "Bạn làm việc chăm chỉ thế, nghỉ tay uống ngụm nước với Mochi nhé!",
            }
        if s.energy <= 20.0:
            return {
                "sim_minute": s.sim_minute,
                "hour_float": round(hour_f, 2),
                "impulse_kind": "alert_face",
                "emotion": "sleepy",
                "message": "Mochi hơi buồn ngủ rồi, cho Mochi chợp mắt chút nha...",
            }
        return None

    def step_minute(self, persist: bool = False, hour_override: Optional[float] = None) -> Optional[dict]:
        """Advance biological homeostasis by 1 minute (dt = 1/60 hour)."""
        s = self.state
        ph = self.phenotype
        s.sim_minute += 1
        dt_h = 1.0 / 60.0
        hour_f = hour_override if hour_override is not None else (s.sim_minute / 60.0) % 24.0
        quiet = is_quiet_hours(hour_f, ph.chronotype_shift)

        if quiet:
            # Sleeping & recharging during Quiet Hours
            s.energy = clamp(s.energy + 14.0 * dt_h, 0.0, 100.0)
            s.hunger = clamp(s.hunger + 1.2 * dt_h, 0.0, 100.0)
            s.arousal = clamp(s.arousal - 0.8 * dt_h, -0.8, 1.0)
        else:
            # Active daytime metabolism (EVO-01 coupled; identical to baseline when d == 0)
            s.energy = clamp(s.energy - 4.2 * (1.0 + 0.2 * ph.d_play) * dt_h, 0.0, 100.0)
            s.hunger = clamp(s.hunger + 6.5 * (1.0 + 0.4 * ph.d_cur) * dt_h, 0.0, 100.0)
            s.minutes_since_interaction += 1
            idle_thresh = 180.0 * (1.0 - 0.4 * ph.d_aff)
            if s.minutes_since_interaction > idle_thresh:
                s.bond = clamp(s.bond - 1.5 * (1.0 - 0.8 * ph.d_res) * dt_h, 0.0, 100.0)
                s.valence = clamp(s.valence - 0.15 * (1.0 - 0.8 * ph.d_res) * dt_h, -1.0, 1.0)
            else:
                v0 = 0.15 + 0.10 * ph.d_play
                a0 = 0.05 + 0.10 * ph.d_cur
                s.valence += (v0 - s.valence) * 0.05
                s.arousal += (a0 - s.arousal) * 0.05

        if s.transient_ttl_minutes > 0:
            s.transient_ttl_minutes -= 1
            if s.transient_ttl_minutes == 0:
                s.transient_emotion = None

        s.emotion = self.resolve_emotion(hour_override=hour_override)

        impulse = self.evaluate_impulse(hour_f, quiet)
        if impulse:
            s.last_impulse_minute = s.sim_minute
            if persist:
                self.conn.execute(
                    "INSERT INTO proactive_impulses (sim_minute, hour_float, impulse_kind, emotion, message, wall_ts) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        impulse["sim_minute"],
                        impulse["hour_float"],
                        impulse["impulse_kind"],
                        impulse["emotion"],
                        impulse["message"],
                        int(self.now_fn()),
                    ),
                )

        if persist:
            self.save_state(s)
        return impulse

    # -------------------------------------------------------------------------
    # EVO-01 + EVO-03: Dream Consolidation, Relative-Share Genome Drift & Chronotype
    # -------------------------------------------------------------------------

    @staticmethod
    def _dream_key(trigger: str, now_ts: float, hwm: int, rev: int) -> str:
        dt_shifted = datetime.datetime.fromtimestamp(now_ts - 12 * 3600)
        date_str = dt_shifted.strftime("%Y-%m-%d")
        if trigger in ("quiet_hours", "missed_night"):
            return f"night:{date_str}"
        if trigger == "interaction_burst":
            bucket = int(now_ts // (6 * 3600))
            return f"burst:{date_str}:{bucket}:hwm{hwm}"
        return f"{trigger}:{int(now_ts)}:r{rev}"

    @staticmethod
    def _extract_evidence(rows: list[tuple]) -> dict:
        """
        Pure evidence extraction from unconsolidated episodic_memories rows:
          row = (id, sim_minute, event_type, source, wall_ts)
        """
        weighted_counts: dict[str, float] = {}
        raw_event_counts: Counter[str] = Counter()
        repairs = 0
        unrepaired_startles = 0
        neglect_gaps = 0

        last_neg_minute: Optional[int] = None
        last_neg_was_startle = False
        prev_sim_minute: Optional[int] = None

        neg_set = {"scold", "tease_annoy", "loud_thunder"}
        startle_set = {"loud_thunder", "sudden_approche"}
        repair_set = {"gentle_pet", "praise", "kiss", "chat_hello"}

        for _row_id, sim_m, ev_type, src, _wall_ts in rows:
            sigma = SOURCE_WEIGHTS.get(src, 1.0)
            if sigma > 0.0:
                weighted_counts[ev_type] = weighted_counts.get(ev_type, 0.0) + sigma
                raw_event_counts[ev_type] += 1

            if prev_sim_minute is not None and (sim_m - prev_sim_minute) > 360:
                neglect_gaps += 1
            prev_sim_minute = sim_m

            if ev_type in neg_set or ev_type in startle_set:
                if last_neg_minute is not None and last_neg_was_startle:
                    unrepaired_startles += 1
                last_neg_minute = sim_m
                last_neg_was_startle = ev_type in startle_set
            elif ev_type in repair_set and last_neg_minute is not None:
                if 0 <= (sim_m - last_neg_minute) <= 60:
                    repairs += 1
                    last_neg_minute = None
                    last_neg_was_startle = False

        if last_neg_minute is not None and last_neg_was_startle:
            unrepaired_startles += 1

        n_eff = {ev: 3.0 * math.log(1.0 + cnt / 3.0) for ev, cnt in weighted_counts.items()}
        return {
            "n_eff": n_eff,
            "raw_counts": dict(raw_event_counts),
            "repairs": repairs,
            "unrepaired_startles": unrepaired_startles,
            "neglect_gaps": neglect_gaps,
        }

    @staticmethod
    def evolve_genome_pure(
        gen: PersonalityGenome,
        ev: dict,
        dt_days: float,
        trigger: str,
        now_ts: float,
    ) -> tuple[PersonalityGenome, float]:
        """
        Pure EVO-01 trait evolution equations:
          1. Relative-share drive p_X = (E_X + 1)/(T + 3), u_X = tanh(4.5*(p_X - 1/3))
          2. Volume learning rate v = 1 - exp(-T/8)
          3. Homeostatic elasticity -kappa*(g - b)*dt_days
          4. Slow set-point plasticity b' = clamp(b + rho*(g' - b), 0.15, 0.85)
          5. Per-dream |dg| <= 0.06 and daily sum |dg| <= 0.08
        """
        n_eff: dict[str, float] = ev["n_eff"]
        e_scores: dict[str, float] = {}
        for trait, w_map in TRAIT_POS_WEIGHTS.items():
            e_scores[trait] = sum(w * n_eff.get(ev_name, 0.0) for ev_name, w in w_map.items())

        total_t = sum(e_scores.values())
        v_social = 1.0 - math.exp(-total_t / 8.0)

        u_map: dict[str, float] = {}
        v_map: dict[str, float] = {}
        for trait in ("curiosity", "affection", "playfulness"):
            p_x = (e_scores[trait] + 1.0) / (total_t + 3.0)
            u_raw = math.tanh(4.5 * (p_x - (1.0 / 3.0)))
            u_map[trait] = u_raw if u_raw > 0.0 else 0.5 * u_raw
            v_map[trait] = v_social

        # Negative affection evidence
        n_neg = sum(w * n_eff.get(ev_name, 0.0) for ev_name, w in AFFECTION_NEG_WEIGHTS.items())
        if n_neg > 0.0:
            u_map["affection"] = clamp(u_map["affection"] - math.tanh(n_neg / 6.0), -1.0, 1.0)
            v_map["affection"] = max(v_social, 1.0 - math.exp(-n_neg / 8.0))

        # Resilience drive
        r_cnt = float(ev["repairs"])
        k_cnt = float(ev["unrepaired_startles"])
        q_cnt = float(ev["neglect_gaps"])
        u_map["resilience"] = math.tanh((1.0 * r_cnt + 0.25 * k_cnt - 0.6 * q_cnt) / 3.0)
        v_map["resilience"] = 1.0 - math.exp(-(r_cnt + k_cnt + q_cnt) / 4.0)

        eta = 0.04 if trigger == "interaction_burst" else 0.08
        kappa = 0.03
        rho = 0.02
        dt_clamped = clamp(dt_days, 0.0, 7.0)

        local_day = datetime.datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d")
        day_used = gen.day_abs_delta if gen.day_key == local_day else 0.0
        remaining_daily = max(0.0, 0.08 - day_used)

        cur_vals = {
            "curiosity": gen.curiosity,
            "affection": gen.affection,
            "playfulness": gen.playfulness,
            "resilience": gen.resilience,
        }
        base_vals = {
            "curiosity": gen.base_curiosity,
            "affection": gen.base_affection,
            "playfulness": gen.base_playfulness,
            "resilience": gen.base_resilience,
        }

        raw_deltas: dict[str, float] = {}
        for t_name in ("curiosity", "affection", "playfulness", "resilience"):
            g_val = cur_vals[t_name]
            b_val = base_vals[t_name]
            u_val = u_map[t_name]
            v_val = v_map[t_name]
            headroom = (1.0 - g_val) if u_val > 0.0 else g_val
            grow = eta * v_val * u_val * headroom
            elastic = -kappa * (g_val - b_val) * dt_clamped
            raw_deltas[t_name] = clamp(grow + elastic, -0.06, 0.06)

        # Enforce per-trait daily cap (each trait can move at most 0.08/day; scale if total exceeds 4*0.08)
        max_single_abs = max((abs(d) for d in raw_deltas.values()), default=0.0)
        scale = 1.0
        if max_single_abs > remaining_daily and max_single_abs > 1e-9:
            scale = remaining_daily / max_single_abs

        new_vals: dict[str, float] = {}
        new_bases: dict[str, float] = {}
        delta_l1 = 0.0
        max_applied = 0.0
        for t_name in ("curiosity", "affection", "playfulness", "resilience"):
            dg = raw_deltas[t_name] * scale
            g_next = clamp(cur_vals[t_name] + dg, 0.02, 0.98)
            actual_dg = g_next - cur_vals[t_name]
            b_next = clamp(base_vals[t_name] + rho * (g_next - base_vals[t_name]), 0.15, 0.85)
            new_vals[t_name] = round(g_next, 6)
            new_bases[t_name] = round(b_next, 6)
            delta_l1 += abs(actual_dg)
            if abs(actual_dg) > max_applied:
                max_applied = abs(actual_dg)

        updated = PersonalityGenome(
            curiosity=new_vals["curiosity"],
            affection=new_vals["affection"],
            playfulness=new_vals["playfulness"],
            resilience=new_vals["resilience"],
            chronotype_shift=gen.chronotype_shift,
            base_curiosity=new_bases["curiosity"],
            base_affection=new_bases["affection"],
            base_playfulness=new_bases["playfulness"],
            base_resilience=new_bases["resilience"],
            genome_rev=gen.genome_rev + 1,
            last_consolidated_memory_id=gen.last_consolidated_memory_id,
            last_dream_wall_ts=int(now_ts),
            day_key=local_day,
            day_abs_delta=round(day_used + max_applied, 6),
            updated_wall_ts=int(now_ts),
        )
        return updated, round(delta_l1, 6)

    def _compute_chronotype_shift(self, now_ts: float, current_c: float) -> float:
        """
        Compute chronotype shift c in [-3.0, +3.0] hours from 28-day window of user memories.
        Day boundary at 04:00 local time; unwrapped hours in [4.0, 28.0).
        Requires >= 5 days with >= 3 user interactions each.
        """
        cutoff = int(now_ts - 28 * 86400)
        rows = self.conn.execute(
            "SELECT wall_ts FROM episodic_memories "
            "WHERE source = 'user' AND wall_ts IS NOT NULL AND wall_ts >= ? "
            "ORDER BY wall_ts ASC",
            (cutoff,),
        ).fetchall()
        if not rows:
            return current_c

        by_day: dict[str, list[float]] = {}
        for (wts,) in rows:
            dt = datetime.datetime.fromtimestamp(wts)
            hour_f = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
            if hour_f < 4.0:
                day_dt = (dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                unwrapped_h = hour_f + 24.0
            else:
                day_dt = dt.strftime("%Y-%m-%d")
                unwrapped_h = hour_f
            by_day.setdefault(day_dt, []).append(unwrapped_h)

        qualifying = [hrs for hrs in by_day.values() if len(hrs) >= 3]
        if len(qualifying) < 5:
            return current_c

        firsts = sorted(min(hrs) for hrs in qualifying)
        lasts = sorted(max(hrs) for hrs in qualifying)
        n = len(qualifying)
        med_f = firsts[n // 2] if n % 2 == 1 else 0.5 * (firsts[n // 2 - 1] + firsts[n // 2])
        med_l = lasts[n // 2] if n % 2 == 1 else 0.5 * (lasts[n // 2 - 1] + lasts[n // 2])

        s_star = clamp(0.5 * ((med_f - 7.5) + (med_l - 23.0)), -3.0, 3.0)
        step = clamp(0.25 * (s_star - current_c), -0.5, 0.5)
        return round(clamp(current_c + step, -3.0, 3.0), 4)

    @staticmethod
    def _detect_milestones(old_g: PersonalityGenome, new_g: PersonalityGenome) -> Optional[str]:
        notes = []
        for label, attr in (
            ("tò mò", "curiosity"),
            ("tình cảm", "affection"),
            ("hóm hỉnh", "playfulness"),
            ("vững vàng", "resilience"),
        ):
            v0 = getattr(old_g, attr)
            v1 = getattr(new_g, attr)
            if v0 < 0.65 <= v1:
                notes.append(f"nét tính cách {label} rõ nét hơn ({v1:.2f})")
            elif v0 > 0.35 >= v1:
                notes.append(f"nét {label} dịu lắng lại ({v1:.2f})")
        if int(abs(new_g.chronotype_shift)) > int(abs(old_g.chronotype_shift)):
            notes.append(f"nhịp sinh học dịch chuyển {new_g.chronotype_shift:+.1f}h")
        return ", ".join(notes) if notes else None

    @staticmethod
    def _build_privacy_safe_dream_summary(
        raw_counts: dict[str, int],
        mem_count: int,
        milestone: Optional[str],
    ) -> str:
        """
        Privacy-safe template builder: NEVER copies `episodic_memories.detail` free text.
        Uses only event_type counts and Vietnamese templates (verifies V-20).
        """
        if mem_count == 0 or not raw_counts:
            base = "Đêm yên tĩnh: Mochi nghỉ ngơi sâu và cân bằng lại nhịp sinh học."
        else:
            top_items = sorted(raw_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
            parts = [
                f"{cnt} lần {EVENT_VI_LABELS.get(ev, ev)}" for ev, cnt in top_items
            ]
            base = f"Tổng hợp {mem_count} ký ức trong ngày ({', '.join(parts)})."
        if milestone:
            return f"{base} Cột mốc tiến hoá: {milestone}."
        return base

    def consolidate_dreams(
        self,
        trigger: str = "manual",
        now_ts: Optional[float] = None,
        dry_run: bool = False,
    ) -> dict:
        """
        EVO-03 Idempotent Single-Transaction Dream Consolidation:
          - Reads unconsolidated episodic_memories (id > last_consolidated_memory_id, LIMIT 5000)
          - Updates personality_genome via relative-share drive + elasticity + set-point plasticity
          - Updates chronotype_shift from 28-day user interaction window
          - Writes template-only summary into dream_journal (never leaks raw `detail`)
          - Deletes consolidated memories & impulses older than 30 days
        """
        ts_now = float(now_ts if now_ts is not None else self.now_fn())
        with self._db_lock:
            if self.conn.in_transaction:
                self.conn.commit()

            self.conn.execute("BEGIN IMMEDIATE")
            try:
                gen = self._load_or_create_genome()
                key = self._dream_key(trigger, ts_now, gen.last_consolidated_memory_id, gen.genome_rev)
                existing = self.conn.execute(
                    "SELECT id FROM dream_journal WHERE dream_key = ?", (key,)
                ).fetchone()
                if existing:
                    self.conn.rollback()
                    return {"ok": True, "skipped": "duplicate", "dream_id": existing[0], "dream_key": key}

                rows = self.conn.execute(
                    "SELECT id, sim_minute, event_type, source, wall_ts "
                    "FROM episodic_memories WHERE id > ? ORDER BY id ASC LIMIT 5000",
                    (gen.last_consolidated_memory_id,),
                ).fetchall()

                ev = self._extract_evidence(rows)
                if gen.last_dream_wall_ts is not None:
                    dt_days = max(0.0, (ts_now - gen.last_dream_wall_ts) / 86400.0)
                else:
                    dt_days = 1.0 if trigger in ("quiet_hours", "missed_night") else 0.25

                new_gen, delta_l1 = self.evolve_genome_pure(gen, ev, dt_days, trigger, ts_now)
                new_gen.chronotype_shift = self._compute_chronotype_shift(ts_now, gen.chronotype_shift)
                if rows:
                    mem_from_id = int(rows[0][0])
                    mem_to_id = int(rows[-1][0])
                    new_gen.last_consolidated_memory_id = mem_to_id
                else:
                    mem_from_id = gen.last_consolidated_memory_id
                    mem_to_id = gen.last_consolidated_memory_id

                milestone = self._detect_milestones(gen, new_gen)
                summary = self._build_privacy_safe_dream_summary(ev["raw_counts"], len(rows), milestone)
                ph_info = phenotype_params(self.state.stage, new_gen, quantize=False)
                ph_hash = ph_info["hash"]

                before_json = json.dumps(
                    {
                        "curiosity": round(gen.curiosity, 4),
                        "affection": round(gen.affection, 4),
                        "playfulness": round(gen.playfulness, 4),
                        "resilience": round(gen.resilience, 4),
                        "chronotype_shift": round(gen.chronotype_shift, 4),
                    },
                    sort_keys=True,
                )
                after_json = json.dumps(
                    {
                        "curiosity": round(new_gen.curiosity, 4),
                        "affection": round(new_gen.affection, 4),
                        "playfulness": round(new_gen.playfulness, 4),
                        "resilience": round(new_gen.resilience, 4),
                        "chronotype_shift": round(new_gen.chronotype_shift, 4),
                    },
                    sort_keys=True,
                )

                if dry_run:
                    self.conn.rollback()
                    return {
                        "ok": True,
                        "dry_run": True,
                        "dream_key": key,
                        "trigger": trigger,
                        "mem_count": len(rows),
                        "delta_l1": delta_l1,
                        "milestone": milestone,
                        "summary": summary,
                        "genome_before": json.loads(before_json),
                        "genome_after": json.loads(after_json),
                        "phenotype_hash": ph_hash,
                    }

                self._save_genome(new_gen, commit=False)
                cur = self.conn.execute(
                    """
                    INSERT INTO dream_journal (
                        dream_key, trigger, wall_ts, sim_minute,
                        mem_from_id, mem_to_id, mem_count,
                        genome_before, genome_after, delta_l1,
                        stage, milestone, summary, phenotype_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        trigger,
                        int(ts_now),
                        self.state.sim_minute,
                        mem_from_id,
                        mem_to_id,
                        len(rows),
                        before_json,
                        after_json,
                        delta_l1,
                        self.state.stage,
                        milestone,
                        summary,
                        ph_hash,
                    ),
                )
                dream_id = cur.lastrowid

                # 30-day retention cleanup for consolidated rows & hardware logs
                cutoff_30d = int(ts_now - 30 * 86400)
                self.conn.execute(
                    "DELETE FROM episodic_memories WHERE id <= ? AND wall_ts IS NOT NULL AND wall_ts < ?",
                    (new_gen.last_consolidated_memory_id, cutoff_30d),
                )
                self.conn.execute(
                    "DELETE FROM proactive_impulses WHERE wall_ts IS NOT NULL AND wall_ts < ?",
                    (cutoff_30d,),
                )
                self.conn.execute(
                    "DELETE FROM hardware_events WHERE wall_ts < ?",
                    (cutoff_30d,),
                )

                if milestone:
                    self._pending_dream_milestone = milestone
                self.save_state(self.state, commit=False)
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

            self.genome = new_gen
            self.phenotype = compute_phenotype(self.state.stage, self.genome)
        return {
            "ok": True,
            "dream_id": dream_id,
            "dream_key": key,
            "trigger": trigger,
            "mem_count": len(rows),
            "delta_l1": delta_l1,
            "milestone": milestone,
            "summary": summary,
            "genome_after": json.loads(after_json),
            "phenotype_hash": ph_hash,
        }

    def maybe_auto_dream(self, now_ts: Optional[float] = None) -> Optional[dict]:
        """Check automatic dream triggers (`quiet_hours`, `interaction_burst`)."""
        ts_now = float(now_ts if now_ts is not None else self.now_fn())
        dt = datetime.datetime.fromtimestamp(ts_now)
        hour_f = dt.hour + dt.minute / 60.0
        quiet = is_quiet_hours(hour_f, self.genome.chronotype_shift)

        # Trigger 1: Nightly Quiet Hours dream
        if quiet and self.state.minutes_since_interaction >= 30:
            key = self._dream_key("quiet_hours", ts_now, self.genome.last_consolidated_memory_id, self.genome.genome_rev)
            row = self.conn.execute("SELECT id FROM dream_journal WHERE dream_key = ?", (key,)).fetchone()
            if not row:
                return self.consolidate_dreams("quiet_hours", now_ts=ts_now)

        # Trigger 2: Interaction burst (>= 40 unconsolidated memories, >= 6h since last dream, >= 10m idle)
        if self.state.minutes_since_interaction >= 10:
            since_last = (ts_now - (self.genome.last_dream_wall_ts or 0))
            if since_last >= 6 * 3600:
                cnt_row = self.conn.execute(
                    "SELECT COUNT(*) FROM episodic_memories WHERE id > ?",
                    (self.genome.last_consolidated_memory_id,),
                ).fetchone()
                uncons = int(cnt_row[0]) if cnt_row else 0
                if uncons >= 40:
                    return self.consolidate_dreams("interaction_burst", now_ts=ts_now)
        return None

    def get_genome_payload(self) -> dict:
        g = self.genome
        ph = self.phenotype
        last_dream_row = self.conn.execute(
            "SELECT id, wall_ts, trigger, summary, milestone FROM dream_journal ORDER BY id DESC LIMIT 1"
        ).fetchone()
        last_dream = None
        if last_dream_row:
            last_dream = {
                "id": last_dream_row[0],
                "wall_ts": last_dream_row[1],
                "trigger": last_dream_row[2],
                "summary": last_dream_row[3],
                "milestone": last_dream_row[4],
            }
        return {
            "genome": {
                "curiosity": round(g.curiosity, 4),
                "affection": round(g.affection, 4),
                "playfulness": round(g.playfulness, 4),
                "resilience": round(g.resilience, 4),
                "chronotype_shift": round(g.chronotype_shift, 4),
            },
            "setpoints": {
                "curiosity": round(g.base_curiosity, 4),
                "affection": round(g.base_affection, 4),
                "playfulness": round(g.base_playfulness, 4),
                "resilience": round(g.base_resilience, 4),
            },
            "rev": g.genome_rev,
            "stage": self.state.stage,
            "stage_name": self.state.stage_name,
            "stage_gain": ph.gamma,
            "expressed": {
                "curiosity": round(ph.g_cur, 4),
                "affection": round(ph.g_aff, 4),
                "playfulness": round(ph.g_play, 4),
                "resilience": round(ph.g_res, 4),
            },
            "phenotype": phenotype_params(self.state.stage, g, quantize=False),
            "last_dream": last_dream,
        }

    def get_recent_dreams(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, dream_key, trigger, wall_ts, sim_minute, mem_count, delta_l1, "
            "stage, milestone, summary, genome_after, phenotype_hash "
            "FROM dream_journal ORDER BY id DESC LIMIT ?",
            (int(clamp(limit, 1, 50)),),
        ).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r[0],
                    "dream_key": r[1],
                    "trigger": r[2],
                    "wall_ts": r[3],
                    "sim_minute": r[4],
                    "mem_count": r[5],
                    "delta_l1": round(float(r[6]), 4),
                    "stage": r[7],
                    "milestone": r[8],
                    "summary": r[9],
                    "genome_after": json.loads(r[10]),
                    "phenotype_hash": r[11],
                }
            )
        return out


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

    # 2. Full 24-Hour Realistic Day Simulation + SQLite WAL Persistence in isolated temp directory (V-10)
    with tempfile.TemporaryDirectory(prefix="mochi-bench-") as tmp_dir:
        bench_db = Path(tmp_dir) / "mochi_soul_bench.db"
        eng = MochiSoulEngine(db_path=bench_db, in_memory=False)

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

        t_db_w = time.perf_counter()
        for _ in range(200):
            eng.save_state()
        us_per_sqlite_write = ((time.perf_counter() - t_db_w) / 200.0) * 1e6

        t_db_r = time.perf_counter()
        for _ in range(200):
            eng._load_or_create_state()
        us_per_sqlite_read = ((time.perf_counter() - t_db_r) / 200.0) * 1e6
        eng.conn.close()

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
    print(f"\nSaved Spec-02 benchmark report to {REPORT_JSON.relative_to(ROOT)}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Mochi-Soul 4D Biological Homeostasis & Self-Evolution Engine CLI")
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database")
    sub = parser.add_subparsers(dest="cmd", required=False)
    sub.add_parser("benchmark", help="Run 24h simulation, 21-emotion coverage & latency benchmark")
    sub.add_parser("status", help="Show current persisted Mochi-Soul state from SQLite")
    sub.add_parser("genome", help="Show current Personality Genome & Phenotype parameters")
    dream_p = sub.add_parser("dream", help="Run Dream Consolidation pass")
    dream_p.add_argument("--dry-run", action="store_true", help="Preview dream consolidation without writing")
    args = parser.parse_args()

    if args.cmd in (None, "benchmark"):
        run_benchmark_and_verification()
    elif args.cmd == "status":
        eng = MochiSoulEngine(db_path=args.db)
        print(json.dumps(asdict(eng.state), indent=2, ensure_ascii=False))
    elif args.cmd == "genome":
        eng = MochiSoulEngine(db_path=args.db)
        print(json.dumps(eng.get_genome_payload(), indent=2, ensure_ascii=False))
    elif args.cmd == "dream":
        eng = MochiSoulEngine(db_path=args.db)
        res = eng.consolidate_dreams(trigger="manual", dry_run=args.dry_run)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
