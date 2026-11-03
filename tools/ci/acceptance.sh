#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
# Repository hygiene scan (home paths, third-party payloads, licence text, SPDX headers, image PII, broken links).
# Run from the repo root of a checked-out tree: bash tools/ci/acceptance.sh. tools/ci/ itself is excluded from the text scans because it names the patterns.
# Prints one line per item: ID, number of hits, PASS/FAIL. Exit 0 only if every item has 0 hits.
# Prints counts only, never matched text, so it cannot echo a secret.
# PART=all (default) runs every check. PART=A is a transitional mode used while the cleanup PR is in flight; CI uses the default.
PART=${PART:-all}
set -u
command -v rg >/dev/null 2>&1 || { echo 'ripgrep (rg) is required: install it, or this scan would report false passes' >&2; exit 2; }
LIC_URL=https://raw.githubusercontent.com/polyformproject/polyform-licenses/1.0.0/PolyForm-Shield-1.0.0.md
canon=${CANON_LICENSE:-$(mktemp)}
[ -s "$canon" ] || curl -fsSL "$LIC_URL" -o "$canon"
fail=0
row() { printf '%-6s %-62s %4s  %s\n' "$1" "$2" "$3" "$([ "$3" = 0 ] && echo PASS || echo FAIL)"; [ "$3" = 0 ] || fail=1; }
cnt() { wc -l | tr -d ' '; }

n=$( { git ls-files | rg -i shouto; rg -n -i shouto . -g '!.git' -g '!tools/ci/'; } | cnt )
row S-01 "shouto: tracked paths + text refs" "$n"

n=$(rg -n -e '/Users/' -e 'file:///' . -g '!.git' -g '!tools/ci/' | cnt)
row S-02 "/Users/ and file:/// anywhere in tree" "$n"

n=$(rg -n -e '~/GOD' -e 'GOD/eleven' -e 'Path\.home\(\)' tools -g '!tools/ci/' | cnt)
row S-03 "~/GOD and home-dir key lookup in tools/" "$n"

n=$( { git ls-files 'themes/*.bin' 'themes/*-preview/*'; git grep -a -l -e font_puhui -e 'srmodels.bin' -- themes docs voices; } | cnt )
row S-04 "prebuilt theme bins / previews / PuHuiTi+ESP-SR payloads tracked" "$n"

n=$(diff <(sed -n '3,$p' LICENSE) "$canon" | rg -c '^[<>]' || true); n=${n:-0}
row S-05 "LICENSE body differs from canonical PolyForm Shield 1.0.0" "$n"

n=$(git ls-files 'tools/*.py' 'tools/**/*.py' | sort -u | while read -r f; do head -4 "$f" | rg -q 'SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0' || echo "$f"; done | cnt)
row S-06 "tools/**/*.py without SPDX header" "$n"

if [ "$PART" = A ]; then row S-07 "SKIPPED in Part A (THIRD_PARTY_NOTICES.md is Part B)" 0; else
n=0; for pat in 'Permission is hereby granted' 'ElevenLabs' 'schematic' 'Espressif' 'PuHuiTi'; do
  # PuHuiTi/Espressif only required if S-04 option B is chosen (bins kept)
  if [ "$pat" = ElevenLabs ] && ! git ls-files voices | rg -q .; then continue; fi
  if [ "$pat" = Espressif ] || [ "$pat" = PuHuiTi ]; then git ls-files 'themes/*.bin' | rg -q . || continue; fi
  rg -q -F "$pat" THIRD_PARTY_NOTICES.md || n=$((n+1)); done
row S-07 "required entries missing from THIRD_PARTY_NOTICES.md" "$n"; fi

if [ "$PART" = A ]; then row S-08 "SKIPPED in Part A (README.md and docs/ are Part B)" 0; else
n=$(rg -n -i -e 'fonts\.googleapis' -e 'fonts\.gstatic' -e 'buymeacoffee' -e 'buy[_ ]me[_ ]a[_ ]coffee' README.md docs | cnt)
row S-08 "Google Fonts / Buy-Me-a-Coffee in README.md + docs/" "$n"; fi

n=$(git ls-files 'voices/extracted-firmware-ogg/*' | cnt)
row S-09 "stock-firmware extracts tracked (voices/extracted-firmware-ogg)" "$n"

n=$(rg -n -e 'VOICE_ID\s*=\s*"[A-Za-z0-9]{18,}"' tools -g '!tools/ci/' | cnt)
row S-10 "hard-coded ElevenLabs voice id in tools/" "$n"

n=$(rg -n -i -e 'access_token' -e 'bearer' -e 'api.?key' -e 'service_role' -e 'supabase' -e 'self\.[a-z_]+\.[a-z_]+' knowledge/03-* | cnt)
row S-11 "token/key words or enumerated vendor MCP tool names in knowledge/03" "$n"

ex=(); [ "$PART" = A ] && ex=(-g '!docs/_config.yml')
n=$(rg -n -e 'local-xiaozhi-server' -e 'deep-dive\.html' -e 'images/cover' . -g '!.git' -g '!tools/ci/' "${ex[@]}" | cnt)
row S-12 "dead refs: local-xiaozhi-server.py, deep-dive.html, images/cover" "$n"
# S-13: PII in tracked raster images (metadata + OCR for SSID / serial-port path / MAC / LAN IP / home path / email). Count only.
OCR_PY=${OCR_PY:-python3}
here=$(cd "$(dirname "$0")" && pwd)
if [ "$PART" = A ]; then
  n=$("$OCR_PY" "$here/image-pii.py" --exclude docs/assets/health-dashboard-preview.png 2>/dev/null | tail -1)
  row S-13 "PII in tracked images (Part A scope; excludes file an open PR deletes)" "${n:-1}"
  p=$("$OCR_PY" "$here/image-pii.py" 2>/dev/null | tail -1)
  printf '%-6s %-62s %4s  %s\n' S-13b "pending: same check incl. docs/assets/health-dashboard-preview.png (Part B)" "${p:-1}" "INFO"
else
  n=$("$OCR_PY" "$here/image-pii.py" 2>/dev/null | tail -1)
  row S-13 "PII in tracked images (metadata + OCR)" "${n:-1}"
fi
# S-14: broken relative links in tracked Markdown must not exceed main's count (3 on the pre-#2 baseline 87e5aef, 2 on main since #2 rewrote the README; main plus #3 also has 2). Count of EXCESS only.
LINK_BASELINE=${LINK_BASELINE:-2}
if [ "$PART" = A ]; then lx=(--exclude README.md --exclude THIRD_PARTY_NOTICES.md --exclude docs/); else lx=(); fi
n=$(python3 "$here/links-check.py" "${lx[@]}" 2>/dev/null | tail -1)
ex=$(( ${n:-999} > LINK_BASELINE ? ${n:-999} - LINK_BASELINE : 0 ))
row S-14 "broken relative .md links above main's baseline of $LINK_BASELINE (now ${n:-?})" "$ex"
exit $fail
