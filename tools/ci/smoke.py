#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# SPDX-FileCopyrightText: 2026 Jang Trinh
"""Smoke tests for the scripts under tools/.

The repository has no unit-test suite, so this runs every script the way a new
contributor would first meet it and checks that it starts cleanly:

  * each script found under tools/ (globbed, tools/ci/ excluded) answers --help without a traceback
  * engine.py status runs against a fresh state database

Everything runs inside a throw-away copy of the repository so scripts that write
reports (plans/reports/*.json, *.png) never dirty the checkout. The gitignored
theme and firmware binaries are not needed: a script that requires them must say so
instead of crashing, and a crash on --help is reported as a failure.

usage: python3 tools/ci/smoke.py      (run from anywhere; exit 1 if any case fails)
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

# Every tools/**/*.py (except tools/ci/) is smoke-tested with --help unless it has an override here.
# DEFAULT: (argv suffix, accepted exit codes, text that must appear in the output)
DEFAULT = (["--help"], {0}, "usage")
# Per-script overrides, keyed by path relative to the repo root.
OVERRIDES = {
    # reflex_60fps.py prints a free-form description rather than an argparse usage line.
    "tools/mochi-soul-engine/reflex_60fps.py": (["--help"], {0}, ""),
}
# Extra cases that exercise a script beyond --help: (label, argv relative to the repo copy, accepted exit codes, text that must appear)
EXTRA = [
    ("engine status", ["tools/mochi-soul-engine/engine.py", "status"], {0}, "minutes_since_interaction"),
]


def discover() -> list[str]:
    found = sorted(
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "tools").rglob("*.py")
        if "ci" not in p.relative_to(ROOT / "tools").parts[:1] and "__pycache__" not in p.parts
    )
    stale = [k for k in OVERRIDES if k not in found] + [a[0] for _, a, _, _ in EXTRA if a[0] not in found]
    if not found or stale:
        sys.exit(f"smoke.py is out of date: no scripts found or stale entries {stale}")
    return found


def build_cases() -> list:
    cases = []
    for rel in discover():
        args, ok, needle = OVERRIDES.get(rel, DEFAULT)
        cases.append((f"{rel.removeprefix('tools/')} {' '.join(args)}", [rel, *args], ok, needle))
    return cases + EXTRA


def main() -> int:
    failed = 0
    cases = build_cases()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", HOME=tmp)
        for label, argv, ok_codes, needle in cases:
            try:
                p = subprocess.run([PY, *argv], cwd=work, env=env, text=True, timeout=120,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                out, rc = p.stdout, p.returncode
            except subprocess.TimeoutExpired:
                out, rc = "", -1
            good = rc in ok_codes and "Traceback" not in out and needle.lower() in out.lower()
            print(f"{'PASS' if good else 'FAIL'}  {label}  (exit {rc})")
            if not good:
                failed += 1
                tail = [ln for ln in out.strip().splitlines() if ln.strip()][-3:]
                for ln in tail:
                    print(f"      | {ln}")
    print(f"\n{len(cases) - failed}/{len(cases)} smoke cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
