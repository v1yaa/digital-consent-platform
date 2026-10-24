"""
Tests for the audit trail functionality.
"""

import sqlite3
import pytest
from datetime import datetime, timezone

from app import services
from app import database as db_module


def _audit_rows(consent_id=None, event_type=None):
    db_path = db_module._db_path()
    conn = sqlite3.connect(db_path)
    q = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if consent_id is not None:
        q += " AND consent_id=?"
        params.append(consent_id)
    if event_type:
        q += " AND event_type=?"
        params.append(event_type)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def test_audit_log_page_loads(client):
    resp = client.get("/audit")
    assert resp.status_code == 200


def test_consent_created_event():
    """Creating a consent generates a consent_created audit event."""
    record = services.create_consent(
        user_identifier="audit_create@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    rows = _audit_rows(consent_id=record.id, event_type="consent_created")
    assert len(rows) == 1
    assert record.user_identifier in rows[0][3]  # description column


def test_consent_denied_event():
    """Denied consent creates consent_denied audit event."""
    record = services.create_consent(
        user_identifier="audit_deny@test.com",
        purpose="marketing",
        scope="email_contact",
        status="denied",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    rows = _audit_rows(consent_id=record.id, event_type="consent_denied")
    assert len(rows) == 1


def test_consent_updated_event():
    """Updating a consent generates a consent_updated audit event."""
    record = services.create_consent(
        user_identifier="audit_upd@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    services.update_consent(
        record_id=record.id,
        purpose="marketing",
        scope="email_contact",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes="updated",
    )
    rows = _audit_rows(consent_id=record.id, event_type="consent_updated")
    assert len(rows) == 1


def test_consent_revoked_event():
    """Revoking a consent generates a consent_revoked audit event."""
    record = services.create_consent(
        user_identifier="audit_rev@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    services.revoke_consent(record.id)
    rows = _audit_rows(consent_id=record.id, event_type="consent_revoked")
    assert len(rows) == 1


def test_audit_log_has_timestamp():
    """All audit events have a non-null timestamp."""
    services.create_consent(
        user_identifier="ts_check@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    all_rows = _audit_rows()
    assert all(row[4] is not None for row in all_rows)  # timestamp column


def test_audit_log_references_consent():
    """Audit events reference their related consent record."""
    record = services.create_consent(
        user_identifier="ref_check@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    rows = _audit_rows(consent_id=record.id)
    assert len(rows) >= 1
    assert all(row[1] == record.id for row in rows)  # consent_id column


def test_report_generated_event_has_no_consent_id():
    """Report-generated audit events have no specific consent_id."""
    services.generate_report()
    rows = _audit_rows(event_type="report_generated")
    assert len(rows) >= 1
    assert rows[-1][1] is None  # consent_id column should be NULL
