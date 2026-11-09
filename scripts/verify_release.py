"""
Township One - Automated Release Verification Script.

Executes and verifies:
1. Ground-truth assertions on clean database seed (T07-1203, T12-0408, T21-1601).
2. Code quality: ruff check backend (0 errors).
3. Type soundness: mypy backend/app (0 errors).
4. Automated tests and statement coverage >= 90%.
5. Frontend verification: TypeScript typecheck, Vitest, and production build.
6. Prohibited wording scanner across repository.
7. Emits verification summary report to docs/reports/summary.json.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config


def run_cmd(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    use_shell = sys.platform == "win32"
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=use_shell)
    return res.returncode, res.stdout, res.stderr


def check_ground_truth_invariants() -> dict:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_url = f"sqlite:///{db_path.replace(os.sep, '/')}"
    old_env = os.environ.get("DATABASE_URL")
    engine = None

    try:
        os.environ["DATABASE_URL"] = db_url

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")

        from backend.app.models.entities import Bill, Flat, Gate, StaffMember, Tower
        from seed.seed_data import seed_database

        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        seed_database(target_engine=engine, mode="safe")

        with Session(engine) as session:
            towers_count = session.query(Tower).count()
            flats_count = session.query(Flat).count()
            staff_count = session.query(StaffMember).count()
            gates_count = session.query(Gate).count()

            assert towers_count == 28, f"Expected 28 towers, found {towers_count}"
            assert flats_count == 2400, f"Expected 2,400 flats, found {flats_count}"
            assert staff_count == 180, f"Expected 180 staff members, found {staff_count}"
            assert gates_count == 4, f"Expected 4 gates, found {gates_count}"

            # T07-1203: Paid in full (balance 0.00)
            f1 = session.query(Flat).filter(Flat.flat_number == "T07-1203").first()
            assert f1 is not None
            b1 = session.query(Bill).filter(Bill.flat_id == f1.id).first()
            assert b1 is not None and b1.balance_amount == Decimal("0.00") and b1.status == "PAID"

            # T12-0408: Unpaid (balance 6,370.00, 47 days overdue)
            f2 = session.query(Flat).filter(Flat.flat_number == "T12-0408").first()
            assert f2 is not None
            b2 = session.query(Bill).filter(Bill.flat_id == f2.id).first()
            assert b2 is not None and b2.balance_amount == Decimal("6370.00") and b2.status == "OVERDUE"

            # T21-1601: Partially paid (balance 5,660.00, 18 days overdue)
            f3 = session.query(Flat).filter(Flat.flat_number == "T21-1601").first()
            assert f3 is not None
            b3 = session.query(Bill).filter(Bill.flat_id == f3.id).first()
            assert b3 is not None and b3.balance_amount == Decimal("5660.00") and b3.status == "PARTIALLY_PAID"

        return {
            "status": "PASS",
            "towers": towers_count,
            "flats": flats_count,
            "staff": staff_count,
            "gates": gates_count,
            "ground_truth_balances": {
                "T07-1203": "0.00",
                "T12-0408": "6370.00",
                "T21-1601": "5660.00",
            },
        }
    finally:
        if engine is not None:
            engine.dispose()
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env
        else:
            os.environ.pop("DATABASE_URL", None)
        try:
            os.remove(db_path)
        except OSError:
            pass


def check_prohibited_words() -> dict:
    patterns = [
        re.compile(r"\bDay\s*[123]\b", re.IGNORECASE),
        re.compile(r"\bD[123]-S[12]\b", re.IGNORECASE),
        re.compile(r"\bacceptance\s*matrix\b", re.IGNORECASE),
        re.compile(r"\bacceptance\s*suite\b", re.IGNORECASE),
        re.compile(r"\bexecution\s*plan\b", re.IGNORECASE),
        re.compile(r"\bcheckpoint\b", re.IGNORECASE),
        re.compile(r"\bphase\s*[0-9IVX]+\b", re.IGNORECASE),
        re.compile(r"\bprompt\s*[A-Z0-9]+\b", re.IGNORECASE),
        re.compile(r"\benterprise-grade\b", re.IGNORECASE),
        re.compile(r"\bproduction-grade\b", re.IGNORECASE),
    ]

    scanned_exts = {".py", ".ts", ".tsx", ".md", ".json", ".yml", ".yaml"}
    skip_dirs = {".git", "node_modules", "dist", ".pytest_cache", "__pycache__", ".venv", "venv"}

    violations = []

    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in scanned_exts:
                continue
            path = os.path.join(root, f)
            # Skip this verification script itself and prior summary report
            if "verify_release.py" in path or "summary.json" in path:
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_no, line in enumerate(fh, 1):
                        for pat in patterns:
                            if pat.search(line):
                                violations.append(f"{path}:{line_no}: {line.strip()[:80]}")
            except Exception:
                pass

    return {
        "status": "PASS" if not violations else "FAIL",
        "violations_count": len(violations),
        "violations": violations[:20],
    }


def main():
    print("=" * 60)
    print("TOWNSHIP ONE — RELEASE VERIFICATION RUNNER")
    print("=" * 60)

    summary = {
        "timestamp": datetime.now(UTC).isoformat(),
        "gates": {},
    }

    # 1. Ground truth
    print("\n1. Verifying Database Parity & Ground-Truth Invariants...")
    gt_res = check_ground_truth_invariants()
    print(f"   Ground-Truth Status: {gt_res['status']}")
    summary["gates"]["database_and_ground_truth"] = gt_res

    # 2. Ruff check
    print("\n2. Verifying Backend Code Quality (Ruff)...")
    rc_code, rc_out, _ = run_cmd(["py", "-m", "ruff", "check", "backend"])
    print(f"   Ruff Return Code: {rc_code}")
    summary["gates"]["ruff"] = {"return_code": rc_code, "status": "PASS" if rc_code == 0 else "FAIL"}

    # 3. Mypy check
    print("\n3. Verifying Backend Type Soundness (Mypy)...")
    my_code, my_out, _ = run_cmd(["py", "-m", "mypy", "backend/app"])
    print(f"   Mypy Return Code: {my_code}")
    summary["gates"]["mypy"] = {"return_code": my_code, "status": "PASS" if my_code == 0 else "FAIL"}

    # 4. Pytest suite with coverage
    print("\n4. Running Backend Test Suite with Coverage...")
    pt_code, pt_out, _ = run_cmd(["py", "-m", "pytest", "--cov=backend/app", "--cov-report=term", "-q"])
    print(f"   Pytest Return Code: {pt_code}")

    cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", pt_out)
    cov_pct = int(cov_match.group(1)) if cov_match else 0
    print(f"   Coverage: {cov_pct}% (Target >= 90%)")
    summary["gates"]["tests_and_coverage"] = {
        "return_code": pt_code,
        "coverage_percentage": cov_pct,
        "status": "PASS" if pt_code == 0 and cov_pct >= 90 else "FAIL",
    }

    # 5. Frontend checks
    print("\n5. Verifying Frontend (TypeScript, Vitest, Vite Build)...")
    fe_tsc_code, _, _ = run_cmd(["npx", "tsc", "--noEmit"], cwd="frontend")
    fe_test_code, _, _ = run_cmd(["npm", "test"], cwd="frontend")
    fe_bld_code, _, _ = run_cmd(["npm", "run", "build"], cwd="frontend")
    fe_pass = (fe_tsc_code == 0) and (fe_test_code == 0) and (fe_bld_code == 0)
    print(f"   Frontend Status: {'PASS' if fe_pass else 'FAIL'}")
    summary["gates"]["frontend"] = {
        "tsc_return_code": fe_tsc_code,
        "test_return_code": fe_test_code,
        "build_return_code": fe_bld_code,
        "status": "PASS" if fe_pass else "FAIL",
    }

    # 6. Prohibited words check
    print("\n6. Scanning Repository for Prohibited Wording...")
    vocab_res = check_prohibited_words()
    print(f"   Vocabulary Guard: {vocab_res['status']} ({vocab_res['violations_count']} violations)")
    summary["gates"]["vocabulary_guard"] = vocab_res

    os.makedirs("docs/reports", exist_ok=True)
    report_path = "docs/reports/summary.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print(f"\nVerification summary saved to: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
