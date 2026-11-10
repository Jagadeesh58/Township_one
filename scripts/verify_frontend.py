"""Run frontend checks supported by the available Node installation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
REPORT = ROOT / "docs" / "reports" / "frontend-validation.json"


def run(command: list[str], timeout: int = 240) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=FRONTEND,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=sys.platform == "win32",
        )
        return {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
            "command": command,
            "stdout": result.stdout[-10000:],
            "stderr": result.stderr[-10000:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "BLOCKED" if isinstance(exc, OSError) else "TIMEOUT",
            "returncode": None,
            "command": command,
            "stdout": "",
            "stderr": str(exc),
        }


def main() -> int:
    _ = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    node_command = [
        "node",
        "-e",
        "console.log(process.version); process.argv = [process.argv[0], 'tsc', '--noEmit']; require('./node_modules/typescript/lib/tsc.js')",
    ]
    typecheck = run(node_command)
    node_version = ""
    if typecheck.get("stdout"):
        node_version = typecheck["stdout"].splitlines()[0].strip().lstrip("v")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", node_version)
    version = tuple(int(part) for part in match.groups()) if match else ()
    supported = bool(version) and (
        (version[0] == 22 and version >= (22, 22, 2))
        or (version[0] == 24 and version >= (24, 15, 0))
        or version[0] >= 26
    )

    if sys.platform == "linux":
        rollup_native = FRONTEND / "node_modules" / "@rollup" / "rollup-linux-x64-gnu"
    elif sys.platform == "win32":
        rollup_native = FRONTEND / "node_modules" / "@rollup" / "rollup-win32-x64-msvc"
    elif sys.platform == "darwin":
        rollup_native = FRONTEND / "node_modules" / "@rollup" / "rollup-darwin-arm64"
    else:
        rollup_native = FRONTEND / "node_modules" / "vite"

    dependencies_present = (FRONTEND / "node_modules" / ".bin").is_dir()
    blockers: list[str] = []
    if not dependencies_present:
        blockers.append("Frontend dependencies are absent; run npm ci with a supported Node version.")
    if not supported:
        blockers.append(f"Node {node_version or 'unknown'} is below package.json's supported engine range.")
    if dependencies_present and not rollup_native.is_dir() and not (FRONTEND / "node_modules" / "vite").is_dir():
        blockers.append("Native Rollup dependency is missing; reinstall with npm ci.")
    blocked_reason = " ".join(blockers)

    if blocked_reason:
        frontend_tests = {
            "status": "BLOCKED",
            "returncode": None,
            "command": ["npm", "test"],
            "stdout": "",
            "stderr": blocked_reason,
        }
        frontend_build = {
            "status": "BLOCKED",
            "returncode": None,
            "command": ["npm", "run", "build"],
            "stdout": "",
            "stderr": blocked_reason,
        }
    else:
        frontend_tests = run(["npm", "test"])
        frontend_build = run(["npm", "run", "build"])

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "node_version": node_version,
        "typescript": typecheck,
        "frontend_tests": frontend_tests,
        "frontend_build": frontend_build,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    return 0 if all(gate.get("status") == "PASS" for gate in (typecheck, frontend_tests, frontend_build)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
