"""
Township One — Visitor Photos Retention Purge Job.

Deletes photo binary files and nulls storage keys for photos older than 90 days.
Retains minimal event metadata for auditability.
Accepts an injectable clock for automated verification and test harnesses.

Usage:
    python -m backend.app.jobs.purge_visitor_photos
    python -m backend.app.jobs.purge_visitor_photos --as-of 2027-03-01T00:00:00Z
"""

import argparse
import sys
from datetime import datetime, timezone
from backend.app.services.visitor_service import purge_visitor_photos


def main():
    parser = argparse.ArgumentParser(description="Purge visitor photos past the 90-day retention cutoff")
    parser.add_argument(
        "--as-of",
        dest="as_of",
        type=str,
        default=None,
        help="Injectable reference datetime in ISO-8601 format (e.g. 2027-03-01T00:00:00Z)"
    )
    args = parser.parse_args()

    as_of_dt = None
    if args.as_of:
        try:
            as_of_dt = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        except ValueError as exc:
            print(f"Error parsing --as-of date: {exc}")
            sys.exit(1)
    else:
        as_of_dt = datetime.now(timezone.utc)

    print(f"Running visitor photo retention purge job with as-of cutoff: {as_of_dt.isoformat()}...")
    purged = purge_visitor_photos(as_of=as_of_dt)
    print(f"Retention purge complete. Photos purged: {purged}")


if __name__ == "__main__":
    main()
