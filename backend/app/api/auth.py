from flask import request, session

from . import api_bp
from ..services.auth_service import authenticate, get_user
from ..utils.response import failure, success


@api_bp.post("/auth/login")
def login():
    payload = request.get_json(force=True)
    user = authenticate(payload.get("username", ""), payload.get("password", ""))
    if not user:
        return failure("用户名或密码错误", 401)
    session["user_id"] = user.id
    return success({"user": user.to_dict()}, message="登录成功")


@api_bp.post("/auth/logout")
def logout():
    session.clear()
    return success(message="已退出登录")


@api_bp.get("/auth/me")
def current_user():
    user = get_user(session.get("user_id"))
    if not user:
        return failure("未登录", 401)
    return success({"user": user.to_dict()})


@api_bp.get("/auth/permissions")
def permissions():
    user = get_user(session.get("user_id"))
    if not user:
        return failure("未登录", 401)
    role_matrix = [
        {"module": "系统总览", "super_admin": "查看/导出", "admin": "查看", "analyst": "查看"},
        {"module": "数据集管理", "super_admin": "导入/训练/导出", "admin": "导入/查看", "analyst": "查看"},
        {"module": "模型训练中心", "super_admin": "训练/查看/导出", "admin": "训练/查看", "analyst": "查看"},
        {"module": "在线检测", "super_admin": "检测/批量/导出", "admin": "检测/批量", "analyst": "检测"},
        {"module": "告警与日志", "super_admin": "查看/筛选/批量处置/导出", "admin": "查看/筛选/导出", "analyst": "查看/筛选"},
        {"module": "系统设置", "super_admin": "查看/修改", "admin": "查看", "analyst": "无"},
    ]
    return success(
        {
            "currentRole": user.role,
            "roles": [
                {"code": "super_admin", "name": "超级管理员"},
                {"code": "admin", "name": "系统管理员"},
                {"code": "analyst", "name": "安全分析员"},
            ],
            "matrix": role_matrix,
        }
    )
