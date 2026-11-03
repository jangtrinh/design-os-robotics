#!/usr/bin/env python3
"""
cook-procedural-avatar.py — 100% Code-Drawn (Procedural Parametric Vector) Mochi Avatar Generator
for RoBot.5320 (240x320 ST7789 IPS LCD).

Generates ALL 21 distinct Xiaozhi emotions procedurally (~9-17 KB each, 8-color flat palette, zero dithering):
  1. neutral      2. happy        3. laughing     4. funny        5. sad
  6. angry        7. crying       8. loving       9. embarrassed 10. surprised
 11. shocked     12. thinking    13. winking     14. cool        15. relaxed
 16. delicious   17. kissy       18. confident   19. sleepy      20. silly
 21. confused

Also packs:
  - Complete esp_mmap_assets binary: themes/procedural-mochi-fullvien-240x320.bin
  - 21-panel Master Contact Sheet (7x3 grid): procedural_mochi_21_preview.png
"""
from __future__ import annotations

import io
import json
import math
import shutil
import struct
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "themes" / "procedural-mochi"
ARTIFACT_DIR = Path("/Users/jangtrinh/.gemini/antigravity/brain/32f1ac36-6292-41f1-ae0c-a80ad0e02a34")

# 8-Color Flat Indexed Palette (Zero Dithering -> Maximum LZW Run-Length Compression)
PALETTE = [
    0, 0, 0,         # 0: Pure Black (#000000) - Background & Boolean Eyelid Masks
    255, 255, 255,   # 1: Pure White (#FFFFFF) - Eyes & Mouth
    70, 230, 255,    # 2: Cyber Cyan (#46E6FF) - Tears, Zzz, Sweat, Tech Accents
    255, 110, 160,   # 3: Sakura Pink (#FF6EA0) - Blush Cheeks & Tongue
    255, 216, 77,    # 4: Starlight Gold (#FFD84D) - Sparkles, Stars, Question Marks
    255, 70, 90,     # 5: Coral Red (#FF465A) - Hearts & Anger Vein
    168, 244, 255,   # 6: Ice Blue (#A8F4FF) - Eye Specular Glint & Shades Glint
    34, 38, 52,      # 7: Dark Slate (#222634) - Sunglasses Frame & Subtle Accents
] + [0, 0, 0] * 248

ALL_21_EMOTIONS = [
    "neutral", "happy", "laughing", "funny", "sad",
    "angry", "crying", "loving", "embarrassed", "surprised",
    "shocked", "thinking", "winking", "cool", "relaxed",
    "delicious", "kissy", "confident", "sleepy", "silly",
    "confused",
]


def draw_heart(d: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: int = 5) -> None:
    r = max(2, int(size * 0.55))
    d.ellipse([cx - size, cy - r, cx + 1, cy + r], fill=color)
    d.ellipse([cx - 1, cy - r, cx + size, cy + r], fill=color)
    d.polygon([(cx - size, cy + r // 3), (cx + size, cy + r // 3), (cx, cy + int(size * 1.35))], fill=color)


def draw_star(d: ImageDraw.ImageDraw, cx: int, cy: int, r_out: int, color: int = 4) -> None:
    r_in = max(2, r_out // 3)
    pts = [
        (cx, cy - r_out), (cx + r_in, cy - r_in),
        (cx + r_out, cy), (cx + r_in, cy + r_in),
        (cx, cy + r_out), (cx - r_in, cy + r_in),
        (cx - r_out, cy), (cx - r_in, cy - r_in),
    ]
    d.polygon(pts, fill=color)


def draw_anger_vein(d: ImageDraw.ImageDraw, cx: int, cy: int, s: int, color: int = 5) -> None:
    g = max(3, s // 3)
    d.line([(cx - s, cy - g), (cx - g, cy - g), (cx - g, cy - s)], fill=color, width=3)
    d.line([(cx + s, cy - g), (cx + g, cy - g), (cx + g, cy - s)], fill=color, width=3)
    d.line([(cx - s, cy + g), (cx - g, cy + g), (cx - g, cy + s)], fill=color, width=3)
    d.line([(cx + s, cy + g), (cx + g, cy + g), (cx + g, cy + s)], fill=color, width=3)


def draw_z(d: ImageDraw.ImageDraw, cx: int, cy: int, sz: int, color: int = 2) -> None:
    pts = [(cx - sz, cy - sz), (cx + sz, cy - sz), (cx - sz, cy + sz), (cx + sz, cy + sz)]
    d.line(pts, fill=color, width=3)


def draw_question_mark(d: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0, color: int = 4) -> None:
    r = int(9 * scale)
    d.arc([cx - r, cy - r * 2, cx + r, cy], start=180, end=45, fill=color, width=3)
    d.line([(cx + r // 2, cy - r // 2), (cx, cy + 2), (cx, cy + int(6 * scale))], fill=color, width=3)
    d.ellipse([cx - 2, cy + int(10 * scale), cx + 2, cy + int(14 * scale)], fill=color)


def draw_sweat_drop(d: ImageDraw.ImageDraw, cx: int, cy: int, sz: int = 10, color: int = 2) -> None:
    d.polygon([(cx, cy - sz), (cx - sz // 2, cy + 2), (cx + sz // 2, cy + 2)], fill=color)
    d.ellipse([cx - sz // 2, cy - 2, cx + sz // 2, cy + sz - 2], fill=color)


def draw_w_mouth(d: ImageDraw.ImageDraw, cx: int, cy: int, w_half: int = 24, h: int = 11, color: int = 1) -> None:
    d.arc([cx - w_half, cy - h, cx, cy + h], start=0, end=180, fill=color, width=4)
    d.arc([cx, cy - h, cx + w_half, cy + h], start=0, end=180, fill=color, width=4)


def draw_std_eye(d: ImageDraw.ImageDraw, cx: int, cy: int, ew: int = 54, eh: int = 62, glint_dx: int = 0, glint_dy: int = 0) -> None:
    d.rounded_rectangle([cx - ew // 2, cy - eh // 2, cx + ew // 2, cy + eh // 2], radius=min(24, eh // 2), fill=1)
    if eh > 26:
        gx0 = cx - ew // 2 + 9 + glint_dx
        gy0 = cy - eh // 2 + 9 + glint_dy
        d.rounded_rectangle([gx0, gy0, gx0 + 11, gy0 + 14], radius=4, fill=6)


def draw_crescent_eye(d: ImageDraw.ImageDraw, cx: int, cy: int, ew: int = 56, eh: int = 60) -> None:
    d.rounded_rectangle([cx - ew // 2, cy - eh // 2, cx + ew // 2, cy + eh // 2], radius=26, fill=1)
    d.ellipse([cx - ew // 2 - 6, cy - 2, cx + ew // 2 + 6, cy + eh // 2 + 28], fill=0)


def render_emotion_frame(emotion: str, frame_idx: int, num_frames: int = 16, w: int = 240, h: int = 320) -> Image.Image:
    t = frame_idx / float(num_frames)
    tau = 2.0 * math.pi * t
    img = Image.new("P", (w, h), 0)
    img.putpalette(PALETTE)
    d = ImageDraw.Draw(img)

    cx_l, cx_r = 66, 174
    cy_base = 136

    if emotion == "neutral":
        by = int(round(3.5 * math.sin(tau)))
        gx = int(round(5.0 * math.sin(tau)))
        blink = max(0.08, 1.0 - math.exp(-((t - 0.5) * 11.5) ** 2))
        eh = max(6, int(round(64 * blink)))
        ey = cy_base + by
        for ex in (cx_l + gx, cx_r + gx):
            draw_std_eye(d, ex, ey, 54, eh)
        d.ellipse([22 + gx, ey + 34, 52 + gx, ey + 50], fill=3)
        d.ellipse([188 + gx, ey + 34, 218 + gx, ey + 50], fill=3)
        draw_w_mouth(d, 120 + gx, ey + 44, 25, 11)

    elif emotion == "happy":
        by = int(round(-4.0 * abs(math.sin(tau))))
        gx = int(round(3.0 * math.sin(tau)))
        ey = cy_base + by
        for ex in (cx_l + gx, cx_r + gx):
            draw_crescent_eye(d, ex, ey, 56, 60)
        d.ellipse([20 + gx, ey + 24, 54 + gx, ey + 44], fill=3)
        d.ellipse([186 + gx, ey + 24, 220 + gx, ey + 44], fill=3)
        my = ey + 34
        mh = 24 + int(round(4.0 * math.sin(tau)))
        d.chord([92 + gx, my - 12, 148 + gx, my + mh], start=0, end=180, fill=1)
        d.chord([102 + gx, my + 2, 138 + gx, my + mh], start=0, end=180, fill=3)

    elif emotion == "laughing":
        by = int(round(-8.0 * abs(math.sin(tau * 2.0))))
        ey = cy_base + by
        # Tightly squeezed '> <' laughing chevrons
        d.line([(cx_l - 22, ey - 18), (cx_l + 18, ey), (cx_l - 22, ey + 18)], fill=1, width=8)
        d.line([(cx_r + 22, ey - 18), (cx_r - 18, ey), (cx_r + 22, ey + 18)], fill=1, width=8)
        d.ellipse([18, ey + 22, 54, ey + 42], fill=3)
        d.ellipse([186, ey + 22, 222, ey + 42], fill=3)
        my = ey + 30
        mw = 36 + int(round(4.0 * math.sin(tau * 2.0)))
        d.chord([120 - mw, my - 14, 120 + mw, my + 34], start=0, end=180, fill=1)
        d.chord([120 - mw + 10, my + 6, 120 + mw - 10, my + 34], start=0, end=180, fill=3)
        # Side laughing tear droplets + stars
        draw_star(d, 34, 64, 10 + int(round(3 * math.sin(tau))), color=4)
        draw_star(d, 206, 64, 10 + int(round(3 * math.cos(tau))), color=4)

    elif emotion == "funny":
        # Goofy asymmetric bounce: Big left eye, small right eye, goofy crooked grin
        by = int(round(5.0 * math.sin(tau * 2.0)))
        gx = int(round(6.0 * math.cos(tau)))
        ey = cy_base + by
        draw_std_eye(d, cx_l + gx, ey - 4, 64, 70, glint_dx=int(4 * math.sin(tau)), glint_dy=int(4 * math.cos(tau)))
        draw_std_eye(d, cx_r + gx, ey + 6, 38, 42, glint_dx=-int(4 * math.sin(tau)))
        d.ellipse([18 + gx, ey + 34, 48 + gx, ey + 50], fill=3)
        d.ellipse([190 + gx, ey + 30, 220 + gx, ey + 46], fill=3)
        # Goofy lopsided buck-tooth smile
        my = ey + 44
        d.arc([88 + gx, my - 14, 152 + gx, my + 16], start=10, end=170, fill=1, width=5)
        d.rectangle([114 + gx, my + 1, 126 + gx, my + 11], fill=1)
        draw_star(d, 198, 58, 11 + int(round(3 * math.sin(tau))), color=4)

    elif emotion == "sad":
        by = 8 + int(round(2.5 * math.sin(tau)))
        ey = cy_base + by
        ew, eh = 54, 58
        draw_std_eye(d, cx_l, ey, ew, eh, glint_dy=8)
        d.polygon([(cx_l - 34, ey - 34), (cx_l + 34, ey - 34), (cx_l - 34, ey + 4)], fill=0)
        draw_std_eye(d, cx_r, ey, ew, eh, glint_dy=8)
        d.polygon([(cx_r - 34, ey - 34), (cx_r + 34, ey - 34), (cx_r + 34, ey + 4)], fill=0)
        tear_y = ey + 16 + int(round(32.0 * t))
        d.ellipse([cx_l - 28, tear_y, cx_l - 16, tear_y + 16], fill=2)
        d.arc([96, ey + 48, 144, ey + 72], start=195, end=345, fill=1, width=5)

    elif emotion == "angry":
        gx = 2 if (frame_idx % 2 == 0) else -2
        by = int(round(2.0 * math.sin(tau * 2.0)))
        ey = cy_base + by
        ew, eh = 56, 58
        for side, cx in ((-1, cx_l + gx), (1, cx_r + gx)):
            d.rounded_rectangle([cx - ew // 2, ey - eh // 2, cx + ew // 2, ey + eh // 2], radius=20, fill=1)
            if side == -1:
                d.polygon([(cx - 34, ey - 34), (cx + 34, ey - 34), (cx + 34, ey + 8)], fill=0)
            else:
                d.polygon([(cx - 34, ey - 34), (cx + 34, ey - 34), (cx - 34, ey + 8)], fill=0)
        d.arc([90 + gx, ey + 44, 150 + gx, ey + 70], start=190, end=350, fill=1, width=6)
        vein_size = 13 + (3 if (frame_idx // 2) % 2 == 0 else 0)
        draw_anger_vein(d, 202, 68, vein_size, color=5)

    elif emotion == "crying":
        # Streaming waterfall tears + wailing mouth
        by = 6 + int(round(3.0 * math.sin(tau * 2.0)))
        ey = cy_base + by
        # Waterfall cyan streams under both eyes
        for ex in (cx_l, cx_r):
            d.rectangle([ex - 18, ey + 6, ex + 18, ey + 95], fill=2)
            # Animated white wave ripples inside the tear stream
            for k in range(3):
                ry = ey + 14 + int(round(((t + k / 3.0) % 1.0) * 72))
                d.line([(ex - 12, ry), (ex + 12, ry)], fill=6, width=3)
            # Squeezed shut crying eye arch on top
            d.arc([ex - 28, ey - 16, ex + 28, ey + 20], start=180, end=360, fill=1, width=7)
        # Wailing open mouth
        mw = 22 + int(round(4 * math.sin(tau * 2.0)))
        d.rounded_rectangle([120 - mw, ey + 38, 120 + mw, ey + 68], radius=12, fill=1)
        d.rounded_rectangle([120 - mw + 5, ey + 46, 120 + mw - 5, ey + 66], radius=8, fill=5)

    elif emotion == "loving":
        # Giant pulsing heart eyes ❤️ ❤️ + floating mini hearts
        by = int(round(3.5 * math.sin(tau)))
        ey = cy_base + by
        h_sz = 26 + int(round(4.0 * abs(math.sin(tau))))
        draw_heart(d, cx_l, ey - 6, h_sz, color=5)
        draw_heart(d, cx_r, ey - 6, h_sz, color=5)
        d.ellipse([18, ey + 28, 54, ey + 46], fill=3)
        d.ellipse([186, ey + 28, 222, ey + 46], fill=3)
        draw_w_mouth(d, 120, ey + 40, 26, 12, color=1)
        # Floating mini hearts
        draw_heart(d, 42, 68 - int(round(16 * t)), 8, color=3)
        draw_heart(d, 198, 74 - int(round(16 * ((t + 0.5) % 1.0))), 9, color=5)

    elif emotion == "embarrassed":
        # Shy averted gaze + diagonal pink blush slashes + sweat drop + wavy mouth
        gx = -10 + int(round(2.0 * math.sin(tau)))
        by = int(round(2.0 * math.cos(tau)))
        ey = cy_base + 4 + by
        for ex in (cx_l + gx, cx_r + gx):
            draw_std_eye(d, ex, ey, 50, 52)
            # Slightly raised shy lower lid
            d.rectangle([ex - 28, ey + 18, ex + 28, ey + 30], fill=0)
        # Large pink blush cheeks + diagonal blush lines across nose
        d.ellipse([16, ey + 22, 62, ey + 46], fill=3)
        d.ellipse([178, ey + 22, 224, ey + 46], fill=3)
        for bx_slash in range(86, 156, 14):
            d.line([(bx_slash, ey + 28), (bx_slash - 6, ey + 38)], fill=3, width=3)
        # Wavy shy mouth
        my = ey + 48
        d.arc([92, my - 6, 112, my + 8], start=0, end=180, fill=1, width=4)
        d.arc([110, my - 6, 130, my + 8], start=180, end=360, fill=1, width=4)
        d.arc([128, my - 6, 148, my + 8], start=0, end=180, fill=1, width=4)
        draw_sweat_drop(d, 210, 74 + int(round(10 * t)), sz=13, color=2)

    elif emotion == "surprised":
        # Wide tall O O eyes + raised high brows + 'o' mouth + '!' mark
        by = int(round(-4.0 * abs(math.sin(tau))))
        ey = cy_base + by
        for ex in (cx_l, cx_r):
            d.ellipse([ex - 30, ey - 36, ex + 30, ey + 36], fill=1)
            d.ellipse([ex - 8, ey - 10, ex + 8, ey + 10], fill=6)
            d.arc([ex - 26, ey - 54, ex + 26, ey - 34], start=200, end=340, fill=1, width=4)
        r_m = 13 + int(round(3.0 * math.sin(tau)))
        d.ellipse([120 - r_m, ey + 44 - r_m, 120 + r_m, ey + 44 + r_m], fill=1)
        d.ellipse([120 - r_m + 5, ey + 44 - r_m + 5, 120 + r_m - 5, ey + 44 + r_m - 5], fill=0)

    elif emotion == "shocked":
        # Cyber-shocked hollow ringing eyes + jitter + lightning shock lines
        gx = 3 if (frame_idx % 2 == 0) else -3
        ey = cy_base
        for ex in (cx_l + gx, cx_r + gx):
            r_sh = 28 + (2 if frame_idx % 4 < 2 else -2)
            d.ellipse([ex - r_sh, ey - r_sh - 4, ex + r_sh, ey + r_sh + 4], fill=1)
            d.ellipse([ex - r_sh + 9, ey - r_sh + 5, ex + r_sh - 9, ey + r_sh - 5], fill=0)
            d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=2)
        # Tall gasping mouth
        d.rounded_rectangle([104 + gx, ey + 38, 136 + gx, ey + 74], radius=14, fill=1)
        d.rounded_rectangle([109 + gx, ey + 43, 131 + gx, ey + 69], radius=10, fill=0)
        # Top shock rays
        for rx_s, ang_dx in ((96, -8), (120, 0), (144, 8)):
            d.line([(rx_s, 44), (rx_s + ang_dx, 68)], fill=4, width=4)

    elif emotion == "thinking":
        # Asymmetric inquisitive eyes looking up-right + chin-ponder mouth + thought bubbles + '?'
        by = int(round(2.5 * math.sin(tau)))
        ey = cy_base + by
        # Left eye: narrowed squint
        draw_std_eye(d, cx_l + 6, ey + 4, 52, 42, glint_dx=8, glint_dy=-4)
        d.rectangle([cx_l - 24, ey - 22, cx_l + 36, ey - 4], fill=0)
        # Right eye: wide inquisitive with raised brow
        draw_std_eye(d, cx_r + 6, ey - 4, 54, 64, glint_dx=8, glint_dy=-6)
        d.arc([cx_r - 22, ey - 52, cx_r + 32, ey - 32], start=195, end=345, fill=1, width=4)
        # Sideways pondering mouth
        d.line([(104, ey + 48), (138, ey + 44)], fill=1, width=5)
        # Floating thought bubbles + '?'
        d.ellipse([164, 78, 172, 86], fill=6)
        d.ellipse([178, 62, 190, 74], fill=6)
        draw_question_mark(d, 206, 52 + int(round(4 * math.sin(tau))), scale=1.2, color=4)

    elif emotion == "winking":
        by = int(round(-4.0 * abs(math.sin(tau))))
        ey = cy_base + by
        # Left eye: big sparkly open eye
        draw_std_eye(d, cx_l, ey, 54, 64)
        # Right eye: bold '<' wink chevron
        d.line([(cx_r + 22, ey - 18), (cx_r - 18, ey), (cx_r + 22, ey + 18)], fill=1, width=8)
        d.ellipse([20, ey + 30, 52, ey + 46], fill=3)
        d.ellipse([188, ey + 30, 220, ey + 46], fill=3)
        draw_w_mouth(d, 120, ey + 40, 26, 12)
        draw_star(d, 206, 66, 11 + int(round(3 * math.sin(tau))), color=4)

    elif emotion == "cool":
        # Cyber Deal-With-It Sunglasses with animated diagonal lens glint!
        by = int(round(3.0 * math.sin(tau)))
        ey = cy_base + by
        # Glowing cyan eyes behind dark shades
        draw_std_eye(d, cx_l, ey, 52, 54)
        draw_std_eye(d, cx_r, ey, 52, 54)
        # Sunglasses bridge & lenses
        d.rectangle([14, ey - 24, 226, ey - 16], fill=1)
        d.polygon([(22, ey - 22), (110, ey - 22), (102, ey + 18), (30, ey + 18)], fill=7, outline=1)
        d.polygon([(130, ey - 22), (218, ey - 22), (210, ey + 18), (138, ey + 18)], fill=7, outline=1)
        # Sweeping specular glint across the lenses
        glint_x = int(round(t * 70))
        for lx0 in (32, 140):
            gx_s = lx0 + (glint_x % 52)
            d.line([(gx_s, ey - 16), (gx_s - 12, ey + 12)], fill=6, width=5)
        # Confident cool half-smirk
        d.arc([96, ey + 32, 152, ey + 56], start=10, end=155, fill=1, width=5)

    elif emotion == "relaxed":
        # Peaceful downward-curving serene closed eyes (︶ ︶) + gentle breathing
        by = int(round(4.0 * math.sin(tau)))
        ey = cy_base + by
        d.arc([cx_l - 26, ey - 18, cx_l + 26, ey + 16], start=15, end=165, fill=1, width=6)
        d.arc([cx_r - 26, ey - 18, cx_r + 26, ey + 16], start=15, end=165, fill=1, width=6)
        d.ellipse([20, ey + 22, 52, ey + 38], fill=3)
        d.ellipse([188, ey + 22, 220, ey + 38], fill=3)
        d.arc([98, ey + 30, 142, ey + 50], start=15, end=165, fill=1, width=4)
        draw_star(d, 198, 66 - int(round(6 * math.sin(tau))), 8, color=6)

    elif emotion == "delicious":
        # Yummy crescent eyes + 'w' mouth + pink tongue licking side-to-side!
        by = int(round(-3.5 * abs(math.sin(tau))))
        ey = cy_base + by
        draw_crescent_eye(d, cx_l, ey, 56, 58)
        draw_crescent_eye(d, cx_r, ey, 56, 58)
        d.ellipse([18, ey + 24, 52, ey + 42], fill=3)
        d.ellipse([188, ey + 24, 222, ey + 42], fill=3)
        my = ey + 38
        # Licking pink tongue moving along the smile
        tx = 134 + int(round(8.0 * math.sin(tau)))
        d.ellipse([tx - 10, my - 2, tx + 12, my + 18], fill=3)
        draw_w_mouth(d, 120, my, 26, 12, color=1)
        draw_star(d, 40, 68, 9, color=4)

    elif emotion == "kissy":
        # Wink + puckered '3' kissy lips + flying heart ❤️
        by = int(round(3.0 * math.sin(tau)))
        ey = cy_base + by
        draw_crescent_eye(d, cx_l, ey, 54, 56)
        d.line([(cx_r + 22, ey - 16), (cx_r - 16, ey), (cx_r + 22, ey + 16)], fill=1, width=7)
        d.ellipse([20, ey + 26, 54, ey + 44], fill=3)
        d.ellipse([186, ey + 26, 220, ey + 44], fill=3)
        # Puckered '3' kissy mouth
        my = ey + 42
        d.arc([110, my - 12, 128, my + 2], start=270, end=110, fill=1, width=4)
        d.arc([110, my - 2, 128, my + 12], start=250, end=90, fill=1, width=4)
        # Flying kiss heart
        hx = 148 + int(round(48.0 * t))
        hy = my - 10 - int(round(46.0 * t))
        draw_heart(d, hx, hy, size=8 + int(round(6.0 * t)), color=5)

    elif emotion == "confident":
        # Smug half-lidded eyes + proud smirk + golden sparkle
        by = int(round(-3.0 * abs(math.sin(tau))))
        gx = int(round(4.0 * math.sin(tau)))
        ey = cy_base + by
        for ex in (cx_l + gx, cx_r + gx):
            draw_std_eye(d, ex, ey, 54, 58, glint_dx=6)
            # Smug flat upper lid covering top 32%
            d.rectangle([ex - 30, ey - 32, ex + 30, ey - 10], fill=0)
            d.line([(ex - 28, ey - 10), (ex + 28, ey - 10)], fill=6, width=3)
        # Confident tilted smirk
        d.arc([94 + gx, ey + 30, 152 + gx, ey + 54], start=15, end=155, fill=1, width=5)
        draw_star(d, 202, 62, 11 + int(round(3 * math.sin(tau))), color=4)

    elif emotion == "sleepy":
        by = int(round(4.0 * math.sin(tau)))
        ey = cy_base + 6 + by
        ew, eh = 54, 48
        for ex in (cx_l, cx_r):
            d.rounded_rectangle([ex - ew // 2, ey - eh // 2, ex + ew // 2, ey + eh // 2], radius=20, fill=1)
            d.rectangle([ex - ew // 2 - 4, ey - eh // 2 - 4, ex + ew // 2 + 4, ey + 4], fill=0)
            d.line([(ex - ew // 2, ey + 4), (ex + ew // 2, ey + 4)], fill=6, width=3)
        d.ellipse([24, ey + 24, 52, ey + 38], fill=3)
        d.ellipse([188, ey + 24, 216, ey + 38], fill=3)
        yr = 7 + int(round(4.0 * (0.5 + 0.5 * math.sin(tau))))
        my = ey + 38
        d.ellipse([120 - yr, my - yr, 120 + yr, my + yr], fill=1)
        if yr > 8:
            d.ellipse([120 - yr + 3, my - yr + 3, 120 + yr - 3, my + yr - 3], fill=3)
        for idx_z, (bx, by_z, bsz) in enumerate([(156, 86, 6), (178, 66, 9), (204, 44, 12)]):
            dy_z = int(round(8.0 * ((t + idx_z * 0.33) % 1.0)))
            draw_z(d, bx, by_z - dy_z, bsz, color=2)

    elif emotion == "silly":
        # Playful cross-eyed / derp look + big pink tongue sticking straight out (:P)
        by = int(round(-5.0 * abs(math.sin(tau * 2.0))))
        ey = cy_base + by
        # Left eye looking inward right, Right eye looking inward left
        draw_std_eye(d, cx_l + 6, ey, 54, 60, glint_dx=18, glint_dy=4)
        draw_std_eye(d, cx_r - 6, ey, 54, 60, glint_dx=-18, glint_dy=4)
        d.ellipse([20, ey + 28, 52, ey + 44], fill=3)
        d.ellipse([188, ey + 28, 220, ey + 44], fill=3)
        my = ey + 40
        # Big silly pink tongue sticking down
        th = 24 + int(round(4.0 * math.sin(tau * 2.0)))
        d.rounded_rectangle([106, my, 134, my + th], radius=12, fill=3)
        d.line([(120, my + 2), (120, my + th - 6)], fill=5, width=2)
        draw_w_mouth(d, 120, my - 2, 26, 11, color=1)

    elif emotion == "confused":
        # One eye raised high, one squinted low + wavy squiggle mouth + '? ?' marks
        by = int(round(3.0 * math.sin(tau)))
        gx = int(round(4.0 * math.cos(tau)))
        ey = cy_base + by
        draw_std_eye(d, cx_l + gx, ey - 8, 56, 64, glint_dy=-4)
        draw_std_eye(d, cx_r + gx, ey + 8, 50, 38, glint_dy=4)
        d.polygon([(cx_r + gx - 30, ey - 18), (cx_r + gx + 30, ey - 18), (cx_r + gx + 30, ey + 2)], fill=0)
        # Wavy confused mouth
        my = ey + 46
        d.arc([92, my - 6, 112, my + 8], start=180, end=360, fill=1, width=4)
        d.arc([110, my - 6, 130, my + 8], start=0, end=180, fill=1, width=4)
        d.arc([128, my - 6, 148, my + 8], start=180, end=360, fill=1, width=4)
        draw_question_mark(d, 42, 60 + int(round(4 * math.sin(tau))), scale=1.0, color=2)
        draw_question_mark(d, 198, 54 + int(round(4 * math.cos(tau))), scale=1.2, color=4)

    return img.crop((0, 16, 240, 256))


def build_all_21_procedural_gifs() -> dict[str, bytes]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    gif_bytes_by_emotion: dict[str, bytes] = {}
    poster_frames: dict[str, Image.Image] = {}

    for emo in ALL_21_EMOTIONS:
        frames = [render_emotion_frame(emo, i, num_frames=16) for i in range(16)]
        poster_frames[emo] = frames[3].convert("RGB")
        buf = io.BytesIO()
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=65,
            loop=0,
            optimize=True,
        )
        raw = buf.getvalue()
        gif_bytes_by_emotion[emo] = raw
        out_file = OUT_DIR / f"{emo}.gif"
        out_file.write_bytes(raw)
        shutil.copyfile(out_file, ARTIFACT_DIR / f"procedural_{emo}.gif")
        print(f"  [GIF] {emo:13s}: {len(raw):6,d} bytes ({len(raw)/1024:5.2f} KB) -> {out_file.name}")

    # Build 21-panel Master Contact Sheet (7 cols x 3 rows, scaled 50% per cell -> 120x160 each)
    cw, ch = 120, 160
    cols, rows = 7, 3
    pad = 8
    label_h = 20
    grid_w = pad + cols * (cw + pad)
    grid_h = pad + rows * (ch + label_h + pad)
    sheet = Image.new("RGB", (grid_w, grid_h), (14, 16, 24))
    draw_s = ImageDraw.Draw(sheet)

    for idx, emo in enumerate(ALL_21_EMOTIONS):
        c = idx % cols
        r = idx // cols
        x0 = pad + c * (cw + pad)
        y0 = pad + r * (ch + label_h + pad)
        thumb = poster_frames[emo].resize((cw, ch), Image.Resampling.NEAREST)
        draw_s.rounded_rectangle([x0 - 1, y0 - 1, x0 + cw, y0 + ch], radius=6, outline=(70, 230, 255), width=1)
        sheet.paste(thumb, (x0, y0))
        kb = len(gif_bytes_by_emotion[emo]) / 1024.0
        draw_s.text((x0 + 4, y0 + ch + 3), f"{idx+1}.{emo} ({kb:.0f}K)", fill=(210, 230, 255))

    sheet_path = OUT_DIR / "procedural_mochi_21_preview.png"
    sheet.save(sheet_path, format="PNG", optimize=True)
    shutil.copyfile(sheet_path, ARTIFACT_DIR / "procedural_mochi_21_preview.png")
    print(f"  [PNG] 21-Panel Master Sheet: {sheet_path} ({sheet_path.stat().st_size:,d} bytes)")
    return gif_bytes_by_emotion


def pack_mmap_assets_21(gif_bytes_by_emotion: dict[str, bytes], out_bin_path: Path) -> None:
    base_bin = ROOT / "profiles/example-esp32s3-n16r8/partitions/08-assets-0xAA0000.bin"
    d_base = base_bin.read_bytes()
    nf, _, _ = struct.unpack("<III", d_base[:12])
    tend = 12 + nf * 44
    base_files = {}
    ordered_names = []
    for i in range(nf):
        ent = d_base[12 + i * 44 : 12 + (i + 1) * 44]
        name = ent[:32].split(b"\x00", 1)[0].decode("utf-8")
        sz, off, w, h = struct.unpack("<IIHH", ent[32:44])
        base_files[name] = (d_base[tend + off + 2 : tend + off + 2 + sz], w, h)
        ordered_names.append(name)

    idx_obj = json.loads(base_files["index.json"][0].decode("utf-8"))
    idx_obj["hide_subtitle"] = True
    idx_obj["skin"]["light"]["text_color"] = "#ffffff"
    idx_obj["skin"]["light"]["background_color"] = "#000000"
    idx_obj["skin"]["dark"]["text_color"] = "#ffffff"
    idx_obj["skin"]["dark"]["background_color"] = "#000000"

    file_to_emotion = {}
    for item in idx_obj["emoji_collection"]:
        emo_name = item["name"]
        fname = item["file"]
        file_to_emotion[fname] = emo_name if emo_name in gif_bytes_by_emotion else "neutral"

    if not any(e.get("name") == "robot_2" for e in idx_obj["emoji_collection"]):
        idx_obj["emoji_collection"].append({"name": "robot_2", "file": "emoji_3ec1da35.gif"})

    new_index_bytes = json.dumps(idx_obj, indent=2).encode("utf-8")
    raw_hdr = base_files["background_dark.raw"][0][:28]
    black_raw_320 = raw_hdr + (b"\x00" * (240 * 320 * 2))

    out_entries = []
    for name in ordered_names:
        if name.endswith(".gif"):
            emo = file_to_emotion.get(name, "neutral")
            out_entries.append((name, gif_bytes_by_emotion[emo], 240, 240))
        elif name == "index.json":
            out_entries.append(("index.json", new_index_bytes, 0, 0))
        elif name in ("background_dark.raw", "background_light.raw"):
            out_entries.append((name, black_raw_320, 0, 0))
        else:
            payload, w, h = base_files[name]
            out_entries.append((name, payload, w, h))

    # Preserve 0000.p3 if present in themes/shouto-mochi-fullvien-240x320.bin
    shouto_bin = ROOT / "themes/shouto-mochi-fullvien-240x320.bin"
    if shouto_bin.exists() and "0000.p3" not in ordered_names:
        ds = shouto_bin.read_bytes()
        nfs, _, _ = struct.unpack("<III", ds[:12])
        tends = 12 + nfs * 44
        for i in range(nfs):
            ent = ds[12 + i * 44 : 12 + (i + 1) * 44]
            nm = ent[:32].split(b"\x00", 1)[0].decode("utf-8")
            sz, off, w, h = struct.unpack("<IIHH", ent[32:44])
            if nm == "0000.p3":
                out_entries.append(("0000.p3", ds[tends + off + 2 : tends + off + 2 + sz], w, h))
                break

    table_buf = bytearray()
    data_buf = bytearray()
    cur_off = 0
    for name, payload, w, h in out_entries:
        name_b = name.encode("utf-8")[:31].ljust(32, b"\x00")
        table_buf += name_b + struct.pack("<IIHH", len(payload), cur_off, w, h)
        data_buf += b"ZZ" + payload
        cur_off += 2 + len(payload)

    body = bytes(table_buf + data_buf)
    checksum = sum(body) & 0xFFFF
    header = struct.pack("<III", len(out_entries), checksum, len(body))
    out_bin_path.write_bytes(header + body)
    print(f"  [BIN] Packed {out_bin_path} ({len(header) + len(body):,d} bytes, checksum=0x{checksum:04x})")


if __name__ == "__main__":
    print("=== Cooking ALL 21 Procedural Code-Drawn Mochi Emotions (240x320) ===")
    gifs = build_all_21_procedural_gifs()
    total_21 = sum(len(v) for v in gifs.values())
    print(f"  [SUM] Total for ALL 21 unique procedural emotions: {total_21:,d} bytes ({total_21/1024:.2f} KB)")
    pack_mmap_assets_21(gifs, ROOT / "themes" / "procedural-mochi-fullvien-240x320.bin")
