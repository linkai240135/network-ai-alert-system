import os

from flask import Flask

from .database import db
from .routes import api, web


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///network_ai_alert.db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_AS_ASCII"] = False

    db.init_app(app)

    with app.app_context():
        from .seed import bootstrap_database

        db.create_all()
        bootstrap_database()

    app.register_blueprint(web)
    app.register_blueprint(api, url_prefix="/api")
    return app
