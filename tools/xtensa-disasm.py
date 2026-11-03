#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""
xtensa-disasm.py — Zero-dependency Xtensa LX7 (ESP32-S3) disassembler & xref analyzer
for ESP-IDF application partition binaries (e.g. 07-ota1-v2.5.3-0x560000.bin).

Usage:
  python3 tools/xtensa-disasm.py disasm <bin> <start_va_hex> <end_va_hex>
  python3 tools/xtensa-disasm.py strings <bin> <substring>
  python3 tools/xtensa-disasm.py xrefs <bin> <target_va_hex>
  python3 tools/xtensa-disasm.py vtable <bin> <drom_va_hex> [count]
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

DROM_VA, DROM_OFF, DROM_LEN = 0x3C270020, 0x000020, 0x0F3000
IROM_VA, IROM_OFF, IROM_LEN = 0x42000020, 0x100020, 0x266E7C


def read_cstr(data: bytes, va: int, max_len: int = 160) -> str | None:
    if DROM_VA <= va < DROM_VA + DROM_LEN:
        off = DROM_OFF + (va - DROM_VA)
        end = data.find(b"\x00", off, off + max_len)
        if end == -1:
            end = off + max_len
        raw = data[off:end]
        if raw and all(32 <= b < 127 or b in (9, 10, 13) or b >= 128 for b in raw):
            return raw.decode("utf-8", "replace")
    return None


def disasm_range(data: bytes, start_va: int, end_va: int) -> None:
    pos = IROM_OFF + (start_va - IROM_VA)
    end_pos = IROM_OFF + (end_va - IROM_VA)
    while pos < end_pos and pos + 3 <= len(data):
        pc = IROM_VA + (pos - IROM_OFF)
        b0 = data[pos]
        op0 = b0 & 0x0F
        if op0 in (0x8, 0x9, 0xA, 0xB, 0xC, 0xD):
            b1 = data[pos + 1]
            w16 = b0 | (b1 << 8)
            r = (w16 >> 12) & 0xF
            s = (w16 >> 8) & 0xF
            t = (w16 >> 4) & 0xF
            if op0 == 0x8:
                print(f"  0x{pc:08x}: l32i.n a{t}, a{s}, {r * 4}")
            elif op0 == 0x9:
                print(f"  0x{pc:08x}: s32i.n a{t}, a{s}, {r * 4}")
            elif op0 == 0xA:
                print(f"  0x{pc:08x}: add.n a{r}, a{s}, a{t}")
            elif op0 == 0xB:
                print(f"  0x{pc:08x}: addi.n a{r}, a{s}, {-1 if t == 0 else t}")
            elif op0 == 0xC:
                i = t | ((r & 0x7) << 4)
                if (r & 0x8) == 0:
                    val = i if i < 96 else i - 128
                    print(f"  0x{pc:08x}: movi.n a{s}, {val}")
                else:
                    imm6 = t | ((r & 0x3) << 4)
                    tgt = pc + 4 + imm6
                    btype = "beqz.n" if (r & 0x4) == 0 else "bnez.n"
                    print(f"  0x{pc:08x}: {btype} a{s}, 0x{tgt:08x}")
            elif op0 == 0xD:
                if r == 0:
                    print(f"  0x{pc:08x}: mov.n a{t}, a{s}")
                elif r == 15 and t == 0:
                    print(f"  0x{pc:08x}: ret.n")
                elif r == 15 and t == 1:
                    print(f"  0x{pc:08x}: retw.n")
                else:
                    print(f"  0x{pc:08x}: narrow_d r={r} s={s} t={t}")
            pos += 2
        else:
            b1, b2 = data[pos + 1], data[pos + 2]
            w24 = b0 | (b1 << 8) | (b2 << 16)
            r = (w24 >> 12) & 0xF
            s = (w24 >> 8) & 0xF
            t = (w24 >> 4) & 0xF
            if op0 == 1:
                imm16 = (w24 >> 8) & 0xFFFF
                simm = imm16 - 0x10000
                lit_va = ((pc + 3) & ~3) + (simm << 2)
                lit_off = IROM_OFF + (lit_va - IROM_VA)
                if 0 <= lit_off <= len(data) - 4:
                    val = struct.unpack("<I", data[lit_off : lit_off + 4])[0]
                    cs = read_cstr(data, val)
                    extra = f" -> {cs!r}" if cs else ""
                    print(f"  0x{pc:08x}: l32r a{t}, [0x{lit_va:08x}] (0x{val:08x}){extra}")
                else:
                    print(f"  0x{pc:08x}: l32r a{t}, [0x{lit_va:08x}]")
            elif op0 == 2:
                imm8 = (w24 >> 16) & 0xFF
                if r == 2:
                    print(f"  0x{pc:08x}: l32i a{t}, a{s}, {imm8 * 4}")
                elif r == 6:
                    print(f"  0x{pc:08x}: s32i a{t}, a{s}, {imm8 * 4}")
                elif r == 0:
                    print(f"  0x{pc:08x}: l8ui a{t}, a{s}, {imm8}")
                elif r == 4:
                    print(f"  0x{pc:08x}: s8i a{t}, a{s}, {imm8}")
                elif r == 10:
                    simm = imm8 if imm8 < 128 else imm8 - 256
                    print(f"  0x{pc:08x}: movi a{t}, {simm | ((s & 0xF) << 8)}")
                elif r == 12:
                    simm = imm8 if imm8 < 128 else imm8 - 256
                    print(f"  0x{pc:08x}: addi a{t}, a{s}, {simm}")
                else:
                    print(f"  0x{pc:08x}: lsi r={r} a{t}, a{s}, {imm8}")
            elif op0 == 5:
                n = (b0 >> 4) & 0x3
                off18 = w24 >> 6
                if off18 & 0x20000:
                    off18 -= 0x40000
                tgt = ((pc & ~3) + (off18 << 2) + 4) & 0xFFFFFFFF
                print(f"  0x{pc:08x}: call{n * 4} 0x{tgt:08x}")
            elif op0 == 6:
                n = (b0 >> 4) & 0x3
                m = (b0 >> 6) & 0x3
                if n == 0:
                    off18 = w24 >> 6
                    if off18 & 0x20000:
                        off18 -= 0x40000
                    tgt = pc + off18 + 4
                    print(f"  0x{pc:08x}: j 0x{tgt:08x}")
                elif n == 1:
                    imm12 = w24 >> 12
                    if imm12 & 0x800:
                        imm12 -= 0x1000
                    tgt = pc + imm12 + 4
                    bnames = ["beqz", "bnez", "bltz", "bgez"]
                    print(f"  0x{pc:08x}: {bnames[m]} a{s}, 0x{tgt:08x}")
                elif n == 3:
                    imm12 = (w24 >> 12) & 0xFFF
                    print(f"  0x{pc:08x}: entry a{s}, {imm12 << 3}")
                else:
                    imm8 = (w24 >> 16) & 0xFF
                    if imm8 & 0x80:
                        imm8 -= 0x100
                    tgt = pc + imm8 + 4
                    print(f"  0x{pc:08x}: br(m={m},r={r}) a{s}, a{t}, 0x{tgt:08x}")
            elif op0 == 7:
                imm8 = (w24 >> 16) & 0xFF
                if imm8 & 0x80:
                    imm8 -= 0x100
                tgt = pc + imm8 + 4
                print(f"  0x{pc:08x}: b(r={r}) a{s}, a{t}, 0x{tgt:08x}")
            elif op0 == 0 and r == 0 and s == 0:
                n = (t >> 2) & 0x3
                m = t & 0x3
                if m == 2:
                    print(f"  0x{pc:08x}: jx/ret (t={t})")
                elif m == 3:
                    print(f"  0x{pc:08x}: callx{n * 4} a{(w24 >> 8) & 0xF}")
                else:
                    print(f"  0x{pc:08x}: op0_0 w24=0x{w24:06x}")
            else:
                print(f"  0x{pc:08x}: op0={op0} r={r} s={s} t={t} w24=0x{w24:06x}")
            pos += 3


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__.strip())
        sys.exit(0)
    if len(sys.argv) < 4:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    data = Path(sys.argv[2]).read_bytes()
    if cmd == "disasm":
        start_va = int(sys.argv[3], 16)
        end_va = int(sys.argv[4], 16)
        disasm_range(data, start_va, end_va)
    elif cmd == "strings":
        needle = sys.argv[3].encode("utf-8")
        idx = DROM_OFF
        while True:
            idx = data.find(needle, idx, DROM_OFF + DROM_LEN)
            if idx == -1:
                break
            start = data.rfind(b"\x00", max(DROM_OFF, idx - 80), idx)
            start = (start + 1) if start != -1 else idx
            end = data.find(b"\x00", idx, idx + 120)
            if end == -1:
                end = idx + 120
            va = DROM_VA + (start - DROM_OFF)
            print(f"0x{va:08x}: {data[start:end].decode('utf-8', 'replace')!r}")
            idx = end + 1
    elif cmd == "xrefs":
        target_va = int(sys.argv[3], 16)
        for pos in range(IROM_OFF, min(len(data) - 3, IROM_OFF + IROM_LEN)):
            pc = IROM_VA + (pos - IROM_OFF)
            b0 = data[pos]
            if (b0 & 0x0F) == 1:
                w24 = b0 | (data[pos + 1] << 8) | (data[pos + 2] << 16)
                simm = ((w24 >> 8) & 0xFFFF) - 0x10000
                lit_va = ((pc + 3) & ~3) + (simm << 2)
                lit_off = IROM_OFF + (lit_va - IROM_VA)
                if 0 <= lit_off <= len(data) - 4:
                    val = struct.unpack("<I", data[lit_off : lit_off + 4])[0]
                    if val == target_va:
                        print(f"L32R 0x{pc:08x} -> [0x{lit_va:08x}] = 0x{val:08x}")
            elif (b0 & 0x0F) == 5:
                w24 = b0 | (data[pos + 1] << 8) | (data[pos + 2] << 16)
                off18 = w24 >> 6
                if off18 & 0x20000:
                    off18 -= 0x40000
                tgt = ((pc & ~3) + (off18 << 2) + 4) & 0xFFFFFFFF
                if tgt == target_va:
                    print(f"CALL 0x{pc:08x} -> 0x{tgt:08x}")
    elif cmd == "vtable":
        vt_va = int(sys.argv[3], 16)
        count = int(sys.argv[4]) if len(sys.argv) > 4 else 45
        off = DROM_OFF + (vt_va - DROM_VA)
        for i in range(count):
            fn = struct.unpack("<I", data[off + i * 4 : off + (i + 1) * 4])[0]
            print(f"  vtable[{i:2d}] (+{i * 4:3d}): 0x{fn:08x}")


if __name__ == "__main__":
    main()
