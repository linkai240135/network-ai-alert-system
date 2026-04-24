from __future__ import annotations

import os

from flask import Flask, jsonify

from .api import api_bp
from .config import DevelopmentConfig
from .extensions import db
from .services.auth_service import ensure_default_admin
from .services.dataset_service import bootstrap_dataset
from .services.settings_service import ensure_default_settings
from .services.training_service import ensure_training_run


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)
    app.secret_key = "network-ai-alert-secret"
    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_default_admin()
        ensure_default_settings()
        if os.getenv("SKIP_AUTO_BOOTSTRAP", "0") != "1":
            bootstrap_dataset()
            ensure_training_run()

    app.register_blueprint(api_bp, url_prefix=app.config["API_PREFIX"])

    @app.get("/")
    def health():
        return jsonify(
            {
                "name": "Network AI Alert System Backend",
                "status": "running",
                "apiPrefix": app.config["API_PREFIX"],
            }
        )

    return app
