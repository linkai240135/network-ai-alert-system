from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User


def ensure_default_admin() -> None:
    if User.query.filter_by(username="admin").first():
        return
    admin = User(username="admin", password_hash=generate_password_hash("admin123"), role="super-admin")
    db.session.add(admin)
    db.session.commit()


def authenticate(username: str, password: str) -> User | None:
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return None
    user.last_login_at = datetime.utcnow()
    try:
        db.session.commit()
    except SQLAlchemyError:
        # Login should not fail just because audit timestamp persistence is delayed.
        db.session.rollback()
    return user


def get_user(user_id: int | None) -> User | None:
    if not user_id:
        return None
    return User.query.get(user_id)
