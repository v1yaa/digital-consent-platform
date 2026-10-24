"""
Shared pytest fixtures for the Digital Consent Platform test suite.
Uses an isolated temporary SQLite database so tests never touch
the development or production database.
"""

import os
import tempfile
import pytest

from app import create_app
from app import database as db_module


@pytest.fixture(scope="session")
def app():
    """Create the Flask application configured for testing with a temp DB."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
        }
    )
    # Point the database layer at the temp file for the test session
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    db_module.init_db()

    yield application

    # Cleanup
    os.environ.pop("DATABASE_URL", None)
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Delete all rows between tests for isolation."""
    yield
    import sqlite3
    db_path = db_module._db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM audit_logs")
    conn.execute("DELETE FROM consent_records")
    conn.commit()
    conn.close()
