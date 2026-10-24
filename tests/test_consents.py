"""
Tests for consent creation, listing, updating, and expiration handling.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app import services
from app import database as db_module


# ---------------------------------------------------------------------------
# Application startup
# ---------------------------------------------------------------------------

def test_app_starts(client):
    """GET / returns HTTP 200 (dashboard loads)."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_dashboard_loads(client):
    """Dashboard renders key sections."""
    resp = client.get("/")
    assert b"Dashboard" in resp.data or b"Total" in resp.data


def test_health_endpoint(client):
    """Health check returns ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Consent creation via service
# ---------------------------------------------------------------------------

def test_create_consent_via_service():
    """Service layer creates a valid consent record and writes an audit event."""
    now = datetime.now(timezone.utc)
    record = services.create_consent(
        user_identifier="alice@example.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=now,
        expiration_date=None,
        notes="Test note",
    )
    assert record.id is not None
    assert record.user_identifier == "alice@example.com"
    assert record.purpose == "analytics"
    assert record.status == "granted"
    assert record.notes == "Test note"

    # Audit event must exist
    import sqlite3
    db_path = db_module._db_path()
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT event_type FROM audit_logs WHERE consent_id=?", (record.id,)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "consent_created"


def test_create_consent_via_form(client):
    """POST to /consents/new with valid data redirects to consent list."""
    resp = client.post(
        "/consents/new",
        data={
            "user_identifier": "bob@example.com",
            "purpose": "marketing",
            "scope": "email_contact",
            "status": "granted",
            "consent_date": "2026-01-01T10:00",
            "expiration_date": "",
            "notes": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"bob@example.com" in resp.data


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_missing_user_identifier_rejected(client):
    """Form submission without a user identifier shows an error."""
    resp = client.post(
        "/consents/new",
        data={
            "user_identifier": "",
            "purpose": "analytics",
            "scope": "read_activity",
            "status": "granted",
            "consent_date": "2026-01-01T10:00",
        },
    )
    assert resp.status_code == 200
    assert b"User identifier is required" in resp.data


def test_invalid_purpose_rejected(client):
    """Form submission with an unknown purpose is rejected."""
    resp = client.post(
        "/consents/new",
        data={
            "user_identifier": "carol@example.com",
            "purpose": "not_a_real_purpose",
            "scope": "read_activity",
            "status": "granted",
            "consent_date": "2026-01-01T10:00",
        },
    )
    assert resp.status_code == 200
    assert b"valid" in resp.data.lower()


def test_invalid_scope_rejected(client):
    """Form submission with an unknown scope is rejected."""
    resp = client.post(
        "/consents/new",
        data={
            "user_identifier": "dave@example.com",
            "purpose": "analytics",
            "scope": "bad_scope",
            "status": "granted",
            "consent_date": "2026-01-01T10:00",
        },
    )
    assert resp.status_code == 200
    assert b"valid" in resp.data.lower()


def test_expiry_before_consent_date_rejected(client):
    """Expiration before consent date must be rejected."""
    resp = client.post(
        "/consents/new",
        data={
            "user_identifier": "eve@example.com",
            "purpose": "analytics",
            "scope": "read_activity",
            "status": "granted",
            "consent_date": "2026-06-01T10:00",
            "expiration_date": "2025-01-01T10:00",
        },
    )
    assert resp.status_code == 200
    assert b"after" in resp.data.lower()


# ---------------------------------------------------------------------------
# Listing and filtering
# ---------------------------------------------------------------------------

def test_consent_list_page(client):
    """Consent list page renders created record."""
    services.create_consent(
        user_identifier="list_user@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    resp = client.get("/consents")
    assert resp.status_code == 200
    assert b"list_user@test.com" in resp.data


def test_filter_by_status(client):
    """Status filter shows only matching records."""
    services.create_consent(
        user_identifier="granted_user@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    services.create_consent(
        user_identifier="denied_user@test.com",
        purpose="analytics",
        scope="read_activity",
        status="denied",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    resp = client.get("/consents?status=denied")
    assert b"denied_user@test.com" in resp.data
    assert b"granted_user@test.com" not in resp.data


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_update_consent(client):
    """Updating a consent record persists changed fields."""
    record = services.create_consent(
        user_identifier="update_me@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes="original",
    )
    rid = record.id

    resp = client.post(
        f"/consents/{rid}/edit",
        data={
            "user_identifier": "update_me@test.com",
            "purpose": "marketing",
            "scope": "email_contact",
            "status": "granted",
            "consent_date": "2026-01-01T10:00",
            "expiration_date": "",
            "notes": "updated note",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    updated = services.get_consent(rid)
    assert updated.purpose == "marketing"
    assert updated.notes == "updated note"


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------

def test_expired_consent_effective_status():
    """A granted consent with a past expiration date reports effective_status='expired'."""
    past = datetime.now(timezone.utc) - timedelta(days=1)
    record = services.create_consent(
        user_identifier="expired_user@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc) - timedelta(days=10),
        expiration_date=past,
        notes=None,
    )
    assert record.effective_status == "expired"


def test_non_expired_consent_is_active():
    """A granted consent with a future expiration date remains active."""
    future = datetime.now(timezone.utc) + timedelta(days=30)
    record = services.create_consent(
        user_identifier="future_user@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=future,
        notes=None,
    )
    assert record.effective_status == "granted"


def test_no_expiry_stays_granted():
    """A granted consent without an expiration date stays granted."""
    record = services.create_consent(
        user_identifier="noexp_user@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    assert record.effective_status == "granted"


def test_filter_by_status_active_excludes_expired_consents(client):
    """Active/granted status filter must not show expired consents."""
    past = datetime.now(timezone.utc) - timedelta(days=2)
    services.create_consent(
        user_identifier="filter_active_valid@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc) - timedelta(days=10),
        expiration_date=None,
        notes=None,
    )
    services.create_consent(
        user_identifier="filter_active_expired@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc) - timedelta(days=10),
        expiration_date=past,
        notes=None,
    )
    resp = client.get("/consents?status=granted")
    assert resp.status_code == 200
    assert b"filter_active_valid@test.com" in resp.data
    assert b"filter_active_expired@test.com" not in resp.data


def test_filter_by_status_expired_includes_explicit_and_computed(client):
    """Expired filter returns both explicitly marked expired and dynamically expired consents."""
    past = datetime.now(timezone.utc) - timedelta(days=2)
    services.create_consent(
        user_identifier="computed_expired@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc) - timedelta(days=10),
        expiration_date=past,
        notes=None,
    )
    services.create_consent(
        user_identifier="explicit_expired@test.com",
        purpose="analytics",
        scope="read_activity",
        status="expired",
        consent_date=datetime.now(timezone.utc) - timedelta(days=10),
        expiration_date=None,
        notes=None,
    )
    resp = client.get("/consents?status=expired")
    assert resp.status_code == 200
    assert b"computed_expired@test.com" in resp.data
    assert b"explicit_expired@test.com" in resp.data


def test_update_consent_persists_user_identifier(client):
    """Editing consent with a corrected user identifier updates the record."""
    record = services.create_consent(
        user_identifier="typo_user@test.com",
        purpose="marketing",
        scope="email_contact",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    resp = client.post(
        f"/consents/{record.id}/edit",
        data={
            "user_identifier": "fixed_user@test.com",
            "purpose": "marketing",
            "scope": "email_contact",
            "status": "granted",
            "consent_date": "2026-01-01T10:00",
            "expiration_date": "",
            "notes": "corrected typo",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    updated = services.get_consent(record.id)
    assert updated.user_identifier == "fixed_user@test.com"
    assert updated.notes == "corrected typo"


def test_update_consent_status_to_revoked_sets_revocation_date(client):
    """Editing status to revoked in form automatically sets revocation_date."""
    record = services.create_consent(
        user_identifier="edit_to_revoke@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    assert record.revocation_date is None
    resp = client.post(
        f"/consents/{record.id}/edit",
        data={
            "user_identifier": "edit_to_revoke@test.com",
            "purpose": "analytics",
            "scope": "read_activity",
            "status": "revoked",
            "consent_date": "2026-01-01T10:00",
            "expiration_date": "",
            "notes": "manually marked revoked in edit",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    updated = services.get_consent(record.id)
    assert updated.status == "revoked"
    assert updated.revocation_date is not None

