from __future__ import annotations

from pathlib import Path

import joblib

from ..extensions import db
from ..models import DatasetRecord, ModelMetric, TrainingRun
from .dataset_service import get_dataset_frame
from .ml_engine import train

ROOT_DIR = Path(__file__).resolve().parents[3]
ARTIFACTS_PATH = ROOT_DIR / "models" / "training_artifacts.joblib"


def _load_training_artifact_summary() -> dict:
    if not ARTIFACTS_PATH.exists():
        return {}
    payload = joblib.load(ARTIFACTS_PATH)
    summary = dict(payload.get("summary", {}))
    summary["models"] = payload.get("models", [])
    summary["class_labels"] = payload.get("class_labels", [])
    summary["confusion_matrix"] = payload.get("confusion_matrix", [])
    summary["classification_report"] = payload.get("classification_report", {})
    return summary


def _enrich_training_payload(payload: dict) -> dict:
    summary = _load_training_artifact_summary()
    if not summary:
        return payload
    merged = {**payload}
    merged["source_dataset_size"] = summary.get("source_dataset_size", payload.get("dataset_size"))
    merged["sampled_training"] = summary.get("sampled_training", False)
    merged["data_source_name"] = "CICIDS2017 Real Flow Dataset"
    merged["data_source_type"] = "cicids2017-parquet"
    merged["unknown_threshold"] = summary.get("unknown_threshold")
    merged["alert_threshold"] = summary.get("alert_threshold")
    merged["detector_name"] = summary.get("detector_name", "DeepSVDD")
    merged["detector_metrics"] = summary.get("detector_metrics", {})
    merged["explanation_engine"] = summary.get("explanation_engine", "Attention rollout + gradient attribution")
    merged["benchmark_best_model"] = summary.get("benchmark_best_model")
    merged["conformal_significance"] = summary.get("conformal_significance")
    merged["primary_story"] = summary.get("primary_story")
    merged["innovation_stack"] = summary.get("innovation_stack", [])
    merged["models"] = summary.get("models", payload.get("metrics", []))
    merged["feedback_loop_count"] = DatasetRecord.query.filter(DatasetRecord.source.like("feedback-loop%")).count()
    merged["training_ratio"] = round(
        merged["dataset_size"] / merged["source_dataset_size"], 4
    ) if merged.get("source_dataset_size") else 1
    if summary.get("class_labels"):
        merged["class_labels"] = summary["class_labels"]
    if summary.get("confusion_matrix"):
        merged["confusion_matrix"] = summary["confusion_matrix"]
    if summary.get("classification_report"):
        merged["classification_report"] = summary["classification_report"]
    return merged


def ensure_training_run() -> None:
    if TrainingRun.query.count() == 0:
        run_training()


def run_training() -> dict:
    df = get_dataset_frame()
    artifacts = train(df)

    training_run = TrainingRun(
        best_model=artifacts.summary["best_model"],
        dataset_size=artifacts.summary["dataset_size"],
        feature_count=artifacts.summary["feature_count"],
        class_count=artifacts.summary["class_count"],
        class_labels=artifacts.class_labels,
        confusion_matrix=artifacts.confusion_matrix,
        classification_report=artifacts.classification_report,
    )
    db.session.add(training_run)
    db.session.flush()
    db.session.add_all(
        [
            ModelMetric(
                training_run_id=training_run.id,
                model_name=item["name"],
                accuracy=item["accuracy"],
                precision=item["precision"],
                recall=item["recall"],
                f1_score=item["f1_score"],
            )
            for item in artifacts.models
        ]
    )
    db.session.commit()
    return training_run.to_dict()


def get_latest_training() -> dict:
    latest = TrainingRun.query.order_by(TrainingRun.created_at.desc()).first()
    if latest:
        return _enrich_training_payload(latest.to_dict())
    ensure_training_run()
    latest = TrainingRun.query.order_by(TrainingRun.created_at.desc()).first()
    return _enrich_training_payload(latest.to_dict())


def get_training_history(limit: int = 10) -> list[dict]:
    ensure_training_run()
    items = TrainingRun.query.order_by(TrainingRun.created_at.desc()).limit(limit).all()
    history = [item.to_dict() for item in items]
    if history:
        history[0] = _enrich_training_payload(history[0])
    return history


def get_training_trends(limit: int = 10) -> dict:
    items = TrainingRun.query.order_by(TrainingRun.created_at.asc()).limit(limit).all()
    history = [item.to_dict() for item in items]
    return {
        "labels": [item["created_at"] for item in history],
        "bestModels": [item["best_model"] for item in history],
        "datasetSizes": [item["dataset_size"] for item in history],
        "f1Series": [
            max((metric["f1_score"] for metric in item["metrics"]), default=0)
            for item in history
        ],
        "items": history,
    }
