"""Smoke test: run /docx in sandbox, print ALL raw events, keep sandbox."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from runner.sandbox import Sandbox
from stages.student import _install_skill_in_sandbox

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OR_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = "google/gemma-4-26b-a4b-it"
SKILL_DIR = Path.home() / ".claude" / "skills" / "docx"
PROMPT = "/docx Create a simple Word document with content Hello World and save it as hello.docx"
SANDBOX_ROOT = Path.home() / ".cache" / "distill_v2_test"

if not OR_KEY:
    sys.exit("OPENROUTER_API_KEY not set")

print(f"Model  : {MODEL}")
print(f"Skill  : {SKILL_DIR}")
print(f"Prompt : {PROMPT}")
print("-" * 60)

with Sandbox(
    name="test-hello",
    api_key=OR_KEY,
    base_url="https://openrouter.ai/api",
    parent_tmp=SANDBOX_ROOT,
    keep_on_fail=True,  # keep always so we can inspect
) as sb:
    _install_skill_in_sandbox(sb, "docx", SKILL_DIR, model=MODEL)
    print(f"Sandbox: {sb.root}")
    print(f"Home   : {sb.home}")
    print(f"CWD    : {sb.cwd}")
    print(f"Skill installed: {(sb.home / '.claude' / 'skills' / 'docx').is_dir()}")
    print(f"settings.json  : {(sb.home / '.claude' / 'settings.json').read_text()}")
    print("-" * 60)

    cmd = [
        "claude",
        "--model",
        MODEL,
        "-p",
        PROMPT,
        "--bare",
        "--verbose",
        "--output-format",
        "stream-json",
        "--dangerously-skip-permissions",
        "--max-turns",
        "20",
    ]
    print(f"CMD: {' '.join(cmd)}\n")

    proc = subprocess.Popen(
        cmd,
        env=sb.env,
        cwd=str(sb.cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert proc.stdout
    for raw in proc.stdout:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            print(f"[EVENT] {json.dumps(obj)[:300]}")
        except json.JSONDecodeError:
            print(f"[RAW]   {raw[:300]}")

    _, stderr = proc.communicate(timeout=120)
    print(f"\n[exit code] {proc.returncode}")
    if stderr.strip():
        print(f"[stderr]\n{stderr.strip()[:1000]}")

    print("\n[files in sandbox cwd]:")
    for f in sorted(sb.cwd.rglob("*")):
        if f.is_file():
            rel = f.relative_to(sb.cwd)
            if not any(p.startswith(".") or p == "node_modules" for p in rel.parts):
                print(f"  {rel}  ({f.stat().st_size} B)")

    # Force keep sandbox even without exception
    sb._keep_on_fail = True
