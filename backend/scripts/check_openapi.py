"""Fail if frontend/openapi.json no longer matches the API.

    uv run python scripts/check_openapi.py         (in backend/; part of `just check-backend`)

Exports the schema into a temporary file with the same command as `just api-types`
and compares it with the committed file. Generated with SQLite like locally: the database
decides some integer limits. It changes nothing in the working tree, so it also passes
with an uncommitted, but current, openapi.json.
"""

import difflib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
COMMITTED = BACKEND.parent / "frontend" / "openapi.json"


def export_command(target: Path) -> list[str]:
    return [
        sys.executable,
        "manage.py",
        "export_openapi_schema",
        "--api",
        "config.api.api",
        "--indent",
        "2",
        "--output",
        str(target),
    ]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "openapi.json"
        subprocess.run(
            export_command(target),
            check=True,
            cwd=BACKEND,
            env={**os.environ, "DB_TYPE": "sqlite", "ADDONS_ENABLED": "false"},
        )
        current = target.read_text(encoding="utf-8")
    committed = COMMITTED.read_text(encoding="utf-8") if COMMITTED.exists() else ""
    if committed != current:
        diff = difflib.unified_diff(
            committed.splitlines(keepends=True),
            current.splitlines(keepends=True),
            "frontend/openapi.json",
            "current API",
        )
        sys.stdout.writelines(diff)
        print(
            "API changed: run `just api-types` and commit both files",
            file=sys.stderr,
        )
        return 1
    print("openapi.json up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
