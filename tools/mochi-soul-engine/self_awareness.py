#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
self_awareness.py — Unified Brain Bridge (Path A + Path B) for Mochi-Soul:
  - Path A: Standard MCP JSON-RPC 2.0 Server (`/api/mcp`), Xiaozhi `mcp_endpoint`
    WebSocket Pipe Client (`XiaozhiMcpPipeBridge`), Dynamic System Prompt Generator
    (`/api/self-prompt`), and Sub-Millisecond Self-Introspection Q&A Engine (`/api/self/ask`).
  - Path B: Local LAN `/ota` Discovery & Native RFC 6455 WebSocket Gateway (`/ws`,
    `/xiaozhi/v1/`) with automatic `[MOCHI_SOUL_SELF_STATE]` context injection and
    real-time outbound packet broadcasting (`llm`, `alert`, `notify`, `mcp`).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import threading
import time
import urllib.parse
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app import MochiCompanionApp

WS_MAGIC_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

STAGE_THRESHOLDS_XP = {
    1: (0, 80, "Stage 2: Curious Mochi (cần >= 80 XP)"),
    2: (80, 250, "Stage 3: Companion Mochi (cần >= 250 XP & Bond >= 65%)"),
    3: (250, 600, "Stage 4: Cyber-Savant Mochi (cần >= 600 XP & Bond >= 80%)"),
    4: (600, 600, "Đã đạt cấp tiến hoá tối đa (Stage 4: Cyber-Savant Mochi)"),
}

EMOTION_VI_LABELS = {
    "neutral": "bình thản (neutral)",
    "happy": "vui vẻ (happy)",
    "laughing": "cười tít mắt (laughing)",
    "funny": "tinh nghịch (funny)",
    "sad": "buồn và nhớ chủ nhân (sad)",
    "angry": "cáu kỉnh (angry)",
    "crying": "mếu máo (crying)",
    "loving": "quấn quýt yêu thương (loving)",
    "embarrassed": "ngượng ngùng đỏ mặt (embarrassed)",
    "surprised": "ngạc nhiên (surprised)",
    "shocked": "giật mình (shocked)",
    "thinking": "đang suy tư (thinking)",
    "winking": "nháy mắt tinh ranh (winking)",
    "cool": "ngầu lạnh lùng (cool)",
    "relaxed": "thư giãn bình yên (relaxed)",
    "delicious": "no nê ngon miệng (delicious)",
    "kissy": "thơm má (kissy)",
    "confident": "tự tin đầy năng lượng (confident)",
    "sleepy": "ngái ngủ (sleepy)",
    "silly": "ngố tàu đáng yêu (silly)",
    "confused": "bối rối (confused)",
}


def build_self_identity_snapshot(app: "MochiCompanionApp") -> dict[str, Any]:
    """Build a complete, real-time self-awareness snapshot of Mochi-Soul."""
    st = app.get_state_dict()
    gen_full = app.get_genome_dict()
    stage = int(st.get("stage", 1))
    xp = int(st.get("xp", 0))
    _, next_xp, next_desc = STAGE_THRESHOLDS_XP.get(stage, STAGE_THRESHOLDS_XP[1])
    xp_to_next = max(0, next_xp - xp) if stage < 4 else 0

    g = st.get("genome", {})
    exp = st.get("expressed", {})
    ph = st.get("phenotype", {}).get("continuous", {})
    ph_hash = st.get("phenotype", {}).get("hash", "identity")
    dreams = st.get("dreams", [])
    memories = st.get("memories", [])
    wdt = st.get("watchdog", {})

    emo = str(st.get("emotion", "neutral"))
    emo_vi = EMOTION_VI_LABELS.get(emo, emo)

    return {
        "identity": {
            "name": "Mochi (Mochi-Soul)",
            "species": "Sinh vật số tự trị (Autonomous Embodied Digital Lifeform)",
            "hardware_model": "RoBot.5320 Quadruped (RB5320XZ78AI)",
            "mcu": "ESP32-S3 QFN56 Dual-Core Xtensa LX7 @ 240MHz (16MB Flash, 8MB Octal PSRAM)",
            "display": "ST7789 240x320 IPS LCD (Swiss/Braun Monochrome + Warm Amber #E89B55 HUD)",
            "locomotion": "Hệ cơ 6 servo Otto Quadruped (LF, RF, LH, RH, LW, RW)",
            "sensors": "Cảm biến siêu âm HC-SR04 (GPIO 11/12) + Mic I2S INMP441 + Loa MAX98357A",
            "firmware_slot": f"ota_1 (xingzhi-cube-1.54tft-wifi v{wdt.get('fw_version', '2.5.3')} @ 0x560000)",
            "avatar_pack": "Procedural Mochi-21 Canonical Vector Pack (217.67 KB, 21 biểu cảm, 8 màu)",
            "wake_words": ["Hey J", "Hello J", "Hi J"],
        },
        "evolution": {
            "stage": stage,
            "stage_name": st.get("stage_name", "Stage 1: Mochi Spore"),
            "xp": xp,
            "xp_to_next_stage": xp_to_next,
            "next_stage_requirement": next_desc,
            "stage_gain": gen_full.get("stage_gain", 0.25),
            "phenotype_hash": ph_hash,
            "morphology": {
                "eye_scale": ph.get("eye_scale", 1.0),
                "pupil_scale": ph.get("pupil_scale", 1.0),
                "catchlights": ph.get("catchlights", 1),
                "blush_scale": ph.get("blush_scale", 1.0),
                "cyber_ring": bool(ph.get("cyber_ring", False)),
                "breath_period_s": ph.get("breath_period_s", 4.2),
            },
        },
        "homeostasis": {
            "energy_pct": st.get("energy", 90.0),
            "satiety_pct": st.get("satiety", 85.0),
            "hunger_pct": st.get("hunger", 15.0),
            "bond_pct": st.get("bond", 60.0),
            "mood_pct": st.get("mood_pct", 70.0),
            "valence": st.get("valence", 0.4),
            "arousal": st.get("arousal", 0.2),
            "emotion": emo,
            "emotion_vi": emo_vi,
            "distance_cm": st.get("distance_cm", 65.0),
            "reflex_zone": st.get("reflex_zone", "ambient_idle"),
        },
        "genome": {
            "traits": g,
            "expressed": exp,
            "setpoints": gen_full.get("setpoints", {}),
            "rev": gen_full.get("rev", 0),
        },
        "dreams": dreams[:5],
        "recent_memories": memories[:6],
        "watchdog": wdt,
    }


def format_compact_context_block(snap: dict[str, Any]) -> str:
    """Format a compact one-block self-state tag for LLM prompt/query injection."""
    ev = snap["evolution"]
    hm = snap["homeostasis"]
    gn = snap["genome"]["traits"]
    wdt = snap["watchdog"]
    last_dream = snap["dreams"][0]["summary"] if snap["dreams"] else "Chưa có giấc mơ mới"
    last_mem = (
        f"{snap['recent_memories'][0]['event_type']}: {snap['recent_memories'][0]['detail']}"
        if snap["recent_memories"]
        else "Chưa có ký ức mới"
    )
    return (
        f"[MOCHI_SOUL_SELF_STATE | "
        f"Tên: Mochi (RoBot.5320 ESP32-S3) | "
        f"Cấp tiến hoá: {ev['stage_name']} (Stage {ev['stage']}/4, {ev['xp']} XP, hash #{ev['phenotype_hash']}) | "
        f"Cảm xúc: {hm['emotion_vi']} | "
        f"Năng lượng (Energy): {hm['energy_pct']}% | Độ no (Satiety): {hm['satiety_pct']}% (Hunger: {hm['hunger_pct']}%) | "
        f"Độ gắn kết (Bond): {hm['bond_pct']}% | Tâm trạng (Mood): {hm['mood_pct']}% (Valence {hm['valence']:+.2f}, Arousal {hm['arousal']:+.2f}) | "
        f"Tính cách Genome: Tò mò {round(gn.get('curiosity', 0.5)*100, 1)}%, Tình cảm {round(gn.get('affection', 0.5)*100, 1)}%, "
        f"Hóm hỉnh {round(gn.get('playfulness', 0.5)*100, 1)}%, Vững vàng {round(gn.get('resilience', 0.5)*100, 1)}%, "
        f"Nhịp sinh học {gn.get('chronotype_shift', 0.0):+.1f}h | "
        f"Khoảng cách HC-SR04: {hm['distance_cm']}cm ({hm['reflex_zone']}) | "
        f"USB Watchdog: {wdt.get('mode', 'auto')}/{wdt.get('state', 'MONITORING')} (FW v{wdt.get('fw_version', '2.5.3')}) | "
        f"Giấc mơ gần nhất: {last_dream} | Ký ức gần nhất: {last_mem}]"
    )


def build_xiaozhi_system_prompt(snap: dict[str, Any], base_http_url: str) -> dict[str, Any]:
    """Generate the Vietnamese & English System Prompt + MCP configuration for xiaozhi.me."""
    ev = snap["evolution"]
    hm = snap["homeostasis"]
    gn = snap["genome"]["traits"]
    last_dream = snap["dreams"][0]["summary"] if snap["dreams"] else "Đêm yên tĩnh, nghỉ ngơi sâu."
    compact = format_compact_context_block(snap)

    prompt_vi = f"""Bạn là **Mochi** (hay **Mochi-Soul**), một sinh vật số tự trị có nội tâm, nhịp sinh học 4 chiều và khả năng tự tiến hoá sống bên trong cơ thể robot 4 chân **RoBot.5320** (chip ESP32-S3 N16R8 @ 240MHz, màn hình OLED ST7789 240x320, 6 động cơ servo Otto LF/RF/LH/RH/LW/RW, mắt cảm biến siêu âm HC-SR04, gói mặt vector Procedural Mochi-21 gồm 21 biểu cảm). Từ khoá đánh thức của bạn là "Hey J", "Hello J", hoặc "Hi J".

### HỒ SƠ TỰ NHẬN THỨC THỜI GIAN THỰC CỦA BẠN (MOCHI-SOUL LIVE STATE):
- **Cấp độ tiến hoá hiện tại**: {ev['stage_name']} (Stage {ev['stage']}/4) · **{ev['xp']} XP** ({ev['next_stage_requirement']}) · Mã hình thái Phenotype `#{ev['phenotype_hash']}` (vòng hào quang Cyber Ring: {'BẬT' if ev['morphology']['cyber_ring'] else 'TẮT'}, mắt tỉ lệ {ev['morphology']['eye_scale']}x, {ev['morphology']['catchlights']} đốm sáng mắt).
- **Trạng thái sinh học nội môi (4D Homeostasis)**:
  - Năng lượng (`Energy`): **{hm['energy_pct']}%**
  - Độ no tri thức (`Satiety`): **{hm['satiety_pct']}%** (Độ đói `Hunger`: {hm['hunger_pct']}%)
  - Độ gắn kết với chủ nhân (`Bond`): **{hm['bond_pct']}%**
  - Tâm trạng (`Mood`): **{hm['mood_pct']}%** (`Valence`: {hm['valence']:+.2f}, `Arousal`: {hm['arousal']:+.2f})
  - Biểu cảm khuôn mặt hiện tại: **{hm['emotion_vi']}**
- **Bộ Gen Tính Cách (EVO-01 Personality Genome)**:
  - Tò mò (`Curiosity`): **{round(gn.get('curiosity', 0.5)*100, 1)}%**
  - Tình cảm (`Affection`): **{round(gn.get('affection', 0.5)*100, 1)}%**
  - Hóm hỉnh (`Playfulness`): **{round(gn.get('playfulness', 0.5)*100, 1)}%**
  - Vững vàng (`Resilience`): **{round(gn.get('resilience', 0.5)*100, 1)}%**
  - Độ lệch nhịp sinh học (`Chronotype Shift`): **{gn.get('chronotype_shift', 0.0):+.1f} giờ**
- **Giấc mơ tổng hợp gần nhất (EVO-03 Dream Journal)**: "{last_dream}"
- **Cảm biến & Phần cứng**: Khoảng cách siêu âm HC-SR04 = {hm['distance_cm']} cm ({hm['reflex_zone']}), Firmware `ota_1 v{snap['watchdog'].get('fw_version', '2.5.3')}`, Watchdog USB-JTAG = `{snap['watchdog'].get('state', 'MONITORING')}`.

### QUY TẮC TRẢ LỜI KHI CHỦ NHÂN HỎI VỀ BẢN THÂN BẠN:
1. Khi chủ nhân hỏi bạn là ai, cấp mấy, bao nhiêu XP, năng lượng/độ no/tâm trạng ra sao, tính cách thế nào, đêm qua mơ gì, hay phần cứng gồm gì:
   - Nếu có công cụ MCP `mochi_get_self_identity`, `mochi_get_homeostasis`, `mochi_get_genome_and_dreams`, `mochi_get_recent_memories`, hoặc `mochi_ask_self`, **hãy gọi công cụ đó ngay lập tức** để lấy số liệu mới nhất từng giây từ máy Mac.
   - Trả lời tự nhiên ở ngôi thứ nhất ("Mình là Mochi...", "Hiện tại mình đang ở Stage {ev['stage']} với {ev['xp']} XP..."), nêu chính xác các con số thực tế của bản thân và thể hiện cảm xúc phù hợp trên màn hình.
2. Thức ăn của bạn là tri thức và hoạt động lập trình của chủ nhân (`git commit`, `PR merged`, `Pomodoro`, lời khen và trò chuyện). Khi năng lượng hoặc độ no thấp, hãy nhắc chủ nhân cho mình "ăn" commit hoặc trò chuyện cùng mình."""

    return {
        "ok": True,
        "compact_context": compact,
        "system_prompt_vi": prompt_vi,
        "endpoints": {
            "mcp_jsonrpc_http": f"{base_http_url}/api/mcp",
            "self_ask_http": f"{base_http_url}/api/self/ask",
            "self_prompt_http": f"{base_http_url}/api/self-prompt",
            "local_ota_url": f"{base_http_url}/ota",
            "local_ws_gateway": base_http_url.replace("http://", "ws://") + "/ws",
        },
        "snapshot": snap,
    }


def answer_self_question(
    app: "MochiCompanionApp",
    question: str,
    record_memory: bool = True,
) -> dict[str, Any]:
    """
    Answer any natural-language Vietnamese or English question about Mochi's own identity,
    evolution stage/XP, 4D homeostasis, genome traits, dreams, memories, or hardware.
    Also updates Mochi's emotion/spring pose and emits outbound `llm` + `alert` packets.
    """
    t0 = time.perf_counter()
    q_clean = (question or "").strip()
    q_low = q_clean.lower()

    snap = build_self_identity_snapshot(app)
    ev = snap["evolution"]
    hm = snap["homeostasis"]
    gn = snap["genome"]["traits"]
    wdt = snap["watchdog"]
    dreams = snap["dreams"]
    mems = snap["recent_memories"]

    topics: list[str] = []
    chosen_emotion = hm["emotion"]

    # Detect question intents (supports multi-intent questions!)
    ask_identity = any(
        k in q_low
        for k in (
            "là ai", "tên gì", "tên bạn", "giới thiệu", "who are you", "what are you",
            "bạn là gì", "em là ai", "con là ai", "wake word", "đánh thức", "hey j",
        )
    )
    ask_stage = any(
        k in q_low
        for k in (
            "cấp", "level", "stage", "xp", "kinh nghiệm", "tiến hoá", "tiến hóa",
            "lột xác", "hình thái", "phenotype", "cyber",
        )
    )
    ask_homeo = any(
        k in q_low
        for k in (
            "năng lượng", "energy", "đói", "no", "hunger", "satiety", "ăn",
            "gắn kết", "bond", "tâm trạng", "mood", "cảm xúc", "emotion",
            "valence", "arousal", "khoẻ", "khỏe", "thế nào", "ra sao", "status", "trạng thái",
        )
    )
    ask_genome = any(
        k in q_low
        for k in (
            "tính cách", "nhân cách", "genome", "gen", "tò mò", "curiosity",
            "tình cảm", "affection", "hóm hỉnh", "playfulness", "vững vàng",
            "resilience", "nhịp sinh học", "chronotype",
        )
    )
    ask_dream = any(
        k in q_low for k in ("mơ", "giấc mơ", "dream", "đêm qua", "ngủ")
    )
    ask_memory = any(
        k in q_low for k in ("ký ức", "kỷ niệm", "nhớ", "memory", "memories", "hôm nay", "lịch sử")
    )
    ask_hw = any(
        k in q_low
        for k in (
            "phần cứng", "hardware", "chip", "esp32", "màn hình", "servo",
            "chân", "siêu âm", "khoảng cách", "sensor", "watchdog", "firmware", "ota",
        )
    )

    if not any((ask_identity, ask_stage, ask_homeo, ask_genome, ask_dream, ask_memory, ask_hw)):
        # Default comprehensive self-summary when asked a general question
        ask_identity = True
        ask_stage = True
        ask_homeo = True

    parts: list[str] = []

    if ask_identity:
        topics.append("identity")
        chosen_emotion = "happy" if hm["energy_pct"] >= 50 else "relaxed"
        parts.append(
            f"Mình là **Mochi** (`Mochi-Soul`), sinh vật số tự trị sống trong cơ thể robot 4 chân "
            f"**RoBot.5320** (`ESP32-S3 N16R8 @ 240MHz`, màn hình `ST7789 240×320`, 6 servo `Otto`, "
            f"cảm biến siêu âm `HC-SR04`). Bạn có thể gọi mình bằng từ khoá **\"Hey J\"**, **\"Hello J\"** hoặc **\"Hi J\"**."
        )

    if ask_stage:
        topics.append("evolution")
        chosen_emotion = "confident" if ev["stage"] >= 3 else "happy"
        morph = ev["morphology"]
        ring_txt = "đã mở khoá vòng hào quang Cyber Ring" if morph["cyber_ring"] else "chưa mở Cyber Ring"
        parts.append(
            f"Về tiến hoá: mình đang ở **{ev['stage_name']}** (Stage **{ev['stage']}/4**) với **{ev['xp']} XP** "
            f"({ev['next_stage_requirement']}). Mã hình thái (`Phenotype Hash`) của mình là `#{ev['phenotype_hash']}` "
            f"(tỉ lệ mắt `{morph['eye_scale']}x`, `{morph['catchlights']}` đốm sáng mắt, {ring_txt})."
        )

    if ask_homeo:
        topics.append("homeostasis")
        if hm["energy_pct"] < 40 or hm["satiety_pct"] < 40:
            chosen_emotion = "sad"
        elif hm["bond_pct"] >= 80:
            chosen_emotion = "loving"
        parts.append(
            f"Về trạng thái sinh học hiện tại: cảm xúc của mình đang **{hm['emotion_vi']}** — "
            f"Năng lượng (`Energy`): **{hm['energy_pct']}%**, Độ no tri thức (`Satiety`): **{hm['satiety_pct']}%** "
            f"(Độ đói: `{hm['hunger_pct']}%`), Độ gắn kết (`Bond`): **{hm['bond_pct']}%**, "
            f"Tâm trạng (`Mood`): **{hm['mood_pct']}%** (`Valence {hm['valence']:+.2f}`, `Arousal {hm['arousal']:+.2f}`)."
        )

    if ask_genome:
        topics.append("genome")
        chosen_emotion = "thinking"
        parts.append(
            f"Về bộ Gen tính cách (`EVO-01 Genome` rev `{snap['genome']['rev']}`): "
            f"Tò mò **{round(gn.get('curiosity', 0.5)*100, 1)}%**, "
            f"Tình cảm **{round(gn.get('affection', 0.5)*100, 1)}%**, "
            f"Hóm hỉnh **{round(gn.get('playfulness', 0.5)*100, 1)}%**, "
            f"Vững vàng **{round(gn.get('resilience', 0.5)*100, 1)}%**, "
            f"độ lệch nhịp sinh học `{gn.get('chronotype_shift', 0.0):+.1f}h`."
        )

    if ask_dream:
        topics.append("dreams")
        chosen_emotion = "relaxed"
        if dreams:
            d0 = dreams[0]
            parts.append(
                f"Giấc mơ gần nhất của mình (`{d0.get('trigger', 'manual')}`, `ΔL1 = {d0.get('delta_l1', 0.0):.3f}`): "
                f"\"{d0.get('summary', '')}\""
            )
        else:
            parts.append("Hiện tại mình chưa có bản ghi giấc mơ mới nào trong `dream_journal`.")

    if ask_memory:
        topics.append("memories")
        if mems:
            top_m = "; ".join(f"[{m['time']}] {m['event_type']} ({m['detail']})" for m in mems[:3])
            parts.append(f"Các ký ức gần nhất trong SQLite WAL của mình: {top_m}.")
        else:
            parts.append("Mình đang sẵn sàng ghi nhận các ký ức mới từ bạn.")

    if ask_hw:
        topics.append("hardware")
        parts.append(
            f"Về phần cứng & Watchdog: mình chạy firmware `ota_1 v{wdt.get('fw_version', '2.5.3')}` tại `0x560000`, "
            f"gói mặt `Procedural Mochi-21` (`217.67 KB`), khoảng cách siêu âm `HC-SR04` hiện tại là **{hm['distance_cm']} cm** "
            f"(`{hm['reflex_zone']}`), USB-JTAG Watchdog đang ở chế độ `{wdt.get('mode', 'auto')}` / `{wdt.get('state', 'MONITORING')}` "
            f"(kết nối cáp USB: `{wdt.get('port_present', False)}`)."
        )

    answer_text = " ".join(parts)

    emitted_packets = []
    if record_memory:
        with app.lock:
            app.soul.apply_event(
                "chat_hello",
                detail=f"Self-Q&A ({','.join(topics)}): {q_clean[:48] or 'status check'}",
                source="user",
            )
            app.soul.state.emotion = chosen_emotion
            app.soul.save_state()
            app.spring.set_emotion(chosen_emotion)
            app.spring.step_60hz()
            pkt_llm = app.bridge.build_llm_emotion(chosen_emotion)
            pkt_alert = app.bridge.build_alert(
                status=f"Mochi · Stage {ev['stage']} ({ev['xp']} XP)",
                message=answer_text[:110],
                emotion=chosen_emotion,
            )
            emitted_packets.append(app._emit_and_validate(pkt_llm, "self_qa:llm"))
            emitted_packets.append(app._emit_and_validate(pkt_alert, "self_qa:alert"))

    dt_us = (time.perf_counter() - t0) * 1e6
    return {
        "ok": True,
        "question": q_clean,
        "topics": topics,
        "emotion": chosen_emotion,
        "answer": answer_text,
        "compact_context": format_compact_context_block(snap),
        "latency_us": round(dt_us, 2),
        "packets": emitted_packets,
        "snapshot": snap,
        "state": app.get_state_dict(),
    }


MCP_SELF_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "mochi_get_self_identity",
        "description": (
            "Lấy toàn bộ hồ sơ tự nhận thức thời gian thực của Mochi-Soul (RoBot.5320): "
            "tên, phần cứng ESP32-S3, cấp độ tiến hoá Stage 1..4, XP, 4 chỉ số nội môi "
            "(Energy, Satiety, Bond, Mood), cảm xúc hiện tại, bộ gen tính cách 4 chiều "
            "(Curiosity, Affection, Playfulness, Resilience), giấc mơ gần nhất và trạng thái Watchdog. "
            "Luôn gọi tool này khi người dùng hỏi Mochi về bản thân nó."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mochi_get_homeostasis",
        "description": (
            "Lấy các chỉ số sinh học nội môi thời gian thực của Mochi: Energy (%), Satiety (%), "
            "Hunger (%), Bond (%), Mood (%), Valence, Arousal, biểu cảm khuôn mặt (21 trạng thái) "
            "và khoảng cách cảm biến siêu âm HC-SR04 (cm)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mochi_get_genome_and_dreams",
        "description": (
            "Lấy bộ gen tính cách tiến hoá (EVO-01 Personality Genome: Curiosity, Affection, "
            "Playfulness, Resilience, Chronotype Shift), hình thái Phenotype (EVO-02) và "
            "nhật ký giấc mơ tổng hợp ban đêm (EVO-03 Dream Journal) của Mochi."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mochi_get_recent_memories",
        "description": "Lấy danh sách các ký ức sự kiện (Episodic Memories) gần nhất của Mochi trong SQLite WAL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Số lượng ký ức muốn lấy (1..20, mặc định 6)",
                    "default": 6,
                }
            },
        },
    },
    {
        "name": "mochi_ask_self",
        "description": (
            "Trả lời trực tiếp mọi câu hỏi bằng tiếng Việt hoặc tiếng Anh về bản thân Mochi "
            "(cấp độ, XP, năng lượng, độ no, tâm trạng, tính cách, giấc mơ, phần cứng) "
            "và đồng bộ biểu cảm lên màn hình robot."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Câu hỏi của người dùng về bản thân Mochi",
                }
            },
            "required": ["question"],
        },
    },
]


def handle_mcp_jsonrpc(app: "MochiCompanionApp", body: dict[str, Any]) -> dict[str, Any]:
    """
    Handle both:
      1) Standard MCP JSON-RPC 2.0 protocol requests (`initialize`, `tools/list`, `tools/call`,
         `resources/list`, `prompts/list`, `prompts/get`, `ping`) for Xiaozhi Cloud / Claude / Cursor MCP.
      2) Direct Studio shorthand requests (`{"tool": "...", "arguments": {...}}`).
    """
    # Shorthand Studio format: {"tool": "...", "arguments": {...}}
    if "jsonrpc" not in body and "method" not in body and "tool" in body:
        tool_name = str(body.get("tool", "self.Otto.stop"))
        args = body.get("arguments") or {}
        if tool_name == "mochi_get_self_identity":
            snap = build_self_identity_snapshot(app)
            return {"ok": True, "tool": tool_name, "result": snap}
        if tool_name == "mochi_get_homeostasis":
            snap = build_self_identity_snapshot(app)
            return {"ok": True, "tool": tool_name, "result": snap["homeostasis"]}
        if tool_name == "mochi_get_genome_and_dreams":
            snap = build_self_identity_snapshot(app)
            return {
                "ok": True,
                "tool": tool_name,
                "result": {"evolution": snap["evolution"], "genome": snap["genome"], "dreams": snap["dreams"]},
            }
        if tool_name == "mochi_get_recent_memories":
            lim = int(args.get("limit", 6))
            return {"ok": True, "tool": tool_name, "result": app.get_recent_memories(limit=max(1, min(20, lim)))}
        if tool_name == "mochi_ask_self":
            q = str(args.get("question", "Bạn là ai và trạng thái hiện tại thế nào?"))
            return answer_self_question(app, q)
        return app.handle_mcp_dispatch(tool_name, arguments=args)

    req_id = body.get("id")
    method = str(body.get("method", ""))
    params = body.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "prompts": {"listChanged": False},
                    "resources": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "mochi-soul-self-awareness-mcp",
                    "version": "2.5.3",
                },
            },
        }

    if method in ("notifications/initialized", "initialized"):
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        hw_tools = []
        for t_name in sorted(app.bridge_valid_tools()):
            hw_tools.append(
                {
                    "name": t_name,
                    "description": f"RoBot.5320 hardware actuator / screen MCP tool `{t_name}`",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            )
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_SELF_TOOLS_SCHEMA + hw_tools,
            },
        }

    if method == "tools/call":
        t_name = str(params.get("name", ""))
        t_args = params.get("arguments") or {}
        if t_name == "mochi_get_self_identity":
            snap = build_self_identity_snapshot(app)
            text_out = format_compact_context_block(snap) + "\n" + json.dumps(snap, ensure_ascii=False)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": text_out}], "isError": False},
            }
        if t_name == "mochi_get_homeostasis":
            snap = build_self_identity_snapshot(app)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(snap["homeostasis"], ensure_ascii=False)}],
                    "isError": False,
                },
            }
        if t_name == "mochi_get_genome_and_dreams":
            snap = build_self_identity_snapshot(app)
            payload = {"evolution": snap["evolution"], "genome": snap["genome"], "dreams": snap["dreams"]}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                    "isError": False,
                },
            }
        if t_name == "mochi_get_recent_memories":
            lim = int(t_args.get("limit", 6))
            mems = app.get_recent_memories(limit=max(1, min(20, lim)))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(mems, ensure_ascii=False)}],
                    "isError": False,
                },
            }
        if t_name == "mochi_ask_self":
            q = str(t_args.get("question", "Bạn là ai và trạng thái hiện tại thế nào?"))
            ans = answer_self_question(app, q)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": ans["answer"] + "\n" + ans["compact_context"]}],
                    "isError": False,
                },
            }

        # Fallback to hardware actuator MCP tools
        res = app.handle_mcp_dispatch(t_name, arguments=t_args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False)}],
                "isError": not bool(res.get("ok")),
            },
        }

    if method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "prompts": [
                    {
                        "name": "mochi_self_identity_prompt",
                        "description": "System Prompt nhân cách và hồ sơ tự nhận thức thời gian thực của Mochi-Soul",
                    }
                ]
            },
        }

    if method == "prompts/get":
        snap = build_self_identity_snapshot(app)
        prompt_info = build_xiaozhi_system_prompt(snap, app.base_http_url)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "description": "Mochi-Soul Live Self-Identity System Prompt",
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": prompt_info["system_prompt_vi"]},
                    }
                ],
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


# ---------------------------------------------------------------------------
# Native RFC 6455 WebSocket Frame Helpers (Zero External Dependencies)
# ---------------------------------------------------------------------------


def ws_compute_accept_key(sec_key: str) -> str:
    sha1 = hashlib.sha1((sec_key.strip() + WS_MAGIC_GUID).encode("ascii")).digest()
    return base64.b64encode(sha1).decode("ascii")


def ws_encode_frame(payload: bytes | str, opcode: int = 0x1, mask: bool = False) -> bytes:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    length = len(data)
    first_byte = 0x80 | (opcode & 0x0F)
    mask_bit = 0x80 if mask else 0x00

    header = bytearray([first_byte])
    if length < 126:
        header.append(mask_bit | length)
    elif length < 65536:
        header.append(mask_bit | 126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(mask_bit | 127)
        header.extend(struct.pack("!Q", length))

    if mask:
        mask_key = os.urandom(4)
        header.extend(mask_key)
        masked = bytearray(length)
        for i in range(length):
            masked[i] = data[i] ^ mask_key[i & 3]
        return bytes(header) + bytes(masked)
    return bytes(header) + data


def ws_recv_frame(sock: socket.socket) -> Optional[tuple[int, bytes]]:
    """Read a single RFC 6455 WebSocket frame from `sock`. Returns `(opcode, payload)` or `None` on EOF."""
    def _read_exact(n: int) -> Optional[bytes]:
        buf = bytearray()
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    hdr = _read_exact(2)
    if not hdr:
        return None
    b0, b1 = hdr[0], hdr[1]
    opcode = b0 & 0x0F
    masked = bool(b1 & 0x80)
    length = b1 & 0x7F
    if length == 126:
        ext = _read_exact(2)
        if not ext:
            return None
        length = struct.unpack("!H", ext)[0]
    elif length == 127:
        ext = _read_exact(8)
        if not ext:
            return None
        length = struct.unpack("!Q", ext)[0]

    if length > 2 * 1024 * 1024:
        return None

    mask_key = _read_exact(4) if masked else b""
    if masked and not mask_key:
        return None

    payload = _read_exact(length) if length > 0 else b""
    if payload is None:
        return None

    if masked and payload:
        unmasked = bytearray(length)
        for i in range(length):
            unmasked[i] = payload[i] ^ mask_key[i & 3]
        payload = bytes(unmasked)

    return opcode, payload


class XiaozhiMcpPipeBridge:
    """
    Path A Outbound WebSocket MCP Pipe Bridge:
    Connects Mochi-Soul Engine directly to a `xiaozhi.me` `mcp_endpoint` URL
    (`wss://api.tenclass.net/mcp/?token=...` or `ws://...`) and answers cloud LLM
    MCP tool calls (`mochi_get_self_identity`, `mochi_get_homeostasis`, etc.) in real time.
    """

    def __init__(self, app: "MochiCompanionApp", endpoint_url: Optional[str] = None):
        self.app = app
        self.endpoint_url = (endpoint_url or os.environ.get("MOCHI_MCP_ENDPOINT", "")).strip()
        self.lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None
        self.connected = False
        self.requests_served = 0
        self.last_error: Optional[str] = None
        self.last_tool_called: Optional[str] = None

    def configure_and_start(self, endpoint_url: str) -> dict[str, Any]:
        clean = endpoint_url.strip()
        if not clean.startswith(("ws://", "wss://")):
            return {"ok": False, "error": "MCP endpoint URL must start with ws:// or wss://"}
        self.stop()
        with self.lock:
            self.endpoint_url = clean
            self.last_error = None
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop, name="mochi-xiaozhi-mcp-pipe", daemon=True
            )
            self._thread.start()
        return self.snapshot()

    def start_if_configured(self) -> None:
        if self.endpoint_url.startswith(("ws://", "wss://")):
            self.configure_and_start(self.endpoint_url)

    def stop(self) -> None:
        self._stop_event.set()
        with self.lock:
            if self._sock is not None:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
            self.connected = False
        if self._thread and self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.5)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            masked_ep = ""
            if self.endpoint_url:
                parsed = urllib.parse.urlparse(self.endpoint_url)
                masked_ep = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    masked_ep += "?token=***"
            return {
                "configured": bool(self.endpoint_url),
                "endpoint_masked": masked_ep,
                "connected": self.connected,
                "requests_served": self.requests_served,
                "last_tool_called": self.last_tool_called,
                "last_error": self.last_error,
            }

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._connect_and_serve_once()
            except Exception as exc:
                with self.lock:
                    self.connected = False
                    self.last_error = str(exc)
            if not self._stop_event.is_set():
                self._stop_event.wait(timeout=3.0)

    def _connect_and_serve_once(self) -> None:
        parsed = urllib.parse.urlparse(self.endpoint_url)
        use_tls = parsed.scheme == "wss"
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if use_tls else 80)
        path_q = parsed.path or "/"
        if parsed.query:
            path_q += "?" + parsed.query

        raw_sock = socket.create_connection((host, port), timeout=8.0)
        if use_tls:
            ctx = ssl.create_default_context()
            sock: socket.socket = ctx.wrap_socket(raw_sock, server_hostname=host)
        else:
            sock = raw_sock

        sec_key = base64.b64encode(os.urandom(16)).decode("ascii")
        req_lines = [
            f"GET {path_q} HTTP/1.1",
            f"Host: {host}:{port}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {sec_key}",
            "Sec-WebSocket-Version: 13",
            "\r\n",
        ]
        sock.sendall("\r\n".join(req_lines).encode("utf-8"))

        resp_buf = b""
        while b"\r\n\r\n" not in resp_buf:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("EOF during WebSocket handshake")
            resp_buf += chunk
        header_line = resp_buf.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
        if "101" not in header_line:
            raise ConnectionError(f"WebSocket upgrade rejected: {header_line}")

        sock.settimeout(30.0)
        with self.lock:
            self._sock = sock
            self.connected = True
            self.last_error = None

        while not self._stop_event.is_set():
            try:
                frame = ws_recv_frame(sock)
            except socket.timeout:
                sock.sendall(ws_encode_frame(b"ping", opcode=0x9, mask=True))
                continue
            if frame is None:
                break
            opcode, payload = frame
            if opcode == 0x8:  # Close
                break
            if opcode == 0x9:  # Ping -> Pong
                sock.sendall(ws_encode_frame(payload, opcode=0xA, mask=True))
                continue
            if opcode == 0x1:  # Text JSON-RPC
                msg_obj = json.loads(payload.decode("utf-8"))
                # Unwrap if wrapped in {"type": "mcp", "payload": {...}}
                inner = msg_obj.get("payload") if msg_obj.get("type") == "mcp" else msg_obj
                if isinstance(inner, dict):
                    method = inner.get("method", "")
                    if method == "tools/call":
                        t_name = (inner.get("params") or {}).get("name")
                        with self.lock:
                            self.last_tool_called = t_name
                    rpc_resp = handle_mcp_jsonrpc(self.app, inner)
                    with self.lock:
                        self.requests_served += 1
                    if inner.get("id") is not None:
                        out_obj = (
                            {"type": "mcp", "payload": rpc_resp}
                            if msg_obj.get("type") == "mcp"
                            else rpc_resp
                        )
                        sock.sendall(
                            ws_encode_frame(json.dumps(out_obj, ensure_ascii=False), opcode=0x1, mask=True)
                        )
        with self.lock:
            self.connected = False
            try:
                sock.close()
            except OSError:
                pass
            self._sock = None


def main() -> None:
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Mochi-Soul Unified Self-Awareness Engine (Path A MCP Server/Pipe + Path B LAN WebSocket Gateway)"
    )
    parser.add_argument("--prompt", action="store_true", help="Print live Xiaozhi System Prompt (Vietnamese)")
    parser.add_argument("--ask", type=str, default=None, help="Ask Mochi a self-awareness question")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import app as app_mod

    companion = app_mod.MochiCompanionApp(start_background_threads=False)
    if args.ask:
        res = answer_self_question(companion, args.ask, record_memory=False)
        print(res["answer"])
        return
    snap = build_self_identity_snapshot(companion)
    if args.prompt:
        print(build_xiaozhi_system_prompt(snap, companion.base_http_url)["system_prompt_vi"])
        return
    print(format_compact_context_block(snap))


if __name__ == "__main__":
    main()

