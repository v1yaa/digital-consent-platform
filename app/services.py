"""
Business-logic service layer for the Consent Management Platform.
Thin wrapper around app.database so routes stay clean.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .database import (
    insert_consent,
    update_consent_db,
    revoke_consent_db,
    get_consent_db,
    list_consents_db,
    get_stats_db,
    get_audit_logs_db,
    generate_report_db,
    export_csv_db,
)
from .models import ConsentRecord, AuditLog


def create_consent(
    user_identifier: str,
    purpose: str,
    scope: str,
    status: str,
    consent_date: Optional[datetime],
    expiration_date: Optional[datetime],
    notes: Optional[str],
) -> ConsentRecord:
    return insert_consent(user_identifier, purpose, scope, status, consent_date, expiration_date, notes)


def update_consent(
    record_id: int,
    purpose: str,
    scope: str,
    status: str,
    consent_date: Optional[datetime],
    expiration_date: Optional[datetime],
    notes: Optional[str],
    user_identifier: Optional[str] = None,
) -> ConsentRecord:
    return update_consent_db(record_id, purpose, scope, status, consent_date, expiration_date, notes, user_identifier)


def revoke_consent(record_id: int) -> ConsentRecord:
    return revoke_consent_db(record_id)


def get_consent(record_id: int) -> Optional[ConsentRecord]:
    return get_consent_db(record_id)


def list_consents(
    status_filter: Optional[str] = None,
    purpose_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
) -> list[ConsentRecord]:
    return list_consents_db(status_filter, purpose_filter, user_filter)


def get_dashboard_stats() -> dict:
    return get_stats_db()


def get_audit_logs(limit: int = 500) -> list[AuditLog]:
    return get_audit_logs_db(limit)


def generate_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    return generate_report_db(start_date, end_date)


def export_csv(records: list[ConsentRecord]) -> str:
    return export_csv_db(records)
