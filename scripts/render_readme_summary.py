"""Render the measured verification table in README.md from summary.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SUMMARY = ROOT / "docs" / "reports" / "summary.json"
START = "<!-- verification-summary:start -->"
END = "<!-- verification-summary:end -->"


def detail_for(name: str, result: dict) -> str:
    if name == "database_seed_and_ground_truth":
        counts = result.get("counts", {})
        return ", ".join(f"{key}: {value}" for key, value in counts.items()) or result.get("error", "")
    if name in {"backend_tests", "backend_tests_and_coverage", "backend_coverage"}:
        output = result.get("stdout", "")
        match = re.search(r"(\d+ passed(?:, \d+ skipped)?(?:, \d+ failed)?[^\n]*)", output)
        coverage = result.get("coverage_percentage")
        text = (
            match.group(1)
            if match
            else (result.get("stderr", "") or result.get("error", "Command output recorded in summary.json"))
        )
        if coverage is not None:
            text += f"; coverage {coverage}%"
        return text.strip().replace("\n", " ")[-180:]
    if name == "frontend_typescript":
        node_version = (
            result.get("stdout", "").strip().splitlines()[0] if result.get("stdout") else "Node version not recorded"
        )
        return f"TypeScript compiler passed ({node_version})."
    if name.startswith("frontend_"):
        return result.get("stderr", "")[:180].replace("\n", " ") or "Command output recorded in summary.json"
    if name == "wording_scan":
        return f"{result.get('count', 'unknown')} finding(s)."
    output = result.get("stdout", "") or result.get("stderr", "")
    return output.strip().splitlines()[-1][-180:] if output.strip() else result.get("error", "See summary.json")


def render() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    rows = [
        "| Check | Result | Measured evidence |",
        "|---|---|---|",
    ]
    for name, result in summary.get("gates", {}).items():
        detail = detail_for(name, result).replace("|", "\\|")
        rows.append(f"| `{name}` | **{result.get('status', 'UNKNOWN')}** | {detail or 'See summary.json'} |")
    rows.append("")
    rows.append(f"Overall result: **{summary.get('overall_status', 'UNKNOWN')}**")
    content = "\n".join([START, *rows, END])
    current = README.read_text(encoding="utf-8")
    start = current.find(START)
    end = current.find(END)
    if start < 0 or end < start:
        raise SystemExit("README verification-summary markers are missing.")
    end += len(END)
    README.write_text(current[:start] + content + current[end:], encoding="utf-8")


if __name__ == "__main__":
    render()
