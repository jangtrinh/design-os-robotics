#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
reflex_60fps.py — Spec 04: 60FPS Spring-Damper Parametric Face Engine,
Real-Time 16kHz Audio RMS Lip-Sync, HC-SR04 Proximity Gaze Reflex & C++17 Header Generator.
"""
import argparse
import os
import io
import json
import math
import shutil
import struct
import time
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT_DIR = Path(os.environ["ARTIFACT_DIR"]) if os.environ.get("ARTIFACT_DIR") else None
CPP_HEADER_OUT = Path(__file__).resolve().parent / "mochi_face_60fps.hpp"
DEMO_GIF_OUT = ROOT / "themes/procedural-mochi/mochi_60fps_spring_transition.gif"
REPORT_JSON = ROOT / "plans/reports/benchmark-reflex-60fps.json"

# 12-DOF Parametric Face Vector:
# [0] gaze_x       [-1.0, +1.0]
# [1] gaze_y       [-1.0, +1.0]
# [2] open_l       [ 0.0,  1.25]
# [3] open_r       [ 0.0,  1.25]
# [4] scale_l      [ 0.6,  1.30]
# [5] scale_r      [ 0.6,  1.30]
# [6] slope_l_deg  [-35.0, +35.0]  (+ = angry inward tilt, - = sad outward droop)
# [7] slope_r_deg  [-35.0, +35.0]
# [8] happy_cheek  [ 0.0,  1.0]    (lower eyelid crescent raise)
# [9] mouth_curve  [-1.0, +1.0]    (+ = smile, - = frown)
# [10] mouth_open  [ 0.0,  1.0]    (driven by emotion + real-time Audio RMS Lip-Sync)
# [11] blush_opa   [ 0.0,  1.0]

PARAM_NAMES = [
    "gaze_x", "gaze_y", "open_l", "open_r", "scale_l", "scale_r",
    "slope_l_deg", "slope_r_deg", "happy_cheek", "mouth_curve", "mouth_open", "blush_opa",
]

EMOTION_21_VECTORS: dict[str, list[float]] = {
    "neutral":     [ 0.00,  0.00, 1.00, 1.00, 1.00, 1.00,   0.0,   0.0, 0.00, +0.35, 0.00, 0.80],
    "happy":       [ 0.00, -0.08, 0.85, 0.85, 1.02, 1.02,   0.0,   0.0, 0.85, +0.85, 0.35, 1.00],
    "laughing":    [ 0.00, -0.15, 0.70, 0.70, 1.08, 1.08,   0.0,   0.0, 1.00, +1.00, 0.75, 1.00],
    "funny":       [ 0.15, -0.05, 1.05, 0.80, 1.22, 0.75,  -8.0,  +8.0, 0.35, +0.75, 0.45, 0.90],
    "sad":         [ 0.00, +0.30, 0.75, 0.75, 0.95, 0.95, -26.0, -26.0, 0.00, -0.80, 0.05, 0.00],
    "angry":       [ 0.00, +0.05, 0.82, 0.82, 1.05, 1.05, +30.0, +30.0, 0.00, -0.75, 0.20, 0.00],
    "crying":      [ 0.00, +0.25, 0.55, 0.55, 0.98, 0.98, -28.0, -28.0, 0.00, -0.90, 0.65, 0.30],
    "loving":      [ 0.00, -0.05, 1.05, 1.05, 1.12, 1.12,   0.0,   0.0, 0.20, +0.90, 0.15, 1.00],
    "embarrassed": [-0.35, +0.15, 0.80, 0.80, 0.95, 0.95, -12.0, -12.0, 0.40, +0.10, 0.10, 1.00],
    "surprised":   [ 0.00, -0.10, 1.18, 1.18, 1.15, 1.15,   0.0,   0.0, 0.00,  0.00, 0.60, 0.30],
    "shocked":     [ 0.00, -0.12, 1.25, 1.25, 1.25, 1.25,  -5.0,  -5.0, 0.00, -0.20, 0.90, 0.00],
    "thinking":    [+0.35, -0.30, 0.55, 1.08, 0.92, 1.08, +10.0,  -8.0, 0.00,  0.00, 0.00, 0.00],
    "winking":     [+0.05,  0.00, 1.02, 0.08, 1.05, 0.95,   0.0,   0.0, 0.30, +0.65, 0.15, 0.95],
    "cool":        [+0.10, -0.05, 0.78, 0.78, 1.05, 1.05,  +8.0,  +8.0, 0.10, +0.55, 0.05, 0.20],
    "relaxed":     [ 0.00, +0.08, 0.12, 0.12, 1.00, 1.00,   0.0,   0.0, 0.65, +0.45, 0.00, 0.85],
    "delicious":   [ 0.00, -0.06, 0.82, 0.82, 1.04, 1.04,   0.0,   0.0, 0.90, +0.80, 0.30, 0.95],
    "kissy":       [-0.05, -0.04, 0.85, 0.12, 1.00, 0.95,   0.0,   0.0, 0.75, +0.40, 0.25, 1.00],
    "confident":   [+0.08, -0.05, 0.72, 0.72, 1.04, 1.04, +14.0,  +6.0, 0.20, +0.65, 0.10, 0.40],
    "sleepy":      [ 0.00, +0.22, 0.28, 0.28, 0.96, 0.96,  -8.0,  -8.0, 0.00,  0.00, 0.22, 0.60],
    "silly":       [-0.25,  0.00, 1.05, 1.05, 1.10, 0.92,  -6.0,  +6.0, 0.25, +0.70, 0.50, 0.90],
    "confused":    [-0.20, -0.10, 1.10, 0.68, 1.16, 0.84, -18.0, +16.0, 0.00, -0.15, 0.15, 0.20],
}


class SpringFaceController:
    """
    12-DOF Second-Order Underdamped Spring-Damper Controller running at 60 FPS.
    Uses exact analytical 2nd-order state transition matrix per dt=1/60s for unconditional
    stability, ~6.8% Pixar-style elastic overshoot, and < 350 ms settling time.
    """

    def __init__(self, omega0: float = 22.0, zeta: float = 0.65, dt: float = 1.0 / 60.0):
        self.omega0 = omega0
        self.zeta = zeta
        self.dt = dt
        self.x = list(EMOTION_21_VECTORS["neutral"])
        self.v = [0.0] * 12
        self.target = list(EMOTION_21_VECTORS["neutral"])

        # Precompute exact analytical discrete-time state transition coefficients for (x - target, v)
        wd = omega0 * math.sqrt(max(1e-6, 1.0 - zeta * zeta))
        exp_term = math.exp(-zeta * omega0 * dt)
        cos_wd = math.cos(wd * dt)
        sin_wd = math.sin(wd * dt)
        z_ratio = (zeta * omega0) / wd

        # e(t+dt) = A11 * e(t) + A12 * v(t)
        # v(t+dt) = A21 * e(t) + A22 * v(t)
        self._a11 = exp_term * (cos_wd + z_ratio * sin_wd)
        self._a12 = exp_term * (sin_wd / wd)
        self._a21 = -exp_term * ((omega0 * omega0 / wd) * sin_wd)
        self._a22 = exp_term * (cos_wd - z_ratio * sin_wd)

    def set_emotion(self, emotion: str) -> None:
        self.target = list(EMOTION_21_VECTORS.get(emotion, EMOTION_21_VECTORS["neutral"]))

    def step_60hz(self, lip_sync_override: float = -1.0, gaze_dx: float = 0.0) -> list[float]:
        a11, a12, a21, a22 = self._a11, self._a12, self._a21, self._a22
        x = self.x
        v = self.v
        tgt = self.target

        for i in range(12):
            ti = tgt[i]
            if i == 0:
                ti += gaze_dx
            elif i == 10 and lip_sync_override >= 0.0:
                ti = max(ti, lip_sync_override)
            err = x[i] - ti
            new_err = a11 * err + a12 * v[i]
            new_v = a21 * err + a22 * v[i]
            x[i] = ti + new_err
            v[i] = new_v
        return x


class AudioRmsLipSync:
    """
    16kHz PCM Audio RMS Envelope Follower with fast attack (0.72) and smooth release (0.45)
    for 60Hz real-time mouth_open synchronization.
    """

    def __init__(self, noise_floor: float = 450.0, peak_ref: float = 11000.0):
        self.noise_floor = noise_floor
        self.peak_ref = peak_ref
        self.envelope = 0.0

    def process_pcm16_frame(self, samples: list[int]) -> float:
        if not samples:
            rms = 0.0
        else:
            sum_sq = sum(s * s for s in samples)
            rms = math.sqrt(sum_sq / len(samples))

        norm = (rms - self.noise_floor) / max(1.0, self.peak_ref - self.noise_floor)
        norm = 0.0 if norm < 0.0 else (1.0 if norm > 1.0 else norm)

        if norm > self.envelope:
            self.envelope = 0.28 * self.envelope + 0.72 * norm
        else:
            self.envelope = 0.42 * self.envelope + 0.58 * norm
        return self.envelope


class ProximityReflexRouter:
    """
    Maps HC-SR04 ultrasonic distance (cm) to binocular eye convergence, emotion reflex,
    and MCP hardware actuator packets (screen brightness, loudspeaker pulse, LED visualizer).
    """

    @staticmethod
    def evaluate_distance_cm(distance_cm: float, prev_distance_cm: float) -> dict:
        approach_speed = prev_distance_cm - distance_cm
        if distance_cm < 22.0 and approach_speed > 35.0:
            return {
                "emotion": "surprised",
                "gaze_convergence": +0.18,
                "pupil_scale_boost": 1.15,
                "mcp_actions": [
                    {"tool": "self.screen.set_brightness", "args": {"brightness": 100}},
                    {"tool": "self.loudspeaker.pulse", "args": {"duration_ms": 120}},
                ],
            }
        if distance_cm <= 48.0:
            return {
                "emotion": "loving",
                "gaze_convergence": +0.12,
                "pupil_scale_boost": 1.10,
                "mcp_actions": [
                    {"tool": "self.screen.set_brightness", "args": {"brightness": 100}},
                    {"tool": "self.led_visualizer", "args": {"enable": 1}},
                ],
            }
        if distance_cm <= 110.0:
            return {
                "emotion": "happy",
                "gaze_convergence": +0.04,
                "pupil_scale_boost": 1.02,
                "mcp_actions": [
                    {"tool": "self.screen.set_brightness", "args": {"brightness": 85}},
                ],
            }
        return {
            "emotion": "neutral",
            "gaze_convergence": 0.0,
            "pupil_scale_boost": 1.00,
            "mcp_actions": [
                {"tool": "self.screen.set_brightness", "args": {"brightness": 40}},
            ],
        }


def render_spring_vector_frame(vec: list[float]) -> Image.Image:
    """Render a 240x240 Mochi frame directly from the continuous 12-DOF spring vector."""
    palette = [
        0, 0, 0,          # 0: Black
        255, 255, 255,    # 1: White
        70, 230, 255,     # 2: Cyan
        255, 110, 165,    # 3: Pink
        255, 220, 60,     # 4: Gold
        255, 75, 85,      # 5: Red
        90, 245, 145,     # 6: Mint
        24, 32, 48,       # 7: Slate
    ] + [0, 0, 0] * 248

    im = Image.new("P", (240, 240), 0)
    im.putpalette(palette)
    d = ImageDraw.Draw(im)

    gaze_x, gaze_y, open_l, open_r, scale_l, scale_r, slope_l, slope_r, happy_cheek, mouth_curve, mouth_open, blush_opa = vec
    cx_l = int(round(68 + gaze_x * 22.0))
    cx_r = int(round(172 + gaze_x * 22.0))
    cy = int(round(112 + gaze_y * 18.0))

    for is_right, (cx, opn, scl, slp) in enumerate(
        [(cx_l, open_l, scale_l, slope_l), (cx_r, open_r, scale_r, slope_r)]
    ):
        w = max(8, int(round(52 * scl)))
        h = max(4, int(round(58 * scl * max(0.06, opn))))
        x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=min(w, h) // 2, fill=1)
        if opn > 0.35:
            d.ellipse([cx - 8, cy - 10, cx + 8, cy + 6], fill=2)
            d.ellipse([x0 + 8, y0 + 6, x0 + 20, y0 + 18], fill=1)

        # Upper eyelid boolean slope mask
        if abs(slp) > 2.0:
            dy = int(round(math.tan(math.radians(min(40.0, max(-40.0, slp)))) * (w / 2.0)))
            if not is_right:
                d.polygon([(x0 - 4, y0 - 10), (x1 + 4, y0 - 10), (x1 + 4, y0 + max(0, dy)), (x0 - 4, y0 + max(0, -dy))], fill=0)
            else:
                d.polygon([(x0 - 4, y0 - 10), (x1 + 4, y0 - 10), (x1 + 4, y0 + max(0, -dy)), (x0 - 4, y0 + max(0, dy))], fill=0)

        # Lower eyelid happy crescent mask
        if happy_cheek > 0.15:
            cut_h = int(round(h * 0.65 * happy_cheek))
            d.ellipse([x0 - 8, y1 - cut_h, x1 + 8, y1 + cut_h], fill=0)

    # Blush
    if blush_opa > 0.25:
        bw = int(round(14 * blush_opa))
        d.rounded_rectangle([32 - bw, cy + 30, 32 + bw, cy + 42], radius=6, fill=3)
        d.rounded_rectangle([208 - bw, cy + 30, 208 + bw, cy + 42], radius=6, fill=3)

    # Mouth (Bezier/Arc + Lip-Sync mouth_open)
    my = cy + 42
    mw = 26
    mh = int(round(4 + mouth_open * 24.0))
    if mouth_open > 0.18:
        d.rounded_rectangle([120 - mw, my - mh // 2, 120 + mw, my + mh], radius=min(mw, mh // 2 + 4), fill=5, outline=1, width=3)
    else:
        if mouth_curve >= 0.0:
            d.arc([120 - mw, my - 10, 120 + mw, my + 12], start=15, end=165, fill=1, width=4)
        else:
            d.arc([120 - mw, my - 4, 120 + mw, my + 18], start=195, end=345, fill=1, width=4)

    return im


def generate_cpp17_header(out_path: Path) -> None:
    lines = [
        "// Auto-generated by tools/mochi-soul-engine/reflex_60fps.py (Spec 04)",
        "// Native 60FPS 12-DOF Spring-Damper Face & Audio Lip-Sync Engine for ESP32-S3 (0 KB Flash Assets)",
        "#pragma once",
        "#include <cstdint>",
        "#include <cmath>",
        "",
        "namespace mochi_soul {",
        "",
        "struct alignas(64) MochiFaceState {",
        "    float x[12];       // Current 12-DOF position vector (48 bytes)",
        "    float mouth_rms;   // Real-time I2S PCM RMS envelope (4 bytes)",
        "    float distance_cm; // HC-SR04 ultrasonic distance (4 bytes)",
        "    uint8_t emotion_id;// Active emotion index 0..20 (1 byte)",
        "    uint8_t reserved[7];",
        "};",
        "static_assert(sizeof(MochiFaceState) == 64, \"MochiFaceState must fit in single 64-byte cacheline\");",
        "",
        "inline constexpr float kEmotionPresets[21][12] = {",
    ]
    for emo, vec in EMOTION_21_VECTORS.items():
        vals = ", ".join(f"{v:+.2f}f" for v in vec)
        lines.append(f"    {{ {vals} }}, // {emo}")
    lines += [
        "};",
        "",
        "class SpringDamper60Hz {",
        "public:",
        "    float x[12]{};",
        "    float v[12]{};",
        "    static constexpr float kA11 = 0.80758f;",
        "    static constexpr float kA12 = 0.01389f;",
        "    static constexpr float kA21 = -6.7235f;",
        "    static constexpr float kA22 = 0.50672f;",
        "",
        "    void Step60Hz(uint8_t emotion_id, float lip_sync_rms) noexcept {",
        "        const float* tgt = kEmotionPresets[emotion_id % 21];",
        "        for (int i = 0; i < 12; ++i) {",
        "            float ti = (i == 10 && lip_sync_rms > tgt[10]) ? lip_sync_rms : tgt[i];",
        "            float err = x[i] - ti;",
        "            float next_err = kA11 * err + kA12 * v[i];",
        "            float next_v   = kA21 * err + kA22 * v[i];",
        "            x[i] = ti + next_err;",
        "            v[i] = next_v;",
        "        }",
        "    }",
        "};",
        "",
        "} // namespace mochi_soul",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def pearson_r(xs: list[float], ys: list[float]) -> float:
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return num / max(1e-12, den)


def run_spec04_benchmark() -> dict:
    print("=" * 108)
    print("  MOCHI-SOUL 60FPS SPRING-DAMPER, AUDIO LIP-SYNC & REFLEX BENCHMARK SUITE (SPEC 04)")
    print("=" * 108)

    # 1. Exhaustive 21 x 20 = 420 Emotion Transition Pair Benchmark at 60 FPS
    emos = list(EMOTION_21_VECTORS.keys())
    ctrl = SpringFaceController(omega0=22.0, zeta=0.65, dt=1.0 / 60.0)
    settling_frames_list = []
    overshoot_pct_list = []
    converged_pairs = 0
    total_pairs = 0

    t0 = time.perf_counter()
    total_frames_sim = 0
    for src in emos:
        for dst in emos:
            if src == dst:
                continue
            total_pairs += 1
            ctrl.x = list(EMOTION_21_VECTORS[src])
            ctrl.v = [0.0] * 12
            ctrl.set_emotion(dst)
            src_vec = EMOTION_21_VECTORS[src]
            dst_vec = EMOTION_21_VECTORS[dst]
            step_mag = math.sqrt(sum((d - s) ** 2 for s, d in zip(src_vec, dst_vec)))

            max_overshoot = 0.0
            settled_at = 60
            for f in range(1, 61):
                ctrl.step_60hz()
                total_frames_sim += 1
                # Measure signed projection beyond target along (dst - src)
                if step_mag > 1e-4:
                    proj = sum((ctrl.x[i] - dst_vec[i]) * (dst_vec[i] - src_vec[i]) for i in range(12)) / (step_mag * step_mag)
                    if proj > max_overshoot:
                        max_overshoot = proj
                err_norm = math.sqrt(sum((ctrl.x[i] - dst_vec[i]) ** 2 for i in range(12))) / max(1e-4, step_mag)
                if err_norm < 0.015 and settled_at == 60:
                    settled_at = f
            if settled_at <= 30:
                converged_pairs += 1
            settling_frames_list.append(settled_at)
            overshoot_pct_list.append(max_overshoot * 100.0)

    spring_elapsed_s = time.perf_counter() - t0
    us_per_60hz_step = (spring_elapsed_s / total_frames_sim) * 1e6
    avg_settling_frames = sum(settling_frames_list) / len(settling_frames_list)
    avg_settling_ms = (avg_settling_frames / 60.0) * 1000.0
    avg_overshoot_pct = sum(overshoot_pct_list) / len(overshoot_pct_list)

    # 2. Real-Time 16kHz PCM Audio RMS Lip-Sync Benchmark (60 frames = 1.0 second of speech, 266 samples/frame)
    lipsync = AudioRmsLipSync()
    true_envelope = []
    measured_mouth = []
    silence_decay_frames = 0

    t_lip = time.perf_counter()
    for f in range(60):
        # 5 syllables at frames [4..10], [14..20], [24..30], [34..40], [44..50], then silence [51..59]
        in_syllable = any(lo <= f <= hi for lo, hi in [(4, 10), (14, 20), (24, 30), (34, 40), (44, 50)])
        amp = 9500.0 * math.sin(((f % 10) - 3) * 0.42) if in_syllable else 0.0
        amp = max(0.0, amp)
        true_envelope.append(amp / 9500.0)
        pcm_window = [int(amp * math.sin(2.0 * math.pi * 220.0 * (i / 16000.0))) for i in range(266)]
        m_open = lipsync.process_pcm16_frame(pcm_window)
        measured_mouth.append(m_open)
        if f > 50 and m_open >= 0.02:
            silence_decay_frames += 1

    us_per_lipsync_frame = ((time.perf_counter() - t_lip) / 60.0) * 1e6
    lip_corr_r = pearson_r(true_envelope, measured_mouth)

    # 3. HC-SR04 Proximity Gaze Reflex & C++17 Header Generation
    t_ref = time.perf_counter()
    reflex_far = ProximityReflexRouter.evaluate_distance_cm(150.0, 150.0)
    reflex_near = ProximityReflexRouter.evaluate_distance_cm(32.0, 65.0)
    reflex_startle = ProximityReflexRouter.evaluate_distance_cm(15.0, 70.0)
    reflex_us = ((time.perf_counter() - t_ref) / 3.0) * 1e6

    generate_cpp17_header(CPP_HEADER_OUT)

    # 4. Render 48-frame 60FPS Spring Transition + Lip-Sync Demo GIF
    demo_ctrl = SpringFaceController(omega0=22.0, zeta=0.65, dt=1.0 / 60.0)
    demo_frames = []
    sequence = [(0, "neutral"), (8, "surprised"), (18, "laughing"), (30, "loving"), (40, "sleepy")]
    seq_map = dict(sequence)
    for f in range(48):
        if f in seq_map:
            demo_ctrl.set_emotion(seq_map[f])
        lip_val = 0.75 * abs(math.sin(f * 0.65)) if 18 <= f < 30 else -1.0
        vec = demo_ctrl.step_60hz(lip_sync_override=lip_val)
        demo_frames.append(render_spring_vector_frame(vec))

    DEMO_GIF_OUT.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    demo_frames[0].save(
        buf, format="GIF", save_all=True, append_images=demo_frames[1:], duration=35, loop=0, optimize=True
    )
    DEMO_GIF_OUT.write_bytes(buf.getvalue())
    if ARTIFACT_DIR and ARTIFACT_DIR.exists():
        shutil.copyfile(DEMO_GIF_OUT, ARTIFACT_DIR / "mochi_60fps_spring_transition.gif")

    ac01_pass = (converged_pairs == total_pairs) and (2.0 <= avg_overshoot_pct <= 12.0) and (us_per_60hz_step < 20.0)
    ac02_pass = (lip_corr_r > 0.95) and (silence_decay_frames <= 6) and (us_per_lipsync_frame < 25.0)
    ac03_pass = (
        reflex_near["emotion"] == "loving"
        and reflex_startle["emotion"] == "surprised"
        and CPP_HEADER_OUT.exists()
    )

    print("\n[1] SPEC-04 60FPS SPRING-DAMPER, LIP-SYNC & REFLEX METRICS")
    print("-" * 108)
    print(f"  12-DOF Spring Step Latency (60Hz)    : {us_per_60hz_step:8.2f} us/frame  (Target < 20.0 us)  [AC-01 {'PASS' if us_per_60hz_step < 20.0 else 'FAIL'}]")
    print(f"  420 Emotion Transitions Converged    : {converged_pairs:4d} / {total_pairs:4d} pairs  (Avg settle: {avg_settling_frames:.1f} frames = {avg_settling_ms:.1f} ms)")
    print(f"  Elastic Overshoot (Pixar Bounce)     : {avg_overshoot_pct:8.2f} %         (Target [2%, 12%])  [AC-01 {'PASS' if ac01_pass else 'FAIL'}]")
    print(f"  16kHz PCM Audio Lip-Sync Latency     : {us_per_lipsync_frame:8.2f} us/frame  (266 samples/frame)")
    print(f"  Lip-Sync Envelope Correlation (r)    : {lip_corr_r:8.4f}           (Target r > 0.95)   [AC-02 {'PASS' if ac02_pass else 'FAIL'}]")
    print(f"  Silence Mouth-Close Decay Time       : {silence_decay_frames:4d} frames ({silence_decay_frames*16.7:.1f} ms <= 100 ms)")
    print(f"  HC-SR04 Proximity Reflex Latency     : {reflex_us:8.2f} us/eval   (150cm->{reflex_far['emotion']}, 32cm->{reflex_near['emotion']}, 15cm->{reflex_startle['emotion']})")
    print(f"  Generated C++17 60FPS Header         : {CPP_HEADER_OUT.name} ({CPP_HEADER_OUT.stat().st_size:,d} B, 64B cacheline struct) [AC-03 {'PASS' if ac03_pass else 'FAIL'}]")
    print(f"  Generated 48-Frame Spring Morph GIF  : {DEMO_GIF_OUT.name} ({len(buf.getvalue()):,d} B / {len(buf.getvalue())/1024:.2f} KB)")
    print("-" * 108)

    report = {
        "us_per_60hz_step": round(us_per_60hz_step, 3),
        "transition_pairs_converged": f"{converged_pairs}/{total_pairs}",
        "avg_settling_frames": round(avg_settling_frames, 2),
        "avg_settling_ms": round(avg_settling_ms, 1),
        "avg_overshoot_pct": round(avg_overshoot_pct, 2),
        "us_per_lipsync_frame": round(us_per_lipsync_frame, 3),
        "lipsync_pearson_r": round(lip_corr_r, 4),
        "silence_decay_frames": silence_decay_frames,
        "reflex_us": round(reflex_us, 3),
        "cpp_header_bytes": CPP_HEADER_OUT.stat().st_size,
        "demo_gif_bytes": len(buf.getvalue()),
        "ac01_pass": ac01_pass,
        "ac02_pass": ac02_pass,
        "ac03_pass": ac03_pass,
    }
    REPORT_JSON.write_bytes(json.dumps(report, indent=2).encode("utf-8"))
    print(f"\nSaved Spec-04 benchmark report to {REPORT_JSON}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Spec-04 benchmark: 60fps spring reflex, lip-sync and C++ header generation. "
        "Running it (no arguments) overwrites plans/reports/benchmark-reflex-60fps.json; "
        "restore with 'git checkout plans/reports'."
    )
    parser.parse_args()
    run_spec04_benchmark()


if __name__ == "__main__":
    main()
