#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""Count-only PII check for tracked raster images (metadata + OCR). Never prints matched text.
usage: image-pii.py [--exclude PATH ...] [PATHSPEC ...]   (default pathspec: docs/ plans/ reference/ themes/)
Needs: pillow + rapidocr-onnxruntime (OCR_PY env var in acceptance.sh points at an interpreter that has them).
Exit 0 always; prints one integer (number of findings) on stdout, notes on stderr."""
import re, subprocess, sys
from PIL import Image
args = sys.argv[1:]; excl = set()
while '--exclude' in args:
    i = args.index('--exclude'); excl.add(args[i+1]); del args[i:i+2]
specs = args or ['docs', 'plans', 'reference', 'themes']
files = [f for f in subprocess.check_output(['git','ls-files','--',*specs],text=True).split('\n')
         if re.search(r'\.(png|jpe?g|webp)$', f, re.I) and f not in excl]
try:
    from rapidocr_onnxruntime import RapidOCR; ocr = RapidOCR()
except Exception:
    print('OCR engine missing (pip install rapidocr-onnxruntime)', file=sys.stderr); print(1); sys.exit(0)
PAT = [r'SSID', r'usbmodem', r'/dev/cu\.', r'/dev/tty', r'/Users/', r'(?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}',
       r'\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b', r'\b192\.0\.2\.\d+\b',
       r'Wi-?Fi\s*[:=]?\s*\S*(?:2\.4G|5G)', r'[\w.+-]+@[\w-]+\.[\w.]+']
bad = 0
for f in files:
    hit = False
    try:
        im = Image.open(f)
        keys = {k.lower() for k in im.info if isinstance(k, str)}
        if keys & {'exif','xml:com.adobe.xmp','xmp','icc_profile_text','author','comment','gps','software','source'}: hit = True
        if getattr(im, '_getexif', lambda: None)(): hit = True
        im.convert('RGB').save('/tmp/_ocr.png')
        res, _ = ocr('/tmp/_ocr.png'); text = ' '.join(x[1] for x in (res or []))
        if any(re.search(p, text, re.I) for p in PAT): hit = True
    except Exception as e:
        print(f'cannot read {f}: {type(e).__name__}', file=sys.stderr); hit = True
    if hit:
        bad += 1; print(f'finding: {f}', file=sys.stderr)   # path only, never the text
print(bad)
