"""
Database models for the Digital Consent and Data Permission Management Platform.
Uses raw sqlite3 (Python stdlib) – no external ORM required.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Sentinel for "naive UTC datetime from DB"
# ---------------------------------------------------------------------------

def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Attach UTC timezone to a naive datetime loaded from SQLite."""
    if dt is None:
        return None
    if isinstance(dt, str):
        # sqlite3 returns strings when detect_types is not set perfectly
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Data classes (plain Python, not ORM)
# ---------------------------------------------------------------------------

@dataclass
class ConsentRecord:
    id: Optional[int]
    user_identifier: str
    purpose: str
    scope: str
    status: str
    consent_date: Optional[datetime]
    expiration_date: Optional[datetime]
    revocation_date: Optional[datetime]
    notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    VALID_STATUSES = {"granted", "denied", "revoked", "expired"}
    VALID_PURPOSES = {
        "account_management",
        "analytics",
        "marketing",
        "service_personalization",
        "third_party_sharing",
        "research",
    }
    VALID_SCOPES = {
        "read_profile",
        "read_activity",
        "write_profile",
        "email_contact",
        "sms_contact",
        "location_data",
        "behavioral_data",
        "demographic_data",
    }

    @property
    def is_expired(self) -> bool:
        if self.expiration_date is None:
            return False
        now = datetime.now(timezone.utc)
        exp = _aware(self.expiration_date)
        return exp is not None and exp < now

    @property
    def effective_status(self) -> str:
        if self.status == "granted" and self.is_expired:
            return "expired"
        return self.status

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_identifier": self.user_identifier,
            "purpose": self.purpose,
            "scope": self.scope,
            "status": self.effective_status,
            "consent_date": self.consent_date.isoformat() if self.consent_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "revocation_date": self.revocation_date.isoformat() if self.revocation_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class AuditLog:
    id: Optional[int]
    consent_id: Optional[int]
    event_type: str
    description: str
    timestamp: Optional[datetime]

    VALID_EVENTS = {
        "consent_created",
        "consent_updated",
        "consent_revoked",
        "consent_expired",
        "report_generated",
        "consent_denied",
    }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "consent_id": self.consent_id,
            "event_type": self.event_type,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
