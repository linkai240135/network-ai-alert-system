from __future__ import annotations

from datetime import datetime

from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="admin")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_login_at": self.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if self.last_login_at else None,
        }


class DatasetRecord(db.Model):
    __tablename__ = "dataset_records"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(128), nullable=False, default="synthetic-cicids-style")
    label = db.Column(db.String(32), nullable=False, index=True)
    flow_duration = db.Column(db.Float, nullable=False)
    packet_rate = db.Column(db.Float, nullable=False)
    byte_rate = db.Column(db.Float, nullable=False)
    syn_rate = db.Column(db.Float, nullable=False)
    dst_port_entropy = db.Column(db.Float, nullable=False)
    failed_login_rate = db.Column(db.Float, nullable=False)
    request_interval_std = db.Column(db.Float, nullable=False)
    payload_mean = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "label": self.label,
            "flow_duration": self.flow_duration,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "syn_rate": self.syn_rate,
            "dst_port_entropy": self.dst_port_entropy,
            "failed_login_rate": self.failed_login_rate,
            "request_interval_std": self.request_interval_std,
            "payload_mean": self.payload_mean,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class TrainingRun(db.Model):
    __tablename__ = "training_runs"

    id = db.Column(db.Integer, primary_key=True)
    best_model = db.Column(db.String(64), nullable=False)
    dataset_size = db.Column(db.Integer, nullable=False)
    feature_count = db.Column(db.Integer, nullable=False)
    class_count = db.Column(db.Integer, nullable=False)
    class_labels = db.Column(db.JSON, nullable=False)
    confusion_matrix = db.Column(db.JSON, nullable=False)
    classification_report = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    metrics = db.relationship("ModelMetric", back_populates="training_run", cascade="all, delete-orphan", lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "best_model": self.best_model,
            "dataset_size": self.dataset_size,
            "feature_count": self.feature_count,
            "class_count": self.class_count,
            "class_labels": self.class_labels,
            "confusion_matrix": self.confusion_matrix,
            "classification_report": self.classification_report,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": [metric.to_dict() for metric in self.metrics],
        }


class ModelMetric(db.Model):
    __tablename__ = "model_metrics"

    id = db.Column(db.Integer, primary_key=True)
    training_run_id = db.Column(db.Integer, db.ForeignKey("training_runs.id"), nullable=False, index=True)
    model_name = db.Column(db.String(64), nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    precision = db.Column(db.Float, nullable=False)
    recall = db.Column(db.Float, nullable=False)
    f1_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    training_run = db.relationship("TrainingRun", back_populates="metrics")

    def to_dict(self) -> dict:
        return {
            "name": self.model_name,
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
        }


class DetectionLog(db.Model):
    __tablename__ = "detection_logs"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(32), nullable=False, index=True)
    risk_level = db.Column(db.String(16), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    advice = db.Column(db.String(255), nullable=False)
    features = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    alert = db.relationship("Alert", back_populates="detection_log", cascade="all, delete-orphan", uselist=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "risk_level": self.risk_level,
            "confidence": round(self.confidence, 4),
            "description": self.description,
            "advice": self.advice,
            "features": self.features,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    detection_log_id = db.Column(db.Integer, db.ForeignKey("detection_logs.id"), nullable=False, unique=True)
    title = db.Column(db.String(128), nullable=False)
    risk_level = db.Column(db.String(16), nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default="待处置")
    confidence = db.Column(db.Float, nullable=False)
    advice = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    detection_log = db.relationship("DetectionLog", back_populates="alert")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "label": self.detection_log.label if self.detection_log else "",
            "risk_level": self.risk_level,
            "status": self.status,
            "confidence": round(self.confidence, 4),
            "advice": self.advice,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    asset_code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    asset_name = db.Column(db.String(128), nullable=False)
    ip_address = db.Column(db.String(64), nullable=False, index=True)
    business_unit = db.Column(db.String(64), nullable=False, default="通信业务区")
    owner_team = db.Column(db.String(64), nullable=False, default="安全运营中心")
    asset_type = db.Column(db.String(32), nullable=False, default="server")
    service_name = db.Column(db.String(64), nullable=False)
    protocol = db.Column(db.String(32), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    risk_score = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(32), nullable=False, default="在线")
    tags = db.Column(db.JSON, nullable=False, default=list)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    incidents = db.relationship("SecurityIncident", back_populates="asset", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "asset_code": self.asset_code,
            "asset_name": self.asset_name,
            "ip_address": self.ip_address,
            "business_unit": self.business_unit,
            "owner_team": self.owner_team,
            "asset_type": self.asset_type,
            "service_name": self.service_name,
            "protocol": self.protocol,
            "port": self.port,
            "risk_score": round(self.risk_score, 4),
            "status": self.status,
            "tags": self.tags or [],
            "last_seen_at": self.last_seen_at.strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class SecurityIncident(db.Model):
    __tablename__ = "security_incidents"

    id = db.Column(db.Integer, primary_key=True)
    incident_no = db.Column(db.String(64), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=True, index=True)
    source_ip = db.Column(db.String(64), nullable=False, index=True)
    destination_ip = db.Column(db.String(64), nullable=False, index=True)
    attack_type = db.Column(db.String(32), nullable=False, index=True)
    attack_stage = db.Column(db.String(64), nullable=False)
    severity = db.Column(db.String(16), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="待研判", index=True)
    event_count = db.Column(db.Integer, nullable=False, default=1)
    latest_confidence = db.Column(db.Float, nullable=False, default=0.0)
    recommendations = db.Column(db.JSON, nullable=False, default=list)
    summary = db.Column(db.JSON, nullable=False, default=dict)
    first_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset = db.relationship("Asset", back_populates="incidents")
    activities = db.relationship("IncidentActivity", back_populates="incident", cascade="all, delete-orphan", lazy="joined")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "incident_no": self.incident_no,
            "title": self.title,
            "asset_id": self.asset_id,
            "asset": self.asset.to_dict() if self.asset else None,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "attack_type": self.attack_type,
            "attack_stage": self.attack_stage,
            "severity": self.severity,
            "status": self.status,
            "event_count": self.event_count,
            "latest_confidence": round(self.latest_confidence, 4),
            "recommendations": self.recommendations or [],
            "summary": self.summary or {},
            "first_seen_at": self.first_seen_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen_at": self.last_seen_at.strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "activities": [item.to_dict() for item in sorted(self.activities, key=lambda row: row.created_at, reverse=True)],
        }


class IncidentActivity(db.Model):
    __tablename__ = "incident_activities"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("security_incidents.id"), nullable=False, index=True)
    action_type = db.Column(db.String(32), nullable=False)
    operator = db.Column(db.String(64), nullable=False, default="system")
    content = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    incident = db.relationship("SecurityIncident", back_populates="activities")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "action_type": self.action_type,
            "operator": self.operator,
            "content": self.content,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class TrainingFeedback(db.Model):
    __tablename__ = "training_feedback"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("security_incidents.id"), nullable=False, index=True)
    attack_type = db.Column(db.String(32), nullable=False)
    expected_label = db.Column(db.String(32), nullable=False)
    feedback_type = db.Column(db.String(32), nullable=False, default="误报")
    comment = db.Column(db.String(255), nullable=False, default="")
    source_ip = db.Column(db.String(64), nullable=False)
    destination_ip = db.Column(db.String(64), nullable=False)
    operator = db.Column(db.String(64), nullable=False, default="analyst")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "attack_type": self.attack_type,
            "expected_label": self.expected_label,
            "feedback_type": self.feedback_type,
            "comment": self.comment,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "operator": self.operator,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class DatasetImportJob(db.Model):
    __tablename__ = "dataset_import_jobs"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(64), nullable=False, default="cicids2017")
    imported_count = db.Column(db.Integer, nullable=False, default=0)
    skipped_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="completed")
    summary = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "source_type": self.source_type,
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
            "status": self.status,
            "summary": self.summary,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "key": self.setting_key,
            "value": self.setting_value,
            "description": self.description,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
