from flask import request

from . import api_bp
from ..services.llm_service import analyze_alert, analyze_incident, chat_with_assistant, generate_incident_report
from ..utils.response import failure, success


@api_bp.post("/ai/analyze-alert")
def ai_analyze_alert():
    payload = request.get_json(force=True)
    alert = payload.get("alert")
    if not isinstance(alert, dict):
        return failure("缺少告警数据")
    return success(analyze_alert(alert, preferred_model=payload.get("model")), message="智能告警研判已生成")


@api_bp.post("/ai/analyze-incident")
def ai_analyze_incident():
    payload = request.get_json(force=True)
    incident = payload.get("incident")
    if not isinstance(incident, dict):
        return failure("缺少事件数据")
    return success(analyze_incident(incident, preferred_model=payload.get("model")), message="智能事件研判已生成")


@api_bp.post("/ai/chat")
def ai_chat():
    payload = request.get_json(force=True)
    question = str(payload.get("question", "")).strip()
    if not question:
        return failure("请输入问题")
    return success(chat_with_assistant(question, payload.get("context") or {}, preferred_model=payload.get("model")), message="智能助手已回复")


@api_bp.post("/ai/generate-report")
def ai_generate_report():
    payload = request.get_json(force=True)
    incident = payload.get("incident")
    if not isinstance(incident, dict):
        return failure("缺少事件数据")
    return success(generate_incident_report(incident, preferred_model=payload.get("model")), message="智能事件报告已生成")
