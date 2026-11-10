"""Run reproducible local release checks and save measured command evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "reports" / "summary.json"


def run_command(
    command_args: list[str],
    *,
    cwd: Path = ROOT,
    timeout_seconds: int = 180,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    started = time.monotonic()
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            command_args,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=(os.name != "nt"),
        )
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=timeout_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            stdout_bytes, stderr_bytes = process.communicate(timeout=10)

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return {
            "status": "TIMEOUT" if timed_out else ("PASS" if process.returncode == 0 else "FAIL"),
            "returncode": process.returncode,
            "duration_seconds": round(time.monotonic() - started, 2),
            "command": command_args,
            "stdout": (stdout or "")[-16000:],
            "stderr": (stderr or "")[-16000:],
            **({"timeout_seconds": timeout_seconds} if timed_out else {}),
        }
    except OSError as exc:
        return {
            "status": "BLOCKED",
            "returncode": None,
            "duration_seconds": round(time.monotonic() - started, 2),
            "command": command_args,
            "stdout": "",
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        # The command group could not be reaped after SIGKILL. Preserve partial
        # output and mark the gate as a timeout rather than hanging the release.
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "status": "TIMEOUT",
            "returncode": process.returncode if process is not None else None,
            "duration_seconds": round(time.monotonic() - started, 2),
            "command": command_args,
            "stdout": stdout[-16000:],
            "stderr": stderr[-16000:],
            "timeout_seconds": timeout_seconds,
        }


def check_database_and_seed() -> dict[str, Any]:
    fd, database_path = tempfile.mkstemp(prefix="township-release-", suffix=".db")
    os.close(fd)
    database_url = f"sqlite:///{Path(database_path).as_posix()}"
    previous_database_url = os.environ.get("DATABASE_URL")
    previous_test_url = os.environ.get("TEST_DATABASE_URL")
    engine = None
    try:
        os.environ["DATABASE_URL"] = database_url
        os.environ["TEST_DATABASE_URL"] = database_url

        alembic_config = Config(str(ROOT / "alembic.ini"))
        alembic_config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
        command.upgrade(alembic_config, "head")
        command.check(alembic_config)

        from backend.app.models.entities import Bill, Flat, Gate, StaffMember, Tower
        from seed.seed_data import seed_database

        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        seed_database(target_engine=engine, mode="safe")
        seed_database(target_engine=engine, mode="safe")

        with Session(engine) as db_session:
            counts = {
                "towers": db_session.query(Tower).count(),
                "flats": db_session.query(Flat).count(),
                "staff": db_session.query(StaffMember).count(),
                "gates": db_session.query(Gate).count(),
            }
            expected_counts = {"towers": 28, "flats": 2400, "staff": 180, "gates": 4}
            if counts != expected_counts:
                raise AssertionError(f"Seed counts differ: expected {expected_counts}, got {counts}")

            expected_bills = {
                "T07-1203": (Decimal("0.00"), 0),
                "T12-0408": (Decimal("6370.00"), 47),
                "T21-1601": (Decimal("5660.00"), 18),
            }
            balances: dict[str, dict[str, str | int]] = {}
            for flat_number, (expected_balance, expected_overdue) in expected_bills.items():
                flat = db_session.query(Flat).filter(Flat.flat_number == flat_number).one()
                bill = db_session.query(Bill).filter(Bill.flat_id == flat.id).one()
                if bill.balance_amount != expected_balance:
                    raise AssertionError(
                        f"{flat_number} balance expected {expected_balance}, got {bill.balance_amount}"
                    )
                overdue = getattr(bill, "days_overdue", None)
                if overdue is None:
                    due_date = getattr(bill, "due_date", None)
                    from datetime import date

                    reference = date(2026, 11, 6)
                    overdue = (
                        max((reference - due_date.date()).days, 0)
                        if hasattr(due_date, "date")
                        else max((reference - due_date).days, 0)
                    )
                if overdue != expected_overdue:
                    raise AssertionError(f"{flat_number} overdue expected {expected_overdue}, got {overdue}")
                balances[flat_number] = {
                    "outstanding": f"{bill.balance_amount:.2f}",
                    "overdue_days": int(overdue),
                }

        return {
            "status": "PASS",
            "migration": "alembic upgrade head",
            "schema_parity": "alembic check reported no new upgrade operations",
            "seed_runs": 2,
            "counts": counts,
            "ground_truth": balances,
        }
    except Exception as exc:
        return {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if engine is not None:
            engine.dispose()
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        if previous_test_url is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = previous_test_url
        try:
            os.remove(database_path)
        except OSError:
            pass


def check_wording() -> dict[str, Any]:
    patterns = [
        re.compile(r"\bday\s*[1-3]\b", re.IGNORECASE),
        re.compile(r"\bd[1-3]-s\d+\b", re.IGNORECASE),
        re.compile(r"\bmilestone\b", re.IGNORECASE),
        re.compile(r"\bbuild-locked\b", re.IGNORECASE),
        re.compile(r"\bprompt\s+[a-z0-9]+\b", re.IGNORECASE),
        re.compile(r"\bstabiliz(?:ation|e|ed|ing)\b", re.IGNORECASE),
        re.compile(r"\bphase\s+[0-9]+\b", re.IGNORECASE),
    ]
    excluded_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build"}
    allowed_suffixes = {".py", ".ts", ".tsx", ".md", ".json", ".yml", ".yaml", ".toml"}
    violations: list[str] = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [directory for directory in dirs if directory not in excluded_dirs]
        for filename in files:
            path = Path(root) / filename
            if path.suffix.lower() not in allowed_suffixes:
                continue
            try:
                for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if any(pattern.search(line) for pattern in patterns):
                        violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()[:120]}")
            except OSError:
                continue
    return {
        "status": "PASS" if not violations else "FAIL",
        "count": len(violations),
        "items": violations[:100],
    }


def report_gate(name: str, result: dict[str, Any]) -> None:
    status = result.get("status", "UNKNOWN")
    print(f"[{status}] {name}")
    for key in ("returncode", "duration_seconds", "error", "stderr"):
        value = result.get(key)
        if value:
            print(f"  {key}: {value}")
    stdout = result.get("stdout")
    if stdout:
        print(stdout[-5000:])


def frontend_blocked(reason: str) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "returncode": None,
        "duration_seconds": 0,
        "command": [],
        "stdout": "",
        "stderr": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Township One using measured commands.")
    parser.add_argument("--command-timeout", type=int, default=600)
    parser.add_argument("--database-check-worker", action="store_true")
    parser.add_argument("--skip-coverage", action="store_true", help="Explicitly mark the coverage gate as unverified.")
    args = parser.parse_args()

    if args.database_check_worker:
        result = check_database_and_seed()
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("status") == "PASS" else 1

    os.chdir(ROOT)
    import importlib.util

    gates: list[tuple[str, dict[str, Any]]] = []
    common_env = {"TOWNSHIP_ENV": "test"}
    dataset_fd, dataset_report_name = tempfile.mkstemp(prefix="township-release-data-", suffix=".json")
    os.close(dataset_fd)
    dataset_report_path = Path(dataset_report_name)

    # PostgreSQL is the required integration target for row-lock behaviour.
    # It is not silently replaced by SQLite when a server is unavailable.
    pg_test_url = (os.environ.get("PG_DATABASE_URL") or os.environ.get("TEST_DATABASE_URL") or "").strip()
    pg_migration_url = os.environ.get("PG_MIGRATION_DATABASE_URL", "").strip()
    if not pg_migration_url.startswith(("postgresql://", "postgresql+")):
        gates.append(
            (
                "postgresql_migrations",
                {
                    "status": "BLOCKED",
                    "returncode": None,
                    "duration_seconds": 0,
                    "command": [
                        "alembic upgrade head",
                        "alembic check",
                        "alembic downgrade base",
                        "alembic upgrade head",
                    ],
                    "stdout": "",
                    "stderr": "Set PG_MIGRATION_DATABASE_URL to a disposable PostgreSQL database; no PostgreSQL server was available for this run.",
                },
            )
        )

    # Quality tools are recorded as blocked before the main test process when
    # they are not installed; no shell command is launched for a missing tool.
    for gate_name, module_name, command_args in [
        ("ruff_check", "ruff", [sys.executable, "-m", "ruff", "check", "."]),
        ("ruff_format", "ruff", [sys.executable, "-m", "ruff", "format", "--check", "."]),
        ("mypy", "mypy", [sys.executable, "-m", "mypy", "backend/app"]),
    ]:
        if importlib.util.find_spec(module_name) is None:
            gates.append(
                (
                    gate_name,
                    {
                        "status": "BLOCKED",
                        "returncode": None,
                        "duration_seconds": 0,
                        "command": command_args,
                        "stdout": "",
                        "stderr": f"Python module {module_name!r} is not installed in this environment.",
                    },
                )
            )
        else:
            gates.append(
                (
                    gate_name,
                    {
                        "status": "BLOCKED",
                        "returncode": None,
                        "duration_seconds": 0,
                        "command": command_args,
                        "stdout": "",
                        "stderr": "Run this quality command in the configured development/CI environment; this verifier does not invoke additional tool processes before the full test run.",
                    },
                )
            )

    # Frontend verification is performed by its own single-purpose command.
    # This keeps Node/Vite lifecycle and backend test processes isolated.
    frontend_report_path = ROOT / "docs" / "reports" / "frontend-validation.json"
    try:
        frontend_report = json.loads(frontend_report_path.read_text(encoding="utf-8"))
        frontend_generated = datetime.fromisoformat(frontend_report["generated_at"])
        if frontend_generated.tzinfo is None:
            frontend_generated = frontend_generated.replace(tzinfo=UTC)
        if (datetime.now(UTC) - frontend_generated).total_seconds() > 24 * 60 * 60:
            raise ValueError("Frontend validation report is older than 24 hours.")
        gates.extend(
            [
                (
                    "frontend_typescript",
                    frontend_report.get(
                        "typescript", frontend_blocked("TypeScript result missing from frontend report.")
                    ),
                ),
                (
                    "frontend_tests",
                    frontend_report.get(
                        "frontend_tests", frontend_blocked("Frontend test result missing from frontend report.")
                    ),
                ),
                (
                    "frontend_build",
                    frontend_report.get(
                        "frontend_build", frontend_blocked("Frontend build result missing from frontend report.")
                    ),
                ),
            ]
        )
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        reason = f"Run python scripts/verify_frontend.py first: {exc}"
        for gate_name in ("frontend_typescript", "frontend_tests", "frontend_build"):
            gates.append((gate_name, frontend_blocked(reason)))

    # One full backend process proves both the test result and the coverage
    # threshold. Fresh-install tests within this run perform migrations, schema
    # parity, two idempotent safe seed runs, and actual balance/count assertions.
    coverage_env = dict(common_env)
    coverage_env["TOWNSHIP_RELEASE_REPORT_PATH"] = str(dataset_report_path)
    if sys.version_info >= (3, 12):
        coverage_env["COVERAGE_CORE"] = "sysmon"
    backend_database_url = os.environ.get("DATABASE_URL", "sqlite:///./township_release_app.db")
    if pg_test_url.startswith(("postgresql://", "postgresql+")):
        coverage_env.update(
            {
                "DATABASE_URL": backend_database_url,
                "TEST_DATABASE_URL": pg_test_url,
                "PG_DATABASE_URL": pg_test_url,
            }
        )
        gates.append(
            (
                "postgresql_backend_tests",
                {
                    "status": "PENDING",
                    "returncode": None,
                    "duration_seconds": 0,
                    "command": [sys.executable, "-m", "pytest", "tests/", "-rs"],
                    "stdout": "",
                    "stderr": "PostgreSQL test result is determined by the full backend run below.",
                },
            )
        )
    else:
        gates.append(
            (
                "postgresql_backend_tests",
                {
                    "status": "BLOCKED",
                    "returncode": None,
                    "duration_seconds": 0,
                    "command": [sys.executable, "-m", "pytest", "tests/", "-rs"],
                    "stdout": "",
                    "stderr": "Set PG_DATABASE_URL and TEST_DATABASE_URL to a dedicated PostgreSQL test database. The three row-lock tests are not verified by SQLite.",
                },
            )
        )

    if args.skip_coverage:
        backend_command = [sys.executable, "-m", "pytest", "-rs", "-q"]
    else:
        backend_command = [
            sys.executable,
            "-m",
            "pytest",
            "-rs",
            "--cov=backend/app",
            "--cov-report=term",
            "--cov-fail-under=90",
            "-q",
        ]

    print("[RUNNING] backend tests and coverage", flush=True)
    backend_result = run_command(
        backend_command,
        timeout_seconds=args.command_timeout,
        extra_env=coverage_env,
    )
    if backend_result.get("status") == "PASS":
        gates.append(("backend_tests", dict(backend_result)))
    else:
        gates.append(("backend_tests", dict(backend_result)))

    dataset_record = None
    try:
        if dataset_report_path.is_file() and dataset_report_path.stat().st_size:
            dataset_record = json.loads(dataset_report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        dataset_record = None
    database_gate = {
        "status": "PASS" if dataset_record else "FAIL",
        "returncode": 0 if dataset_record else 1,
        "duration_seconds": backend_result.get("duration_seconds", 0),
        "command": [
            "pytest tests/test_fresh_install.py::test_fresh_database_migration_seed_and_ground_truth_invariants"
        ],
        "stdout": json.dumps(dataset_record, indent=2)
        if dataset_record
        else "Fresh-install test did not emit its measured database record.",
        "stderr": ""
        if dataset_record
        else "Fresh-install migrations, schema parity, repeated seed or ground-truth assertions did not pass.",
    }
    if dataset_record:
        database_gate.update(dataset_record)
    gates.append(("database_seed_and_ground_truth", database_gate))

    if args.skip_coverage:
        gates.append(
            (
                "backend_coverage",
                {
                    "status": "BLOCKED",
                    "returncode": None,
                    "duration_seconds": 0,
                    "command": [sys.executable, "-m", "pytest", "-rs", "--cov=backend/app", "--cov-fail-under=90"],
                    "stdout": "",
                    "stderr": "Coverage was explicitly skipped by the caller.",
                },
            )
        )
    else:
        coverage_output = backend_result.get("stdout", "")
        precise_match = re.search(r"Total coverage:\s*([0-9]+(?:\.[0-9]+)?)%", coverage_output)
        fallback_match = re.search(r"TOTAL\s+\d+\s+\d+\s+([0-9]+(?:\.[0-9]+)?)%", coverage_output)
        coverage_match = precise_match or fallback_match
        coverage_result = dict(backend_result)
        if coverage_match:
            coverage_result["coverage_percentage"] = float(coverage_match.group(1))
        coverage_result["purpose"] = "Coverage threshold measured by the same full backend test run."
        gates.append(("backend_coverage", coverage_result))

    if pg_test_url.startswith(("postgresql://", "postgresql+")):
        gates = [
            (
                name,
                {
                    **result,
                    "status": backend_result.get("status", "UNKNOWN"),
                    "returncode": backend_result.get("returncode"),
                    "duration_seconds": backend_result.get("duration_seconds", 0),
                    "stdout": backend_result.get("stdout", ""),
                    "stderr": backend_result.get("stderr", ""),
                },
            )
            if name == "postgresql_backend_tests"
            else (name, result)
            for name, result in gates
        ]

    gates.append(("wording_scan", check_wording()))
    failed = any(result.get("status") != "PASS" for _, result in gates)
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "platform": sys.platform,
        "gates": {name: result for name, result in gates},
        "overall_status": "FAIL" if failed else "PASS",
        "all_gates_passed": not failed,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    try:
        renderer_path = ROOT / "scripts" / "render_readme_summary.py"
        renderer_spec = importlib.util.spec_from_file_location("township_readme_renderer", renderer_path)
        if renderer_spec is None or renderer_spec.loader is None:
            raise RuntimeError("README summary renderer could not be loaded.")
        renderer_module = importlib.util.module_from_spec(renderer_spec)
        renderer_spec.loader.exec_module(renderer_module)
        renderer_module.render()
        summary["readme_summary_render"] = {
            "status": "PASS",
            "returncode": 0,
            "command": [sys.executable, "scripts/render_readme_summary.py"],
            "stdout": "README verification table rendered from summary.json.",
            "stderr": "",
        }
    except Exception as exc:
        summary["readme_summary_render"] = {
            "status": "FAIL",
            "returncode": 1,
            "command": [sys.executable, "scripts/render_readme_summary.py"],
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }
        summary["overall_status"] = "FAIL"
        summary["all_gates_passed"] = False
    REPORT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        dataset_report_path.unlink(missing_ok=True)
    except OSError:
        pass

    for name, result in gates:
        report_gate(name, result)
    report_gate("readme_summary_render", summary["readme_summary_render"])
    print(f"\nReport: {REPORT.relative_to(ROOT)}")
    print(f"Overall: {summary['overall_status']}")
    return 0 if summary["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
