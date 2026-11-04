#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
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

import argparse
import hashlib
import importlib.util
import io
import json
import os
import shutil
import struct
import sys
from pathlib import Path
from typing import Any, NamedTuple

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "themes" / "procedural-mochi"
ARTIFACT_DIR = Path(os.environ["ARTIFACT_DIR"]) if os.environ.get("ARTIFACT_DIR") else None


class Morph(NamedTuple):
    stage: int = 1
    eye_q: float = 1.0
    catch: int = 1
    blush_q: float = 1.0
    brackets: bool = False
    star: bool = False

    @property
    def is_identity(self) -> bool:
        return (
            self.stage == 1
            and self.eye_q == 1.0
            and self.catch == 1
            and self.blush_q == 1.0
            and not self.brackets
            and not self.star
        )


IDENTITY_MORPH = Morph()


def _load_soul_engine() -> Any:
    p = ROOT / "tools" / "mochi-soul-engine" / "engine.py"
    spec = importlib.util.spec_from_file_location("mochi_soul_engine", p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load soul engine from {p}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def morph_from_stage_and_genome(stage: int, genome_dict: dict[str, Any] | None = None) -> tuple[Morph, dict[str, Any]]:
    eng = _load_soul_engine()
    params = eng.phenotype_params(stage=stage, genome=genome_dict or {}, quantize=True)
    morph = Morph(
        stage=int(params["stage"]),
        eye_q=float(params["eye_q"]),
        catch=int(params["catch"]),
        blush_q=float(params["blush_q"]),
        brackets=bool(params["brackets"]),
        star=bool(params["star"]),
    )
    return morph, params

def _load_canonical_vectors() -> Any:
    if "mochi_canonical_vectors" in sys.modules:
        return sys.modules["mochi_canonical_vectors"]
    p = ROOT / "tools" / "mochi_canonical_vectors.py"
    spec = importlib.util.spec_from_file_location("mochi_canonical_vectors", p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load canonical vectors from {p}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_VEC_MOD = _load_canonical_vectors()

# 8-Color Canonical Mochi Anime Indexed Palette (24 bytes = 8 RGB triplets -> 3-bit LZW Global Color Table)
#   0: #000000 Pure Black        (Background & Eyelid/Mouth Cutouts)
#   1: #EAFCFF Crisp Mochi White (Primary Eyes, Brows, Mouth, Teeth & Visor)
#   2: #B8E6F8 Mochi Ice-Blue    (Eye Bottom Shading, Tears, Sweat, Smoke & Rain)
#   3: #E080E4 Mochi Orchid-Pink (Cheek Blushes, Floating Hearts & Tongue Highlights)
#   4: #EEE46E Mochi Bee Gold    (Flying Bee Body, Stars, Sparkles & Yellow-Green Gradient)
#   5: #E6312E Mochi Bright Red  (3D Heart Eyes, Open Mouth Tongue & Subway Ring)
#   6: #7644A8 Mochi Deep Violet (Rage Flames, Blush Upper Rim, Gloom Lines & Visor Trim)
#   7: #4C1A24 Mochi Dark Maroon (Inner Mouth Cavity & Textured Tongue Shadow)
PALETTE: list[int] = list(_VEC_MOD.MOCHI_PALETTE_8)

ALL_21_EMOTIONS = [
    "neutral", "happy", "laughing", "funny", "sad",
    "angry", "crying", "loving", "embarrassed", "surprised",
    "shocked", "thinking", "winking", "cool", "relaxed",
    "delicious", "kissy", "confident", "sleepy", "silly",
    "confused",
]

POSTER_FRAME_IDX: dict[str, int] = {
    "relaxed": 1,
    "delicious": 1,
    "thinking": 2,
    "winking": 2,
    "surprised": 3,
}


def draw_star(d: ImageDraw.ImageDraw, cx: int, cy: int, r_out: int, color: int = 4) -> None:
    r_in = max(1, r_out // 3)
    pts = [
        (cx, cy - r_out), (cx + r_in, cy - r_in),
        (cx + r_out, cy), (cx + r_in, cy + r_in),
        (cx, cy + r_out), (cx - r_in, cy + r_in),
        (cx - r_out, cy), (cx - r_in, cy - r_in),
    ]
    d.polygon(pts, fill=color)


def render_emotion_frame(
    emotion: str,
    frame_idx: int,
    num_frames: int = 10,
    w: int = 240,
    h: int = 320,
    morph: Morph = IDENTITY_MORPH,
) -> Image.Image:
    """Render a 240x240 indexed-palette frame for `emotion` from the 100% authentic Mochi scanline vectors."""
    _ = (w, h)
    all_vecs = _VEC_MOD.decode_all_emotion_scanlines()
    emo_frames = all_vecs.get(emotion) or all_vecs["neutral"]
    total_src = len(emo_frames)
    if num_frames <= 1 or num_frames == total_src:
        src_idx = frame_idx % total_src
    else:
        src_idx = int(round((frame_idx % num_frames) * (total_src - 1) / float(num_frames - 1))) % total_src

    spans = emo_frames[src_idx]
    out_w, out_h = 240, 240
    y_off = (out_h - int(_VEC_MOD.FACE_SRC_H)) // 2
    buf = bytearray(out_w * out_h)

    blush_pad = 0
    if not morph.is_identity and morph.blush_q != 1.0:
        blush_pad = max(-4, min(6, round((morph.blush_q - 1.0) * 12.0)))
    eye_thicken = (not morph.is_identity) and (morph.eye_q != 1.0)

    for y_src, x0, span_w, color in spans:
        ry = y_src + y_off
        if ry < 0 or ry >= out_h:
            continue
        nx0 = x0
        nx1 = min(out_w, x0 + span_w)
        if blush_pad != 0 and color == 3 and 55 <= y_src <= 125 and (x0 < 85 or nx1 > 155):
            nx0 = max(0, nx0 - blush_pad)
            nx1 = min(out_w, nx1 + blush_pad)
        if nx1 <= nx0:
            continue
        row_base = ry * out_w
        span_len = nx1 - nx0
        buf[row_base + nx0 : row_base + nx1] = bytes([color]) * span_len
        if eye_thicken and color in (1, 2) and 34 <= y_src <= 104 and ry > 0:
            up_base = (ry - 1) * out_w
            for x_pos in range(nx0, nx1):
                if buf[up_base + x_pos] == 0:
                    buf[up_base + x_pos] = color

    img = Image.frombytes("P", (out_w, out_h), bytes(buf))
    img.putpalette(PALETTE)

    if not morph.is_identity:
        d = ImageDraw.Draw(img)
        if morph.catch >= 2:
            for y_src, x0, span_w, color in spans:
                if color == 2 and span_w >= 14 and 38 <= y_src <= 92:
                    gx = x0 + 4 + (src_idx % 2)
                    gy = y_off + y_src - 2
                    if 0 <= gx < out_w - 2 and 0 <= gy < out_h - 2:
                        d.rectangle([gx, gy, gx + 1, gy + 1], fill=1)
                    break
        if morph.brackets:
            bx0, by0, bx1, by1 = 6, y_off - 4, 233, y_off + int(_VEC_MOD.FACE_SRC_H) + 3
            arm = 9
            for sx, sy, dx, dy in (
                (bx0, by0, arm, arm),
                (bx1, by0, -arm, arm),
                (bx0, by1, arm, -arm),
                (bx1, by1, -arm, -arm),
            ):
                d.line([(sx, sy), (sx + dx, sy)], fill=2, width=2)
                d.line([(sx, sy), (sx, sy + dy)], fill=2, width=2)
        if morph.star:
            draw_star(d, 222, y_off + 8 + (src_idx % 3), 5 + (src_idx % 2), color=4)

    return img


def build_all_21_procedural_gifs(
    morph: Morph = IDENTITY_MORPH,
    out_dir: Path | None = None,
    write_files: bool = True,
    quiet: bool = False,
) -> dict[str, bytes]:
    target_dir = out_dir if out_dir is not None else OUT_DIR
    if write_files:
        target_dir.mkdir(parents=True, exist_ok=True)
        if ARTIFACT_DIR:
            ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    gif_bytes_by_emotion: dict[str, bytes] = {}
    poster_frames: dict[str, Image.Image] = {}

    for emo in ALL_21_EMOTIONS:
        raw_frames = [render_emotion_frame(emo, i, num_frames=10, morph=morph) for i in range(10)]
        p_idx = POSTER_FRAME_IDX.get(emo, 3)
        poster_frames[emo] = raw_frames[p_idx].convert("RGB")
        dedup_frames: list[Image.Image] = []
        durations: list[int] = []
        prev_bytes: bytes | None = None
        for frm in raw_frames:
            fb = frm.tobytes()
            if fb == prev_bytes and durations:
                durations[-1] += 80
            else:
                dedup_frames.append(frm)
                durations.append(80)
                prev_bytes = fb
        if len(dedup_frames) == 1:
            dedup_frames.append(dedup_frames[0].copy())
            durations = [400, 400]
        buf = io.BytesIO()
        dedup_frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=dedup_frames[1:],
            duration=durations,
            loop=0,
            optimize=False,
        )
        raw = buf.getvalue()
        gif_bytes_by_emotion[emo] = raw
        if write_files:
            out_file = target_dir / f"{emo}.gif"
            out_file.write_bytes(raw)
            if ARTIFACT_DIR:
                shutil.copyfile(out_file, ARTIFACT_DIR / f"procedural_{emo}.gif")
            if not quiet:
                print(f"  [GIF] {emo:13s}: {len(raw):6,d} bytes ({len(raw)/1024:5.2f} KB) -> {out_file.name}")

    if write_files:
        # Build 21-panel Master Contact Sheet (7 cols x 3 rows, scaled 50% per cell -> 120x120 each)
        cw, ch = 120, 120
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

        sheet_path = target_dir / "procedural_mochi_21_preview.png"
        sheet.save(sheet_path, format="PNG", optimize=True)
        if ARTIFACT_DIR:
            shutil.copyfile(sheet_path, ARTIFACT_DIR / "procedural_mochi_21_preview.png")
        docs_mochi_dir = ROOT / "docs" / "assets" / "mochi"
        if target_dir.resolve() == OUT_DIR.resolve() and docs_mochi_dir.is_dir():
            shutil.copyfile(sheet_path, docs_mochi_dir / "procedural_mochi_21_preview.png")
            for doc_emo in ("angry", "cool", "happy", "loving", "neutral", "shocked", "sleepy", "thinking"):
                src_gif = target_dir / f"{doc_emo}.gif"
                if src_gif.is_file():
                    shutil.copyfile(src_gif, docs_mochi_dir / f"{doc_emo}.gif")
        if not quiet:
            print(f"  [PNG] 21-Panel Master Sheet: {sheet_path} ({sheet_path.stat().st_size:,d} bytes)")
    return gif_bytes_by_emotion


DEFAULT_WAKE_COMMANDS = [
    {"command": "HEY J", "text": "Hey J", "action": "wake"},
    {"command": "HEY JAY", "text": "Hey J", "action": "wake"},
    {"command": "HELLO J", "text": "Hello J", "action": "wake"},
    {"command": "HELLO JAY", "text": "Hello J", "action": "wake"},
    {"command": "HI J", "text": "Hi J", "action": "wake"},
    {"command": "HI JAY", "text": "Hi J", "action": "wake"},
]


def compute_mmap_assets_21_bytes(
    gif_bytes_by_emotion: dict[str, bytes],
    base_bin: Path,
    srmodels_bin: Path | None = None,
    dedup_identical: bool = False,
    quiet: bool = False,
) -> tuple[bytes, int]:
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

    if srmodels_bin is None:
        for candidate in (
            base_bin.parent.parent / "unpacked-assets" / "srmodels_mn6_en.bin",
            ROOT / "unpacked-assets" / "srmodels_mn6_en.bin",
        ):
            if candidate.is_file():
                srmodels_bin = candidate
                break

    idx_obj = json.loads(base_files["index.json"][0].decode("utf-8"))
    idx_obj["hide_subtitle"] = True
    idx_obj["skin"]["light"]["text_color"] = "#ffffff"
    idx_obj["skin"]["light"]["background_color"] = "#000000"
    idx_obj["skin"]["dark"]["text_color"] = "#ffffff"
    idx_obj["skin"]["dark"]["background_color"] = "#000000"

    if srmodels_bin is not None and srmodels_bin.is_file():
        srmodels_payload = srmodels_bin.read_bytes()
        idx_obj["multinet_model"] = {
            "language": "en",
            "duration": 3000,
            "threshold": 0.45,
            "commands": DEFAULT_WAKE_COMMANDS,
        }
        if not quiet:
            print(
                f"  [SR]  Embedded MultiNet6 English wake model from {srmodels_bin.name} "
                f"({len(srmodels_payload):,d} bytes, commands={[c['command'] for c in DEFAULT_WAKE_COMMANDS]})"
            )
    else:
        srmodels_payload = base_files["srmodels.bin"][0]

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
        elif name == "srmodels.bin":
            out_entries.append(("srmodels.bin", srmodels_payload, 0, 0))
        elif name in ("background_dark.raw", "background_light.raw"):
            out_entries.append((name, black_raw_320, 0, 0))
        else:
            payload, w, h = base_files[name]
            out_entries.append((name, payload, w, h))

    # Preserve 0000.p3 if present in existing procedural theme binary
    prev_bin = ROOT / "themes/procedural-mochi-fullvien-240x320.bin"
    if prev_bin.exists() and "0000.p3" not in ordered_names:
        ds = prev_bin.read_bytes()
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
    seen_offsets: dict[bytes, int] = {}
    for name, payload, w, h in out_entries:
        name_b = name.encode("utf-8")[:31].ljust(32, b"\x00")
        if dedup_identical:
            digest = hashlib.sha1(payload).digest()
            if digest in seen_offsets:
                table_buf += name_b + struct.pack("<IIHH", len(payload), seen_offsets[digest], w, h)
                continue
            seen_offsets[digest] = cur_off
        table_buf += name_b + struct.pack("<IIHH", len(payload), cur_off, w, h)
        data_buf += b"ZZ" + payload
        cur_off += 2 + len(payload)

    body = bytes(table_buf + data_buf)
    checksum = sum(body) & 0xFFFF
    header = struct.pack("<III", len(out_entries), checksum, len(body))
    return header + body, checksum


def pack_mmap_assets_21(
    gif_bytes_by_emotion: dict[str, bytes],
    out_bin_path: Path,
    base_bin: Path,
    srmodels_bin: Path | None = None,
    dedup_identical: bool = False,
) -> tuple[int, int]:
    full_bytes, checksum = compute_mmap_assets_21_bytes(
        gif_bytes_by_emotion,
        base_bin,
        srmodels_bin=srmodels_bin,
        dedup_identical=dedup_identical,
    )
    out_bin_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_bin_path.with_suffix(out_bin_path.suffix + ".tmp")
    tmp_path.write_bytes(full_bytes)
    os.replace(tmp_path, out_bin_path)
    print(f"  [BIN] Packed {out_bin_path} ({len(full_bytes):,d} bytes, checksum=0x{checksum:04x})")
    return len(full_bytes), checksum


def _load_genome_arg(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    if raw == "-":
        data = json.loads(sys.stdin.read() or "{}")
    else:
        p = Path(raw)
        data = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else json.loads(raw)
    if isinstance(data, dict) and isinstance(data.get("genome"), dict):
        return dict(data["genome"])
    return dict(data) if isinstance(data, dict) else {}


def _degrade_steps(morph: Morph) -> list[tuple[str, Morph]]:
    steps: list[tuple[str, Morph]] = []
    cur = morph
    if cur.star:
        cur = cur._replace(star=False)
        steps.append(("star->False", cur))
    if cur.brackets:
        cur = cur._replace(brackets=False)
        steps.append(("brackets->False", cur))
    if cur.blush_q != 1.0:
        cur = cur._replace(blush_q=1.0)
        steps.append(("blush_q->1.0", cur))
    if cur.eye_q != 1.0:
        cur = cur._replace(eye_q=1.0)
        steps.append(("eye_q->1.0", cur))
    if cur.catch != 1:
        cur = cur._replace(catch=1)
        steps.append(("catch->1", cur))
    return steps


DEFAULT_BASE_BIN = ROOT / "profiles/example-esp32s3-n16r8/partitions/08-assets-0xAA0000.bin"


def _resolve_base_bin(base_bin: Path) -> Path:
    if base_bin.is_file():
        return base_bin
    if base_bin != DEFAULT_BASE_BIN:
        return base_bin
    candidates: list[Path] = []
    env_prof = os.environ.get("ROBOT_PROFILE_DIR", "").strip()
    if env_prof:
        candidates.append(Path(env_prof) / "partitions" / "08-assets-0xAA0000.bin")
    candidates.extend(sorted((ROOT / "profiles").glob("robot-*/partitions/08-assets-0xAA0000.bin")))
    candidates.append(ROOT / "themes" / "procedural-mochi-fullvien-240x320.bin")
    for cand in candidates:
        if cand.is_file():
            return cand
    return base_bin


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Synthesize the 21 procedural Mochi GIFs into themes/procedural-mochi/ and pack "
        "themes/procedural-mochi-fullvien-240x320.bin (local build output, not tracked). "
        "Set ARTIFACT_DIR to also copy the GIFs and contact sheet to another folder.",
    )
    ap.add_argument(
        "--base-bin",
        type=Path,
        default=DEFAULT_BASE_BIN,
        help="your own dump of the device assets partition (read only; not shipped in this repo)",
    )
    ap.add_argument(
        "--srmodels-bin",
        type=Path,
        default=None,
        help="optional MultiNet srmodels.bin override (auto-detects unpacked-assets/srmodels_mn6_en.bin when present)",
    )
    ap.add_argument(
        "--stage",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        help="optional evolutionary stage (1=Mochi Spore, 2=Mochi Sprout, 3=Mochi Companion, 4=Cyber-Mochi Spirit)",
    )
    ap.add_argument(
        "--genome-json",
        type=str,
        default=None,
        help="optional path to genome JSON file, '-' for stdin, or inline JSON string",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="override output directory for the 21 GIFs and preview sheet",
    )
    ap.add_argument(
        "--out-bin",
        type=Path,
        default=None,
        help="override output path for the packed esp_mmap_assets .bin",
    )
    ap.add_argument(
        "--partition-bytes",
        type=int,
        default=5_636_096,
        help="0xAA0000 assets partition byte size (default: 5,636,096)",
    )
    ap.add_argument(
        "--reserve-bytes",
        type=int,
        default=16_384,
        help="mandatory safety reserve inside the assets partition (default: 16,384)",
    )
    ap.add_argument(
        "--budget-only",
        action="store_true",
        help="verify GIF + mmap partition budget without writing the output .bin",
    )
    ap.add_argument(
        "--dedup-identical",
        action="store_true",
        help="deduplicate identical GIF payloads in the mmap assets data table",
    )
    args = ap.parse_args()
    args.base_bin = _resolve_base_bin(args.base_bin)
    if not args.base_bin.is_file():
        print(f"error: base assets dump not found: {args.base_bin}", file=sys.stderr)
        return 2

    evo_mode = args.stage is not None or args.genome_json is not None
    genome_dict = _load_genome_arg(args.genome_json)
    stage_val = int(args.stage) if args.stage is not None else int(genome_dict.get("stage", 1))
    if evo_mode:
        morph, phenotype_manifest = morph_from_stage_and_genome(stage_val, genome_dict)
        phash = str(phenotype_manifest["hash"])
        out_dir = args.out_dir or (ROOT / "themes" / "procedural-mochi-evo" / f"s{morph.stage}-{phash}")
        out_bin = args.out_bin or (ROOT / "themes" / f"procedural-mochi-evo-s{morph.stage}-{phash}.bin")
    else:
        morph = IDENTITY_MORPH
        phenotype_manifest = {
            "stage": 1,
            "stage_name": "Mochi Spore",
            "eye_scale": 1.0,
            "catchlights": 1,
            "blush_width_scale": 1.0,
            "cyber_brackets": False,
            "star_glint": False,
            "hash": "identity",
        }
        out_dir = args.out_dir or OUT_DIR
        out_bin = args.out_bin or (ROOT / "themes" / "procedural-mochi-fullvien-240x320.bin")

    max_bytes = int(args.partition_bytes) - int(args.reserve_bytes)
    write_gifs = not args.budget_only or (args.out_dir is not None) or evo_mode
    print(
        f"=== Cooking ALL 21 Procedural Code-Drawn Mochi Emotions (240x320, stage={morph.stage}, "
        f"hash={phenotype_manifest['hash']}) ==="
    )
    gifs = build_all_21_procedural_gifs(morph=morph, out_dir=out_dir, write_files=write_gifs)
    total_21 = sum(len(v) for v in gifs.values())
    print(f"  [SUM] Total for ALL 21 unique procedural emotions: {total_21:,d} bytes ({total_21/1024:.2f} KB)")

    full_bytes, checksum = compute_mmap_assets_21_bytes(
        gifs,
        args.base_bin,
        srmodels_bin=args.srmodels_bin,
        dedup_identical=args.dedup_identical,
    )
    degraded_steps_applied: list[str] = []
    if len(full_bytes) > max_bytes:
        for step_label, next_morph in _degrade_steps(morph):
            print(
                f"  [BUDGET] {len(full_bytes):,d} B > max {max_bytes:,d} B; degrading {step_label} ...",
                file=sys.stderr,
            )
            degraded_steps_applied.append(step_label)
            morph = next_morph
            gifs = build_all_21_procedural_gifs(morph=morph, out_dir=out_dir, write_files=write_gifs, quiet=True)
            full_bytes, checksum = compute_mmap_assets_21_bytes(
                gifs,
                args.base_bin,
                srmodels_bin=args.srmodels_bin,
                dedup_identical=args.dedup_identical,
                quiet=True,
            )
            if len(full_bytes) <= max_bytes:
                break

    total_bin = len(full_bytes)
    headroom = max_bytes - total_bin
    print(
        f"  [BUDGET] total_bin={total_bin:,d} B | max_allowed={max_bytes:,d} B "
        f"(partition={args.partition_bytes:,d} B, reserve={args.reserve_bytes:,d} B) | "
        f"headroom={headroom:+,d} B | degraded={degraded_steps_applied}"
    )

    if evo_mode and write_gifs:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_out = dict(phenotype_manifest)
        manifest_out["total_21_gif_bytes"] = sum(len(v) for v in gifs.values())
        manifest_out["total_bin_bytes"] = total_bin
        manifest_out["max_allowed_bytes"] = max_bytes
        manifest_out["degraded_steps"] = degraded_steps_applied
        (out_dir / "phenotype.json").write_text(json.dumps(manifest_out, indent=2) + "\n", encoding="utf-8")

    if total_bin > max_bytes:
        print(
            f"error: packed binary ({total_bin:,d} B) exceeds partition budget ({max_bytes:,d} B) "
            f"even after full degradation ({degraded_steps_applied}); refusing to write {out_bin}",
            file=sys.stderr,
        )
        return 3

    if args.budget_only:
        return 0

    out_bin.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_bin.with_suffix(out_bin.suffix + ".tmp")
    tmp_path.write_bytes(full_bytes)
    os.replace(tmp_path, out_bin)
    print(f"  [BIN] Packed {out_bin} ({total_bin:,d} bytes, checksum=0x{checksum:04x})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
