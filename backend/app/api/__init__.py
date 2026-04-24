from flask import Blueprint, request, session

from ..utils.response import failure

api_bp = Blueprint("api_v1", __name__)


@api_bp.before_request
def ensure_authenticated():
    if session.get("user_id"):
        return None
    if request.path.endswith("/auth/login"):
        return None
    return failure("未登录或登录状态已过期", 401)


from . import ai, assets, auth, dashboard, datasets, detection, incidents, settings, system, training  # noqa: E402,F401
