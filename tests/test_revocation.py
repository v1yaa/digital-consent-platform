"""
Tests for the revocation workflow.
"""

import sqlite3
import pytest
from datetime import datetime, timezone

from app import services
from app import database as db_module


def _create(**kwargs):
    defaults = dict(
        user_identifier="revoke_test@example.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    defaults.update(kwargs)
    return services.create_consent(**defaults)


# ---------------------------------------------------------------------------
# Revocation via service
# ---------------------------------------------------------------------------

def test_revoke_changes_status():
    """Revocation sets status to 'revoked'."""
    record = _create(user_identifier="rev_user@test.com")
    services.revoke_consent(record.id)
    updated = services.get_consent(record.id)
    assert updated.status == "revoked"


def test_revoke_sets_revocation_timestamp():
    """Revocation records the revocation timestamp."""
    record = _create(user_identifier="rev_ts@test.com")
    services.revoke_consent(record.id)
    updated = services.get_consent(record.id)
    assert updated.revocation_date is not None


def test_revoke_writes_audit_event():
    """Revocation writes a consent_revoked audit log entry."""
    record = _create(user_identifier="rev_audit@test.com", purpose="marketing", scope="email_contact")
    services.revoke_consent(record.id)

    db_path = db_module._db_path()
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT event_type, description FROM audit_logs WHERE consent_id=? AND event_type='consent_revoked'",
        (record.id,),
    ).fetchone()
    conn.close()
    assert row is not None
    assert "revoked" in row[1].lower()


def test_revoke_record_not_reported_as_active():
    """Revoked record does not appear in the 'active' count of the dashboard."""
    record = _create(user_identifier="rev_active@test.com")
    services.revoke_consent(record.id)
    stats = services.get_dashboard_stats()
    assert stats["revoked"] >= 1
    # Revoked record should NOT be in active count
    records = services.list_consents(status_filter="granted")
    active_ids = [r.id for r in records]
    assert record.id not in active_ids


# ---------------------------------------------------------------------------
# Revocation via HTTP route
# ---------------------------------------------------------------------------

def test_revoke_via_post(client):
    """POST /consents/<id>/revoke revokes the record and redirects."""
    record = _create(user_identifier="web_revoke@test.com")
    resp = client.post(f"/consents/{record.id}/revoke", follow_redirects=True)
    assert resp.status_code == 200
    assert b"revoked" in resp.data.lower()

    updated = services.get_consent(record.id)
    assert updated.status == "revoked"


def test_revoke_already_revoked_shows_warning(client):
    """Attempting to revoke an already-revoked record shows a warning."""
    record = _create(user_identifier="double_revoke@test.com")
    services.revoke_consent(record.id)

    resp = client.post(f"/consents/{record.id}/revoke", follow_redirects=True)
    assert resp.status_code == 200
    assert b"cannot be revoked" in resp.data or b"warning" in resp.data.lower()
