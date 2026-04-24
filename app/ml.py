from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .database import db
from .models import DatasetRecord, DetectionLog, Alert, ModelMetric, TrainingRun

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DATASET_PATH = DATA_DIR / "network_flows.csv"
MODEL_PATH = MODELS_DIR / "best_model.joblib"
ARTIFACTS_PATH = MODELS_DIR / "training_artifacts.joblib"

ATTACK_DESCRIPTIONS = {
    "BENIGN": "正常通信流量",
    "DoS": "拒绝服务攻击，表现为短时高频流量冲击",
    "PortScan": "端口扫描行为，通常具有高目的端口变化率",
    "Bot": "僵尸网络控制流量，常表现为周期性异常连接",
    "BruteForce": "暴力破解攻击，通常伴随高失败率和重复尝试",
    "WebAttack": "针对Web服务的异常访问与攻击行为",
}

FEATURE_COLUMNS = [
    "flow_duration",
    "packet_rate",
    "byte_rate",
    "syn_rate",
    "dst_port_entropy",
    "failed_login_rate",
    "request_interval_std",
    "payload_mean",
]


@dataclass
class TrainingResult:
    summary: Dict
    models: List[Dict]
    confusion_matrix: List[List[int]]


def _rng(seed: int = 42) -> np.random.Generator:
    return np.random.default_rng(seed)


def ensure_dataset(samples_per_class: int = 300) -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATASET_PATH.exists():
        return pd.read_csv(DATASET_PATH)

    rng = _rng()
    rows = []
    profiles = {
        "BENIGN": dict(flow_duration=(60, 420), packet_rate=(20, 140), byte_rate=(500, 5000), syn_rate=(0.01, 0.08),
                       dst_port_entropy=(0.1, 0.35), failed_login_rate=(0.0, 0.04), request_interval_std=(0.2, 1.2),
                       payload_mean=(300, 1100)),
        "DoS": dict(flow_duration=(10, 120), packet_rate=(400, 1300), byte_rate=(12000, 45000), syn_rate=(0.45, 0.95),
                    dst_port_entropy=(0.05, 0.18), failed_login_rate=(0.0, 0.1), request_interval_std=(0.01, 0.18),
                    payload_mean=(80, 360)),
        "PortScan": dict(flow_duration=(20, 150), packet_rate=(140, 500), byte_rate=(1800, 8500), syn_rate=(0.35, 0.75),
                         dst_port_entropy=(0.72, 0.98), failed_login_rate=(0.0, 0.08), request_interval_std=(0.03, 0.35),
                         payload_mean=(60, 240)),
        "Bot": dict(flow_duration=(150, 600), packet_rate=(80, 280), byte_rate=(2500, 9000), syn_rate=(0.1, 0.4),
                    dst_port_entropy=(0.3, 0.65), failed_login_rate=(0.02, 0.15), request_interval_std=(0.4, 1.8),
                    payload_mean=(180, 700)),
        "BruteForce": dict(flow_duration=(40, 260), packet_rate=(50, 240), byte_rate=(1200, 7000), syn_rate=(0.08, 0.35),
                           dst_port_entropy=(0.08, 0.22), failed_login_rate=(0.55, 0.98), request_interval_std=(0.02, 0.25),
                           payload_mean=(90, 300)),
        "WebAttack": dict(flow_duration=(30, 280), packet_rate=(40, 220), byte_rate=(1500, 14000), syn_rate=(0.05, 0.22),
                          dst_port_entropy=(0.2, 0.55), failed_login_rate=(0.02, 0.2), request_interval_std=(0.06, 0.55),
                          payload_mean=(450, 1800)),
    }

    for label, config in profiles.items():
        for _ in range(samples_per_class):
            row = {feature: round(rng.uniform(*bounds), 4) for feature, bounds in config.items()}
            row["label"] = label
            rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(DATASET_PATH, index=False)
    return df


def load_dataset() -> pd.DataFrame:
    if DatasetRecord.query.count() > 0:
        records = [item.to_feature_dict() for item in DatasetRecord.query.order_by(DatasetRecord.id).all()]
        return pd.DataFrame(records)
    return ensure_dataset()


def train_models() -> TrainingResult:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_dataset()
    x = df[FEATURE_COLUMNS]
    y = df["label"]
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y_encoded, test_size=0.25, random_state=42, stratify=y_encoded
    )

    candidates = [
        ("Random Forest", RandomForestClassifier(n_estimators=220, random_state=42, class_weight="balanced")),
        ("Decision Tree", DecisionTreeClassifier(max_depth=10, random_state=42, class_weight="balanced")),
        (
            "Logistic Regression",
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("clf", LogisticRegression(max_iter=3000, multi_class="auto")),
                ]
            ),
        ),
    ]

    model_scores = []
    best_payload = None
    best_f1 = -1.0

    for name, model in candidates:
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        result = {
            "name": name,
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "precision": round(float(precision_score(y_test, pred, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, pred, average="weighted", zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, pred, average="weighted", zero_division=0)), 4),
        }
        model_scores.append(result)
        if result["f1_score"] > best_f1:
            best_f1 = result["f1_score"]
            best_payload = {"model_name": name, "model": model, "pred": pred, "y_test": y_test}

    assert best_payload is not None
    confusion = confusion_matrix(best_payload["y_test"], best_payload["pred"]).tolist()
    classification = classification_report(
        best_payload["y_test"],
        best_payload["pred"],
        target_names=encoder.classes_,
        output_dict=True,
        zero_division=0,
    )

    joblib.dump(
        {
            "model": best_payload["model"],
            "label_encoder": encoder,
            "feature_columns": FEATURE_COLUMNS,
            "model_name": best_payload["model_name"],
        },
        MODEL_PATH,
    )
    joblib.dump(
        {
            "summary": {
                "dataset_size": int(len(df)),
                "feature_count": len(FEATURE_COLUMNS),
                "class_count": int(df["label"].nunique()),
                "best_model": best_payload["model_name"],
            },
            "models": model_scores,
            "confusion_matrix": confusion,
            "class_labels": encoder.classes_.tolist(),
            "classification_report": classification,
        },
        ARTIFACTS_PATH,
    )
    artifacts = joblib.load(ARTIFACTS_PATH)
    persist_training_artifacts(artifacts)
    return TrainingResult(
        summary=artifacts["summary"],
        models=artifacts["models"],
        confusion_matrix=artifacts["confusion_matrix"],
    )


def ensure_trained() -> None:
    if not MODEL_PATH.exists() or not ARTIFACTS_PATH.exists():
        train_models()


def model_artifacts() -> Dict:
    latest_run = TrainingRun.query.order_by(TrainingRun.created_at.desc()).first()
    if latest_run:
        return {
            "summary": {
                "dataset_size": latest_run.dataset_size,
                "feature_count": latest_run.feature_count,
                "class_count": latest_run.class_count,
                "best_model": latest_run.best_model,
            },
            "models": [metric.to_dict() for metric in latest_run.metrics],
            "confusion_matrix": latest_run.confusion_matrix,
            "class_labels": latest_run.class_labels,
            "classification_report": latest_run.classification_report,
            "created_at": latest_run.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
    ensure_trained()
    return joblib.load(ARTIFACTS_PATH)


def dataset_overview() -> Dict:
    df = load_dataset()
    counts = df["label"].value_counts().to_dict()
    recent_logs = DetectionLog.query.order_by(DetectionLog.created_at.desc()).limit(8).all()
    return {
        "dataset_name": "Synthetic CICIDS-style Flow Dataset",
        "records": int(len(df)),
        "features": len(FEATURE_COLUMNS),
        "attack_types": int(df["label"].nunique()),
        "class_distribution": counts,
        "feature_columns": FEATURE_COLUMNS,
        "preview": df.head(8).to_dict(orient="records"),
        "recent_detections": [item.to_dict() for item in recent_logs],
    }


def risk_level(label: str) -> str:
    mapping = {
        "BENIGN": "低",
        "WebAttack": "中",
        "PortScan": "中",
        "Bot": "高",
        "BruteForce": "高",
        "DoS": "高",
    }
    return mapping.get(label, "中")


def mitigation_advice(label: str) -> str:
    mapping = {
        "BENIGN": "保持监测即可，无需人工处置。",
        "DoS": "建议限流并封禁异常源IP，检查网关与防火墙策略。",
        "PortScan": "建议触发主机侧审计，屏蔽高频探测源并核查暴露端口。",
        "Bot": "建议隔离异常终端，检查外联地址并执行恶意程序扫描。",
        "BruteForce": "建议启用验证码和登录频率限制，检查弱口令账号。",
        "WebAttack": "建议联动WAF日志排查恶意请求，并核查Web服务漏洞。",
    }
    return mapping.get(label, "建议人工复核异常流量。")


def predict(features: Dict) -> Dict:
    ensure_trained()
    payload = joblib.load(MODEL_PATH)
    model = payload["model"]
    encoder = payload["label_encoder"]
    ordered = [float(features[column]) for column in payload["feature_columns"]]
    arr = pd.DataFrame([ordered], columns=payload["feature_columns"])
    pred_encoded = model.predict(arr)[0]
    label = encoder.inverse_transform([pred_encoded])[0]
    if hasattr(model, "predict_proba"):
        confidence = float(np.max(model.predict_proba(arr)[0]))
    else:
        confidence = 0.82
    return {
        "label": label,
        "description": ATTACK_DESCRIPTIONS[label],
        "risk_level": risk_level(label),
        "confidence": round(confidence, 4),
        "advice": mitigation_advice(label),
        "features": {key: float(value) for key, value in features.items()},
    }


def persist_training_artifacts(artifacts: Dict | None = None) -> TrainingRun:
    if artifacts is None:
        artifacts = joblib.load(ARTIFACTS_PATH)

    training_run = TrainingRun(
        best_model=artifacts["summary"]["best_model"],
        dataset_size=artifacts["summary"]["dataset_size"],
        feature_count=artifacts["summary"]["feature_count"],
        class_count=artifacts["summary"]["class_count"],
        class_labels=artifacts["class_labels"],
        confusion_matrix=artifacts["confusion_matrix"],
        classification_report=artifacts["classification_report"],
    )
    db.session.add(training_run)
    db.session.flush()

    metrics = [
        ModelMetric(
            training_run_id=training_run.id,
            model_name=item["name"],
            accuracy=item["accuracy"],
            precision=item["precision"],
            recall=item["recall"],
            f1_score=item["f1_score"],
        )
        for item in artifacts["models"]
    ]
    db.session.add_all(metrics)
    db.session.commit()
    return training_run


def save_detection(result: Dict) -> tuple[DetectionLog, Alert | None]:
    detection = DetectionLog(
        label=result["label"],
        risk_level=result["risk_level"],
        confidence=result["confidence"],
        description=result["description"],
        advice=result["advice"],
        features=result["features"],
    )
    db.session.add(detection)
    db.session.flush()

    alert = None
    if result["label"] != "BENIGN":
        alert = Alert(
            detection_log_id=detection.id,
            title=f"{result['label']} 异常事件",
            risk_level=result["risk_level"],
            confidence=result["confidence"],
            advice=result["advice"],
        )
        db.session.add(alert)

    db.session.commit()
    return detection, alert
