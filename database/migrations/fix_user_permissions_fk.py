#!/usr/bin/env python
"""Migration: Fix user_permissions FK referencing missing users_legacy_backup table.

Scenario:
  Current schema (corrupted legacy FK):
    FOREIGN KEY (user_id) REFERENCES "users_legacy_backup" (id)

  Desired schema:
    FOREIGN KEY (user_id) REFERENCES users (id)

Approach (SQLite limitation friendly):
  1. Detect if user_permissions table references users_legacy_backup.
  2. If not, exit gracefully (idempotent).
  3. PRAGMA foreign_keys=OFF.
  4. Create user_permissions_new with correct FK.
  5. Copy data.
  6. Drop old table, rename new.
  7. Recreate needed indexes & constraints.
  8. PRAGMA foreign_keys=ON and run checks.

Safety:
  - Creates a timestamped SQL backup of original table schema+data in data/migration_backups/.
  - Aborts if users table missing or if any copy step fails.
"""

from __future__ import annotations

import os
import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path("data/qa_intelligence.db")
BACKUP_DIR = Path("data/migration_backups")


def log(msg: str) -> None:
    print(f"[fix_user_permissions_fk] {msg}")


def table_ddl(con: sqlite3.Connection, table: str) -> str | None:
    cur = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def needs_migration(ddl: str) -> bool:
    return 'users_legacy_backup' in ddl and 'FOREIGN KEY (user_id)' in ddl


def main() -> None:
    if not DB_PATH.exists():
        log(f"Database not found: {DB_PATH}")
        return

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        ddl = table_ddl(con, "user_permissions")
        if ddl is None:
            log("Table user_permissions not found; nothing to do.")
            return
        if not needs_migration(ddl):
            log("Schema already correct (no users_legacy_backup reference). Exiting.")
            return

        log("Detected legacy FK reference to users_legacy_backup. Starting migration.")

        # Preconditions
        users_exists = table_ddl(con, "users") is not None
        if not users_exists:
            log("ERROR: users table not found. Abort.")
            return

        # Backup current table (schema + data)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_sql = BACKUP_DIR / f"user_permissions_legacy_{ts}.sql"
        with open(backup_sql, "w", encoding="utf-8") as f:
            f.write(f"-- Backup of user_permissions prior to FK fix at {ts} UTC\n")
            f.write(ddl + ";\n")
            for row in con.execute("SELECT * FROM user_permissions"):
                cols = list(row.keys())
                values = []
                for c in cols:
                    v = row[c]
                    if v is None:
                        values.append("NULL")
                    elif isinstance(v, (int, float)):
                        values.append(str(v))
                    else:
                        values.append("'" + str(v).replace("'", "''") + "'")
                f.write(
                    f"INSERT INTO user_permissions ({', '.join(cols)}) VALUES ({', '.join(values)});\n"
                )
        log(f"Backup written: {backup_sql}")

        # Drop dependent views referencing legacy table (if exist)
        views = list(
            con.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='view' AND sql LIKE '%users_legacy_backup%'"
            )
        )
        dropped_views: list[tuple[str, str]] = []
        for v in views:
            name = v[0]
            sql = v[1]
            dropped_views.append((name, sql))
            log(f"Dropping dependent view: {name}")
            con.execute(f"DROP VIEW IF EXISTS {name}")

        # Start migration
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys=OFF;")
        cur.execute("BEGIN IMMEDIATE;")

        new_table_sql = (
            "CREATE TABLE user_permissions_new ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "user_id INTEGER NOT NULL,"
            "permission_id INTEGER NOT NULL,"
            "granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            "granted_by VARCHAR(50),"
            "revoked_at DATETIME,"
            "revoked_by VARCHAR(100),"
            "expires_at DATETIME,"
            "is_active BOOLEAN DEFAULT 1,"
            "FOREIGN KEY (user_id) REFERENCES users (id),"
            "FOREIGN KEY (permission_id) REFERENCES permissions (id),"
            "UNIQUE(user_id, permission_id)"
            ");"
        )
        cur.execute(new_table_sql)
        log("Created user_permissions_new with corrected FK")

        # Copy data (verify referenced users exist)
        missing_users = list(
            cur.execute(
                "SELECT DISTINCT up.user_id FROM user_permissions up "
                "LEFT JOIN users u ON u.id = up.user_id WHERE u.id IS NULL"
            )
        )
        if missing_users:
            log(
                f"WARNING: {len(missing_users)} user_ids lack matching users; those rows will be skipped."
            )

        cur.execute(
            "INSERT OR IGNORE INTO user_permissions_new "
            "(id, user_id, permission_id, granted_at, granted_by, revoked_at, revoked_by, expires_at, is_active) "
            "SELECT up.id, up.user_id, up.permission_id, up.granted_at, up.granted_by, up.revoked_at, up.revoked_by, up.expires_at, up.is_active "
            "FROM user_permissions up JOIN users u ON u.id = up.user_id"
        )
        copied = cur.rowcount
        log(f"Copied {copied} rows into user_permissions_new")

        # Drop old & rename
        cur.execute("DROP TABLE user_permissions;")
        cur.execute("ALTER TABLE user_permissions_new RENAME TO user_permissions;")
        log("Replaced legacy table")

        # Index recreation
        cur.execute(
            "CREATE INDEX idx_user_permissions_active ON user_permissions(user_id, is_active);"
        )
        log("Recreated index idx_user_permissions_active")

        cur.execute("COMMIT;")
        cur.execute("PRAGMA foreign_keys=ON;")

    # Validation checks
        fk_issues = list(cur.execute("PRAGMA foreign_key_check;"))
        if fk_issues:
            log(f"Foreign key issues remain: {fk_issues}")
        else:
            log("Foreign key check: OK (no violations)")

        integrity = list(cur.execute("PRAGMA integrity_check;"))
        log(f"Integrity check: {integrity[0][0] if integrity else 'UNKNOWN'}")

        # Recreate views updated to reference users instead of users_legacy_backup
        for name, sql in dropped_views:
            new_sql = sql.replace('"users_legacy_backup"', 'users').replace('users_legacy_backup', 'users')
            try:
                con.execute(new_sql)
                log(f"Recreated view {name} with updated references")
            except Exception as e:  # noqa: BLE001
                log(f"WARNING: failed to recreate view {name}: {e}")

        log("Migration complete.")
    finally:
        con.close()


if __name__ == "__main__":  # pragma: no cover
    main()
