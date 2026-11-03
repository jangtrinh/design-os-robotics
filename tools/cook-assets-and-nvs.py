#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
Cook full-screen 240x320 esp_mmap_assets binary + HUD-enabled NVS image for RoBot.5320 (ESP32-S3 N16R8).
"""
import binascii
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_fullvien_240x320(
    base_320_path: Path,
    fullvien_240_path: Path,
    out_path: Path,
) -> None:
    d320 = base_320_path.read_bytes()
    nf320, _, _ = struct.unpack("<III", d320[:12])
    tend320 = 12 + nf320 * 44
    files320 = {}
    for i in range(nf320):
        ent = d320[12 + i * 44 : 12 + (i + 1) * 44]
        name = ent[:32].split(b"\x00", 1)[0].decode("utf-8")
        sz, off, w, h = struct.unpack("<IIHH", ent[32:44])
        files320[name] = (d320[tend320 + off + 2 : tend320 + off + 2 + sz], w, h)

    d240 = fullvien_240_path.read_bytes()
    nf240, _, _ = struct.unpack("<III", d240[:12])
    tend240 = 12 + nf240 * 44
    files240 = {}
    ordered_names = []
    for i in range(nf240):
        ent = d240[12 + i * 44 : 12 + (i + 1) * 44]
        name = ent[:32].split(b"\x00", 1)[0].decode("utf-8")
        sz, off, w, h = struct.unpack("<IIHH", ent[32:44])
        files240[name] = (d240[tend240 + off + 2 : tend240 + off + 2 + sz], w, h)
        ordered_names.append(name)

    raw_hdr = files320["background_dark.raw"][0][:28]
    black_raw_320 = raw_hdr + (b"\x00" * (240 * 320 * 2))

    idx_obj = json.loads(files320["index.json"][0].decode("utf-8"))
    idx_obj["hide_subtitle"] = True
    idx_obj["skin"]["light"]["text_color"] = "#ffffff"
    idx_obj["skin"]["light"]["background_color"] = "#000000"
    idx_obj["skin"]["dark"]["text_color"] = "#ffffff"
    idx_obj["skin"]["dark"]["background_color"] = "#000000"
    if not any(e.get("name") == "robot_2" for e in idx_obj["emoji_collection"]):
        idx_obj["emoji_collection"].append({"name": "robot_2", "file": "emoji_f6e81fd7.gif"})
    new_index_bytes = json.dumps(idx_obj, indent=2).encode("utf-8")

    out_entries = []
    for name in ordered_names:
        if name.startswith("font_"):
            out_entries.append(("font_puhui_deepseek_20_4.bin", files320["font_puhui_deepseek_20_4.bin"][0], 0, 0))
        elif name == "srmodels.bin":
            out_entries.append(("srmodels.bin", files320["srmodels.bin"][0], 0, 0))
        elif name.endswith(".gif"):
            payload, w, h = files240[name]
            out_entries.append((name, payload, w, h))
        elif name == "index.json":
            out_entries.append(("index.json", new_index_bytes, 0, 0))
        elif name in ("background_dark.raw", "background_light.raw"):
            out_entries.append((name, black_raw_320, 0, 0))

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
    out_path.write_bytes(header + body)
    print(f"Built {out_path} ({len(header) + len(body)} bytes, checksum=0x{checksum:04x})")


def patch_nvs_hud(nvs_in: Path, nvs_out: Path, p_bat: int = -1, p_chg: int = -1) -> None:
    """Patch p_bat and p_chg in NVS lcd_cfg.

    Note: On RB5320XZ78AI (2.8" TFT ST7789), the TP4056 module is wired power-only
    (OUT+/OUT- -> 5V0/GND) with NO ADC voltage divider wire to ESP32-S3 GPIO pins.
    Setting p_bat=17 reads 0V on GPIO 17 (ADC2_CH6) and permanently reports 0% battery.
    Keep p_bat=-1, p_chg=-1 unless a hardware voltage divider is soldered.
    """
    nvs = bytearray(nvs_in.read_bytes())
    for idx, key_expected, new_val in [(113, "p_bat", p_bat), (114, "p_chg", p_chg)]:
        off = 64 + idx * 32
        ent = bytearray(nvs[off : off + 32])
        key = ent[8:24].split(b"\x00", 1)[0].decode("utf-8")
        assert key == key_expected, f"Expected {key_expected}, got {key}"
        ent[24:28] = struct.pack("<i", new_val)
        crc = binascii.crc32(bytes(ent[0:4] + ent[8:32]), 0xFFFFFFFF) & 0xFFFFFFFF
        ent[4:8] = struct.pack("<I", crc)
        nvs[off : off + 32] = ent
    nvs_out.write_bytes(nvs)
    print(f"Wrote {nvs_out} ({len(nvs)} bytes, p_bat={p_bat}, p_chg={p_chg})")


if __name__ == "__main__":
    build_fullvien_240x320(
        ROOT / "themes/mochi-240x320.bin",
        ROOT / "themes/mochi-fullvien-240x240.bin",
        ROOT / "themes/mochi-fullvien-240x320.bin",
    )
    patch_nvs_hud(
        ROOT / "profiles/example-esp32s3-n16r8/partitions/03-nvs-0x009000.bin",
        ROOT / "profiles/example-esp32s3-n16r8/nvs-hud-enabled.bin",
    )
