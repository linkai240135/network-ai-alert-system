from __future__ import annotations

from datetime import datetime

from .database import db


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

    def to_feature_dict(self) -> dict:
        return {
            "flow_duration": self.flow_duration,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "syn_rate": self.syn_rate,
            "dst_port_entropy": self.dst_port_entropy,
            "failed_login_rate": self.failed_login_rate,
            "request_interval_std": self.request_interval_std,
            "payload_mean": self.payload_mean,
            "label": self.label,
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

    metrics = db.relationship(
        "ModelMetric",
        back_populates="training_run",
        cascade="all, delete-orphan",
        lazy="joined",
    )


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

    alert = db.relationship(
        "Alert",
        back_populates="detection_log",
        cascade="all, delete-orphan",
        uselist=False,
    )

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
