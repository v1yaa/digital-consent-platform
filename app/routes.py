"""
Flask routes for the Digital Consent and Data Permission Management Platform.
CSRF protection implemented using Flask's built-in session-based token
(itsdangerous is installed as a Flask dependency).
"""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .models import ConsentRecord
from . import services

bp = Blueprint("main", __name__)

# ---------------------------------------------------------------------------
# Label maps (used in templates)
# ---------------------------------------------------------------------------

PURPOSE_LABELS = {
    "account_management": "Account Management",
    "analytics": "Analytics",
    "marketing": "Marketing",
    "service_personalization": "Service Personalization",
    "third_party_sharing": "Third-Party Sharing",
    "research": "Research",
}

SCOPE_LABELS = {
    "read_profile": "Read Profile",
    "read_activity": "Read Activity",
    "write_profile": "Write Profile",
    "email_contact": "Email Contact",
    "sms_contact": "SMS Contact",
    "location_data": "Location Data",
    "behavioral_data": "Behavioral Data",
    "demographic_data": "Demographic Data",
}

# ---------------------------------------------------------------------------
# Lightweight CSRF helpers (no Flask-WTF required)
# ---------------------------------------------------------------------------

def _get_csrf_token() -> str:
    """Generate (or retrieve) a per-session CSRF token."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def _validate_csrf():
    """Abort 400 if the submitted CSRF token does not match the session token.
    Skipped when the app is in TESTING mode."""
    from flask import current_app
    if current_app.config.get("TESTING") or not current_app.config.get("WTF_CSRF_ENABLED", True):
        return
    token = request.form.get("csrf_token", "")
    if not token or token != session.get("_csrf_token"):
        abort(400, "CSRF token missing or invalid.")


# Make token available to all templates
@bp.context_processor
def inject_csrf():
    return {"csrf_token": _get_csrf_token}


# ---------------------------------------------------------------------------
# Date parsing helper
# ---------------------------------------------------------------------------

def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Form validation
# ---------------------------------------------------------------------------

def _validate_consent_form(form) -> list[str]:
    errors = []
    uid = form.get("user_identifier", "").strip()
    if not uid:
        errors.append("User identifier is required.")
    elif len(uid) > 255:
        errors.append("User identifier must be 255 characters or fewer.")

    purpose = form.get("purpose", "")
    if purpose not in ConsentRecord.VALID_PURPOSES:
        errors.append("Please select a valid data-processing purpose.")

    scope = form.get("scope", "")
    if scope not in ConsentRecord.VALID_SCOPES:
        errors.append("Please select a valid permission scope.")

    status = form.get("status", "")
    if status not in ConsentRecord.VALID_STATUSES:
        errors.append("Please select a valid consent status.")

    consent_date_raw = form.get("consent_date", "")
    consent_date = _parse_dt(consent_date_raw)
    if not consent_date:
        errors.append("Consent date is required and must be a valid date/time.")

    expiration_raw = form.get("expiration_date", "").strip()
    if expiration_raw:
        exp_dt = _parse_dt(expiration_raw)
        if exp_dt is None:
            errors.append("Expiration date must be a valid date/time if provided.")
        elif consent_date and exp_dt <= consent_date:
            errors.append("Expiration date must be after the consent date.")

    return errors


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@bp.route("/")
def index():
    stats = services.get_dashboard_stats()
    return render_template(
        "index.html",
        stats=stats,
        purpose_labels=PURPOSE_LABELS,
        scope_labels=SCOPE_LABELS,
    )


# ---------------------------------------------------------------------------
# Consent list
# ---------------------------------------------------------------------------

@bp.route("/consents")
def consents():
    status_filter = request.args.get("status", "all")
    purpose_filter = request.args.get("purpose", "all")
    user_filter = request.args.get("user", "").strip()
    records = services.list_consents(status_filter, purpose_filter, user_filter)
    return render_template(
        "consents.html",
        records=records,
        status_filter=status_filter,
        purpose_filter=purpose_filter,
        user_filter=user_filter,
        purpose_labels=PURPOSE_LABELS,
        scope_labels=SCOPE_LABELS,
        valid_purposes=sorted(ConsentRecord.VALID_PURPOSES),
    )


# ---------------------------------------------------------------------------
# Create consent
# ---------------------------------------------------------------------------

@bp.route("/consents/new", methods=["GET", "POST"])
def consent_new():
    if request.method == "POST":
        _validate_csrf()
        errors = _validate_consent_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "consent_form.html",
                action="Create",
                form=request.form,
                record=None,
                purpose_labels=PURPOSE_LABELS,
                scope_labels=SCOPE_LABELS,
            ), 200

        record = services.create_consent(
            user_identifier=request.form["user_identifier"],
            purpose=request.form["purpose"],
            scope=request.form["scope"],
            status=request.form["status"],
            consent_date=_parse_dt(request.form.get("consent_date", "")),
            expiration_date=_parse_dt(request.form.get("expiration_date", "")),
            notes=request.form.get("notes", ""),
        )
        flash(f"Consent record #{record.id} created successfully.", "success")
        return redirect(url_for("main.consents"))

    return render_template(
        "consent_form.html",
        action="Create",
        form={},
        record=None,
        purpose_labels=PURPOSE_LABELS,
        scope_labels=SCOPE_LABELS,
    )


# ---------------------------------------------------------------------------
# Edit consent
# ---------------------------------------------------------------------------

@bp.route("/consents/<int:record_id>/edit", methods=["GET", "POST"])
def consent_edit(record_id: int):
    record = services.get_consent(record_id)
    if record is None:
        abort(404)

    if request.method == "POST":
        _validate_csrf()
        errors = _validate_consent_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "consent_form.html",
                action="Update",
                form=request.form,
                record=record,
                purpose_labels=PURPOSE_LABELS,
                scope_labels=SCOPE_LABELS,
            ), 200

        record = services.update_consent(
            record_id=record_id,
            purpose=request.form["purpose"],
            scope=request.form["scope"],
            status=request.form["status"],
            consent_date=_parse_dt(request.form.get("consent_date", "")),
            expiration_date=_parse_dt(request.form.get("expiration_date", "")),
            notes=request.form.get("notes", ""),
        )
        flash(f"Consent record #{record_id} updated successfully.", "success")
        return redirect(url_for("main.consents"))

    return render_template(
        "consent_form.html",
        action="Update",
        form={},
        record=record,
        purpose_labels=PURPOSE_LABELS,
        scope_labels=SCOPE_LABELS,
    )


# ---------------------------------------------------------------------------
# Revoke consent
# ---------------------------------------------------------------------------

@bp.route("/consents/<int:record_id>/revoke", methods=["POST"])
def consent_revoke(record_id: int):
    _validate_csrf()
    record = services.get_consent(record_id)
    if record is None:
        abort(404)

    if record.effective_status not in ("granted", "denied"):
        flash(
            f"Consent #{record_id} cannot be revoked (current status: {record.effective_status}).",
            "warning",
        )
        return redirect(url_for("main.consents"))

    services.revoke_consent(record_id)
    flash(f"Consent record #{record_id} has been revoked successfully.", "success")
    return redirect(url_for("main.consents"))


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

@bp.route("/audit")
def audit_logs():
    logs = services.get_audit_logs(limit=500)
    return render_template("audit_logs.html", logs=logs)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@bp.route("/reports")
def reports():
    start_raw = request.args.get("start_date", "")
    end_raw = request.args.get("end_date", "")
    start_date = _parse_dt(start_raw) if start_raw else None
    end_date = _parse_dt(end_raw) if end_raw else None
    report = services.generate_report(start_date=start_date, end_date=end_date)
    return render_template(
        "reports.html",
        report=report,
        start_date=start_raw,
        end_date=end_raw,
        purpose_labels=PURPOSE_LABELS,
    )


@bp.route("/reports/export")
def reports_export():
    start_raw = request.args.get("start_date", "")
    end_raw = request.args.get("end_date", "")
    start_date = _parse_dt(start_raw) if start_raw else None
    end_date = _parse_dt(end_raw) if end_raw else None
    report = services.generate_report(start_date=start_date, end_date=end_date)
    csv_data = services.export_csv(report["records"])
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=consent_report.csv"},
    )


# ---------------------------------------------------------------------------
# Health check (Docker / CI)
# ---------------------------------------------------------------------------

@bp.route("/health")
def health():
    return {"status": "ok"}, 200


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@bp.app_errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404


@bp.app_errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, message=str(e.description)), 400


@bp.app_errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="An internal error occurred."), 500
