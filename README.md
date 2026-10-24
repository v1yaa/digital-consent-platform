# ConsentVault — Digital Consent and Data Permission Management Platform

> **Academic demonstration project.** This application illustrates consent-record management concepts and is not a production legal-compliance tool.

## Overview

ConsentVault is a full-stack web application that enables organizations to record, manage, monitor, and audit user consent for data-processing activities. It provides a dashboard, consent lifecycle management, revocation, an immutable audit trail, and compliance reporting — all running locally without external services.

## Features

| Category | Details |
|---|---|
| **Dashboard** | Live stat cards, donut + bar charts, recent audit events, quick-action links |
| **Consent Management** | Create, view, edit consent records with purpose, scope, and expiry |
| **Permission Scopes** | Eight distinct scope categories per consent record |
| **Expiration Handling** | Automatic effective-status calculation based on UTC timestamps |
| **Revocation** | One-click revocation with audit trail and timestamp recording |
| **Audit Trail** | Chronological log of all consent lifecycle events |
| **Compliance Reports** | Aggregate stats, purpose breakdown, expiring-soon list, date-range filter |
| **CSV Export** | Download full report data as a CSV file |
| **CSRF Protection** | Session-based token validation on all state-changing forms |
| **Docker Support** | Production Gunicorn container with named SQLite volume |
| **Automated Tests** | 41 pytest tests across four test modules |

## Technology Stack

- **Backend:** Python 3.12, Flask 3.1
- **Database:** SQLite (via Python `sqlite3` stdlib)
- **Frontend:** HTML5, CSS3, Bootstrap 5.3, Chart.js 4.4
- **WSGI Server:** Gunicorn 26
- **Testing:** Pytest 9.1
- **Container:** Docker, Docker Compose v2
- **CI:** GitHub Actions
- **Fonts:** Google Fonts – Inter

## Repository Structure

```
digital-consent-platform/
├── app/
│   ├── __init__.py          # Application factory
│   ├── routes.py            # Flask Blueprint (all URL handlers)
│   ├── models.py            # Python dataclasses (ConsentRecord, AuditLog)
│   ├── database.py          # SQLite3 CRUD layer
│   ├── services.py          # Business-logic facade
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html       # Dashboard
│   │   ├── consents.html    # Consent list with filters
│   │   ├── consent_form.html
│   │   ├── audit_logs.html
│   │   ├── reports.html
│   │   └── error.html
│   └── static/
│       ├── css/style.css    # Custom design system
│       └── js/app.js        # Chart.js init, sidebar, flash auto-dismiss
├── tests/
│   ├── conftest.py          # Fixtures (temp-file SQLite, test client)
│   ├── test_consents.py     # 15 tests
│   ├── test_revocation.py   # 6 tests
│   ├── test_audit.py        # 8 tests
│   └── test_reports.py      # 12 tests
├── docs/
│   ├── architecture.md
│   ├── git-workflow.md
│   ├── docker-design.md
│   ├── testing-report.md
│   └── screenshots/
├── .github/
│   └── workflows/tests.yml  # GitHub Actions CI
├── .gitignore
├── .dockerignore
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── wsgi.py
├── README.md
└── REPORT.md
```

## Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.12 |
| Git | 2.x |
| Docker Desktop | 4.x (for containerized run) |
| PowerShell | 5.1 (Windows) |

## Local Installation (Without Docker)

```powershell
# Clone / enter the project
cd "c:\Permission Management Platform\digital-consent-platform"

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install Flask Werkzeug gunicorn pytest

# Copy env template
Copy-Item .env.example .env

# Run the development server
python wsgi.py
```

Open **http://localhost:5000** in your browser.

## Docker Installation

### Build and start

```powershell
# Build image and start container (detached)
docker compose up --build -d

# Check container status
docker compose ps

# View live logs
docker compose logs -f web
```

Application is available at **http://localhost:8080** (default `HOST_PORT`).

### Stop (preserve data)

```powershell
docker compose stop
```

### Stop and remove containers (data volume is preserved)

```powershell
docker compose down
```

### Full teardown including database volume

```powershell
docker compose down -v
```

### Restart and verify data persists

```powershell
docker compose restart
docker compose exec web python -c "from app.database import get_db; [print(r) for r in __import__('contextlib').suppress()]"
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | random token | Flask session secret — change in production |
| `DATABASE_URL` | `sqlite:///consent.db` | SQLite DB path. Docker uses `sqlite:////data/consent.db` |
| `HOST_PORT` | `8080` | Host port mapped to the container |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode (development only) |

Copy `.env.example` → `.env` and adjust values. **Never commit `.env` to Git.**

## Testing

```powershell
# Run full test suite
python -m pytest tests/ -v

# Run specific module
python -m pytest tests/test_consents.py -v

# Run with short traceback
python -m pytest tests/ --tb=short
```

**Result: 41 tests, 0 failures.**

## Git Branching Strategy

```
main          ← stable, production-ready releases
  └── develop ← integration branch
        ├── feature/consent  ← consent CRUD + UI
        ├── feature/revoke   ← revocation workflow
        └── feature/report   ← compliance reporting
release/v1.0  ← release preparation (branched from develop)
hotfix/*      ← urgent fixes off main (if needed)
```

## Database Persistence

- **Local run:** SQLite file at `consent.db` (project root) — excluded from Git via `.gitignore`
- **Docker:** Named volume `consent_data` mounted at `/data/consent.db` — survives container restarts and upgrades

## Known Limitations

1. No user authentication — labelled clearly as an academic local demo
2. Single SQLite file is not suitable for multi-process production deployments
3. The audit trail is not cryptographically tamper-proof
4. CSRF tokens use Flask's session (cookie-based); a production app should use SameSite cookies and HTTPS

## Future Enhancements

- User authentication (Flask-Login or OAuth2)
- PostgreSQL backend for concurrent multi-user deployments
- Email notifications for expiring consents
- REST API layer (OpenAPI spec)
- Role-based access control for compliance officers vs. administrators
- Scheduled job to automatically mark expired consents in the database
