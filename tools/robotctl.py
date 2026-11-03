#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
robotctl.py — Complete CLI Mastery & Optimization Toolkit for RoBot.5320 (ESP32-S3 N16R8)
Supports:
  - Inspecting & decoding all active NVS namespaces/keys (wifi, lcd_cfg, config, display, audio, mqtt, websocket)
  - In-place & new-entry NVS patching with valid ESP-IDF CRC32 (set-wifi, set-tuning, enable-hud, etc.)
  - Instant OTA slot switching (ota_0 <-> ota_1) via 0xD000 otadata
  - Building full-bleed 240x320 esp_mmap_assets themes with crisp #FFFFFF HUD status bar
"""
import argparse
import binascii
import glob
import json
import os
import re
import select
import socket
import ssl
import subprocess
import struct
import sys
import termios
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / os.environ.get("ROBOT_PROFILE_DIR", "profiles/example-esp32s3-n16r8")
DEFAULT_NVS = PROFILE_DIR / "nvs-hud-enabled.bin"
ORIG_NVS = PROFILE_DIR / "partitions/03-nvs-0x009000.bin"
DEFAULT_THEME = ROOT / "themes/procedural-mochi-fullvien-240x320.bin"
DEFAULT_PORT = os.environ.get("ESPPORT", "/dev/cu.usbmodem*")
ROBOT_MAC_FULL = os.environ.get("ROBOT_MAC", "aa:bb:cc:dd:ee:ff").lower()
ROBOT_MAC_FRAG = ROBOT_MAC_FULL.replace(":0", ":")
ROBOT_LAN_IP = os.environ.get("ROBOT_IP", "")


def nvs_crc32(ent_32: bytes) -> int:
    return binascii.crc32(ent_32[0:4] + ent_32[8:32], 0xFFFFFFFF) & 0xFFFFFFFF


def parse_nvs(nvs_bytes: bytes) -> dict:
    namespaces = {0: "__namespaces__"}
    result = {}
    for p in range(len(nvs_bytes) // 4096):
        page = nvs_bytes[p * 4096 : (p + 1) * 4096]
        p_state, p_seq = struct.unpack("<II", page[:8])
        if p_state == 0xFFFFFFFF:
            continue
        bmap = page[32:64]
        i = 0
        while i < 126:
            st = (bmap[i // 4] >> ((i % 4) * 2)) & 0x3
            if st != 0x2:
                i += 1
                continue
            off = 64 + i * 32
            ent = page[off : off + 32]
            ns, typ, span, chunk_idx, crc = struct.unpack("<BBBBI", ent[:8])
            key = ent[8:24].split(b"\x00", 1)[0].decode("utf-8", "replace")
            if ns == 0 and typ == 0x01:
                ns_idx = ent[24]
                namespaces[ns_idx] = key
                result.setdefault(key, {})
                i += 1
                continue
            ns_name = namespaces.get(ns, f"ns_{ns}")
            result.setdefault(ns_name, {})
            if typ == 0x01:  # u8
                val = ent[24]
            elif typ == 0x11:  # i8
                val = struct.unpack("<b", ent[24:25])[0]
            elif typ == 0x02:  # u16
                val = struct.unpack("<H", ent[24:26])[0]
            elif typ == 0x12:  # i16
                val = struct.unpack("<h", ent[24:26])[0]
            elif typ == 0x04:  # u32
                val = struct.unpack("<I", ent[24:28])[0]
            elif typ == 0x14:  # i32
                val = struct.unpack("<i", ent[24:28])[0]
            elif typ == 0x21 and span > 1:  # sz string
                str_len = struct.unpack("<H", ent[24:26])[0]
                raw = b"".join(
                    page[64 + (i + 1 + k) * 32 : 64 + (i + 2 + k) * 32]
                    for k in range(span - 1)
                )
                val = raw[: max(0, str_len - 1)].decode("utf-8", "replace")
            else:
                val = f"<type=0x{typ:02x} span={span}>"
            result[ns_name][key] = {
                "value": val,
                "page": p,
                "slot": i,
                "ns": ns,
                "type": f"0x{typ:02x}",
                "span": span,
            }
            i += max(1, span)
    return result


def patch_i32_or_u8_in_nvs(
    nvs: bytearray, page_idx: int, slot_idx: int, new_val: int, is_u8: bool = False
) -> None:
    off = page_idx * 4096 + 64 + slot_idx * 32
    ent = bytearray(nvs[off : off + 32])
    if is_u8:
        ent[24:32] = bytes([new_val & 0xFF]) + b"\xff" * 7
    else:
        ent[24:28] = struct.pack("<i", new_val)
    crc = nvs_crc32(bytes(ent))
    ent[4:8] = struct.pack("<I", crc)
    nvs[off : off + 32] = ent


def append_u8_to_page1(nvs: bytearray, ns_id: int, key: str, val: int) -> int:
    """Append or update a u8 key in Page 1 if an empty slot (0b11) exists."""
    page_off = 4096
    bmap = bytearray(nvs[page_off + 32 : page_off + 64])
    # First check if key already exists as active (0b10) in Page 1
    for i in range(126):
        st = (bmap[i // 4] >> ((i % 4) * 2)) & 0x3
        if st == 0x2:
            off = page_off + 64 + i * 32
            ent = nvs[off : off + 32]
            ent_ns = ent[0]
            ent_key = ent[8:24].split(b"\x00", 1)[0].decode("utf-8", "replace")
            if ent_ns == ns_id and ent_key == key:
                patch_i32_or_u8_in_nvs(nvs, 1, i, val, is_u8=True)
                return i

    # Otherwise find first Empty slot (0b11) in Page 0, 1, or 2
    for p in (0, 1, 2):
        p_off = p * 4096
        bm = bytearray(nvs[p_off + 32 : p_off + 64])
        for i in range(126):
            st = (bm[i // 4] >> ((i % 4) * 2)) & 0x3
            if st == 0x3:
                # Set bitmap state from 0b11 (Empty) to 0b10 (Written): clear bit (i%4)*2
                bm[i // 4] &= ~(1 << ((i % 4) * 2))
                nvs[p_off + 32 : p_off + 64] = bm
                ent = bytearray(32)
                ent[0] = ns_id
                ent[1] = 0x01  # u8
                ent[2] = 1  # span=1
                ent[3] = 0xFF  # chunk_idx
                ent[8:24] = key.encode("utf-8")[:15].ljust(16, b"\x00")
                ent[24:32] = bytes([val & 0xFF]) + b"\xff" * 7
                crc = nvs_crc32(bytes(ent))
                ent[4:8] = struct.pack("<I", crc)
                nvs[p_off + 64 + i * 32 : p_off + 64 + (i + 1) * 32] = ent
                return i
    raise RuntimeError("No empty NVS slot found in Page 0 or Page 1")


def update_string_in_page1(nvs: bytearray, ns_id: int, key: str, new_str: str) -> None:
    """Update an existing span=2 string (<=31 chars) in Page 1 in-place."""
    s_bytes = new_str.encode("utf-8") + b"\x00"
    if len(s_bytes) > 32:
        raise ValueError("In-place string update requires length <= 31 bytes")
    page_off = 4096
    bmap = nvs[page_off + 32 : page_off + 64]
    for i in range(125):
        st = (bmap[i // 4] >> ((i % 4) * 2)) & 0x3
        if st != 0x2:
            continue
        off = page_off + 64 + i * 32
        ent = bytearray(nvs[off : off + 32])
        if ent[0] == ns_id and ent[1] == 0x21 and ent[2] == 2:
            ent_key = ent[8:24].split(b"\x00", 1)[0].decode("utf-8", "replace")
            if ent_key == key:
                data_slot = s_bytes.ljust(32, b"\xff")
                data_crc = binascii.crc32(s_bytes, 0xFFFFFFFF) & 0xFFFFFFFF
                ent[24:26] = struct.pack("<H", len(s_bytes))
                ent[26:28] = b"\xff\xff"
                ent[28:32] = struct.pack("<I", data_crc)
                ent[4:8] = struct.pack("<I", nvs_crc32(bytes(ent)))
                nvs[off : off + 32] = ent
                nvs[off + 32 : off + 64] = data_slot
                return
    raise KeyError(f"String key {key} (ns={ns_id}) not found in Page 1")


def cmd_status(args: argparse.Namespace) -> None:
    nvs_path = Path(args.nvs)
    parsed = parse_nvs(nvs_path.read_bytes())
    print(f"=== NVS Configuration ({nvs_path.name}) ===")
    for ns, items in parsed.items():
        if not items:
            continue
        print(f"\n[{ns}]")
        for k, meta in items.items():
            print(f"  {k:18s} = {repr(meta['value']):38s} (page={meta['page']}, slot={meta['slot']}, type={meta['type']})")


def cmd_optimize(args: argparse.Namespace) -> None:
    nvs = bytearray(ORIG_NVS.read_bytes())
    # 1. Enable Battery ADC (GPIO 17) & Charging Status (GPIO 38) in lcd_cfg (ns=5, Page 0 slots 113 & 114)
    patch_i32_or_u8_in_nvs(nvs, 0, 113, args.p_bat, is_u8=False)
    patch_i32_or_u8_in_nvs(nvs, 0, 114, args.p_chg, is_u8=False)
    # 1b. Disable WeChat bubble chat UI (u_wch = 0 at Page 1 slot 17) so only the face is shown
    patch_i32_or_u8_in_nvs(nvs, 1, 17, args.wechat, is_u8=False)
    # 1c. Control wifi.pypass_device (Page 1 slot 31, u8): 0 = unbind to personal xiaozhi.me for Voice Cloning, 1 = shared bypass
    patch_i32_or_u8_in_nvs(nvs, 1, 31, args.pypass_device, is_u8=True)
    # 2. Switch display.theme (ns=8, Page 1 slot 2) from 'light' to 'dark'
    update_string_in_page1(nvs, 8, "theme", args.theme)
    # 3. Enable weather/clock/lunar idle screen (ns=2 'config', key='enable_weather' = 1)
    slot_w = append_u8_to_page1(nvs, 2, "enable_weather", 1 if args.enable_weather else 0)
    # 4. Enable LED music visualizer & song thumbnail (ns=2 'config')
    slot_l = append_u8_to_page1(nvs, 2, "led_visualizer", 1)
    slot_t = append_u8_to_page1(nvs, 2, "thumb_song", 1)
    # 5. Optional Wi-Fi update
    if args.ssid:
        update_string_in_page1(nvs, 6, "ssid", args.ssid)
    if args.password is not None:
        update_string_in_page1(nvs, 6, "password", args.password)

    out_path = Path(args.out)
    out_path.write_bytes(nvs)
    print(
        f"Optimized NVS saved to {out_path} "
        f"(p_bat={args.p_bat}, p_chg={args.p_chg}, theme={args.theme}, "
        f"enable_weather slot={slot_w}, led_visualizer slot={slot_l}, thumb_song slot={slot_t})"
    )
    if args.flash:
        cmd = [
            "uvx", "--from", "esptool", "esptool",
            "--port", args.port, "--baud", "921600",
            "write-flash", "0x9000", str(out_path),
        ]
        subprocess.run(cmd, check=True)


# ─── Terminal Health Dashboard & Live Telemetry ──────────────────────────────

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_CYAN = "\033[36m"

LOG_RE = re.compile(r"^([IWE])\s*\((\d+)\)\s*([^:]+):\s*(.*)$")
ANSI_STRIP_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def badge(status: str) -> str:
    if status == "OK":
        return f"{ANSI_GREEN}{ANSI_BOLD}[  OK  ]{ANSI_RESET}"
    if status == "WARN":
        return f"{ANSI_YELLOW}{ANSI_BOLD}[ WARN ]{ANSI_RESET}"
    return f"{ANSI_RED}{ANSI_BOLD}[ FAIL ]{ANSI_RESET}"


def fmt_uptime(ms: int) -> str:
    sec = ms // 1000
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}h {m:02d}m {s:02d}s ({ms} ms)"


def probe_usb_and_serial(port: str, listen_sec: float = 0.6, state_cache: dict | None = None) -> dict:
    if state_cache is None:
        state_cache = {}
    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    target = port if os.path.exists(port) else (ports[0] if ports else None)
    if not target:
        return {"connected": False, "port": port, "lines": [], "error": "USB cable unplugged"}

    raw_bytes = b""
    err_msg = None
    try:
        fd = os.open(target, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            attrs = termios.tcgetattr(fd)
            # Configure raw 115200 8N1 and clear HUPCL so closing fd never drops DTR or resets ESP32-S3
            attrs[0] = 0
            attrs[1] = 0
            attrs[2] = (attrs[2] & ~(termios.CSIZE | termios.PARENB | termios.CSTOPB | termios.HUPCL)) | termios.CS8 | termios.CREAD | termios.CLOCAL
            attrs[3] = 0
            attrs[4] = termios.B115200
            attrs[5] = termios.B115200
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            t0 = time.time()
            while time.time() - t0 < listen_sec:
                r, _, _ = select.select([fd], [], [], 0.1)
                if r:
                    chunk = os.read(fd, 8192)
                    if chunk:
                        raw_bytes += chunk
        finally:
            os.close(fd)
    except Exception as exc:
        err_msg = str(exc)

    text = ANSI_STRIP_RE.sub("", raw_bytes.decode("utf-8", "replace"))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    parsed_logs = state_cache.get("recent_logs", [])
    uptime_ms = state_cache.get("uptime_ms")
    app_state = state_cache.get("app_state", "idle / ready")
    warn_count = state_cache.get("warn_count", 0)
    err_count = state_cache.get("err_count", 0)

    for ln in lines:
        m = LOG_RE.match(ln)
        if m:
            lvl, ts_str, tag, msg = m.groups()
            uptime_ms = int(ts_str)
            if lvl == "W":
                warn_count += 1
            elif lvl == "E":
                err_count += 1
            if "STATE:" in msg or "SetDeviceState" in msg or "state" in msg.lower():
                app_state = f"{tag}: {msg[:45]}"
            parsed_logs.append((lvl, uptime_ms, tag.strip(), msg.strip()))
        else:
            clean_ln = "".join(ch for ch in ln if ch.isprintable())
            if len(clean_ln) >= 4 and clean_ln.isascii():
                parsed_logs.append(("I", uptime_ms or 0, "serial", clean_ln[:72]))

    parsed_logs = parsed_logs[-8:]
    state_cache["recent_logs"] = parsed_logs
    state_cache["uptime_ms"] = uptime_ms
    state_cache["app_state"] = app_state
    state_cache["warn_count"] = warn_count
    state_cache["err_count"] = err_count

    return {
        "connected": True,
        "port": target,
        "bytes_read": len(raw_bytes),
        "uptime_ms": uptime_ms,
        "app_state": app_state,
        "warn_count": warn_count,
        "err_count": err_count,
        "recent_logs": parsed_logs,
        "error": err_msg,
    }


def _lookup_arp() -> tuple[str | None, str | None]:
    try:
        arp_out = subprocess.check_output(["arp", "-an"], text=True, timeout=2.0)
        for line in arp_out.splitlines():
            low = line.lower()
            if ROBOT_MAC_FRAG in low or ROBOT_MAC_FULL in low:
                m = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+\S+\s+on\s+(\S+)", line)
                if m:
                    return m.group(1), m.group(2)
    except Exception:
        pass
    return None, None


def probe_lan_network() -> dict:
    ip, iface = _lookup_arp()
    if not ip and ROBOT_LAN_IP:
        # Refresh expired macOS ARP table if ROBOT_IP is configured in environment
        try:
            subprocess.run(["ping", "-c", "1", "-W", "500", ROBOT_LAN_IP], capture_output=True, timeout=1.0)
        except Exception:
            pass
        ip, iface = _lookup_arp()

    if not ip:
        return {"online": False, "ip": None, "iface": None, "rtt_ms": None, "weather_portal": False}

    rtt_ms = None
    ping_ok = False
    try:
        p = subprocess.run(
            ["ping", "-c", "1", "-W", "900", ip],
            capture_output=True,
            text=True,
            timeout=1.5,
        )
        if p.returncode == 0:
            ping_ok = True
            m = re.search(r"time=([\d.]+)\s*ms", p.stdout)
            if m:
                rtt_ms = float(m.group(1))
    except Exception:
        pass

    # Check if local WeatherServer (:80) is open
    weather_portal = False
    try:
        with socket.create_connection((ip, 80), timeout=0.25):
            weather_portal = True
    except Exception:
        pass

    return {
        "online": ping_ok,
        "ip": ip,
        "iface": iface,
        "rtt_ms": rtt_ms,
        "weather_portal": weather_portal,
    }


def probe_cloud_services() -> list[dict]:
    results = []
    # 1. Tenclass WebSocket AI Host (TCP/TLS 443)
    t0 = time.time()
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection(("api.tenclass.net", 443), timeout=1.5) as sock:
            with ctx.wrap_socket(sock, server_hostname="api.tenclass.net"):
                ms = (time.time() - t0) * 1000
                results.append({"name": "Xiaozhi AI Voice WS (api.tenclass.net:443)", "ok": True, "detail": f"TLS OK ({ms:.0f} ms)"})
    except Exception as exc:
        results.append({"name": "Xiaozhi AI Voice WS (api.tenclass.net:443)", "ok": False, "detail": str(exc)[:40]})

    # 2. Open-Meteo Weather API (used by idle screen)
    t0 = time.time()
    url = "https://api.open-meteo.com/v1/forecast?latitude=21.0368&longitude=105.8347&current_weather=true"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RoBot5320-HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            ms = (time.time() - t0) * 1000
            body = json.loads(resp.read().decode("utf-8", "replace"))
            cw = body.get("current_weather", {})
            temp = cw.get("temperature", "?")
            results.append({"name": "Open-Meteo Weather API (Idle Screen)", "ok": True, "detail": f"HTTP {resp.status} ({ms:.0f} ms, {temp}°C)"})
    except urllib.error.HTTPError as he:
        results.append({"name": "Open-Meteo Weather API (Idle Screen)", "ok": False, "detail": f"HTTP {he.code} (transient upstream 503/rate-limit)"})
    except Exception as exc:
        results.append({"name": "Open-Meteo Weather API (Idle Screen)", "ok": False, "detail": str(exc)[:40]})

    return results


def audit_profile_and_theme(nvs_path: Path, theme_path: Path) -> dict:
    nvs_data = parse_nvs(nvs_path.read_bytes()) if nvs_path.exists() else {}
    lcd = nvs_data.get("lcd_cfg", {})
    cfg = nvs_data.get("config", {})
    disp = nvs_data.get("display", {})
    wifi = nvs_data.get("wifi", {})

    p_bat = lcd.get("p_bat", {}).get("value")
    p_chg = lcd.get("p_chg", {}).get("value")
    u_wch = lcd.get("u_wch", {}).get("value")
    theme_mode = disp.get("theme", {}).get("value")
    en_weather = cfg.get("enable_weather", {}).get("value")
    led_vis = cfg.get("led_visualizer", {}).get("value")
    ssid = wifi.get("ssid", {}).get("value", "?")

    theme_ok = False
    hide_subtitle = None
    has_robot2 = False
    checksum_ok = False
    n_files = 0
    if theme_path.exists():
        tb = theme_path.read_bytes()
        n_files, stored_cs, calc_len = struct.unpack("<III", tb[:12])
        data_start = 12 + n_files * 44
        calc_cs = sum(tb[12 : 12 + calc_len]) & 0xFFFF
        checksum_ok = (stored_cs == calc_cs)
        for i in range(n_files):
            ent = tb[12 + i * 44 : 12 + (i + 1) * 44]
            fname = ent[:32].split(b"\x00", 1)[0].decode("utf-8", "replace")
            if fname == "index.json":
                sz_i, off_i, _, _ = struct.unpack("<IIHH", ent[32:44])
                raw_i = tb[data_start + off_i + 2 : data_start + off_i + 2 + sz_i]
                idx_json = json.loads(raw_i.rstrip(b"\x00").decode("utf-8", "replace"))
                hide_subtitle = idx_json.get("hide_subtitle")
                emojis = idx_json.get("emoji_collection", [])
                has_robot2 = any(e.get("name") == "robot_2" for e in emojis)
                break
        theme_ok = checksum_ok and (hide_subtitle is True) and has_robot2

    checks = [
        ("Battery ADC Guard (RB5320)", p_bat == -1 and p_chg == -1, f"p_bat={p_bat}, p_chg={p_chg} (TP4056 power-only, 0% ghost disabled)"),
        ("Face-Only Mode (No Chat UI)", u_wch == 0 and hide_subtitle is True, f"u_wch={u_wch}, hide_subtitle={hide_subtitle}"),
        ("Procedural Mochi-21 Assets", theme_ok, f"{n_files} assets, checksum={'OK' if checksum_ok else 'ERR'}, robot_2={'OK' if has_robot2 else 'MISSING'}"),
        ("Dark Mode + Idle Weather + LED", theme_mode == "dark" and en_weather == 1 and led_vis == 1, f"theme={theme_mode}, weather={en_weather}, led_vis={led_vis}"),
    ]
    return {"ssid": ssid, "checks": checks}


def render_dashboard(usb: dict, lan: dict, cloud: list[dict], audit: dict, watch_mode: bool = False) -> str:
    out = []
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    out.append(f"{ANSI_BOLD}{ANSI_CYAN}╔══════════════════════════════════════════════════════════════════════════════╗{ANSI_RESET}")
    out.append(f"{ANSI_BOLD}{ANSI_CYAN}║  🤖 ROBOT.5320 HEALTH & TELEMETRY DASHBOARD  •  {now_str}          ║{ANSI_RESET}")
    out.append(f"{ANSI_BOLD}{ANSI_CYAN}╚══════════════════════════════════════════════════════════════════════════════╝{ANSI_RESET}")

    # 1. Hardware & Link Layer
    out.append(f"\n{ANSI_BOLD}1. HARDWARE & NETWORK LINK (Non-Intrusive Probe){ANSI_RESET}")
    usb_st = "OK" if usb["connected"] else "FAIL"
    usb_detail = f"{usb['port']} (passive 115200 8N1, ~HUPCL no-reset)" if usb["connected"] else usb.get("error", "Disconnected")
    out.append(f"  {badge(usb_st)} {'USB-JTAG Serial':28s} : {usb_detail}")

    lan_st = "OK" if lan["online"] else ("WARN" if lan["ip"] else "FAIL")
    if lan["online"]:
        rtt_note = f"{lan['rtt_ms']:.1f} ms (Wi-Fi powersave beacon)" if lan["rtt_ms"] and lan["rtt_ms"] > 100 else f"{lan['rtt_ms'] or 0:.1f} ms"
        lan_detail = f"IP {lan['ip']} ({lan['iface']}) • MAC {ROBOT_MAC_FULL} • RTT {rtt_note}"
    elif lan["ip"]:
        lan_detail = f"ARP cached at {lan['ip']} ({lan['iface']}) • sleeping or unreachable"
    else:
        lan_detail = f"MAC {ROBOT_MAC_FULL} not found in local ARP table"
    out.append(f"  {badge(lan_st)} {'Wi-Fi LAN (' + str(audit['ssid']) + ')':28s} : {lan_detail}")

    up_str = fmt_uptime(usb["uptime_ms"]) if usb.get("uptime_ms") else "Waiting for UART log event (press VOL/BOOT or speak)..."
    out.append(f"  {badge('OK' if usb['connected'] else 'WARN')} {'Runtime Uptime & State':28s} : {up_str} • {usb.get('app_state', 'idle')}")

    # 2. Cloud & Upstream Services
    out.append(f"\n{ANSI_BOLD}2. UPSTREAM AI & WEATHER SERVICES{ANSI_RESET}")
    for c in cloud:
        st = "OK" if c["ok"] else "WARN"
        out.append(f"  {badge(st)} {c['name']:42s} : {c['detail']}")

    # 3. Profile, NVS & Theme Integrity
    out.append(f"\n{ANSI_BOLD}3. NVS & MOCHI FULL-BLEED THEME AUDIT (ota_1: Xiaozhi v2.5.3){ANSI_RESET}")
    for name, ok, detail in audit["checks"]:
        out.append(f"  {badge('OK' if ok else 'FAIL')} {name:34s} : {detail}")

    # 4. Recent UART Logs
    out.append(f"\n{ANSI_BOLD}4. LIVE UART TELEMETRY BUFFER (warn={usb.get('warn_count', 0)}, err={usb.get('err_count', 0)}){ANSI_RESET}")
    logs = usb.get("recent_logs", [])
    if not logs:
        out.append(f"  {ANSI_DIM}(Quiet idle — no new serial log lines emitted in the last window){ANSI_RESET}")
    else:
        for lvl, ts, tag, msg in logs[-6:]:
            c = ANSI_RED if lvl == "E" else (ANSI_YELLOW if lvl == "W" else ANSI_DIM)
            out.append(f"  {c}[{lvl}] ({ts:>8d} ms) {tag:16s}: {msg[:68]}{ANSI_RESET}")

    if watch_mode:
        out.append(f"\n{ANSI_DIM}Press Ctrl+C to exit live dashboard (safe: will NOT reset or interrupt robot).{ANSI_RESET}")
    return "\n".join(out)


def cmd_health(args: argparse.Namespace) -> None:
    nvs_path = Path(args.nvs)
    theme_path = Path(args.theme_bin)
    state_cache: dict = {}
    audit = audit_profile_and_theme(nvs_path, theme_path)
    cloud = probe_cloud_services()
    last_cloud_ts = time.time()

    if not getattr(args, "watch", False):
        usb = probe_usb_and_serial(args.port, listen_sec=args.listen, state_cache=state_cache)
        lan = probe_lan_network()
        print(render_dashboard(usb, lan, cloud, audit, watch_mode=False))
        return

    try:
        while True:
            if time.time() - last_cloud_ts > 15.0:
                cloud = probe_cloud_services()
                last_cloud_ts = time.time()
            usb = probe_usb_and_serial(args.port, listen_sec=1.0, state_cache=state_cache)
            lan = probe_lan_network()
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(render_dashboard(usb, lan, cloud, audit, watch_mode=True) + "\n")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print(f"\n{ANSI_GREEN}Exited dashboard cleanly (robot continues running undisturbed).{ANSI_RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RoBot.5320 Complete Mastery CLI & Health Dashboard")
    sub = parser.add_subparsers(dest="cmd", required=False)

    p_hlth = sub.add_parser("health", help="Quick non-intrusive terminal health check (USB, Wi-Fi LAN, Cloud, NVS/Theme, UART)")
    p_hlth.add_argument("--port", default=DEFAULT_PORT)
    p_hlth.add_argument("--nvs", default=str(DEFAULT_NVS if DEFAULT_NVS.exists() else ORIG_NVS))
    p_hlth.add_argument("--theme-bin", default=str(DEFAULT_THEME))
    p_hlth.add_argument("--listen", type=float, default=0.6, help="Seconds to passively sample UART logs")
    p_hlth.add_argument("-w", "--watch", action="store_true", help="Live auto-refreshing terminal dashboard")
    p_hlth.set_defaults(func=cmd_health)

    p_dash = sub.add_parser("dashboard", help="Live auto-refreshing terminal telemetry dashboard (alias for health --watch)")
    p_dash.add_argument("--port", default=DEFAULT_PORT)
    p_dash.add_argument("--nvs", default=str(DEFAULT_NVS if DEFAULT_NVS.exists() else ORIG_NVS))
    p_dash.add_argument("--theme-bin", default=str(DEFAULT_THEME))
    p_dash.add_argument("--listen", type=float, default=1.0)
    p_dash.set_defaults(func=cmd_health, watch=True)

    p_stat = sub.add_parser("status", help="Decode and display all active NVS settings")
    p_stat.add_argument("--nvs", default=str(DEFAULT_NVS if DEFAULT_NVS.exists() else ORIG_NVS))
    p_stat.set_defaults(func=cmd_status)

    p_opt = sub.add_parser("optimize", help="Build & optionally flash optimized NVS image")
    p_opt.add_argument("--p-bat", type=int, default=-1, help="-1 = disabled (RB5320XZ78AI has no ADC divider wire)")
    p_opt.add_argument("--p-chg", type=int, default=-1, help="-1 = disabled (RB5320XZ78AI has no TP4056 CHRG# wire)")
    p_opt.add_argument("--wechat", type=int, default=0, help="0 = Face only, 1 = WeChat bubble chat UI")
    p_opt.add_argument("--pypass-device", type=int, default=1, help="0 = Unbind to personal xiaozhi.me for Voice Cloning, 1 = Shared seller bypass")
    p_opt.add_argument("--theme", choices=["dark", "light"], default="dark")
    p_opt.add_argument("--enable-weather", type=int, default=1)
    p_opt.add_argument("--ssid", default=None)
    p_opt.add_argument("--password", default=None)
    p_opt.add_argument("--out", default=str(DEFAULT_NVS))
    p_opt.add_argument("--flash", action="store_true")
    p_opt.add_argument("--port", default=DEFAULT_PORT)
    p_opt.set_defaults(func=cmd_optimize)

    args = parser.parse_args()
    if not args.cmd:
        args = parser.parse_args(["health"])
    args.func(args)


if __name__ == "__main__":
    main()
