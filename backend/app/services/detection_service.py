from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import func, or_

from ..extensions import db
from ..models import Alert, DatasetRecord, DetectionLog
from ..utils.constants import FEATURE_COLUMNS
from .asset_service import derive_asset_context, upsert_asset
from .incident_service import upsert_incident_from_detection
from .ml_engine import predict

RESOLVED_STATUS = "已处置"
PENDING_STATUS = "待处置"


def validate_payload(payload: dict) -> list[str]:
    return [column for column in FEATURE_COLUMNS if column not in payload]


def _normalize_features(payload: dict) -> dict[str, float]:
    return {column: round(float(payload[column]), 6) for column in FEATURE_COLUMNS}


def _build_detection_meta(result: dict, source: str) -> dict[str, Any]:
    return {
        "source": source,
        "classifier_name": result.get("classifier_name"),
        "raw_label": result["raw_label"],
        "anomaly_score": result["anomaly_score"],
        "binary_decision": result["binary_decision"],
        "attack_stage": result["attack_stage"],
        "unknown_flag": result["unknown_flag"],
        "service_profile": result["service_profile"],
        "top_features": result["top_features"],
        "recommendations": result["recommendations"],
        "explanation_method": result.get("explanation_method"),
        "detector_name": result.get("detector_name"),
        "detector_score": result.get("detector_score"),
        "detector_threshold": result.get("detector_threshold"),
        "detector_baseline": result.get("detector_baseline"),
        "detector_flag": result.get("detector_flag"),
        "conformal_p_value": result.get("conformal_p_value"),
        "prediction_set": result.get("prediction_set", []),
        "uncertainty_level": result.get("uncertainty_level"),
        "requires_review": result.get("requires_review", False),
    }


def _hydrate_detection_log(item: DetectionLog) -> dict:
    data = item.to_dict()
    meta = {}
    if isinstance(data.get("features"), dict):
        meta = data["features"].get("_meta", {})
    data.update(
        {
            "source": meta.get("source", "manual"),
            "classifier_name": meta.get("classifier_name", "FT-Transformer"),
            "raw_label": meta.get("raw_label", data["label"]),
            "anomaly_score": meta.get("anomaly_score", data["confidence"]),
            "binary_decision": meta.get("binary_decision", "anomaly" if data["label"] != "BENIGN" else "normal"),
            "attack_stage": meta.get("attack_stage", "异常分析阶段"),
            "unknown_flag": meta.get("unknown_flag", False),
            "service_profile": meta.get("service_profile", {}),
            "top_features": meta.get("top_features", []),
            "recommendations": meta.get("recommendations", [data["advice"]]),
            "asset_context": meta.get("asset_context", {}),
            "explanation_method": meta.get("explanation_method", "Statistical deviation"),
            "detector_name": meta.get("detector_name", "DeepSVDD"),
            "detector_score": meta.get("detector_score", data["confidence"]),
            "detector_threshold": meta.get("detector_threshold"),
            "detector_baseline": meta.get("detector_baseline"),
            "detector_flag": meta.get("detector_flag", False),
            "conformal_p_value": meta.get("conformal_p_value"),
            "prediction_set": meta.get("prediction_set", []),
            "uncertainty_level": meta.get("uncertainty_level", "medium"),
            "requires_review": meta.get("requires_review", False),
        }
    )
    return data


def _hydrate_alert(item: Alert) -> dict:
    data = item.to_dict()
    if item.detection_log:
        enriched_log = _hydrate_detection_log(item.detection_log)
        data.update(
            {
                "attack_stage": enriched_log["attack_stage"],
                "classifier_name": enriched_log["classifier_name"],
                "binary_decision": enriched_log["binary_decision"],
                "unknown_flag": enriched_log["unknown_flag"],
                "service_profile": enriched_log["service_profile"],
                "top_features": enriched_log["top_features"],
                "recommendations": enriched_log["recommendations"],
                "source": enriched_log["source"],
                "anomaly_score": enriched_log["anomaly_score"],
                "asset_context": enriched_log["asset_context"],
                "conformal_p_value": enriched_log["conformal_p_value"],
                "prediction_set": enriched_log["prediction_set"],
                "uncertainty_level": enriched_log["uncertainty_level"],
                "requires_review": enriched_log["requires_review"],
            }
        )
    return data


def _service_profile_name(service_profile: dict) -> str:
    if not service_profile:
        return "未知服务"
    return f"{service_profile.get('name', '未知服务')}:{service_profile.get('port', '--')}"


def run_detection(payload: dict, source: str = "manual") -> dict:
    normalized = _normalize_features(payload)
    result = predict(normalized)
    asset_context = derive_asset_context(result["service_profile"], result, normalized)
    feature_payload = {**result["features"], "_meta": {**_build_detection_meta(result, source), "asset_context": asset_context}}
    detection = DetectionLog(
        label=result["label"],
        risk_level=result["risk_level"],
        confidence=result["confidence"],
        description=result["description"],
        advice=result["advice"],
        features=feature_payload,
    )
    db.session.add(detection)
    db.session.flush()

    alert = None
    incident = None
    if result["binary_decision"] == "anomaly":
        service_profile = result["service_profile"]
        alert = Alert(
            detection_log_id=detection.id,
            title=f"{result['label']} 异常事件 - {_service_profile_name(service_profile)}",
            risk_level=result["risk_level"],
            status=PENDING_STATUS,
            confidence=result["confidence"],
            advice=result["advice"],
        )
        db.session.add(alert)
        db.session.flush()
        asset = upsert_asset(asset_context)
        incident = upsert_incident_from_detection(alert.to_dict(), asset, result, asset_context)
    db.session.commit()

    saved_detection = DetectionLog.query.get(detection.id)
    saved_alert = Alert.query.get(alert.id) if alert else None
    return {
        "result": _hydrate_detection_log(saved_detection),
        "alert": _hydrate_alert(saved_alert) if saved_alert else None,
        "incident": incident.to_dict() if incident else None,
    }


def list_detection_logs(limit: int = 20) -> list[dict]:
    items = DetectionLog.query.order_by(DetectionLog.created_at.desc()).limit(limit).all()
    return [_hydrate_detection_log(item) for item in items]


def list_alerts(
    limit: int = 20,
    risk_level: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
) -> list[dict]:
    query = Alert.query.join(DetectionLog).order_by(Alert.created_at.desc())
    if risk_level:
        query = query.filter(Alert.risk_level == risk_level)
    if status:
        query = query.filter(Alert.status == status)
    if keyword:
        keyword_like = f"%{keyword}%"
        query = query.filter(
            or_(
                Alert.title.like(keyword_like),
                DetectionLog.label.like(keyword_like),
                DetectionLog.description.like(keyword_like),
            )
        )
    items = query.limit(limit).all()
    return [_hydrate_alert(item) for item in items]


def batch_detect_from_frame(frame: pd.DataFrame, source: str = "batch_csv") -> dict:
    results = []
    alert_count = 0
    unknown_count = 0
    for _, row in frame.iterrows():
        payload = {column: float(row[column]) for column in FEATURE_COLUMNS if column in row}
        outcome = run_detection(payload, source=source)
        if outcome["alert"]:
            alert_count += 1
        if outcome["result"]["unknown_flag"]:
            unknown_count += 1
        results.append(outcome["result"])
    return {
        "total": len(results),
        "alertCount": alert_count,
        "unknownCount": unknown_count,
        "results": results[:50],
    }


def get_alert_trends(limit: int = 14) -> dict:
    rows = (
        db.session.query(func.date(Alert.created_at), func.count(Alert.id))
        .group_by(func.date(Alert.created_at))
        .order_by(func.date(Alert.created_at).asc())
        .all()
    )
    rows = rows[-limit:]
    high_risk = Alert.query.filter(Alert.risk_level == "高").count()
    unknown_count = DetectionLog.query.filter(DetectionLog.label == "UNKNOWN").count()
    return {
        "labels": [str(item[0]) for item in rows],
        "counts": [int(item[1]) for item in rows],
        "highRiskCount": high_risk,
        "unknownCount": unknown_count,
    }


def batch_update_alert_status(ids: list[int], status: str = RESOLVED_STATUS) -> int:
    if not ids:
        return 0
    items = Alert.query.filter(Alert.id.in_(ids)).all()
    for item in items:
        item.status = status
    db.session.commit()
    return len(items)


def get_service_portrait(limit: int = 300) -> dict:
    logs = DetectionLog.query.order_by(DetectionLog.created_at.desc()).limit(limit).all()
    service_counter: dict[str, dict[str, Any]] = {}
    stage_counter: dict[str, int] = {}
    port_counter: dict[int, int] = {}
    unknown_count = 0

    for log in logs:
        enriched = _hydrate_detection_log(log)
        stage = enriched["attack_stage"]
        stage_counter[stage] = stage_counter.get(stage, 0) + 1
        if enriched["unknown_flag"]:
            unknown_count += 1

        profile = enriched.get("service_profile") or {}
        key = _service_profile_name(profile)
        bucket = service_counter.setdefault(
            key,
            {
                "name": profile.get("name", "未知服务"),
                "port": profile.get("port", 0),
                "protocol": profile.get("protocol", "N/A"),
                "keywords": profile.get("keywords", ""),
                "count": 0,
                "highRiskCount": 0,
            },
        )
        bucket["count"] += 1
        if enriched["risk_level"] == "高":
            bucket["highRiskCount"] += 1
        if profile.get("port") is not None:
            port = int(profile.get("port", 0))
            port_counter[port] = port_counter.get(port, 0) + 1

    services = sorted(service_counter.values(), key=lambda item: (item["highRiskCount"], item["count"]), reverse=True)
    ports = [
        {"port": port, "count": count}
        for port, count in sorted(port_counter.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    stages = [
        {"name": name, "value": value}
        for name, value in sorted(stage_counter.items(), key=lambda item: item[1], reverse=True)
    ]
    return {
        "services": services[:6],
        "ports": ports,
        "stages": stages,
        "unknownCount": unknown_count,
    }


def simulate_realtime_stream(sample_size: int = 12) -> dict:
    recent_records = DatasetRecord.query.order_by(DatasetRecord.id.desc()).limit(max(sample_size * 8, 80)).all()
    if not recent_records:
        return {"total": 0, "alerts": 0, "unknownCount": 0, "items": []}

    selected = list(reversed(recent_records[:sample_size]))
    timeline = []
    alert_count = 0
    unknown_count = 0

    for record in selected:
        payload = {column: float(getattr(record, column)) for column in FEATURE_COLUMNS}
        outcome = run_detection(payload, source="stream_simulation")
        result = outcome["result"]
        if outcome["alert"]:
            alert_count += 1
        if result["unknown_flag"]:
            unknown_count += 1
        timeline.append(
            {
                "id": result["id"],
                "timestamp": result["created_at"],
                "label": result["label"],
                "attack_stage": result["attack_stage"],
                "risk_level": result["risk_level"],
                "confidence": result["confidence"],
                "anomaly_score": result["anomaly_score"],
                "service_profile": result["service_profile"],
                "unknown_flag": result["unknown_flag"],
            }
        )

    return {
        "total": len(timeline),
        "alerts": alert_count,
        "unknownCount": unknown_count,
        "items": timeline,
    }
