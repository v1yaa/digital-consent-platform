"""
SQLite database layer for the Digital Consent Platform.
Uses Python's built-in sqlite3 module – no external ORM required.
"""

from __future__ import annotations

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from .models import ConsentRecord, AuditLog

# ---------------------------------------------------------------------------
# DB path helper
# ---------------------------------------------------------------------------

def _db_path() -> str:
    raw = os.environ.get("DATABASE_URL", "sqlite:///consent.db")
    # Strip sqlite:/// prefix
    if raw.startswith("sqlite:////"):
        return raw[10:]   # absolute path: sqlite:////data/consent.db -> /data/consent.db
    if raw.startswith("sqlite:///"):
        return raw[10:]   # relative path: sqlite:///consent.db -> consent.db
    return raw


@contextmanager
def get_db():
    """Yield an open sqlite3 connection with row_factory set."""
    path = _db_path()
    # Ensure parent directory exists (for /data/consent.db in Docker)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS consent_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_identifier  TEXT    NOT NULL,
    purpose          TEXT    NOT NULL,
    scope            TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'granted',
    consent_date     TEXT    NOT NULL,
    expiration_date  TEXT,
    revocation_date  TEXT,
    notes            TEXT,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    consent_id  INTEGER REFERENCES consent_records(id),
    event_type  TEXT    NOT NULL,
    description TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL
);
"""


def init_db():
    with get_db() as conn:
        conn.executescript(DDL)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dt_str(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Row -> dataclass
# ---------------------------------------------------------------------------

def _row_to_consent(row) -> ConsentRecord:
    return ConsentRecord(
        id=row["id"],
        user_identifier=row["user_identifier"],
        purpose=row["purpose"],
        scope=row["scope"],
        status=row["status"],
        consent_date=_parse_dt(row["consent_date"]),
        expiration_date=_parse_dt(row["expiration_date"]),
        revocation_date=_parse_dt(row["revocation_date"]),
        notes=row["notes"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _row_to_audit(row) -> AuditLog:
    return AuditLog(
        id=row["id"],
        consent_id=row["consent_id"],
        event_type=row["event_type"],
        description=row["description"],
        timestamp=_parse_dt(row["timestamp"]),
    )


# ---------------------------------------------------------------------------
# Consent CRUD
# ---------------------------------------------------------------------------

def insert_consent(
    user_identifier: str,
    purpose: str,
    scope: str,
    status: str,
    consent_date: Optional[datetime],
    expiration_date: Optional[datetime],
    notes: Optional[str],
) -> ConsentRecord:
    now = _now_str()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO consent_records
               (user_identifier, purpose, scope, status, consent_date,
                expiration_date, revocation_date, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,NULL,?,?,?)""",
            (
                user_identifier.strip(),
                purpose,
                scope,
                status,
                _dt_str(consent_date) or now,
                _dt_str(expiration_date),
                notes.strip() if notes else None,
                now,
                now,
            ),
        )
        rid = cur.lastrowid
        event = "consent_created" if status == "granted" else "consent_denied"
        conn.execute(
            "INSERT INTO audit_logs (consent_id, event_type, description, timestamp) VALUES (?,?,?,?)",
            (
                rid,
                event,
                f"Consent record created for user '{user_identifier}' — purpose: {purpose}, scope: {scope}, status: {status}.",
                now,
            ),
        )
        row = conn.execute("SELECT * FROM consent_records WHERE id=?", (rid,)).fetchone()
        return _row_to_consent(row)


def update_consent_db(
    record_id: int,
    purpose: str,
    scope: str,
    status: str,
    consent_date: Optional[datetime],
    expiration_date: Optional[datetime],
    notes: Optional[str],
    user_identifier: Optional[str] = None,
) -> ConsentRecord:
    now = _now_str()
    with get_db() as conn:
        rev_val = now if status == "revoked" else None
        if user_identifier:
            conn.execute(
                """UPDATE consent_records
                   SET user_identifier=?, purpose=?, scope=?, status=?, consent_date=?,
                       expiration_date=?, revocation_date=CASE WHEN ?='revoked' THEN COALESCE(revocation_date, ?) ELSE NULL END,
                       notes=?, updated_at=?
                   WHERE id=?""",
                (
                    user_identifier.strip(),
                    purpose,
                    scope,
                    status,
                    _dt_str(consent_date) or now,
                    _dt_str(expiration_date),
                    status,
                    rev_val,
                    notes.strip() if notes else None,
                    now,
                    record_id,
                ),
            )
        else:
            conn.execute(
                """UPDATE consent_records
                   SET purpose=?, scope=?, status=?, consent_date=?,
                       expiration_date=?, revocation_date=CASE WHEN ?='revoked' THEN COALESCE(revocation_date, ?) ELSE NULL END,
                       notes=?, updated_at=?
                   WHERE id=?""",
                (
                    purpose,
                    scope,
                    status,
                    _dt_str(consent_date) or now,
                    _dt_str(expiration_date),
                    status,
                    rev_val,
                    notes.strip() if notes else None,
                    now,
                    record_id,
                ),
            )
        conn.execute(
            "INSERT INTO audit_logs (consent_id, event_type, description, timestamp) VALUES (?,?,?,?)",
            (
                record_id,
                "consent_updated",
                f"Consent record #{record_id} updated — new status: {status}, purpose: {purpose}.",
                now,
            ),
        )
        row = conn.execute("SELECT * FROM consent_records WHERE id=?", (record_id,)).fetchone()
        return _row_to_consent(row)


def revoke_consent_db(record_id: int) -> ConsentRecord:
    now = _now_str()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM consent_records WHERE id=?", (record_id,)).fetchone()
        if row is None:
            raise ValueError(f"Consent record #{record_id} not found.")
        record = _row_to_consent(row)
        conn.execute(
            "UPDATE consent_records SET status='revoked', revocation_date=?, updated_at=? WHERE id=?",
            (now, now, record_id),
        )
        conn.execute(
            "INSERT INTO audit_logs (consent_id, event_type, description, timestamp) VALUES (?,?,?,?)",
            (
                record_id,
                "consent_revoked",
                f"Consent record #{record_id} revoked for user '{record.user_identifier}' — purpose: {record.purpose}.",
                now,
            ),
        )
        updated_row = conn.execute("SELECT * FROM consent_records WHERE id=?", (record_id,)).fetchone()
        return _row_to_consent(updated_row)


def get_consent_db(record_id: int) -> Optional[ConsentRecord]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM consent_records WHERE id=?", (record_id,)).fetchone()
        return _row_to_consent(row) if row else None


def list_consents_db(
    status_filter: Optional[str] = None,
    purpose_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
) -> list[ConsentRecord]:
    query = "SELECT * FROM consent_records WHERE 1=1"
    params: list = []

    now = _now_str()
    if status_filter and status_filter != "all":
        if status_filter == "expired":
            query += " AND ((status='expired') OR (status='granted' AND expiration_date IS NOT NULL AND expiration_date < ?))"
            params.append(now)
        elif status_filter == "granted":
            query += " AND status='granted' AND (expiration_date IS NULL OR expiration_date >= ?)"
            params.append(now)
        else:
            query += " AND status=?"
            params.append(status_filter)

    if purpose_filter and purpose_filter != "all":
        query += " AND purpose=?"
        params.append(purpose_filter)

    if user_filter:
        query += " AND LOWER(user_identifier) LIKE ?"
        params.append(f"%{user_filter.lower()}%")

    query += " ORDER BY created_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_consent(r) for r in rows]


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

def get_stats_db() -> dict:
    now = _now_str()
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM consent_records").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM consent_records WHERE status='granted' AND (expiration_date IS NULL OR expiration_date >= ?)", (now,)
        ).fetchone()[0]
        expired = conn.execute(
            "SELECT COUNT(*) FROM consent_records WHERE (status='expired') OR (status='granted' AND expiration_date IS NOT NULL AND expiration_date < ?)", (now,)
        ).fetchone()[0]
        revoked = conn.execute("SELECT COUNT(*) FROM consent_records WHERE status='revoked'").fetchone()[0]
        denied = conn.execute("SELECT COUNT(*) FROM consent_records WHERE status='denied'").fetchone()[0]

        recent_rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()
        recent_logs = [_row_to_audit(r) for r in recent_rows]

        purpose_rows = conn.execute(
            "SELECT purpose, COUNT(*) as cnt FROM consent_records GROUP BY purpose"
        ).fetchall()
        purpose_breakdown = {r["purpose"]: r["cnt"] for r in purpose_rows}

    return {
        "total": total,
        "active": active,
        "expired": expired,
        "revoked": revoked,
        "denied": denied,
        "recent_logs": recent_logs,
        "purpose_breakdown": purpose_breakdown,
    }


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

def get_audit_logs_db(limit: int = 500) -> list[AuditLog]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_audit(r) for r in rows]


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def generate_report_db(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    from datetime import timedelta

    query = "SELECT * FROM consent_records WHERE 1=1"
    params: list = []
    if start_date:
        query += " AND consent_date >= ?"
        params.append(_dt_str(start_date))
    if end_date:
        query += " AND consent_date <= ?"
        params.append(_dt_str(end_date))
    query += " ORDER BY created_at DESC"

    now_str = _now_str()
    now_dt = datetime.now(timezone.utc)
    soon_str = _dt_str(now_dt + timedelta(days=30))

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        records = [_row_to_consent(r) for r in rows]

        stats = {"total": len(records), "active": 0, "denied": 0, "revoked": 0, "expired": 0}
        by_purpose: dict[str, int] = {}
        expiring_soon: list[ConsentRecord] = []

        for r in records:
            eff = r.effective_status
            if eff in stats:
                stats[eff] += 1
            else:
                stats["active"] += 1

            by_purpose[r.purpose] = by_purpose.get(r.purpose, 0) + 1

            if (
                r.status == "granted"
                and r.expiration_date is not None
                and _dt_str(r.expiration_date) >= now_str
                and _dt_str(r.expiration_date) <= soon_str
            ):
                expiring_soon.append(r)

        # Write audit event for report generation
        conn.execute(
            "INSERT INTO audit_logs (consent_id, event_type, description, timestamp) VALUES (NULL,?,?,?)",
            (
                "report_generated",
                f"Compliance report generated — {stats['total']} records in scope.",
                now_str,
            ),
        )

    return {
        "stats": stats,
        "by_purpose": by_purpose,
        "expiring_soon": expiring_soon,
        "records": records,
        "start_date": start_date,
        "end_date": end_date,
    }


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv_db(records: list[ConsentRecord]) -> str:
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "User Identifier", "Purpose", "Scope", "Status",
        "Consent Date", "Expiration Date", "Revocation Date",
        "Notes", "Created At", "Updated At",
    ])
    for r in records:
        writer.writerow([
            r.id,
            r.user_identifier,
            r.purpose,
            r.scope,
            r.effective_status,
            r.consent_date.isoformat() if r.consent_date else "",
            r.expiration_date.isoformat() if r.expiration_date else "",
            r.revocation_date.isoformat() if r.revocation_date else "",
            r.notes or "",
            r.created_at.isoformat() if r.created_at else "",
            r.updated_at.isoformat() if r.updated_at else "",
        ])
    return output.getvalue()
