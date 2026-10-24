"""
Application factory for the Digital Consent and Data Permission Management Platform.
Uses only packages available in the existing environment:
  - Flask (already installed)
  - itsdangerous (installed as Flask dependency)
  - Python stdlib sqlite3
"""

import os
import secrets

from flask import Flask

from .database import init_db


def create_app(config: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    app.config.update(
        SECRET_KEY=secret_key,
        TESTING=False,
        WTF_CSRF_ENABLED=True,
    )

    if config:
        app.config.update(config)

    # ------------------------------------------------------------------ #
    # Database initialisation (idempotent – safe to call on every start)  #
    # ------------------------------------------------------------------ #
    init_db()

    # ------------------------------------------------------------------ #
    # Blueprints                                                          #
    # ------------------------------------------------------------------ #
    from .routes import bp
    app.register_blueprint(bp)

    return app
