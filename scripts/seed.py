"""
Township One — Seed Entrypoint Script.

Executes database seeding for development or demo environments.
Standard invocation:
    python scripts/seed.py
    python scripts/seed.py --mode reset-demo --confirm-local-demo
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from seed.seed_data import seed_database
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Township One Safe Database Seeder")
    parser.add_argument(
        "--mode",
        choices=["safe", "reset-demo"],
        default="safe",
        help="Seeding mode: 'safe' (idempotent, non-destructive) or 'reset-demo' (destructive clean reset)"
    )
    parser.add_argument(
        "--confirm-local-demo",
        action="store_true",
        help="Explicit confirmation required to execute destructive reset on local demo database"
    )
    args = parser.parse_args()

    seed_database(mode=args.mode, confirm_local_demo=args.confirm_local_demo)
