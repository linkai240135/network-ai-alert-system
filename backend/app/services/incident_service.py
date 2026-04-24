from __future__ import annotations

from datetime import datetime, timedelta

from ..extensions import db
from ..models import Alert, DatasetRecord, IncidentActivity, SecurityIncident, TrainingFeedback
from ..utils.constants import FEATURE_COLUMNS

PENDING_STATUS = "待研判"
PROCESSING_STATUS = "研判中"
WAIT_HANDLE_STATUS = "待处置"
RESOLVED_STATUS = "已处置"
OPEN_STATUSES = [PENDING_STATUS, PROCESSING_STATUS, WAIT_HANDLE_STATUS]


def _build_incident_no(attack_type: str, source_ip: str, destination_ip: str) -> str:
    safe_source = source_ip.replace(".", "")
    safe_dest = destination_ip.replace(".", "")
    prefix = f"INC-{attack_type.upper()}-{safe_source[-4:]}-{safe_dest[-4:]}"
    existing_count = SecurityIncident.query.filter(SecurityIncident.incident_no.like(f"{prefix}%")).count()
    return prefix if existing_count == 0 else f"{prefix}-{existing_count + 1:02d}"


def _find_open_incident(attack_type: str, source_ip: str, destination_ip: str) -> SecurityIncident | None:
    recent_threshold = datetime.utcnow() - timedelta(hours=6)
    return (
        SecurityIncident.query.filter(
            SecurityIncident.attack_type == attack_type,
            SecurityIncident.source_ip == source_ip,
            SecurityIncident.destination_ip == destination_ip,
            SecurityIncident.last_seen_at >= recent_threshold,
            SecurityIncident.status.in_(OPEN_STATUSES),
        )
        .order_by(SecurityIncident.last_seen_at.desc())
        .first()
    )


def add_incident_activity(incident: SecurityIncident, action_type: str, content: str, operator: str = "system") -> None:
    db.session.add(
        IncidentActivity(
            incident_id=incident.id,
            action_type=action_type,
            operator=operator,
            content=content,
        )
    )


def upsert_incident_from_detection(alert_data: dict, asset, result: dict, asset_context: dict) -> SecurityIncident:
    incident = _find_open_incident(result["label"], asset_context["source_ip"], asset_context["destination_ip"])
    if not incident:
        incident = SecurityIncident(
            incident_no=_build_incident_no(result["label"], asset_context["source_ip"], asset_context["destination_ip"]),
            title=f"{result['label']} 安全事件 - {asset.asset_name}",
            asset_id=asset.id,
            source_ip=asset_context["source_ip"],
            destination_ip=asset_context["destination_ip"],
            attack_type=result["label"],
            attack_stage=result["attack_stage"],
            severity=result["risk_level"],
            status=PENDING_STATUS,
            event_count=1,
            latest_confidence=result["confidence"],
            recommendations=result["recommendations"],
            summary={
                "binary_decision": result["binary_decision"],
                "unknown_flag": result["unknown_flag"],
                "service_profile": result["service_profile"],
                "top_features": result["top_features"],
                "latest_alert_id": alert_data["id"] if alert_data else None,
                "explanation_method": result.get("explanation_method"),
                "detector_name": result.get("detector_name"),
                "classifier_name": result.get("classifier_name"),
                "conformal_p_value": result.get("conformal_p_value"),
                "prediction_set": result.get("prediction_set", []),
            },
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
        )
        db.session.add(incident)
        db.session.flush()
        add_incident_activity(incident, "create", "系统基于异常检测结果自动生成安全事件。")
    else:
        incident.event_count += 1
        incident.latest_confidence = max(incident.latest_confidence, result["confidence"])
        incident.attack_stage = result["attack_stage"]
        incident.severity = result["risk_level"]
        incident.recommendations = result["recommendations"]
        incident.summary = {
            "binary_decision": result["binary_decision"],
            "unknown_flag": result["unknown_flag"],
            "service_profile": result["service_profile"],
            "top_features": result["top_features"],
            "latest_alert_id": alert_data["id"] if alert_data else None,
            "explanation_method": result.get("explanation_method"),
            "detector_name": result.get("detector_name"),
            "classifier_name": result.get("classifier_name"),
            "conformal_p_value": result.get("conformal_p_value"),
            "prediction_set": result.get("prediction_set", []),
        }
        incident.last_seen_at = datetime.utcnow()
        add_incident_activity(incident, "aggregate", f"系统聚合了一条同源同目标的 {result['label']} 告警。")
    db.session.flush()
    return incident


def list_incidents(limit: int = 20, status: str | None = None, severity: str | None = None) -> list[dict]:
    query = SecurityIncident.query.order_by(SecurityIncident.last_seen_at.desc())
    if status:
        query = query.filter(SecurityIncident.status == status)
    if severity:
        query = query.filter(SecurityIncident.severity == severity)
    return [item.to_dict() for item in query.limit(limit).all()]


def get_incident_detail(incident_id: int) -> dict | None:
    incident = SecurityIncident.query.get(incident_id)
    return incident.to_dict() if incident else None


def update_incident_status(incident_id: int, status: str, operator: str = "analyst", note: str | None = None) -> dict | None:
    incident = SecurityIncident.query.get(incident_id)
    if not incident:
        return None
    incident.status = status
    add_incident_activity(
        incident,
        "status",
        note or f"事件状态更新为“{status}”。",
        operator=operator,
    )
    db.session.commit()
    return incident.to_dict()


def add_incident_note(incident_id: int, content: str, operator: str = "analyst") -> dict | None:
    incident = SecurityIncident.query.get(incident_id)
    if not incident:
        return None
    add_incident_activity(incident, "note", content, operator=operator)
    db.session.commit()
    return incident.to_dict()


def get_incident_board() -> dict:
    incidents = SecurityIncident.query.order_by(SecurityIncident.last_seen_at.desc()).limit(50).all()
    status_summary = {}
    severity_summary = {}
    for incident in incidents:
        status_summary[incident.status] = status_summary.get(incident.status, 0) + 1
        severity_summary[incident.severity] = severity_summary.get(incident.severity, 0) + 1
    return {
        "stats": {
            "total": SecurityIncident.query.count(),
            "pending": SecurityIncident.query.filter(SecurityIncident.status == PENDING_STATUS).count(),
            "processing": SecurityIncident.query.filter(SecurityIncident.status == PROCESSING_STATUS).count(),
            "resolved": SecurityIncident.query.filter(SecurityIncident.status == RESOLVED_STATUS).count(),
            "feedbackCount": TrainingFeedback.query.count(),
            "feedbackSamples": DatasetRecord.query.filter(DatasetRecord.source.like("feedback-loop%")).count(),
        },
        "statusSummary": status_summary,
        "severitySummary": severity_summary,
        "items": [item.to_dict() for item in incidents[:10]],
    }


def build_incident_report(incident_id: int) -> dict | None:
    incident = SecurityIncident.query.get(incident_id)
    if not incident:
        return None
    asset = incident.asset
    recommendations = incident.recommendations or []
    activities = sorted(incident.activities, key=lambda item: item.created_at)
    lines = [
        "# 安全事件报告",
        "",
        f"事件编号：{incident.incident_no}",
        f"事件标题：{incident.title}",
        f"事件类型：{incident.attack_type}",
        f"风险等级：{incident.severity}",
        f"事件状态：{incident.status}",
        f"攻击阶段：{incident.attack_stage}",
        f"事件聚合数：{incident.event_count}",
        "",
        "## 资产信息",
        f"资产名称：{asset.asset_name if asset else '--'}",
        f"资产地址：{asset.ip_address if asset else incident.destination_ip}",
        f"业务域：{asset.business_unit if asset else '--'}",
        f"服务端口：{asset.protocol if asset else '--'}/{asset.port if asset else '--'}",
        "",
        "## 影响范围",
        f"源地址：{incident.source_ip}",
        f"目标地址：{incident.destination_ip}",
        f"最近时间：{incident.last_seen_at.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 研判建议",
    ]
    lines.extend([f"{idx + 1}. {item}" for idx, item in enumerate(recommendations)])
    lines.append("")
    lines.append("## 处置记录")
    if activities:
        lines.extend(
            [
                f"- [{item.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {item.operator} / {item.action_type}：{item.content}"
                for item in activities
            ]
        )
    else:
        lines.append("- 暂无处置记录")
    return {
        "filename": f"{incident.incident_no}.md",
        "content": "\n".join(lines),
        "summary": incident.to_dict(),
    }


def get_source_attack_chain(source_ip: str) -> dict:
    incidents = (
        SecurityIncident.query.filter(SecurityIncident.source_ip == source_ip)
        .order_by(SecurityIncident.first_seen_at.asc())
        .all()
    )
    timeline = []
    nodes = [{"id": source_ip, "name": source_ip, "category": "source", "symbolSize": 54}]
    links = []
    asset_seen = set()
    for incident in incidents:
        asset_name = incident.asset.asset_name if incident.asset else incident.destination_ip
        timeline.append(
            {
                "incident_no": incident.incident_no,
                "attack_type": incident.attack_type,
                "attack_stage": incident.attack_stage,
                "severity": incident.severity,
                "status": incident.status,
                "target": asset_name,
                "time": incident.first_seen_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        if asset_name not in asset_seen:
            nodes.append({"id": asset_name, "name": asset_name, "category": "asset", "symbolSize": 38})
            asset_seen.add(asset_name)
        links.append({"source": source_ip, "target": asset_name, "label": incident.attack_type})
    return {
        "sourceIp": source_ip,
        "timeline": timeline,
        "graph": {"nodes": nodes, "links": links},
    }


def _extract_feedback_features(incident: SecurityIncident) -> dict | None:
    latest_alert_id = (incident.summary or {}).get("latest_alert_id")
    if not latest_alert_id:
        return None
    alert = Alert.query.get(latest_alert_id)
    if not alert or not alert.detection_log or not isinstance(alert.detection_log.features, dict):
        return None
    payload = alert.detection_log.features
    try:
        return {column: float(payload[column]) for column in FEATURE_COLUMNS}
    except Exception:
        return None


def create_feedback(incident_id: int, feedback_type: str, expected_label: str, comment: str, operator: str = "analyst") -> dict | None:
    incident = SecurityIncident.query.get(incident_id)
    if not incident:
        return None

    feedback_features = _extract_feedback_features(incident)
    feedback = TrainingFeedback(
        incident_id=incident.id,
        attack_type=incident.attack_type,
        expected_label=expected_label,
        feedback_type=feedback_type,
        comment=comment,
        source_ip=incident.source_ip,
        destination_ip=incident.destination_ip,
        operator=operator,
    )
    db.session.add(feedback)
    db.session.flush()

    feedback_sample_id = None
    if feedback_features:
        sample = DatasetRecord(
            source=f"feedback-loop:{feedback.id}:{feedback_type}",
            label=expected_label,
            flow_duration=feedback_features["flow_duration"],
            packet_rate=feedback_features["packet_rate"],
            byte_rate=feedback_features["byte_rate"],
            syn_rate=feedback_features["syn_rate"],
            dst_port_entropy=feedback_features["dst_port_entropy"],
            failed_login_rate=feedback_features["failed_login_rate"],
            request_interval_std=feedback_features["request_interval_std"],
            payload_mean=feedback_features["payload_mean"],
        )
        db.session.add(sample)
        db.session.flush()
        feedback_sample_id = sample.id

    add_incident_activity(
        incident,
        "feedback",
        (
            f"已提交反馈：{feedback_type}，期望标签为 {expected_label}。"
            + (f" 系统已回写训练样本 #{feedback_sample_id}。" if feedback_sample_id else " 由于缺少原始特征，本次未生成回流样本。")
        ),
        operator=operator,
    )
    db.session.commit()

    payload = feedback.to_dict()
    payload["feedback_sample_id"] = feedback_sample_id
    payload["feedback_sample_created"] = feedback_sample_id is not None
    return payload


def list_feedback(limit: int = 20) -> list[dict]:
    items = TrainingFeedback.query.order_by(TrainingFeedback.created_at.desc()).limit(limit).all()
    return [item.to_dict() for item in items]
