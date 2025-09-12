#!/usr/bin/env python
"""Migration: Fix user_roles FK referencing users_legacy_backup and remove orphan entries.

Steps:
 1. Detect legacy reference.
 2. Backup existing table schema+data.
 3. Create new table with correct FK to users.
 4. Copy only rows whose user_id exists in users.
 5. Replace table and recreate constraints.
 6. Report dropped (orphan) rows count.
"""

from __future__ import annotations

import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path("data/qa_intelligence.db")
BACKUP_DIR = Path("data/migration_backups")


def log(msg: str) -> None:
    print(f"[fix_user_roles_fk] {msg}")


def fetch_table_sql(con: sqlite3.Connection, name: str) -> str | None:
    cur = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def main() -> None:
    if not DB_PATH.exists():
        log("Database not found")
        return
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        ddl = fetch_table_sql(con, "user_roles")
        if ddl is None:
            log("user_roles table missing; nothing to do")
            return
        if 'users_legacy_backup' not in ddl:
            log("user_roles already references users. Exiting.")
            return

        users_exists = fetch_table_sql(con, "users") is not None
        if not users_exists:
            log("ERROR: users table missing; abort")
            return

        # Backup
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_sql = BACKUP_DIR / f"user_roles_legacy_{ts}.sql"
        with open(backup_sql, "w", encoding="utf-8") as f:
            f.write(f"-- Backup user_roles at {ts} UTC\n")
            f.write(ddl + ";\n")
            for row in con.execute("SELECT * FROM user_roles"):
                values = []
                for v in row:
                    if v is None:
                        values.append("NULL")
                    elif isinstance(v, (int, float)):
                        values.append(str(v))
                    else:
                        values.append("'" + str(v).replace("'", "''") + "'")
                f.write(
                    "INSERT INTO user_roles VALUES (" + ", ".join(values) + ");\n"
                )
        log(f"Backup written: {backup_sql}")

        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys=OFF;")
        cur.execute("BEGIN IMMEDIATE;")

        cur.execute(
            "CREATE TABLE user_roles_new ("
            "user_id INTEGER NOT NULL,"
            "role_id INTEGER NOT NULL,"
            "assigned_by VARCHAR(100),"
            "expires_at DATETIME,"
            "is_active BOOLEAN DEFAULT 1,"
            "assigned_at DATETIME,"
            "CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id),"
            "CONSTRAINT uq_user_role UNIQUE (user_id, role_id),"
            "CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,"
            "CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE"
            ");"
        )
        log("Created user_roles_new")

        # Count orphans
        orphan_rows = list(
            cur.execute(
                "SELECT ur.user_id, ur.role_id FROM user_roles ur LEFT JOIN users u ON u.id = ur.user_id WHERE u.id IS NULL"
            )
        )
        if orphan_rows:
            log(f"Found {len(orphan_rows)} orphan rows that will be dropped: {orphan_rows}")

        cur.execute(
            "INSERT OR IGNORE INTO user_roles_new (user_id, role_id, assigned_by, expires_at, is_active, assigned_at) "
            "SELECT ur.user_id, ur.role_id, ur.assigned_by, ur.expires_at, ur.is_active, ur.assigned_at "
            "FROM user_roles ur JOIN users u ON u.id = ur.user_id"
        )
        copied = cur.rowcount
        log(f"Copied {copied} rows into user_roles_new")

        cur.execute("DROP TABLE user_roles;")
        cur.execute("ALTER TABLE user_roles_new RENAME TO user_roles;")
        log("Replaced user_roles table")

        cur.execute("COMMIT;")
        cur.execute("PRAGMA foreign_keys=ON;")

        fk = list(cur.execute("PRAGMA foreign_key_check;"))
        if fk:
            log(f"Foreign key issues remain: {fk}")
        else:
            log("Foreign key check: OK")

        log("Migration complete.")
    finally:
        con.close()


if __name__ == "__main__":  # pragma: no cover
    main()
