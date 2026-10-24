"""
Tests for compliance report generation and CSV export.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app import services


def _seed(n_granted=3, n_revoked=2, n_denied=1, n_expired=1):
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=5)
    records = []

    for i in range(n_granted):
        records.append(services.create_consent(
            user_identifier=f"granted_{i}@test.com",
            purpose="analytics",
            scope="read_activity",
            status="granted",
            consent_date=now,
            expiration_date=None,
            notes=None,
        ))
    for i in range(n_revoked):
        r = services.create_consent(
            user_identifier=f"revoked_{i}@test.com",
            purpose="marketing",
            scope="email_contact",
            status="granted",
            consent_date=now,
            expiration_date=None,
            notes=None,
        )
        services.revoke_consent(r.id)
        records.append(r)
    for i in range(n_denied):
        records.append(services.create_consent(
            user_identifier=f"denied_{i}@test.com",
            purpose="analytics",
            scope="read_activity",
            status="denied",
            consent_date=now,
            expiration_date=None,
            notes=None,
        ))
    for i in range(n_expired):
        records.append(services.create_consent(
            user_identifier=f"expired_{i}@test.com",
            purpose="analytics",
            scope="read_activity",
            status="granted",
            consent_date=now - timedelta(days=10),
            expiration_date=past,
            notes=None,
        ))
    return records


def test_report_page_loads(client):
    resp = client.get("/reports")
    assert resp.status_code == 200


def test_report_counts_total():
    _seed(n_granted=2, n_revoked=1, n_denied=0, n_expired=0)
    report = services.generate_report()
    assert report["stats"]["total"] == 3


def test_report_counts_active():
    _seed(n_granted=4, n_revoked=0, n_denied=0, n_expired=0)
    report = services.generate_report()
    assert report["stats"]["active"] == 4


def test_report_counts_revoked():
    _seed(n_granted=0, n_revoked=3, n_denied=0, n_expired=0)
    report = services.generate_report()
    assert report["stats"]["revoked"] == 3


def test_report_counts_expired():
    _seed(n_granted=0, n_revoked=0, n_denied=0, n_expired=2)
    report = services.generate_report()
    assert report["stats"]["expired"] == 2


def test_report_counts_denied():
    _seed(n_granted=0, n_revoked=0, n_denied=3, n_expired=0)
    report = services.generate_report()
    assert report["stats"]["denied"] == 3


def test_report_by_purpose():
    _seed(n_granted=3, n_revoked=0, n_denied=0, n_expired=0)
    report = services.generate_report()
    assert "analytics" in report["by_purpose"]
    assert report["by_purpose"]["analytics"] >= 3


def test_report_expiring_soon():
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=15)
    services.create_consent(
        user_identifier="soon@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=now,
        expiration_date=soon,
        notes=None,
    )
    report = services.generate_report()
    assert len(report["expiring_soon"]) >= 1


def test_report_date_range_filter():
    t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2025, 6, 1, tzinfo=timezone.utc)
    t3 = datetime(2025, 12, 1, tzinfo=timezone.utc)

    services.create_consent(
        user_identifier="jan@test.com", purpose="analytics", scope="read_activity",
        status="granted", consent_date=t1, expiration_date=None, notes=None,
    )
    services.create_consent(
        user_identifier="jun@test.com", purpose="analytics", scope="read_activity",
        status="granted", consent_date=t2, expiration_date=None, notes=None,
    )
    services.create_consent(
        user_identifier="dec@test.com", purpose="analytics", scope="read_activity",
        status="granted", consent_date=t3, expiration_date=None, notes=None,
    )
    report = services.generate_report(
        start_date=datetime(2025, 4, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 8, 1, tzinfo=timezone.utc),
    )
    users = [r.user_identifier for r in report["records"]]
    assert "jun@test.com" in users
    assert "jan@test.com" not in users
    assert "dec@test.com" not in users


def test_csv_export_returns_200(client):
    resp = client.get("/reports/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type


def test_csv_export_has_header(client):
    resp = client.get("/reports/export")
    text = resp.data.decode("utf-8")
    assert "User Identifier" in text
    assert "Purpose" in text
    assert "Status" in text


def test_csv_export_contains_records(client):
    services.create_consent(
        user_identifier="csv_user@test.com",
        purpose="analytics",
        scope="read_activity",
        status="granted",
        consent_date=datetime.now(timezone.utc),
        expiration_date=None,
        notes=None,
    )
    resp = client.get("/reports/export")
    text = resp.data.decode("utf-8")
    assert "csv_user@test.com" in text
