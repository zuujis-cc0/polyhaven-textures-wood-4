#!/usr/bin/env python3
"""Check this mirror against MANIFEST.tsv: every listed file is here with its size and SHA-256, every asset has a
preview, and nothing else is in the repository. Written by cc0-mirror; runs in the check workflow."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OWN = {"README.md", "MANIFEST.tsv", ".mirror.json", "LICENSE", ".github/workflows/check.yml", ".github/workflows/update.yml",
       ".github/verify.py"}
GIT_LIMIT = 100 * 1000 * 1000

problems = []
rows = (ROOT / "MANIFEST.tsv").read_text().splitlines()
if not rows or rows[0].split("\t") != ["path", "bytes", "sha256", "md5", "source"]:
    sys.exit("MANIFEST.tsv: missing or wrong header")
listed = set()
for line in rows[1:]:
    path, size, sha, _md5, _src = line.split("\t")
    listed.add(path)
    f = ROOT / path
    if not f.is_file():
        problems.append(f"{path}: listed but missing")
        continue
    if f.stat().st_size != int(size):
        problems.append(f"{path}: {f.stat().st_size} bytes, the manifest says {size}")
    elif hashlib.sha256(f.read_bytes()).hexdigest() != sha:
        problems.append(f"{path}: SHA-256 does not match the manifest")
    if int(size) >= GIT_LIMIT:
        problems.append(f"{path}: over GitHub's 100 MB file limit")
assets = json.loads((ROOT / ".mirror.json").read_text())["assets"]
previews = set()
for a in assets:
    found = sorted((ROOT / "previews").glob(f"{a}.*")) if (ROOT / "previews").is_dir() else []
    previews |= {f.relative_to(ROOT).as_posix() for f in found}  # optional: some sources have no picture
files = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True).stdout.split("\0")
files = {f for f in files if f} or {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts}
for extra in sorted(files - listed - previews - OWN):
    problems.append(f"{extra}: not in MANIFEST.tsv")
if problems:
    print("\n".join(problems))
    sys.exit(f"{len(problems)} problem(s)")
print(f"OK: {len(listed)} files, {len(assets)} assets")
