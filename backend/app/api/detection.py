from io import BytesIO

import pandas as pd
from flask import request

from . import api_bp
from ..services.detection_service import (
    batch_detect_from_frame,
    batch_update_alert_status,
    get_alert_trends,
    get_service_portrait,
    list_alerts,
    list_detection_logs,
    run_detection,
    simulate_realtime_stream,
    validate_payload,
)
from ..utils.constants import FEATURE_COLUMNS
from ..utils.response import failure, success


@api_bp.post("/detection/run")
def detection_run():
    payload = request.get_json(force=True)
    missing = validate_payload(payload)
    if missing:
        return failure(f"缺少字段: {', '.join(missing)}")
    return success(run_detection(payload), message="检测完成")


@api_bp.get("/detection/logs")
def detection_logs():
    limit = int(request.args.get("limit", 20))
    return success({"items": list_detection_logs(limit=limit)})


@api_bp.get("/alerts")
def alerts():
    limit = int(request.args.get("limit", 20))
    return success(
        {
            "items": list_alerts(
                limit=limit,
                risk_level=request.args.get("risk_level"),
                status=request.args.get("status"),
                keyword=request.args.get("keyword"),
            )
        }
    )


@api_bp.post("/detection/batch")
def detection_batch():
    if "file" not in request.files:
        return failure("请上传 CSV 文件")
    raw = request.files["file"].read()
    frame = pd.read_csv(BytesIO(raw))
    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        return failure(f"CSV 缺少字段: {', '.join(missing)}")
    result = batch_detect_from_frame(frame)
    return success(result, message="批量检测完成")


@api_bp.get("/alerts/trends")
def alert_trends():
    limit = int(request.args.get("limit", 14))
    return success(get_alert_trends(limit=limit))


@api_bp.put("/alerts/status")
def alert_status_batch():
    payload = request.get_json(force=True)
    updated = batch_update_alert_status(payload.get("ids", []), payload.get("status", "已处置"))
    return success({"updated": updated}, message="告警状态已更新")


@api_bp.get("/alerts/service-portrait")
def alert_service_portrait():
    limit = int(request.args.get("limit", 300))
    return success(get_service_portrait(limit=limit))


@api_bp.post("/detection/simulate-stream")
def detection_simulate_stream():
    payload = request.get_json(silent=True) or {}
    sample_size = int(payload.get("sample_size", 12))
    sample_size = max(4, min(sample_size, 30))
    return success(simulate_realtime_stream(sample_size=sample_size), message="实时流模拟完成")
