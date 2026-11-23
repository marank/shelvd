#!/usr/bin/env python3
"""
The checks for what is about to be committed — fast enough to run before every commit.

    just check-changed

Looks at the files changed against the last commit (staged, unstaged and new) and runs only
what they can break: lint, formatting and complexity on the changed files, the type checks of
the part they belong to, the tests of the touched apps or the tests related to the changed
frontend files, and the schema, migrations, docs or workflow checks when those files changed.
`just check` still runs everything and must pass before a push; CI runs it anyway.

Only the standard library, so it runs before the backend's environment exists.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = (".py",)
WEB = (".ts", ".tsx", ".vue", ".js", ".mjs")
ALL_TESTS = ("backend/config/", "backend/apps/core/", "backend/conftest.py", "backend/pyproject.toml")


def changed_files() -> list[str]:
    def git(*args: str) -> list[str]:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        return [line for line in out.splitlines() if line]

    files = git("diff", "--name-only", "HEAD") + git("ls-files", "--others", "--exclude-standard")
    return sorted({f for f in files if (ROOT / f).exists()})


def run(cwd: str, *cmd: str) -> bool:
    print(f"\n$ ({cwd}) {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT / cwd, check=False).returncode == 0


def inside(files: list[str], folder: str, suffixes: tuple[str, ...] = ()) -> list[str]:
    return [f.removeprefix(folder) for f in files if f.startswith(folder) and f.endswith(suffixes or "")]


def backend_steps(files: list[str]) -> list[tuple[str, ...]]:
    py = inside(files, "backend/", PY)
    if not inside(files, "backend/"):
        return []
    steps: list[tuple[str, ...]] = [("uv", "run", "mypy", "."), ("uv", "run", "lint-imports")]
    if py:
        steps[:0] = [("uv", "run", "ruff", "check", *py), ("uv", "run", "ruff", "format", "--check", *py),
                     ("uv", "run", "complexipy", *py)]
    if any("/models/" in f or "/migrations/" in f for f in py):
        steps.append(("uv", "run", "python", "manage.py", "makemigrations", "--check", "--dry-run"))
    if any(part in f for f in py for part in ("/api/", "/schemas/", "/serializers/")):
        steps.append(("uv", "run", "python", "scripts/check_openapi.py"))
    if any(f.startswith(ALL_TESTS) for f in files):
        steps.append(("uv", "run", "pytest", "-q"))
    else:
        apps = sorted({f.split("/")[2] for f in files if f.startswith("backend/apps/") and f.count("/") > 2})
        tests = [f"apps/{a}/tests" for a in apps if (ROOT / "backend" / "apps" / a / "tests").is_dir()]
        if tests:
            steps.append(("uv", "run", "pytest", "-q", *tests))
    return steps


def frontend_steps(files: list[str]) -> list[tuple[str, ...]]:
    web = inside(files, "frontend/", WEB)
    if not inside(files, "frontend/"):
        return []
    steps: list[tuple[str, ...]] = []
    if web:
        steps += [("pnpm", "exec", "prettier", "--check", *web), ("pnpm", "exec", "eslint", *web)]
    steps.append(("pnpm", "type-check"))
    if web:
        steps.append(("pnpm", "exec", "vitest", "related", "--run", "--passWithNoTests", *web))
    return steps


def main() -> int:
    files = changed_files()
    if not files:
        print("Nothing changed since the last commit.")
        return 0
    plan = [("backend", s) for s in backend_steps(files)] + [("frontend", s) for s in frontend_steps(files)]
    if inside(files, "docs/"):
        plan.append((".", ("just", "check-docs")))
    if inside(files, ".github/workflows/"):
        plan.append((".", ("just", "check-workflows")))
    failed = [" ".join(step) for cwd, step in plan if not run(cwd, *step)]
    if any(f.startswith(("Dockerfile", "docker/", "compose")) for f in files):
        print("\nThe image is not tested here: `just docker-up` locally, or CI after the push.")
    if failed:
        print("\nFailed:\n  " + "\n  ".join(failed))
        return 1
    print("\nChecks for the changed files passed. `just check` runs everything before a push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
