#!/usr/bin/env python3
"""
Format and lint the one file an AI coding agent just changed (Claude Code hook).

.claude/settings.json runs this after every Edit/Write: the agent sees what is left right
away, in the same step, instead of at commit time. Only that file, so it takes seconds:
ruff format + ruff check --fix for backend Python, prettier + eslint --fix for frontend
sources. Exit code 2 hands the remaining problems back to the agent; anything else stays
quiet. `just check-changed` and `just check` remain the real gates.

Only the standard library; reads the hook's JSON from stdin.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = (".ts", ".tsx", ".vue", ".js", ".mjs")


def run(cwd: Path, *cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def main() -> int:
    event = json.load(sys.stdin)
    raw = event.get("tool_input", {}).get("file_path") or ""
    path = Path(raw).resolve()
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return 0  # outside the repo
    if not path.is_file():
        return 0
    if rel.startswith("backend/") and rel.endswith(".py"):
        cwd, file = ROOT / "backend", rel.removeprefix("backend/")
        run(cwd, "uv", "run", "ruff", "format", file)
        result = run(cwd, "uv", "run", "ruff", "check", "--fix", file)
    elif rel.startswith("frontend/src/") and rel.endswith(WEB):
        cwd, file = ROOT / "frontend", rel.removeprefix("frontend/")
        run(cwd, "pnpm", "exec", "prettier", "--write", file)
        result = run(cwd, "pnpm", "exec", "eslint", "--fix", file)
    else:
        return 0
    if result.returncode == 0:
        return 0
    print(f"{rel} still has lint problems — fix them, don't silence them:", file=sys.stderr)
    print((result.stdout + result.stderr).strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
