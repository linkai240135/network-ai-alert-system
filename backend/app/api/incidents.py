from flask import request

from . import api_bp
from ..services.incident_service import (
    add_incident_note,
    build_incident_report,
    create_feedback,
    get_incident_board,
    get_incident_detail,
    get_source_attack_chain,
    list_feedback,
    list_incidents,
    update_incident_status,
)
from ..utils.response import failure, success


@api_bp.get("/incidents")
def incidents_list():
    limit = int(request.args.get("limit", 20))
    status = request.args.get("status")
    severity = request.args.get("severity")
    return success({"items": list_incidents(limit=limit, status=status, severity=severity)})


@api_bp.get("/incidents/board")
def incidents_board():
    return success(get_incident_board())


@api_bp.get("/incidents/<int:incident_id>")
def incident_detail(incident_id: int):
    item = get_incident_detail(incident_id)
    if not item:
        return failure("事件不存在", 404)
    return success(item)


@api_bp.put("/incidents/<int:incident_id>/status")
def incident_status_update(incident_id: int):
    payload = request.get_json(force=True)
    item = update_incident_status(
        incident_id,
        payload.get("status", "研判中"),
        operator=payload.get("operator", "analyst"),
        note=payload.get("note"),
    )
    if not item:
        return failure("事件不存在", 404)
    return success(item, message="事件状态已更新")


@api_bp.post("/incidents/<int:incident_id>/notes")
def incident_note_add(incident_id: int):
    payload = request.get_json(force=True)
    if not payload.get("content"):
        return failure("请输入处置说明")
    item = add_incident_note(
        incident_id,
        payload["content"],
        operator=payload.get("operator", "analyst"),
    )
    if not item:
        return failure("事件不存在", 404)
    return success(item, message="研判记录已追加")


@api_bp.get("/incidents/<int:incident_id>/report")
def incident_report(incident_id: int):
    item = build_incident_report(incident_id)
    if not item:
        return failure("事件不存在", 404)
    return success(item)


@api_bp.get("/incidents/source-chain")
def incident_source_chain():
    source_ip = request.args.get("source_ip", "")
    if not source_ip:
        return failure("请提供 source_ip")
    return success(get_source_attack_chain(source_ip))


@api_bp.post("/incidents/<int:incident_id>/feedback")
def incident_feedback(incident_id: int):
    payload = request.get_json(force=True)
    item = create_feedback(
        incident_id,
        payload.get("feedback_type", "误报"),
        payload.get("expected_label", "BENIGN"),
        payload.get("comment", ""),
        operator=payload.get("operator", "analyst"),
    )
    if not item:
        return failure("事件不存在", 404)
    return success(item, message="反馈已提交")


@api_bp.get("/training/feedback")
def training_feedback_list():
    return success({"items": list_feedback()})
