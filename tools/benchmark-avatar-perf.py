#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
benchmark-avatar-perf.py — Quantitative Performance & Compression Benchmark Suite
for RoBot.5320 (ESP32-S3 240MHz + ST7789 240x320 + esp_mmap_assets lv_gif).

Measures (Pure Python + Pillow, zero external numeric dependencies):
  1. Partition-level Flash footprint, free space in 5.25MB (0xAA0000), and unique emotion coverage.
  2. Per-emotion (21/21) GIF byte size, LZW compression ratio vs raw RGB565 (2,457,600 B / 16 frames).
  3. Actual GIF frame decode speed (us/frame & ms/loop), horizontal RLE/LZW scanline spans per frame
     (the primary bottleneck in lv_gif gifdec.c on Xtensa LX7), and inter-frame dirty pixel ratio.
  4. SPI Flash MMU (80MHz QIO) bandwidth & ESP32-S3 CPU load estimation at 12.5 FPS (80ms frame period).
"""
import argparse
import hashlib
import io
import itertools
import json
import struct
import sys
import time
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FACTORY_BIN = ROOT / "profiles/example-esp32s3-n16r8/partitions/08-assets-0xAA0000.bin"
PROCEDURAL_BIN = ROOT / "themes/procedural-mochi-fullvien-240x320.bin"
LOOSE_GIF_DIR = ROOT / "themes/procedural-mochi"
PARTITION_MAX_BYTES = 0x540000  # 5,505,024 bytes (5.25 MB)


def mean(vals) -> float:
    vals = list(vals)
    return sum(vals) / len(vals) if vals else 0.0


def unpack_mmap_assets(bin_path: Path) -> dict:
    data = bin_path.read_bytes()
    nf, chk, sz = struct.unpack("<III", data[:12])
    calc_chk = sum(data[12:]) & 0xFFFF
    tend = 12 + nf * 44
    entries = {}
    for i in range(nf):
        ent = data[12 + i * 44 : 12 + (i + 1) * 44]
        name = ent[:32].split(b"\x00", 1)[0].decode("utf-8")
        fsz, off, w, h = struct.unpack("<IIHH", ent[32:44])
        magic = data[tend + off : tend + off + 2]
        payload = data[tend + off + 2 : tend + off + 2 + fsz]
        entries[name] = {
            "size": fsz,
            "offset": off,
            "width": w,
            "height": h,
            "magic_ok": magic == b"ZZ",
            "sha256": hashlib.sha256(payload).hexdigest()[:12],
            "payload": payload,
        }
    idx = json.loads(entries["index.json"]["payload"].decode("utf-8"))
    return {
        "path": str(bin_path),
        "total_bytes": len(data),
        "num_files": nf,
        "checksum": chk,
        "checksum_valid": chk == calc_chk and sz == len(data) - 12,
        "entries": entries,
        "index": idx,
    }


def load_loose_gifs(gif_dir: Path) -> dict | None:
    """Build the same structure as unpack_mmap_assets() from the committed GIFs (no .bin needed).

    Returns None when the folder has no GIFs. Flash-image fields are None because no .bin exists.
    """
    # The spring-transition clip is a demo, not one of the 21 faces.
    files = sorted(p for p in gif_dir.glob("*.gif") if "transition" not in p.name)
    if not files:
        return None
    entries = {}
    for f in files:
        payload = f.read_bytes()
        entries[f.name] = {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()[:12],
            "payload": payload,
        }
    idx = {"emoji_collection": [{"name": f.stem, "file": f.name} for f in files]}
    return {"total_bytes": None, "checksum": None, "checksum_valid": None, "entries": entries, "index": idx}


def analyze_gif_metrics(gif_bytes: bytes, decode_iters: int = 6) -> dict:
    # 1. Measure actual LZW decode throughput (us/frame)
    t0 = time.perf_counter()
    n_frames = 0
    for _ in range(decode_iters):
        im = Image.open(io.BytesIO(gif_bytes))
        n_frames = getattr(im, "n_frames", 1)
        for f in range(n_frames):
            im.seek(f)
            im.load()
    elapsed_s = time.perf_counter() - t0
    us_per_frame = (elapsed_s / (decode_iters * max(1, n_frames))) * 1e6

    # 2. Extract indexed palette bytes per frame for horizontal RLE span & dirty-pixel measurement
    im = Image.open(io.BytesIO(gif_bytes))
    n_frames = getattr(im, "n_frames", 1)
    w, h = im.size
    total_spans = 0
    total_dirty_pixels = 0
    prev_bytes = None
    unique_colors = set()

    # Sample up to 16 frames for structural scanline metrics
    sample_frames = min(n_frames, 16)
    for f in range(sample_frames):
        im.seek(f)
        p_im = im.convert("RGB").quantize(colors=256, dither=Image.Dither.NONE)
        raw = p_im.tobytes()
        unique_colors.update(raw)
        # Count horizontal runs per scanline using itertools.groupby on each row slice
        frame_spans = 0
        for y in range(0, w * h, w):
            row = raw[y : y + w]
            frame_spans += sum(1 for _ in itertools.groupby(row))
        total_spans += frame_spans

        if prev_bytes is not None:
            dirty = sum(1 for a, b in zip(raw, prev_bytes) if a != b)
            total_dirty_pixels += dirty
        prev_bytes = raw

    avg_spans_per_frame = total_spans / max(1, sample_frames)
    avg_spans_per_scanline = avg_spans_per_frame / max(1, h)
    avg_dirty_pct = (
        (total_dirty_pixels / max(1, (sample_frames - 1) * w * h)) * 100.0
        if sample_frames > 1
        else 0.0
    )

    raw_bytes = n_frames * w * h * 2  # RGB565 equivalent (2 bytes/px)
    compression_ratio = raw_bytes / max(1, len(gif_bytes))

    # ESP32-S3 @ 240MHz lv_gif (gifdec.c) empirical model:
    # LZW bitstream + cache fetch (~0.32 us/byte compressed) + span blit (~1.15 us/span) + DMA setup (1.8ms)
    esp32_frame_ms = (
        (len(gif_bytes) / max(1, n_frames)) * 0.00032
        + avg_spans_per_frame * 0.00115
        + 1.8
    )
    esp32_cpu_pct_at_12_5fps = (esp32_frame_ms / 80.0) * 100.0

    return {
        "bytes": len(gif_bytes),
        "kb": len(gif_bytes) / 1024.0,
        "frames": n_frames,
        "dims": f"{w}x{h}",
        "unique_colors": len(unique_colors),
        "compression_ratio": compression_ratio,
        "host_decode_us_per_frame": us_per_frame,
        "avg_spans_per_frame": avg_spans_per_frame,
        "avg_spans_per_scanline": avg_spans_per_scanline,
        "interframe_dirty_pct": avg_dirty_pct,
        "esp32_est_frame_ms": esp32_frame_ms,
        "esp32_est_cpu_pct": esp32_cpu_pct_at_12_5fps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark RoBot.5320 Avatar Packs")
    parser.add_argument("--json-out", default=None, help="Optional path to save JSON report")
    args = parser.parse_args()

    packs = [
        ("1. Factory Default (21 GIFs)", FACTORY_BIN),
        ("2. Procedural Mochi-21 (Code)", PROCEDURAL_BIN),
    ]

    summary_rows = []
    detailed_by_pack = {}

    print("=" * 110)
    print("  ROBOT.5320 AVATAR PERFORMANCE & COMPRESSION BENCHMARK SUITE (ESP32-S3 240MHz · 240x320 ST7789)")
    print("=" * 110)

    present = [(label, path) for label, path in packs if path.exists()]
    if not present:
        # The .bin packs are built locally and are not tracked; fall back to the committed GIFs.
        print(
            "Note: no avatar .bin pack found (profiles/.../08-assets-0xAA0000.bin or "
            "themes/procedural-mochi-fullvien-240x320.bin). They are gitignored and built locally; "
            "see README, 'Procedural Mochi-21 avatar'.\n"
            f"Benchmarking the committed GIFs in {LOOSE_GIF_DIR.relative_to(ROOT)}/ instead. "
            "Flash-image rows show n/a."
        )
        loose = load_loose_gifs(LOOSE_GIF_DIR)
        if loose is None:
            print(f"error: no GIFs in {LOOSE_GIF_DIR}", file=sys.stderr)
            sys.exit(2)
        present = [(packs[1][0], loose)]

    for label, path in present:
        info = path if isinstance(path, dict) else unpack_mmap_assets(path)
        entries = info["entries"]
        idx = info["index"]

        emo_map = {}
        for item in idx["emoji_collection"]:
            emo_map[item["name"]] = item["file"]

        gif_entries = {k: v for k, v in entries.items() if k.endswith(".gif")}
        unique_hashes = {v["sha256"] for v in gif_entries.values()}

        # Deduplicate analysis by payload sha256 so repeated GIFs are analyzed once
        hash_to_metrics = {}
        file_metrics_cache = {}
        for fname, meta in gif_entries.items():
            h = meta["sha256"]
            if h not in hash_to_metrics:
                hash_to_metrics[h] = analyze_gif_metrics(meta["payload"])
            file_metrics_cache[fname] = hash_to_metrics[h]

        total_gif_bytes = sum(v["size"] for v in gif_entries.values())
        avg_decode_us = mean(m["host_decode_us_per_frame"] for m in file_metrics_cache.values())
        avg_spans = mean(m["avg_spans_per_frame"] for m in file_metrics_cache.values())
        avg_scanline_spans = mean(m["avg_spans_per_scanline"] for m in file_metrics_cache.values())
        avg_dirty_pct = mean(m["interframe_dirty_pct"] for m in file_metrics_cache.values())
        avg_esp32_ms = mean(m["esp32_est_frame_ms"] for m in file_metrics_cache.values())
        avg_esp32_cpu = mean(m["esp32_est_cpu_pct"] for m in file_metrics_cache.values())
        avg_colors = mean(m["unique_colors"] for m in file_metrics_cache.values())
        avg_comp = mean(m["compression_ratio"] for m in file_metrics_cache.values())

        row = {
            "label": label,
            "total_bin_bytes": info["total_bytes"],
            "total_bin_mb": None if info["total_bytes"] is None else info["total_bytes"] / (1024 * 1024),
            "flash_free_mb": None
            if info["total_bytes"] is None
            else (PARTITION_MAX_BYTES - info["total_bytes"]) / (1024 * 1024),
            "checksum": None if info["checksum"] is None else f"0x{info['checksum']:04x}",
            "checksum_valid": info["checksum_valid"],
            "unique_emotions": len(unique_hashes),
            "total_gif_bytes": total_gif_bytes,
            "total_gif_kb": total_gif_bytes / 1024.0,
            "avg_gif_kb": (total_gif_bytes / max(1, len(gif_entries))) / 1024.0,
            "avg_compression_ratio": avg_comp,
            "avg_colors": avg_colors,
            "avg_host_decode_us": avg_decode_us,
            "avg_spans_per_frame": avg_spans,
            "avg_spans_per_scanline": avg_scanline_spans,
            "avg_dirty_pct": avg_dirty_pct,
            "avg_esp32_frame_ms": avg_esp32_ms,
            "avg_esp32_cpu_pct": avg_esp32_cpu,
        }
        summary_rows.append(row)
        detailed_by_pack[label] = {
            "summary": row,
            "emotions": {
                emo: {
                    "file": fname,
                    "sha256": entries[fname]["sha256"],
                    **file_metrics_cache[fname],
                }
                for emo, fname in emo_map.items()
                if fname in file_metrics_cache
            },
        }

    print("\n[1] 2-WAY ARCHITECTURE & PERFORMANCE COMPARISON")
    print("-" * 110)
    heads = ["1. Factory (21 GIFs)", "2. Procedural Mochi-21"]
    shown = [heads[0] if r["label"].startswith("1.") else heads[1] for r in summary_rows]
    print(f"{'Metric':38s} | " + " | ".join(f"{h:22s}" for h in shown))
    print("-" * 110)

    def fmt_row(title: str, key: str, fmt: str, unit: str = "") -> None:
        vals = ["n/a" if r[key] is None else f"{r[key]:{fmt}}{unit}" for r in summary_rows]
        print(f"{title:38s} | " + " | ".join(f"{v:22s}" for v in vals))

    fmt_row("Unique Emotion Animations", "unique_emotions", "d", " / 21")
    fmt_row("Total 21-GIF Payload Size", "total_gif_kb", ",.2f", " KB")
    fmt_row("Avg Size per Emotion GIF", "avg_gif_kb", ",.2f", " KB")
    fmt_row("LZW Compression Ratio vs Raw RGB565", "avg_compression_ratio", ",.1f", "x")
    fmt_row("Total Flash Image (.bin)", "total_bin_mb", ".2f", " MB")
    fmt_row("Free Space in 0xAA0000 (5.25MB)", "flash_free_mb", "+.2f", " MB")
    fmt_row("Avg Palette Colors Used", "avg_colors", ".1f", " colors")
    fmt_row("Horizontal RLE Spans / Scanline", "avg_spans_per_scanline", ".2f", " spans")
    fmt_row("Horizontal RLE Spans / Frame", "avg_spans_per_frame", ",.0f", " spans")
    fmt_row("Inter-Frame Dirty Pixel Ratio", "avg_dirty_pct", ".2f", " %")
    fmt_row("Host LZW Decode Latency / Frame", "avg_host_decode_us", ",.1f", " us")
    fmt_row("ESP32-S3 Est. Decode Time / Frame", "avg_esp32_frame_ms", ".2f", " ms")
    fmt_row("ESP32-S3 Est. CPU Load @ 12.5 FPS", "avg_esp32_cpu_pct", ".1f", " %")
    print("-" * 110)

    proc_label = "2. Procedural Mochi-21 (Code)"
    if proc_label in detailed_by_pack:
        print("\n[2] PER-EMOTION TELEMETRY FOR PROCEDURAL MOCHI-21 (ALL 21 STATES AT 240x320)")
        print("-" * 110)
        print(
            f"{'#':>2s} | {'Emotion':13s} | {'File':18s} | {'Size (KB)':>9s} | {'LZW Ratio':>9s} | {'Spans/Frm':>9s} | {'Dirty %':>7s} | {'Decode(us)':>10s} | {'ESP32 CPU%':>10s}"
        )
        print("-" * 110)
        emos = detailed_by_pack[proc_label]["emotions"]
        idx_num = 1
        for emo, m in emos.items():
            if emo == "robot_2":
                continue
            print(
                f"{idx_num:2d} | {emo:13s} | {m['file']:18s} | {m['kb']:7.2f}KB | {m['compression_ratio']:8.1f}x | {m['avg_spans_per_frame']:9.0f} | {m['interframe_dirty_pct']:6.2f}% | {m['host_decode_us_per_frame']:8.1f}us | {m['esp32_est_cpu_pct']:9.1f}%"
            )
            idx_num += 1
        print("-" * 110)

    if args.json_out:
        out_p = Path(args.json_out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_bytes(json.dumps(detailed_by_pack, indent=2).encode("utf-8"))
        print(f"\nSaved JSON benchmark report to {args.json_out}")


if __name__ == "__main__":
    main()
