"""Fail if a production dependency's license doesn't fit the project's own license.

    uv run python scripts/check_licenses.py        (in backend/; part of `just check-backend`)

Installs only the production dependencies from uv.lock into a throwaway venv, reads
their licenses with pip-licenses and checks them against `project.license` in
pyproject.toml (the same rule as frontend/scripts/check-licenses.mjs):

- Always fine: permissive licenses (MIT, BSD, Apache, ISC, PSF, MPL-2.0, ...) and LGPL,
  which doesn't bind an application that merely uses the library (e.g. psycopg).
- AGPL-3.0 or GPL-3.0 project: GPL-3.0, AGPL-3.0 and GPL-2.0 "or later" are fine as well
  (section 13 of both licenses). GPL-2.0-only, a GPL without a version, and copyleft
  licenses the GPL can't absorb (EPL-1.0, CDDL, MPL-1.1) are not.
- Any other project license (MIT, Apache-2.0, proprietary): no GPL or AGPL at all.
- Never: SSPL, and no license information (check the package by hand, add it to ALLOW).

Several licenses ("MIT OR GPL-2.0", or classifiers joined by ";") are alternatives:
the package passes if one of them does.
"""

import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

SSPL = re.compile(r"SSPL|Server Side Public", re.IGNORECASE)
LESSER = re.compile(r"LGPL|Lesser General Public|Library General Public", re.IGNORECASE)
# Whole tokens only, so "LGPL" doesn't count as "GPL".
GPL = re.compile(r"(?<![A-Za-z])A?GPL|General Public License", re.IGNORECASE)
V3_OR_LATER = re.compile(r"v3|(?<![\d.])3(\.0)?(?![\d.])|or[- ]later|\+", re.IGNORECASE)
GPL_INCOMPATIBLE = re.compile(
    r"EPL-1|Eclipse Public License 1|CDDL|Common Development and Distribution"
    r"|MPL-1\.1|Mozilla Public License 1\.1",
    re.IGNORECASE,
)
NO_LICENSE = re.compile(r"^(|UNKNOWN|UNLICENSED|Unknown|NOASSERTION)$")
ALTERNATIVES = re.compile(r"\s+OR\s+|;\s*", re.IGNORECASE)

# Packages whose metadata is wrong or ambiguous, after checking them by hand: the package
# name as key, the reason as value.
ALLOW: dict[str, str] = {
    # No license metadata; the wheel's dist-info/licenses/LICENSE is the MIT license
    # (checked for 0.5.0).
    "resvg_py": "MIT, in the LICENSE file only",
}

# pip-licenses and what it brings along; not part of the app.
TOOLING = ["pip-licenses", "prettytable", "wcwidth"]


def production_licenses() -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory() as tmp:
        requirements = Path(tmp) / "requirements.txt"
        venv = Path(tmp) / "venv"
        bin_dir = venv / ("Scripts" if sys.platform == "win32" else "bin")
        run = ["uv", "--quiet"]
        subprocess.run(
            [
                *run,
                "export",
                "--locked",
                "--no-dev",
                "--no-hashes",
                "--format",
                "requirements.txt",
                "-o",
                str(requirements),
            ],
            check=True,
        )
        subprocess.run([*run, "venv", str(venv)], check=True)
        subprocess.run(
            [*run, "pip", "install", "--python", str(venv), "-r", str(requirements), *TOOLING[:1]],
            check=True,
        )
        output = subprocess.run(
            [str(bin_dir / "pip-licenses"), "--format=json", "--ignore-packages", *TOOLING],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    licenses: list[dict[str, str]] = json.loads(output)
    return licenses


def copyleft_project() -> bool:
    """True when the project itself is (A)GPL-3.0, so GPL-3.0 dependencies fit."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    own = project.get("project", {}).get("license", "")
    own = own.get("text", "") if isinstance(own, dict) else own
    return bool(re.match(r"A?GPL-3\.0", own))


def compatible(license_: str, copyleft: bool) -> bool:
    for alternative in ALTERNATIVES.split(license_.strip("() ")):
        parts = re.split(r"\s+AND\s+", alternative.strip("() "), flags=re.IGNORECASE)
        if all(compatible_part(part.strip("() "), copyleft) for part in parts):
            return True
    return False


def compatible_part(license_: str, copyleft: bool) -> bool:
    if NO_LICENSE.match(license_) or SSPL.search(license_):
        return False
    if LESSER.search(license_):
        return True
    if GPL.search(license_):
        return copyleft and bool(V3_OR_LATER.search(license_))
    return not (copyleft and GPL_INCOMPATIBLE.search(license_))


def main() -> int:
    copyleft = copyleft_project()
    bad = []
    for pkg in production_licenses():
        name, license_ = pkg["Name"], pkg.get("License", "")
        if name.lower() in ALLOW:
            continue
        if not compatible(license_, copyleft):
            bad.append(f"{name} {pkg.get('Version', '')}: {license_ or 'no license information'}")
    for line in bad:
        print(f"incompatible license: {line}")
    if not bad:
        print("licenses ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
