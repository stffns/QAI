"""Database integrity & foreign key health check.

Purpose:
  Catch silent SQLite corruption or broken foreign key references early in CI.

Behavior:
  - Targets the primary application database at `data/qa_intelligence.db`.
  - If env QA_DB_PATH is set, uses that path instead.
  - Skips gracefully if the database file does not exist (e.g., first install) OR
    if env QA_SKIP_DB_INTEGRITY=1.
  - Runs:
       PRAGMA integrity_check;   (expects single row 'ok')
       PRAGMA foreign_key_check; (expects no rows)
  - Fails with detailed diagnostic output otherwise.

Rationale:
  Previous incidents of index corruption & legacy FK references went undetected
  until runtime. This test provides an early warning safety net.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest


DEFAULT_DB = Path("data/qa_intelligence.db")


def _should_skip() -> tuple[bool, str]:
    if os.getenv("QA_SKIP_DB_INTEGRITY") == "1":
        return True, "QA_SKIP_DB_INTEGRITY=1"
    return False, ""


def _get_db_path() -> Path:
    env_path = os.getenv("QA_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open SQLite DB in read-only mode if possible; fall back to normal open."""
    uri = f"file:{db_path}?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        # Fallback (e.g., older SQLite build lacking ro or path not accessible ro)
        return sqlite3.connect(str(db_path))


@pytest.mark.integration
def test_sqlite_integrity_and_foreign_keys():
    skip, reason = _should_skip()
    if skip:
        pytest.skip(f"Database integrity test skipped: {reason}")

    db_path = _get_db_path()

    if not db_path.exists():
        pytest.skip(f"Database file not found: {db_path}")

    # Avoid extremely large dumps on failure; collect only first N violations
    MAX_VIOLATIONS_DISPLAY = 25

    con = _open_readonly(db_path)
    try:
        con.row_factory = sqlite3.Row
        # Ensure FK enforcement (needed for foreign_key_check reliability)
        con.execute("PRAGMA foreign_keys=ON;")

        integrity_rows = list(con.execute("PRAGMA integrity_check;"))
        assert integrity_rows, "No rows returned from PRAGMA integrity_check; unexpected."\
        
        ok_rows = [r[0] for r in integrity_rows]
        if ok_rows != ["ok"]:
            tables = list(con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1;"))
            table_list = ", ".join(r[0] for r in tables)
            assert ok_rows == ["ok"], (
                "SQLite integrity_check failed. First entries: "
                f"{ok_rows[:5]} (full count={len(ok_rows)}). "
                f"Tables present: {table_list}"
            )

        fk_rows = list(con.execute("PRAGMA foreign_key_check;"))
        if fk_rows:
            sample = fk_rows[:MAX_VIOLATIONS_DISPLAY]
            details = ", ".join(
                f"(table={r[0]}, rowid={r[1]}, parent={r[2]}, fkid={r[3]})" for r in sample
            )
            leftover = len(fk_rows) - len(sample)
            if leftover > 0:
                details += f" ... (+{leftover} more)"
            pytest.fail(
                "Foreign key violations detected: "
                f"{details}. Run 'PRAGMA foreign_key_check;' locally for full list."
            )
    finally:
        con.close()
