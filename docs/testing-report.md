# Testing Report

## Test Suite Summary

**Executed:** 2026-10-24  
**Python:** 3.12.4  
**pytest:** 9.1.1  
**Platform:** Windows 11  
**Total tests:** 41  
**Passed:** 41  
**Failed:** 0  
**Duration:** ~1.6 seconds  

## Test Modules

| Module | Tests | Coverage area |
|---|---|---|
| `test_consents.py` | 15 | App startup, dashboard, CRUD, form validation, filtering, expiration |
| `test_revocation.py` | 6 | Status change, timestamp, audit event, active exclusion, HTTP route, duplicate |
| `test_audit.py` | 8 | Page load, event types, timestamps, consent references, report events |
| `test_reports.py` | 12 | Page load, totals, per-status counts, purpose grouping, expiring-soon, date range, CSV |

## Test Isolation Strategy

- Each test session uses a **temporary SQLite file** created with `tempfile.mkstemp()`.
- The `DATABASE_URL` environment variable is pointed at this file for the entire session.
- An `autouse` fixture deletes all rows from `consent_records` and `audit_logs` between every individual test.
- CSRF validation is disabled (`WTF_CSRF_ENABLED=False`) for the test client.

## Full Test Output

```
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-9.1.1, pluggy-1.6.0
collected 41 items

tests/test_audit.py::test_audit_log_page_loads PASSED
tests/test_audit.py::test_consent_created_event PASSED
tests/test_audit.py::test_consent_denied_event PASSED
tests/test_audit.py::test_consent_updated_event PASSED
tests/test_audit.py::test_consent_revoked_event PASSED
tests/test_audit.py::test_audit_log_has_timestamp PASSED
tests/test_audit.py::test_audit_log_references_consent PASSED
tests/test_audit.py::test_report_generated_event_has_no_consent_id PASSED
tests/test_consents.py::test_app_starts PASSED
tests/test_consents.py::test_dashboard_loads PASSED
tests/test_consents.py::test_health_endpoint PASSED
tests/test_consents.py::test_create_consent_via_service PASSED
tests/test_consents.py::test_create_consent_via_form PASSED
tests/test_consents.py::test_missing_user_identifier_rejected PASSED
tests/test_consents.py::test_invalid_purpose_rejected PASSED
tests/test_consents.py::test_invalid_scope_rejected PASSED
tests/test_consents.py::test_expiry_before_consent_date_rejected PASSED
tests/test_consents.py::test_consent_list_page PASSED
tests/test_consents.py::test_filter_by_status PASSED
tests/test_consents.py::test_update_consent PASSED
tests/test_consents.py::test_expired_consent_effective_status PASSED
tests/test_consents.py::test_non_expired_consent_is_active PASSED
tests/test_consents.py::test_no_expiry_stays_granted PASSED
tests/test_reports.py::test_report_page_loads PASSED
tests/test_reports.py::test_report_counts_total PASSED
tests/test_reports.py::test_report_counts_active PASSED
tests/test_reports.py::test_report_counts_revoked PASSED
tests/test_reports.py::test_report_counts_expired PASSED
tests/test_reports.py::test_report_counts_denied PASSED
tests/test_reports.py::test_report_by_purpose PASSED
tests/test_reports.py::test_report_expiring_soon PASSED
tests/test_reports.py::test_report_date_range_filter PASSED
tests/test_reports.py::test_csv_export_returns_200 PASSED
tests/test_reports.py::test_csv_export_has_header PASSED
tests/test_reports.py::test_csv_export_contains_records PASSED
tests/test_revocation.py::test_revoke_changes_status PASSED
tests/test_revocation.py::test_revoke_sets_revocation_timestamp PASSED
tests/test_revocation.py::test_revoke_writes_audit_event PASSED
tests/test_revocation.py::test_revoke_record_not_reported_as_active PASSED
tests/test_revocation.py::test_revoke_via_post PASSED
tests/test_revocation.py::test_revoke_already_revoked_shows_warning PASSED

============================== 41 passed in 1.59s =============================
```

## GitHub Actions CI

The workflow at `.github/workflows/tests.yml` runs this suite automatically on every push and pull request. It:

1. Checks out the repository
2. Sets up Python 3.12 with pip cache
3. Installs dependencies from `requirements.txt`
4. Runs `pytest tests/ -v --tb=short` with an in-memory database
5. Uploads any XML test result artifacts
