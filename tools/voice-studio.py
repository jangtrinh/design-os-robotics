#!/usr/bin/env python3
"""
voice-studio.py — Complete Voice Personalization & Firmware Ogg Opus Toolkit for DESIGN:OS Robotics.
Capabilities:
  1. Extract all 39 embedded Ogg Opus audio streams from ota_1 firmware (0x02efc4..0x04aefd)
  2. Generate Studio "Golden 15s Reference Audio" (.wav 24kHz Mono & .mp3) for Zero-Shot Voice Cloning:
     - Uses ElevenLabs API (eleven_multilingual_v2) when ELEVENLABS_API_KEY is set
     - Also builds 3 Neural Studio reference variants (Natural Sweet, Mochi Anime +18% Formant/Pitch, Warm Companion)
  3. Generate custom 16kHz Mono Ogg Opus wake-up responses ("Dạ Mochi nghe nè J ơi!", "Yo J!") for ESP32-S3
"""
import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OTA1_BIN = ROOT / "profiles/example-esp32s3-n16r8/partitions/07-ota1-v2.5.3-0x560000.bin"
VOICES_DIR = ROOT / "voices"
EXTRACTED_OGG_DIR = VOICES_DIR / "extracted-firmware-ogg"
GOLDEN_DIR = VOICES_DIR / "golden-reference"
CUSTOM_WAKE_DIR = VOICES_DIR / "custom-wake-ogg"

GOLDEN_SCRIPT_VI = (
    "Chào J nhé! Mình là trợ lý Mochi của riêng bạn đây. "
    "Hôm nay thời tiết ngoài trời dễ chịu lắm, J muốn mình điểm tin sáng nay, "
    "bật một bản nhạc thật êm, hay cùng trò chuyện thư giãn nào? "
    "Dù là công việc bận rộn hay những lúc cần tìm một ý tưởng mới, "
    "cứ gọi một tiếng là mình luôn sẵn sàng lắng nghe và đồng hành cùng J ngay!"
)


def extract_firmware_oggs(fw_path: Path, out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = fw_path.read_bytes()
    ogg_offsets = []
    pos = 0
    while True:
        idx = data.find(b"OggS\x00", pos)
        if idx == -1:
            break
        if data[idx + 5] & 0x02:  # BOS (Beginning of Stream)
            ogg_offsets.append(idx)
        pos = idx + 4

    manifest = []
    for i, off in enumerate(ogg_offsets):
        p = off
        end_off = off
        while p < min(len(data), off + 200000):
            nxt = data.find(b"OggS\x00", p)
            if nxt == -1:
                break
            if data[nxt + 5] & 0x04:  # EOS (End of Stream)
                n_seg = data[nxt + 26]
                end_off = nxt + 27 + n_seg + sum(data[nxt + 27 : nxt + 27 + n_seg])
                break
            p = nxt + 4
        blob = data[off:end_off]
        role = f"snd_wake_{i - 34}" if i >= 34 else ("lang_pack_1" if i <= 16 else "lang_pack_2")
        fname = f"ogg_{i:02d}_{role}_0x{off:06x}.ogg"
        (out_dir / fname).write_bytes(blob)
        manifest.append({
            "index": i,
            "file": fname,
            "offset_hex": f"0x{off:06x}",
            "end_hex": f"0x{end_off:06x}",
            "max_size_bytes": end_off - off,
            "role": role,
        })
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def generate_elevenlabs_golden(text: str, voice_id: str, api_key: str, out_mp3: Path, out_wav: Path) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({
        "text": text,
        "model_id": "eleven_v4",
        "language_code": "vi",
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.82,
            "style": 0.20,
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
        out_mp3.write_bytes(resp.read())
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(out_mp3),
            "-af", "highpass=f=80,acompressor=threshold=-18dB:ratio=2.5:attack=10:release=100,loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur=0.3",
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(out_wav),
        ],
        check=True,
        capture_output=True,
    )


def generate_studio_golden_variants(text: str, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_mp3 = out_dir / "_base_hoaimy.mp3"
    subprocess.run(
        [
            "uvx", "--from", "edge-tts", "edge-tts",
            "--voice", "vi-VN-HoaiMyNeural",
            "--rate=+4%",
            "--text", text,
            "--write-media", str(raw_mp3),
        ],
        check=True,
        capture_output=True,
    )

    variants = [
        (
            "01-golden-mochi-cute-anime",
            "asetrate=24000*1.16,aresample=24000,atempo=0.92,highpass=f=90,equalizer=f=3500:width_type=o:width=1.5:g=3,loudnorm=I=-16:TP=-1.5:LRA=11",
        ),
        (
            "02-golden-mochi-sweet-assistant",
            "asetrate=24000*1.08,aresample=24000,atempo=0.96,highpass=f=85,equalizer=f=3000:width_type=o:width=1.5:g=2,loudnorm=I=-16:TP=-1.5:LRA=11",
        ),
        (
            "03-golden-natural-studio-vi",
            "highpass=f=80,acompressor=threshold=-18dB:ratio=2:attack=10:release=100,loudnorm=I=-16:TP=-1.5:LRA=11",
        ),
    ]

    outputs = []
    for slug, af_chain in variants:
        wav_p = out_dir / f"{slug}.wav"
        mp3_p = out_dir / f"{slug}.mp3"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(raw_mp3),
                "-af", af_chain,
                "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_p),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(wav_p),
                "-c:a", "libmp3lame", "-b:a", "192k", str(mp3_p),
            ],
            check=True,
            capture_output=True,
        )
        outputs.append(wav_p)
    raw_mp3.unlink(missing_ok=True)
    return outputs


def build_custom_wake_oggs(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts = [
        ("wake_00_oi_j_oi", "Ơi, J gọi mình hả?"),
        ("wake_01_mochi_nghe_ne", "Dạ, Mochi nghe nè!"),
        ("wake_02_yo_j", "Yo J! Có mình đây!"),
    ]
    created = []
    for slug, phrase in prompts:
        tmp_mp3 = out_dir / f"_{slug}.mp3"
        out_ogg = out_dir / f"{slug}.ogg"
        if not out_ogg.exists():
            for attempt in range(4):
                r = subprocess.run(
                    [
                        "uvx", "--from", "edge-tts", "edge-tts",
                        "--voice", "vi-VN-HoaiMyNeural",
                        "--text", phrase,
                        "--write-media", str(tmp_mp3),
                    ],
                    capture_output=True,
                )
                if r.returncode == 0 and tmp_mp3.exists() and tmp_mp3.stat().st_size > 0:
                    break
            # Encode as 16kHz Mono Ogg Opus at 14kbps so it fits inside <2KB firmware slots if needed
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(tmp_mp3),
                    "-af", "asetrate=24000*1.15,aresample=16000,atempo=0.95,loudnorm=I=-15:TP=-1.0",
                    "-ar", "16000", "-ac", "1",
                    "-c:a", "libopus", "-b:a", "14k", "-vbr", "on", "-application", "voip",
                    str(out_ogg),
                ],
                check=True,
                capture_output=True,
            )
            tmp_mp3.unlink(missing_ok=True)
        created.append(out_ogg)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="DESIGN:OS Robotics Voice Studio & Firmware Ogg Toolkit")
    parser.add_argument("--text", default=GOLDEN_SCRIPT_VI, help="Golden reference Vietnamese script (~15s)")
    parser.add_argument("--elevenlabs-key", default=os.environ.get("ELEVENLABS_API_KEY", ""))
    parser.add_argument("--elevenlabs-voice-id", default=os.environ.get("ELEVENLABS_VOICE_ID", "<ELEVENLABS_VOICE_ID>"))
    args = parser.parse_args()

    if OTA1_BIN.exists():
        manifest = extract_firmware_oggs(OTA1_BIN, EXTRACTED_OGG_DIR)
        print(f"[1/3] Extracted {len(manifest)} Ogg Opus streams from ota_1 -> {EXTRACTED_OGG_DIR}")

    if args.elevenlabs_key:
        el_mp3 = GOLDEN_DIR / "00-elevenlabs-golden-reference.mp3"
        el_wav = GOLDEN_DIR / "00-elevenlabs-golden-reference.wav"
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        generate_elevenlabs_golden(args.text, args.elevenlabs_voice_id, args.elevenlabs_key, el_mp3, el_wav)
        print(f"[2/3] Generated ElevenLabs Golden Reference -> {el_wav}")

    studio_wavs = generate_studio_golden_variants(args.text, GOLDEN_DIR)
    print(f"[2/3] Generated {len(studio_wavs)} Studio Golden Reference voice clones (.wav & .mp3) -> {GOLDEN_DIR}")
    for w in studio_wavs:
        print(f"      - {w.name} ({w.stat().st_size:,} B)")

    wake_oggs = build_custom_wake_oggs(CUSTOM_WAKE_DIR)
    print(f"[3/3] Built {len(wake_oggs)} custom 16kHz Ogg Opus wake responses -> {CUSTOM_WAKE_DIR}")
    for o in wake_oggs:
        print(f"      - {o.name} ({o.stat().st_size:,} B)")


if __name__ == "__main__":
    main()
