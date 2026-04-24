from flask import request

from . import api_bp
from ..services.settings_service import get_settings, update_settings
from ..utils.response import success


@api_bp.get("/settings")
def settings_list():
    return success({"items": get_settings()})


@api_bp.put("/settings")
def settings_update():
    payload = request.get_json(force=True)
    return success({"items": update_settings(payload)}, message="系统设置已更新")
