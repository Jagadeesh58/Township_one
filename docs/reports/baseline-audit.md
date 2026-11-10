# Repository Inspection Notes

These notes describe findings in the supplied source snapshot before the current edits. They are not a statement of the present verification result.

## Findings in the supplied snapshot

- SQLAlchemy model declarations and Alembic migration definitions did not describe the same schema.
- A fresh database migration followed by the documented seed path was not reliable.
- Two seed entry points were referenced by different parts of the repository.
- README and report files contained outdated test information and inconsistent run commands.
- Python lint and type-check configuration did not cover the whole application consistently.
- PostgreSQL row-lock behaviour and browser-based journeys had not been demonstrated by the supplied test evidence.
- The guard interface did not persist visitor photo Blobs offline, although some documentation described offline synchronization.
- Visitor-photo deletion could record a failed filesystem removal as successful.

## Evidence policy

The earlier archive did not retain the raw command output needed to reproduce its historical numeric measurements. Those figures are not repeated here. The current command output, return codes, skip reasons and database seed evidence are recorded by `scripts/verify_release.py` in `docs/reports/summary.json`.

A blocked or unexecuted check must remain identified as unverified. SQLite results do not establish PostgreSQL row-lock behaviour, and source-level browser code does not establish that a deployed browser workflow works.
