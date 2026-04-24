from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from .ml import FEATURE_COLUMNS, dataset_overview, model_artifacts, predict, save_detection, train_models
from .models import Alert, DetectionLog, TrainingRun

web = Blueprint("web", __name__)
api = Blueprint("api", __name__)


@web.get("/")
def index():
    return render_template("index.html", feature_columns=FEATURE_COLUMNS)


@api.get("/overview")
def overview():
    data = dataset_overview()
    artifacts = model_artifacts()
    data["training"] = artifacts["summary"]
    data["models"] = artifacts["models"]
    data["class_labels"] = artifacts["class_labels"]
    data["confusion_matrix"] = artifacts["confusion_matrix"]
    data["training_created_at"] = artifacts.get("created_at")
    data["db_mode"] = "MySQL" if "mysql" in current_app.config["SQLALCHEMY_DATABASE_URI"] else "SQLite"
    return jsonify(data)


@api.post("/train")
def retrain():
    result = train_models()
    return jsonify(
        {
            "message": "模型训练完成",
            "summary": result.summary,
            "models": result.models,
            "confusion_matrix": result.confusion_matrix,
        }
    )


@api.post("/predict")
def detect():
    payload = request.get_json(force=True)
    missing = [column for column in FEATURE_COLUMNS if column not in payload]
    if missing:
        return jsonify({"error": f"缺少字段: {', '.join(missing)}"}), 400

    result = predict(payload)
    detection, alert = save_detection(result)
    return jsonify(
        {
            "result": {**result, "id": detection.id, "created_at": detection.created_at.strftime("%Y-%m-%d %H:%M:%S")},
            "alert": alert.to_dict() if alert else None,
        }
    )


@api.get("/alerts")
def alerts():
    items = Alert.query.order_by(Alert.created_at.desc()).limit(20).all()
    return jsonify({"alerts": [item.to_dict() for item in items]})


@api.get("/detections")
def detections():
    items = DetectionLog.query.order_by(DetectionLog.created_at.desc()).limit(20).all()
    return jsonify({"detections": [item.to_dict() for item in items]})


@api.get("/system")
def system():
    latest_training = TrainingRun.query.order_by(TrainingRun.created_at.desc()).first()
    return jsonify(
        {
            "architecture": {
                "frontend": "Vue 3 + ECharts + Axios(CDN)",
                "backend": "Flask REST API",
                "database": "MySQL (recommended) / SQLite (local fallback)",
                "ml": "scikit-learn + pandas + numpy",
            },
            "database_uri": current_app.config["SQLALCHEMY_DATABASE_URI"],
            "latest_training": latest_training.created_at.strftime("%Y-%m-%d %H:%M:%S") if latest_training else None,
        }
    )
