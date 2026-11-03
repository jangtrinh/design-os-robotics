#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""Count broken relative links in tracked Markdown files (inline [text](path) and <img src>-less). Count only, no text.
usage: links-check.py [--exclude PREFIX ...]   -> prints the number of broken links on stdout"""
import os, re, subprocess, sys
args = sys.argv[1:]; excl = []
while '--exclude' in args:
    i = args.index('--exclude'); excl.append(args[i+1]); del args[i:i+2]
tracked = set(subprocess.check_output(['git', 'ls-files'], text=True).split('\n')) - {''}
dirs = {os.path.dirname(f) for f in tracked}
for f in list(tracked):
    d = os.path.dirname(f)
    while d:
        dirs.add(d); d = os.path.dirname(d)
LINK = re.compile(r'(?<!\!)\[[^\]]*\]\(\s*<?([^)\s>]+)')
bad = 0
for f in sorted(tracked):
    if not f.endswith('.md') or any(f == e or f.startswith(e) for e in excl): continue
    in_code = False
    for line in open(f, encoding='utf-8', errors='replace'):
        if line.lstrip().startswith('```'): in_code = not in_code
        if in_code: continue
        for m in LINK.finditer(line):
            t = m.group(1)
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', t) or t.startswith(('#', '//')): continue
            t = re.split(r'[#?]', t)[0]
            if not t: continue
            p = os.path.normpath(os.path.join(os.path.dirname(f), t)) if not t.startswith('/') else t.lstrip('/')
            if p not in tracked and p not in dirs: bad += 1
print(bad)
