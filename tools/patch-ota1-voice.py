#!/usr/bin/env python3
"""
Synthesize Vietnamese on-device voice prompts + wake-up responses using ElevenLabs Custom Voice
(`<ELEVENLABS_VOICE_ID>`, `eleven_v4`, `language_code="vi"`), encode them into the exact
XiaoZhi Ogg Opus format (`24 kHz`, mono, `16 kbps`, `frame_duration=60ms`, `OpusHead` + `k\\x83`),
and patch them into `07-ota1-v2.5.3-0x560000.bin` (`Seg 0` `0x02efc4..0x04aefd` + `Seg 3`
literal pool `0x102b98..0x102da0`) with recalculated ESP-IDF XOR checksum & SHA256 digest.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG_OTA1 = ROOT / "profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-0x560000.bin"
OUT_OTA1 = ROOT / "profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-custom-voice.bin"
CACHE_DIR = ROOT / "voices/ota1-vi-ogg"

VOICE_ID = "<ELEVENLABS_VOICE_ID>"
MODEL_ID = "eleven_v4"

# Exact literal pool offsets (file offsets in 07-ota1-v2.5.3-0x560000.bin) for all 38 OggS streams:
# Each entry is (ogg_index, start_lit_foff, end_lit_foff, slug, vietnamese_text_or_None)
OGG_SLOTS_38: list[tuple[int, int, int, str, str | None]] = [
    ( 0, 0x102b98, 0x102d24, "en_0",            None),
    ( 1, 0x102b9c, 0x102d28, "en_1",            None),
    ( 2, 0x102ba0, 0x102d2c, "en_2",            None),
    ( 3, 0x102ba4, 0x102d30, "en_3",            None),
    ( 4, 0x102ba8, 0x102d34, "en_4",            None),
    ( 5, 0x102bac, 0x102d38, "en_5",            None),
    ( 6, 0x102bb0, 0x102d3c, "en_6",            None),
    ( 7, 0x102bb4, 0x102d40, "en_7",            None),
    ( 8, 0x102bb8, 0x102d44, "en_8",            None),
    ( 9, 0x102bbc, 0x102d48, "en_9",            None),
    (10, 0x102bc0, 0x102d4c, "en_activation",   None),
    (11, 0x102bc4, 0x102d50, "en_err_pin",      None),
    (12, 0x102bc8, 0x102d54, "en_err_reg",      None),
    (13, 0x102bcc, 0x102d58, "en_upgrade",      None),
    (14, 0x102bd0, 0x102d5c, "en_welcome",      None),
    (15, 0x102bd4, 0x102d60, "en_wificonfig",   None),
    # Vietnamese voice prompts (Ogg[16..31]) -> Synthesized with ElevenLabs Custom Voice (vi)
    (16, 0x102cb4, 0x102d64, "vi_0",            "Không."),
    (17, 0x102cb8, 0x102d68, "vi_1",            "Một."),
    (18, 0x102cbc, 0x102d6c, "vi_2",            "Hai."),
    (19, 0x102cc0, 0x102d70, "vi_3",            "Ba."),
    (20, 0x102cc4, 0x102d74, "vi_4",            "Bốn."),
    (21, 0x102cc8, 0x102d78, "vi_5",            "Năm."),
    (22, 0x102ccc, 0x102d7c, "vi_6",            "Sáu."),
    (23, 0x102cd0, 0x102d80, "vi_7",            "Bảy."),
    (24, 0x102cd4, 0x102d84, "vi_8",            "Tám."),
    (25, 0x102cd8, 0x102d88, "vi_9",            "Chín."),
    (26, 0x102cdc, 0x102d8c, "vi_activation",   "Vui lòng đăng nhập trang quản trị để kích hoạt thiết bị."),
    (27, 0x102ce0, 0x102d90, "vi_err_pin",      "Không tìm thấy thẻ SIM, vui lòng kiểm tra lại."),
    (28, 0x102ce4, 0x102d94, "vi_err_reg",      "Không thể đăng ký mạng, vui lòng kiểm tra tín hiệu."),
    (29, 0x102ce8, 0x102d98, "vi_upgrade",      "Hệ thống đang nâng cấp, J đợi mình một chút nhé!"),
    (30, 0x102cec, 0x102d9c, "vi_welcome",      "Xin chào J! Mình là Mochi nè!"),
    (31, 0x102cf0, 0x102da0, "vi_wificonfig",   "Đang vào chế độ cấu hình Wi-Fi."),
    # Common sounds (Ogg[32..37]): patch Ogg[35] (P3_POPUP wake response) & Ogg[36] (P3_SUCCESS boot greeting)
    (32, 0x102cf8, 0x102cf4, "p3_0",            None),
    (33, 0x102d00, 0x102cfc, "p3_exclamation",  None),
    (34, 0x102d08, 0x102d04, "p3_low_battery",  None),
    (35, 0x102d10, 0x102d0c, "p3_popup_wake",   "Dạ, J nói đi!"),
    (36, 0x102d18, 0x102d14, "p3_success_boot", "Chào J! Mình sẵn sàng rồi nè!"),
    (37, 0x102d20, 0x102d1c, "p3_vibration",    None),
]

DROM_VADDR_BASE = 0x3C270000
OGG_REGION_START = 0x02EFC4
OGG_REGION_END = 0x04AEFD
OGG_REGION_MAX_BYTES = OGG_REGION_END - OGG_REGION_START  # 114,489 bytes


def load_elevenlabs_api_key() -> str:
    env_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if env_key:
        return env_key
    key_file = Path.home() / "GOD/eleven.md"
    if key_file.exists():
        for line in key_file.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("sk_"):
                return s
    raise RuntimeError("Missing ELEVENLABS_API_KEY and ~/GOD/eleven.md")


def synthesize_xiaozhi_ogg(text_vi: str, out_ogg: Path, api_key: str, bitrate: str = "16k") -> bytes:
    """Synthesize Vietnamese speech via ElevenLabs and transcode to XiaoZhi 60ms 24kHz Ogg Opus."""
    if out_ogg.exists() and out_ogg.stat().st_size > 400:
        return out_ogg.read_bytes()

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128"
    payload = json.dumps({
        "text": text_vi,
        "model_id": MODEL_ID,
        "language_code": "vi",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85,
            "style": 0.30,
            "use_speaker_boost": True,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        mp3_bytes = resp.read()

    out_ogg.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
        tf.write(mp3_bytes)
        tmp_mp3 = Path(tf.name)

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-i", str(tmp_mp3),
                "-af", "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-45dB,aresample=24000",
                "-c:a", "libopus",
                "-b:a", bitrate,
                "-ac", "1",
                "-ar", "24000",
                "-vbr", "on",
                "-compression_level", "10",
                "-application", "voip",
                "-frame_duration", "60",
                str(out_ogg),
            ],
            check=True,
        )
    finally:
        tmp_mp3.unlink(missing_ok=True)

    return out_ogg.read_bytes()


def verify_and_update_esp_image(img: bytearray) -> tuple[int, str]:
    """Recalculate ESP-IDF image XOR checksum and trailing SHA256 digest over the 6 segments."""
    magic, seg_count, _spi_mode, _spi_size, _entry = struct.unpack_from("<BBBBI", img, 0)
    assert magic == 0xE9 and seg_count == 6, f"Unexpected ESP image header: magic=0x{magic:02x}, segs={seg_count}"
    off = 24
    chk = 0xEF
    for _ in range(seg_count):
        _load_addr, seg_len = struct.unpack_from("<II", img, off)
        seg_data = img[off + 8 : off + 8 + seg_len]
        for b in seg_data:
            chk ^= b
        off += 8 + seg_len

    pad_end = (off + 16) & ~15
    img[pad_end - 1] = chk
    digest = hashlib.sha256(img[:pad_end]).digest()
    img[pad_end : pad_end + 32] = digest
    assert pad_end + 32 == 0x37D340, f"Unexpected image end 0x{pad_end + 32:06x}"
    return chk, digest.hex()


def main() -> None:
    orig_full = ORIG_OTA1.read_bytes()
    # We only need the active 3,658,560-byte ESP-IDF image (0x000000..0x37d340)
    img = bytearray(orig_full[:0x37D340])

    # Extract original 38 OggS payloads using the literal pool pointers
    orig_oggs: dict[int, bytes] = {}
    for idx, s_foff, e_foff, slug, _text in OGG_SLOTS_38:
        s_vaddr = struct.unpack_from("<I", img, s_foff)[0]
        e_vaddr = struct.unpack_from("<I", img, e_foff)[0]
        s_off = s_vaddr - DROM_VADDR_BASE
        e_off = e_vaddr - DROM_VADDR_BASE
        assert img[s_off : s_off + 4] == b"OggS", f"Slot {idx} ({slug}) at 0x{s_off:06x} missing OggS magic"
        assert e_off > s_off, f"Slot {idx} ({slug}) invalid bounds 0x{s_off:06x}..0x{e_off:06x}"
        orig_oggs[idx] = bytes(img[s_off:e_off])

    api_key = ""
    new_oggs: dict[int, bytes] = {}
    for idx, _s_foff, _e_foff, slug, text_vi in OGG_SLOTS_38:
        if text_vi is None:
            new_oggs[idx] = orig_oggs[idx]
        else:
            out_ogg = CACHE_DIR / f"ogg_{idx:02d}_{slug}.ogg"
            if not out_ogg.exists() and not api_key:
                api_key = load_elevenlabs_api_key()
            ogg_bytes = synthesize_xiaozhi_ogg(text_vi, out_ogg, api_key, bitrate="14k")
            new_oggs[idx] = ogg_bytes
            print(f"  Ogg[{idx:02d}] {slug:16s}: {len(orig_oggs[idx]):5d} B -> {len(ogg_bytes):5d} B | {text_vi}")

    # Check total size inside OGG_REGION_START..OGG_REGION_END (with 4-byte 0x00 separator between streams)
    total_needed = sum(len(b) + 4 for b in new_oggs.values()) - 4
    if total_needed > OGG_REGION_MAX_BYTES:
        # Compact unused English prompts Ogg[10..15] to Ogg[00] so Vietnamese prompts have plenty of headroom
        for en_idx in range(10, 16):
            new_oggs[en_idx] = orig_oggs[0]
        total_needed = sum(len(b) + 4 for b in new_oggs.values()) - 4

    assert total_needed <= OGG_REGION_MAX_BYTES, (
        f"Total Ogg region {total_needed:,} B exceeds max {OGG_REGION_MAX_BYTES:,} B"
    )

    # Clear OGG_REGION_START..OGG_REGION_END and pack all 38 OggS streams contiguously
    img[OGG_REGION_START:OGG_REGION_END] = b"\x00" * OGG_REGION_MAX_BYTES
    cur_foff = OGG_REGION_START
    for idx, s_foff, e_foff, slug, _text in OGG_SLOTS_38:
        payload = new_oggs[idx]
        s_vaddr = DROM_VADDR_BASE + cur_foff
        e_vaddr = s_vaddr + len(payload)
        img[cur_foff : cur_foff + len(payload)] = payload
        struct.pack_into("<I", img, s_foff, s_vaddr)
        struct.pack_into("<I", img, e_foff, e_vaddr)
        cur_foff += len(payload) + 4

    chk, sha_hex = verify_and_update_esp_image(img)
    OUT_OTA1.write_bytes(img)
    print(
        f"\nPatched & verified {OUT_OTA1}\n"
        f"  Ogg region used = {total_needed:,} / {OGG_REGION_MAX_BYTES:,} bytes ({OGG_REGION_MAX_BYTES - total_needed:,} B free)\n"
        f"  Image size      = {len(img):,} bytes (0x{len(img):06x})\n"
        f"  XOR Checksum    = 0x{chk:02x}\n"
        f"  SHA256 Digest   = {sha_hex}"
    )


if __name__ == "__main__":
    main()
