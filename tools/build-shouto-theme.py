#!/usr/bin/env python3
"""
Build the Context-True 21-Emotion (1 cohesive scene per emotion — no idle state jumping)
+ 92-Key EmojiCollection + Custom Wake Word ("Hello J" / "Hi J" / "Yo J" / "Hey J" via mn6_en)
full-bleed 240x320 Shouto Mochi ("Just a Mochi" @ShoutoEmoji) theme binary
(`themes/shouto-mochi-fullvien-240x320.bin`), extracted emotion preview GIFs
(`themes/shouto-mochi-preview/<emotion>.gif`), and contact sheet
(`docs/assets/shouto-mochi-contact-sheet.png`) for RoBot.5320 (ESP32-S3 N16R8).

Source pack: ~/Products/Just_A_Mochi_ShoutoEmoji.zip (199 VP9+Alpha 100x100 WebM stickers)
Base assets: themes/mochi-fullvien-240x320.bin
Wake model : MultiNet6 English (`mn6_en` + `fst`) packed into `srmodels.bin`
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ZIP = Path("~/Products/Just_A_Mochi_ShoutoEmoji.zip").expanduser()
BASE_BIN = ROOT / "themes/mochi-fullvien-240x320.bin"
SRMODELS_MN6_BIN = ROOT / "profiles/example-esp32s3-n16r8/unpacked-assets/srmodels_mn6_en.bin"
OUT_BIN = ROOT / "themes/shouto-mochi-fullvien-240x320.bin"
PREVIEW_DIR = ROOT / "themes/shouto-mochi-preview"
CONTACT_SHEET = ROOT / "docs/assets/shouto-mochi-contact-sheet.png"

# 21 emotions x 1 cohesive sticker animation per emotion (context-true: no jumping across unrelated poses)
EMOTION_SCENES_21: list[tuple[str, str, int, str]] = [
    ("neutral",     "emoji_f6e81fd7.gif",   1, "Calm idle breathing & gentle bounce"),
    ("happy",       "emoji_43f8e4b6.gif", 125, "Golden sparkles & joyful smile"),
    ("laughing",    "emoji_8b614299.gif",  17, "Hearty belly laugh"),
    ("funny",       "emoji_087e2e85.gif",   7, "Playful rainbow stream"),
    ("sad",         "emoji_76922dfc.gif",  95, "Falling teardrops & drooping ears"),
    ("angry",       "emoji_82f95ba7.gif",  56, "Pulsing anger veins & huffing"),
    ("crying",      "emoji_398ebfdb.gif",  54, "Streaming cyan waterfall tears"),
    ("loving",      "emoji_2f1842ad.gif", 147, "Floating pink hearts & warm hug"),
    ("embarrassed", "emoji_830fff3d.gif", 126, "Deep blush & bashful steam"),
    ("surprised",   "emoji_8468cfb7.gif",  36, "Wide-eyed alert surprise"),
    ("shocked",     "emoji_f3098c15.gif", 162, "Dramatic lightning strike shock"),
    ("thinking",    "emoji_69e1a2a9.gif", 145, "Pondering with '...' thought bubble"),
    ("winking",     "emoji_96f1d507.gif",  97, "Playful mischievous wink"),
    ("cool",        "emoji_25726719.gif",  80, "Sunglasses lens glint"),
    ("relaxed",     "emoji_9520d9e7.gif",   3, "Cozy warm tea sip"),
    ("delicious",   "emoji_8a9e0e24.gif",  71, "Happy boba milk tea treat"),
    ("kissy",       "emoji_ae6c04d1.gif",   4, "Sweet flower & flying kiss"),
    ("confident",   "emoji_b0da8028.gif",  58, "Radiant golden aura flex"),
    ("sleepy",      "emoji_d7c25b82.gif", 128, "Floating 'Z z' peaceful sleep"),
    ("silly",       "emoji_7b85603e.gif", 107, "Party horn & confetti celebration"),
    ("confused",    "emoji_583d2acb.gif", 195, "Head tilt with floating '?'"),
]

# All 71 additional system/UI icon keys in ota_1 EmojiCollection table (0x6db84..0x6de68)
# mapped onto our 21 Mochi GIF slots so all 92 firmware keys resolve without fallback warnings.
SYSTEM_ICON_ALIASES_71: list[tuple[str, str]] = [
    ("robot_2",                     "emoji_f6e81fd7.gif"),
    ("person",                      "emoji_43f8e4b6.gif"),
    ("home",                        "emoji_f6e81fd7.gif"),
    ("settings",                    "emoji_69e1a2a9.gif"),
    ("power_settings_new",          "emoji_d7c25b82.gif"),
    ("check",                       "emoji_43f8e4b6.gif"),
    ("check_circle",                "emoji_b0da8028.gif"),
    ("close",                       "emoji_82f95ba7.gif"),
    ("cancel",                      "emoji_76922dfc.gif"),
    ("delete",                      "emoji_398ebfdb.gif"),
    ("warning",                     "emoji_8468cfb7.gif"),
    ("info",                        "emoji_69e1a2a9.gif"),
    ("help",                        "emoji_583d2acb.gif"),
    ("contact_support",             "emoji_583d2acb.gif"),
    ("notifications",               "emoji_8468cfb7.gif"),
    ("schedule",                    "emoji_9520d9e7.gif"),
    ("alarm",                       "emoji_8468cfb7.gif"),
    ("watch",                       "emoji_9520d9e7.gif"),
    ("calendar_month",              "emoji_43f8e4b6.gif"),
    ("progress_activity",           "emoji_69e1a2a9.gif"),
    ("refresh",                     "emoji_7b85603e.gif"),
    ("repeat",                      "emoji_7b85603e.gif"),
    ("search",                      "emoji_69e1a2a9.gif"),
    ("explore",                     "emoji_25726719.gif"),
    ("navigation",                  "emoji_b0da8028.gif"),
    ("location_on",                 "emoji_8468cfb7.gif"),
    ("language",                    "emoji_43f8e4b6.gif"),
    ("chat_bubble",                 "emoji_43f8e4b6.gif"),
    ("mail",                        "emoji_ae6c04d1.gif"),
    ("phone",                       "emoji_8468cfb7.gif"),
    ("mic",                         "emoji_43f8e4b6.gif"),
    ("mic_off",                     "emoji_d7c25b82.gif"),
    ("headphones",                  "emoji_25726719.gif"),
    ("music_note",                  "emoji_7b85603e.gif"),
    ("play_arrow",                  "emoji_43f8e4b6.gif"),
    ("pause",                       "emoji_9520d9e7.gif"),
    ("stop",                        "emoji_d7c25b82.gif"),
    ("skip_previous",               "emoji_96f1d507.gif"),
    ("skip_next",                   "emoji_96f1d507.gif"),
    ("favorite",                    "emoji_2f1842ad.gif"),
    ("star",                        "emoji_b0da8028.gif"),
    ("sports_esports",              "emoji_087e2e85.gif"),
    ("image",                       "emoji_43f8e4b6.gif"),
    ("photo_camera",                "emoji_96f1d507.gif"),
    ("edit_square",                 "emoji_69e1a2a9.gif"),
    ("calculate",                   "emoji_69e1a2a9.gif"),
    ("eyeglasses",                  "emoji_25726719.gif"),
    ("brightness_6",                "emoji_b0da8028.gif"),
    ("device_thermostat",           "emoji_830fff3d.gif"),
    ("memory",                      "emoji_b0da8028.gif"),
    ("sd_card",                     "emoji_8a9e0e24.gif"),
    ("bluetooth",                   "emoji_25726719.gif"),
    ("link",                        "emoji_2f1842ad.gif"),
    ("lock",                        "emoji_25726719.gif"),
    ("lock_open",                   "emoji_43f8e4b6.gif"),
    ("key",                         "emoji_b0da8028.gif"),
    ("download",                    "emoji_8a9e0e24.gif"),
    ("cloud_download",              "emoji_8a9e0e24.gif"),
    ("cloud_upload",                "emoji_b0da8028.gif"),
    ("cloud_off",                   "emoji_f3098c15.gif"),
    ("arrow_back",                  "emoji_96f1d507.gif"),
    ("arrow_forward",               "emoji_96f1d507.gif"),
    ("arrow_upward",                "emoji_b0da8028.gif"),
    ("arrow_downward",              "emoji_9520d9e7.gif"),
    ("keyboard_arrow_left",         "emoji_96f1d507.gif"),
    ("keyboard_arrow_right",        "emoji_96f1d507.gif"),
    ("keyboard_arrow_up",           "emoji_b0da8028.gif"),
    ("keyboard_arrow_down",         "emoji_9520d9e7.gif"),
    ("keyboard_double_arrow_left",  "emoji_96f1d507.gif"),
    ("keyboard_double_arrow_right", "emoji_96f1d507.gif"),
    ("keyboard_double_arrow_up",    "emoji_b0da8028.gif"),
    ("keyboard_double_arrow_down",  "emoji_9520d9e7.gif"),
]


def build_srmodels_mn6_en(out_path: Path) -> bytes:
    """Download (if needed) and pack esp-sr MultiNet6 English (`fst` + `mn6_en`) into `srmodels.bin` format."""
    if out_path.exists() and out_path.stat().st_size > 3_700_000:
        return out_path.read_bytes()

    base_url = "https://raw.githubusercontent.com/espressif/esp-sr/master/model/multinet_model"
    cache_dir = Path("/tmp/esp_sr_mn6")
    for fn in ["_MODEL_INFO_", "mn6_data", "mn6_index", "vocab"]:
        dest = cache_dir / "mn6_en" / fn
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            urllib.request.urlretrieve(f"{base_url}/mn6_en/{fn}", dest)

    cmds_txt = (
        "1,HELLO J\n"
        "2,HELLO JAY\n"
        "3,HI J\n"
        "4,HI JAY\n"
        "5,YO J\n"
        "6,YO JAY\n"
        "7,HEY J\n"
        "8,HEY JAY\n"
    ).encode("utf-8")

    models: list[tuple[str, list[tuple[str, bytes]]]] = [
        ("fst", [
            ("commands_cn.txt", cmds_txt),
            ("commands_en.txt", cmds_txt),
        ]),
        ("mn6_en", [
            ("_MODEL_INFO_", (cache_dir / "mn6_en/_MODEL_INFO_").read_bytes()),
            ("mn6_data",     (cache_dir / "mn6_en/mn6_data").read_bytes()),
            ("mn6_index",    (cache_dir / "mn6_en/mn6_index").read_bytes()),
            ("vocab",        (cache_dir / "mn6_en/vocab").read_bytes()),
        ]),
    ]

    total_files = sum(len(files) for _, files in models)
    header_size = 4 + len(models) * 36 + total_files * 40
    cur_offset = header_size

    header = bytearray(struct.pack("<I", len(models)))
    payload = bytearray()
    for m_name, files in models:
        header += m_name.encode("utf-8")[:31].ljust(32, b"\x00")
        header += struct.pack("<I", len(files))
        for f_name, f_bytes in files:
            header += f_name.encode("utf-8")[:31].ljust(32, b"\x00")
            header += struct.pack("<II", cur_offset, len(f_bytes))
            payload += f_bytes
            cur_offset += len(f_bytes)

    blob = bytes(header + payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(blob)
    return blob


def unpack_mmap_assets(bin_path: Path) -> tuple[list[str], dict[str, tuple[bytes, int, int]]]:
    data = bin_path.read_bytes()
    num_files, checksum_u16, body_len = struct.unpack("<III", data[:12])
    assert len(data) == 12 + body_len, f"Size mismatch in {bin_path}"
    assert (sum(data[12:]) & 0xFFFF) == checksum_u16, f"Checksum mismatch in {bin_path}"

    table_end = 12 + num_files * 44
    ordered_names: list[str] = []
    files: dict[str, tuple[bytes, int, int]] = {}
    for i in range(num_files):
        ent = data[12 + i * 44 : 12 + (i + 1) * 44]
        name = ent[:32].split(b"\x00", 1)[0].decode("utf-8")
        sz, off, w, h = struct.unpack("<IIHH", ent[32:44])
        magic = data[table_end + off : table_end + off + 2]
        assert magic == b"ZZ", f"Missing ZZ magic for {name} at offset {off}"
        payload = data[table_end + off + 2 : table_end + off + 2 + sz]
        ordered_names.append(name)
        files[name] = (payload, w, h)
    return ordered_names, files


def enhance_floating_dark_symbols(im: Image.Image) -> None:
    """Brighten floating dark symbols ('Z z', '?', notes) outside the white Mochi body so they pop on #000000."""
    px = im.load()
    white_mask = Image.new("L", im.size, 0)
    wm_px = white_mask.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 100 and r > 140 and g > 140 and b > 140:
                wm_px[x, y] = 255
    dilated_white = white_mask.filter(ImageFilter.MaxFilter(9))
    dw_px = dilated_white.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 25 and dw_px[x, y] == 0 and r < 110 and g < 110 and b < 110:
                px[x, y] = (135, 225, 255, min(255, int(a * 1.4)))


def decode_and_scale_scene(webm_path: Path, max_scene_frames: int = 12) -> list[Image.Image]:
    """Decode one 100x100 VP9+Alpha WebM sticker and composite onto 240x240 #000000 RGB frames."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-c:v", "libvpx-vp9",
                "-i", str(webm_path),
                str(td_path / "raw_%03d.png"),
            ],
            check=False,
        )
        raw_pngs = sorted(td_path.glob("raw_*.png"))
        if not raw_pngs:
            raise RuntimeError(f"Failed to decode frames from {webm_path}")

        if len(raw_pngs) > max_scene_frames:
            step = len(raw_pngs) / float(max_scene_frames)
            raw_pngs = [raw_pngs[min(len(raw_pngs) - 1, int(round(i * step)))] for i in range(max_scene_frames)]

        frames_rgba = [Image.open(p).convert("RGBA") for p in raw_pngs]
        for im in frames_rgba:
            enhance_floating_dark_symbols(im)

        ux0, uy0, ux1, uy1 = 100, 100, 0, 0
        for im in frames_rgba:
            alpha = im.getchannel("A")
            bb = alpha.point(lambda a: 255 if a > 16 else 0).getbbox()
            if bb:
                ux0 = min(ux0, bb[0])
                uy0 = min(uy0, bb[1])
                ux1 = max(ux1, bb[2])
                uy1 = max(uy1, bb[3])

        bw, bh = max(1, ux1 - ux0), max(1, uy1 - uy0)
        touches_border = ux0 <= 1 or uy0 <= 1 or ux1 >= 99 or uy1 >= 99
        target_span = 240 if touches_border else 232
        scale = target_span / max(bw, bh)
        new_w = max(1, int(round(100 * scale)))
        new_h = max(1, int(round(100 * scale)))
        cx = (ux0 + ux1) / 2.0 * scale
        cy = (uy0 + uy1) / 2.0 * scale
        paste_x = int(round(120 - cx))
        paste_y = int(round(120 - cy))

        scene_rgb: list[Image.Image] = []
        for im in frames_rgba:
            scaled = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (240, 240), (0, 0, 0, 255))
            canvas.alpha_composite(scaled, (paste_x, paste_y))
            rgb = canvas.convert("RGB")
            px = rgb.load()
            for y in range(240):
                for x in range(240):
                    r, g, b = px[x, y]
                    if r >= 244 and g >= 244 and b >= 244:
                        px[x, y] = (255, 255, 255)
                    elif r <= 12 and g <= 12 and b <= 12:
                        px[x, y] = (0, 0, 0)
            scene_rgb.append(rgb)
        return scene_rgb


def build_single_scene_gif(webm_path: Path, out_gif_path: Path, max_frames: int = 12, max_colors: int = 12) -> tuple[bytes, int]:
    """Encode 1 cohesive Mochi sticker animation into a smooth single-context 240x240 GIF."""
    all_frames = decode_and_scale_scene(webm_path, max_scene_frames=max_frames)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for fi, rgb in enumerate(all_frames):
            rgb.save(td_path / f"proc_{fi:03d}.png")

        palette_path = td_path / "palette.png"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-framerate", "8",
                "-i", str(td_path / "proc_%03d.png"),
                "-vf", f"palettegen=max_colors={max_colors}:stats_mode=diff",
                str(palette_path),
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-framerate", "8",
                "-i", str(td_path / "proc_%03d.png"),
                "-i", str(palette_path),
                "-lavfi", "paletteuse=dither=none:diff_mode=rectangle",
                "-loop", "0",
                str(out_gif_path),
            ],
            check=True,
        )
        gif_bytes = out_gif_path.read_bytes()
        return gif_bytes, len(all_frames)


def render_contact_sheet(preview_dir: Path, out_png: Path) -> None:
    cols, rows = 6, 4
    cw, ch = 256, 284
    sheet = Image.new("RGB", (cols * cw, rows * ch), (14, 15, 20))
    draw = ImageDraw.Draw(sheet)

    items_22 = EMOTION_SCENES_21 + [("robot_2", "emoji_f6e81fd7.gif", 1, "Alias of neutral")]
    for k, (emotion, _gif_file, idx, _desc) in enumerate(items_22):
        r, c = k // cols, k % cols
        x0, y0 = c * cw, r * ch
        gif_path = preview_dir / f"{emotion}.gif"
        im = Image.open(gif_path)
        nf = getattr(im, "n_frames", 1)
        target_frame = min(nf - 1, nf // 2)
        im.seek(target_frame)
        frame_rgb = im.convert("RGB")
        draw.rectangle([x0 + 7, y0 + 33, x0 + 8 + 240, y0 + 34 + 240], outline=(48, 52, 66))
        sheet.paste(frame_rgb, (x0 + 8, y0 + 34))
        sz_kb = gif_path.stat().st_size / 1024.0
        draw.text((x0 + 8, y0 + 10), f"{emotion} (#{idx:03d}, {nf}f, {sz_kb:.1f}KB)", fill=(120, 255, 190))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)


def verify_mmap_binary(bin_path: Path) -> tuple[int, int, int]:
    data = bin_path.read_bytes()
    total_size = len(data)
    assert total_size <= 5_636_096, f"Binary size {total_size:,} exceeds 5,636,096 B (0x560000) assets partition"
    num_files, checksum_u16, body_len = struct.unpack("<III", data[:12])
    assert num_files == 26, f"Expected 26 files, got {num_files}"
    assert 12 + body_len == total_size, f"Header body_len {body_len} != {total_size - 12}"
    calc_csum = sum(data[12:]) & 0xFFFF
    assert calc_csum == checksum_u16, f"Checksum mismatch: 0x{calc_csum:04x} != 0x{checksum_u16:04x}"

    table_end = 12 + num_files * 44
    gif_count = 0
    for i in range(num_files):
        ent = data[12 + i * 44 : 12 + (i + 1) * 44]
        name = ent[:32].split(b"\x00", 1)[0].decode("utf-8")
        sz, off, w, h = struct.unpack("<IIHH", ent[32:44])
        assert data[table_end + off : table_end + off + 2] == b"ZZ", f"Missing ZZ magic at entry {i} ({name})"
        payload = data[table_end + off + 2 : table_end + off + 2 + sz]
        if name.endswith(".gif"):
            gif_count += 1
            assert (w, h) == (240, 240), f"GIF {name} table dims {(w, h)} != (240, 240)"
            assert payload[:6] in (b"GIF89a", b"GIF87a"), f"Invalid GIF header in {name}"
            gw, gh = struct.unpack("<HH", payload[6:10])
            assert (gw, gh) == (240, 240), f"GIF {name} logical screen {(gw, gh)} != (240, 240)"
    assert gif_count == 21, f"Expected 21 GIF entries, found {gif_count}"
    return total_size, checksum_u16, num_files


def main() -> None:
    ordered_names, base_files = unpack_mmap_assets(BASE_BIN)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    all_21 = [idx for _, _, idx, _ in EMOTION_SCENES_21]
    assert len(all_21) == 21 and len(set(all_21)) == 21, "Expected 21 unique sticker indices"

    with tempfile.TemporaryDirectory() as unpack_tmp:
        unpack_root = Path(unpack_tmp)
        with zipfile.ZipFile(DEFAULT_ZIP, "r") as zf:
            zf.extractall(unpack_root)
        pack_dir = unpack_root / "Just_A_Mochi_ShoutoEmoji"
        manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
        items_by_index = {item["index"]: item for item in manifest["items"]}

        gif_payloads: dict[str, bytes] = {}
        for emotion, gif_filename, sticker_idx, desc in EMOTION_SCENES_21:
            webm_path = pack_dir / items_by_index[sticker_idx]["filename"]
            preview_gif = PREVIEW_DIR / f"{emotion}.gif"
            gif_bytes, n_frames = build_single_scene_gif(webm_path, preview_gif, max_frames=12, max_colors=16)
            gif_payloads[gif_filename] = gif_bytes
            print(
                f"  {emotion:12s} <- #{sticker_idx:03d} "
                f"-> {gif_filename} ({n_frames:2d}f, {len(gif_bytes):7,d} B) | {desc}"
            )

    shutil.copyfile(PREVIEW_DIR / "neutral.gif", PREVIEW_DIR / "robot_2.gif")

    # Match the exact 22-state index.json structure of mochi-fullvien-240x320.bin
    idx_obj = json.loads(base_files["index.json"][0].decode("utf-8"))
    idx_obj["hide_subtitle"] = True
    idx_obj["skin"]["light"] = {
        "text_color": "#ffffff",
        "background_color": "#000000",
        "background_image": "background_light.raw",
    }
    idx_obj["skin"]["dark"] = {
        "text_color": "#ffffff",
        "background_color": "#000000",
        "background_image": "background_dark.raw",
    }

    emoji_collection: list[dict[str, str]] = []
    for emotion, gif_filename, _, _ in EMOTION_SCENES_21:
        emoji_collection.append({"name": emotion, "file": gif_filename})
    emoji_collection.append({"name": "robot_2", "file": "emoji_f6e81fd7.gif"})

    idx_obj["emoji_collection"] = emoji_collection
    idx_obj.pop("multinet_model", None)
    new_index_bytes = json.dumps(idx_obj, indent=2).encode("utf-8")

    out_entries: list[tuple[str, bytes, int, int]] = []
    for name in ordered_names:
        if name.endswith(".gif"):
            out_entries.append((name, gif_payloads[name], 240, 240))
        elif name == "index.json":
            out_entries.append(("index.json", new_index_bytes, 0, 0))
        else:
            payload, w, h = base_files[name]
            out_entries.append((name, payload, w, h))

    table_buf = bytearray()
    data_buf = bytearray()
    cur_off = 0
    for name, payload, w, h in out_entries:
        name_b = name.encode("utf-8")[:31].ljust(32, b"\x00")
        table_buf += name_b + struct.pack("<IIHH", len(payload), cur_off, w, h)
        data_buf += b"ZZ" + payload
        cur_off += 2 + len(payload)

    body = bytes(table_buf + data_buf)
    checksum_u16 = sum(body) & 0xFFFF
    header = struct.pack("<III", len(out_entries), checksum_u16, len(body))
    OUT_BIN.parent.mkdir(parents=True, exist_ok=True)
    OUT_BIN.write_bytes(header + body)

    render_contact_sheet(PREVIEW_DIR, CONTACT_SHEET)
    shutil.copyfile(CONTACT_SHEET, PREVIEW_DIR / "contact-sheet.png")

    total_size, verified_csum, verified_nf = verify_mmap_binary(OUT_BIN)
    print(
        f"\nBuilt & verified {OUT_BIN}\n"
        f"  total_size       = {total_size:,} bytes ({total_size / (1024 * 1024):.2f} MB / 5.37 MB max)\n"
        f"  num_files        = {verified_nf} (21 single-context GIFs, {len(emoji_collection)} emoji_collection keys)\n"
        f"  checksum         = 0x{verified_csum:04x}"
    )


if __name__ == "__main__":
    main()
