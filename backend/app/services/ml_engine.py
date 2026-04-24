from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from xgboost import DMatrix, XGBClassifier

from ..utils.constants import (
    ALERT_TRIGGER_THRESHOLD,
    ATTACK_DESCRIPTIONS,
    ATTACK_STAGES,
    FEATURE_COLUMNS,
    FEATURE_LABELS,
    MITIGATION_ADVICE,
    RISK_LEVELS,
    SERVICE_PROFILES,
    UNKNOWN_ANOMALY_THRESHOLD,
)

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
MODEL_DIR = ROOT_DIR / "models"
DATASET_PATH = DATA_DIR / "network_flows.csv"
MODEL_PATH = MODEL_DIR / "best_model.joblib"
ARTIFACTS_PATH = MODEL_DIR / "training_artifacts.joblib"
MAX_TRAINING_ROWS = 240000
MAX_DEEP_MODEL_ROWS = 120000
CALIBRATION_SIGNIFICANCE = 0.10
DEEP_SVDD_SCORE_SCALE = 1000.0


@dataclass
class TrainingArtifacts:
    summary: dict
    models: list[dict]
    class_labels: list[str]
    confusion_matrix: list[list[int]]
    classification_report: dict


class TabularTransformerBlock(nn.Module):
    def __init__(self, embed_dim: int, num_heads: int, hidden_dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.attention = nn.MultiheadAttention(embed_dim=embed_dim, num_heads=num_heads, dropout=dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(embed_dim)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.feed_forward = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embed_dim),
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, tokens: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        attended, attention_weights = self.attention(tokens, tokens, tokens, need_weights=True, average_attn_weights=False)
        tokens = self.norm1(tokens + self.dropout(attended))
        feed_forward = self.feed_forward(tokens)
        tokens = self.norm2(tokens + self.dropout(feed_forward))
        return tokens, attention_weights


class FTTransformerClassifier(nn.Module):
    def __init__(
        self,
        feature_count: int,
        class_count: int,
        embed_dim: int = 48,
        num_heads: int = 4,
        hidden_dim: int = 96,
        depth: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.feature_embedding = nn.Parameter(torch.randn(feature_count, embed_dim) * 0.02)
        self.value_weight = nn.Parameter(torch.randn(feature_count, embed_dim) * 0.02)
        self.value_bias = nn.Parameter(torch.zeros(feature_count, embed_dim))
        self.cls_token = nn.Parameter(torch.randn(1, 1, embed_dim) * 0.02)
        self.blocks = nn.ModuleList(
            [TabularTransformerBlock(embed_dim=embed_dim, num_heads=num_heads, hidden_dim=hidden_dim, dropout=dropout) for _ in range(depth)]
        )
        self.norm = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, class_count)

    def forward(self, values: torch.Tensor, return_attention: bool = False):
        tokens = self.feature_embedding.unsqueeze(0) + values.unsqueeze(-1) * self.value_weight.unsqueeze(0) + self.value_bias.unsqueeze(0)
        cls_token = self.cls_token.expand(values.size(0), -1, -1)
        tokens = torch.cat([cls_token, tokens], dim=1)
        attentions: list[torch.Tensor] = []
        for block in self.blocks:
            tokens, attention = block(tokens)
            attentions.append(attention)
        logits = self.head(self.norm(tokens[:, 0]))
        if return_attention:
            return logits, attentions
        return logits


class DeepSVDDEncoder(nn.Module):
    def __init__(self, input_dim: int, latent_dim: int = 8) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, latent_dim),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.network(values)


def ensure_local_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def generate_dataset(samples_per_class: int = 300) -> pd.DataFrame:
    ensure_local_dirs()
    if DATASET_PATH.exists():
        return pd.read_csv(DATASET_PATH)

    generator = np.random.default_rng(42)
    rows = []
    profiles = {
        "BENIGN": dict(flow_duration=(60, 420), packet_rate=(20, 140), byte_rate=(500, 5000), syn_rate=(0.01, 0.08), dst_port_entropy=(0.1, 0.35), failed_login_rate=(0.0, 0.04), request_interval_std=(0.2, 1.2), payload_mean=(300, 1100)),
        "DoS": dict(flow_duration=(10, 120), packet_rate=(400, 1300), byte_rate=(12000, 45000), syn_rate=(0.45, 0.95), dst_port_entropy=(0.05, 0.18), failed_login_rate=(0.0, 0.1), request_interval_std=(0.01, 0.18), payload_mean=(80, 360)),
        "PortScan": dict(flow_duration=(20, 150), packet_rate=(140, 500), byte_rate=(1800, 8500), syn_rate=(0.35, 0.75), dst_port_entropy=(0.72, 0.98), failed_login_rate=(0.0, 0.08), request_interval_std=(0.03, 0.35), payload_mean=(60, 240)),
        "Bot": dict(flow_duration=(150, 600), packet_rate=(80, 280), byte_rate=(2500, 9000), syn_rate=(0.1, 0.4), dst_port_entropy=(0.3, 0.65), failed_login_rate=(0.02, 0.15), request_interval_std=(0.4, 1.8), payload_mean=(180, 700)),
        "BruteForce": dict(flow_duration=(40, 260), packet_rate=(50, 240), byte_rate=(1200, 7000), syn_rate=(0.08, 0.35), dst_port_entropy=(0.08, 0.22), failed_login_rate=(0.55, 0.98), request_interval_std=(0.02, 0.25), payload_mean=(90, 300)),
        "WebAttack": dict(flow_duration=(30, 280), packet_rate=(40, 220), byte_rate=(1500, 14000), syn_rate=(0.05, 0.22), dst_port_entropy=(0.2, 0.55), failed_login_rate=(0.02, 0.2), request_interval_std=(0.06, 0.55), payload_mean=(450, 1800)),
    }

    for label, config in profiles.items():
        for _ in range(samples_per_class):
            record = {feature_name: round(generator.uniform(*bounds), 4) for feature_name, bounds in config.items()}
            record["label"] = label
            rows.append(record)

    frame = pd.DataFrame(rows)
    frame.to_csv(DATASET_PATH, index=False)
    return frame


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _sample_training_frame(frame: pd.DataFrame, max_rows: int) -> tuple[pd.DataFrame, int, bool]:
    original_size = len(frame)
    if original_size <= max_rows:
        return frame.copy(), original_size, False

    sampled_parts = []
    for label_name, group in frame.groupby("label"):
        sample_size = max(1, int(round(max_rows * len(group) / original_size)))
        sampled_group = group.sample(n=sample_size, random_state=42).copy()
        sampled_group["label"] = label_name
        sampled_parts.append(sampled_group)
    sampled = pd.concat(sampled_parts, ignore_index=True)
    return sampled, original_size, True


def _feature_statistics(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    statistics = {}
    for feature_name in FEATURE_COLUMNS:
        statistics[feature_name] = {
            "mean": float(frame[feature_name].mean()),
            "std": float(frame[feature_name].std() or 1.0),
            "q1": float(frame[feature_name].quantile(0.25)),
            "q3": float(frame[feature_name].quantile(0.75)),
        }
    return statistics


def _candidate_models(class_count: int) -> list[tuple[str, object]]:
    return [
        (
            "XGBoost",
            XGBClassifier(
                n_estimators=260,
                max_depth=8,
                learning_rate=0.07,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="multi:softprob" if class_count > 2 else "binary:logistic",
                eval_metric="mlogloss" if class_count > 2 else "logloss",
                tree_method="hist",
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "LightGBM",
            LGBMClassifier(
                n_estimators=260,
                learning_rate=0.07,
                num_leaves=63,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="multiclass" if class_count > 2 else "binary",
                random_state=42,
                n_jobs=-1,
                verbosity=-1,
            ),
        ),
        (
            "Logistic Regression",
            Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=3000)),
            ]),
        ),
    ]


def _build_tensor_loader(features: np.ndarray, labels: np.ndarray, batch_size: int = 1024, shuffle: bool = True) -> DataLoader:
    dataset = TensorDataset(torch.tensor(features, dtype=torch.float32), torch.tensor(labels, dtype=torch.long))
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def _evaluate_predictions(true_labels: np.ndarray, pred_labels: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": round(float(accuracy_score(true_labels, pred_labels)), 4),
        "precision": round(float(precision_score(true_labels, pred_labels, average="weighted", zero_division=0)), 4),
        "recall": round(float(recall_score(true_labels, pred_labels, average="weighted", zero_division=0)), 4),
        "f1_score": round(float(f1_score(true_labels, pred_labels, average="weighted", zero_division=0)), 4),
    }


def _train_ft_transformer(train_features: np.ndarray, train_labels: np.ndarray, calibration_features: np.ndarray, calibration_labels: np.ndarray, class_count: int) -> dict[str, Any]:
    scaler = StandardScaler()
    scaled_train = scaler.fit_transform(train_features)
    scaled_calibration = scaler.transform(calibration_features)
    device = _device()
    model = FTTransformerClassifier(feature_count=len(FEATURE_COLUMNS), class_count=class_count).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    train_loader = _build_tensor_loader(scaled_train, train_labels, batch_size=1024, shuffle=True)
    calibration_inputs = torch.tensor(scaled_calibration, dtype=torch.float32, device=device)
    best_state = None
    best_f1 = -1.0

    for _ in range(8):
        model.train()
        for batch_inputs, batch_labels in train_loader:
            batch_inputs = batch_inputs.to(device)
            batch_labels = batch_labels.to(device)
            optimizer.zero_grad()
            logits = model(batch_inputs)
            loss = criterion(logits, batch_labels)
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            calibration_logits = model(calibration_inputs)
            calibration_pred = calibration_logits.argmax(dim=1).cpu().numpy()
        calibration_f1 = f1_score(calibration_labels, calibration_pred, average="weighted", zero_division=0)
        if calibration_f1 > best_f1:
            best_f1 = calibration_f1
            best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}

    if best_state:
        model.load_state_dict(best_state)

    return {
        "state_dict": {key: value.cpu() for key, value in model.state_dict().items()},
        "scaler": scaler,
        "config": {"feature_count": len(FEATURE_COLUMNS), "class_count": class_count},
    }


def _predict_ft_probabilities(bundle: dict[str, Any], features: np.ndarray) -> np.ndarray:
    scaler: StandardScaler = bundle["scaler"]
    model = FTTransformerClassifier(**bundle["config"])
    model.load_state_dict(bundle["state_dict"])
    model.eval()
    inputs = torch.tensor(scaler.transform(features), dtype=torch.float32)
    with torch.no_grad():
        logits = model(inputs)
        probabilities = torch.softmax(logits, dim=1).cpu().numpy()
    return probabilities


def _compute_attention_contributions(bundle: dict[str, Any], features: pd.DataFrame) -> tuple[np.ndarray, str]:
    scaler: StandardScaler = bundle["scaler"]
    model = FTTransformerClassifier(**bundle["config"])
    model.load_state_dict(bundle["state_dict"])
    model.eval()
    scaled = scaler.transform(features)
    inputs = torch.tensor(scaled, dtype=torch.float32, requires_grad=True)
    logits, attentions = model(inputs, return_attention=True)
    predicted_index = int(torch.argmax(logits[0]).item())
    logits[0, predicted_index].backward()
    gradients = inputs.grad[0].detach().abs().numpy()
    if attentions:
        stacked_attention = torch.stack(attentions)
        cls_attention = stacked_attention.mean(dim=(0, 2))[0, 0, 1:].detach().cpu().numpy()
    else:
        cls_attention = np.ones(len(FEATURE_COLUMNS), dtype=float)
    combined = np.abs(gradients) + np.abs(cls_attention)
    if combined.sum() == 0:
        combined = np.ones(len(FEATURE_COLUMNS), dtype=float)
    return combined / combined.sum(), "Attention rollout + gradient attribution"


def _train_deep_svdd(benign_train: np.ndarray, benign_eval: np.ndarray, attack_eval: np.ndarray) -> dict[str, Any]:
    scaler = StandardScaler()
    scaled_train = scaler.fit_transform(benign_train)
    scaled_benign_eval = scaler.transform(benign_eval)
    scaled_attack_eval = scaler.transform(attack_eval) if len(attack_eval) else np.empty((0, len(FEATURE_COLUMNS)))
    device = _device()
    encoder = DeepSVDDEncoder(input_dim=len(FEATURE_COLUMNS)).to(device)
    optimizer = torch.optim.Adam(encoder.parameters(), lr=1e-3, weight_decay=1e-5)
    train_loader = DataLoader(TensorDataset(torch.tensor(scaled_train, dtype=torch.float32)), batch_size=1024, shuffle=True)

    encoder.eval()
    with torch.no_grad():
        center = encoder(torch.tensor(scaled_train[: min(len(scaled_train), 4096)], dtype=torch.float32, device=device)).mean(dim=0).detach()

    for _ in range(8):
        encoder.train()
        for (batch_inputs,) in train_loader:
            batch_inputs = batch_inputs.to(device)
            optimizer.zero_grad()
            embeddings = encoder(batch_inputs)
            loss = torch.mean(torch.sum((embeddings - center) ** 2, dim=1))
            loss.backward()
            optimizer.step()

    encoder.eval()
    with torch.no_grad():
        benign_scores = (
            torch.sum((encoder(torch.tensor(scaled_benign_eval, dtype=torch.float32, device=device)) - center) ** 2, dim=1).cpu().numpy()
            * DEEP_SVDD_SCORE_SCALE
        )
        attack_scores = (
            torch.sum((encoder(torch.tensor(scaled_attack_eval, dtype=torch.float32, device=device)) - center) ** 2, dim=1).cpu().numpy()
            * DEEP_SVDD_SCORE_SCALE
            if len(scaled_attack_eval)
            else np.asarray([])
        )

    candidate_quantiles = [0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98]
    candidates = []
    for quantile in candidate_quantiles:
        threshold = float(np.quantile(benign_scores, quantile)) if len(benign_scores) else 1.0
        benign_recall = float(np.mean(benign_scores <= threshold)) if len(benign_scores) else 1.0
        attack_recall = float(np.mean(attack_scores > threshold)) if len(attack_scores) else 0.0
        candidates.append(((benign_recall + attack_recall) / 2, threshold, benign_recall, attack_recall, quantile))
    _, threshold, benign_recall, attack_recall, selected_quantile = max(candidates, key=lambda item: item[0])
    baseline = float(np.median(benign_scores)) if len(benign_scores) else 0.0
    score_spread = max(float(np.std(benign_scores)), 1e-6)
    return {
        "scaler": scaler,
        "state_dict": {key: value.cpu() for key, value in encoder.state_dict().items()},
        "config": {"input_dim": len(FEATURE_COLUMNS), "latent_dim": 8},
        "center": center.cpu().numpy(),
        "threshold": threshold,
        "baseline": baseline,
        "score_spread": score_spread,
        "metrics": {
            "threshold": round(threshold, 6),
            "benign_baseline": round(baseline, 6),
            "benign_recall": round(benign_recall, 4),
            "attack_recall": round(attack_recall, 4),
            "selected_quantile": round(selected_quantile, 4),
            "score_spread": round(score_spread, 6),
        },
    }


def _score_deep_svdd(bundle: dict[str, Any], features: np.ndarray) -> np.ndarray:
    encoder = DeepSVDDEncoder(**bundle["config"])
    encoder.load_state_dict(bundle["state_dict"])
    encoder.eval()
    scaled = bundle["scaler"].transform(features)
    center = torch.tensor(bundle["center"], dtype=torch.float32)
    with torch.no_grad():
        embeddings = encoder(torch.tensor(scaled, dtype=torch.float32))
    scores = torch.sum((embeddings - center) ** 2, dim=1).cpu().numpy() * DEEP_SVDD_SCORE_SCALE
    return scores


def _build_conformal_scores(probabilities: np.ndarray, true_labels: np.ndarray) -> np.ndarray:
    return 1.0 - probabilities[np.arange(len(true_labels)), true_labels]


def _conformal_inference(bundle: dict[str, Any], probabilities: np.ndarray) -> tuple[float, list[str], bool, str]:
    predicted_index = int(np.argmax(probabilities))
    predicted_prob = float(probabilities[predicted_index])
    nonconformity = 1.0 - predicted_prob
    calibration_scores = np.asarray(bundle["scores"], dtype=float)
    p_value = float((np.sum(calibration_scores >= nonconformity) + 1) / (len(calibration_scores) + 1))
    prediction_set = []
    label_encoder: LabelEncoder = bundle["label_encoder"]
    for label_index, probability in enumerate(probabilities):
        candidate_nonconformity = 1.0 - float(probability)
        candidate_p = float((np.sum(calibration_scores >= candidate_nonconformity) + 1) / (len(calibration_scores) + 1))
        if candidate_p > bundle["significance"]:
            prediction_set.append(label_encoder.classes_[label_index])
    requires_review = p_value < max(bundle["significance"], 0.12) or len(prediction_set) > 2
    if p_value >= 0.40:
        uncertainty_level = "low"
    elif p_value >= 0.18:
        uncertainty_level = "medium"
    else:
        uncertainty_level = "high"
    return p_value, prediction_set, requires_review, uncertainty_level


def _feature_importance_map(model: object) -> dict[str, float]:
    estimator = model.named_steps["clf"] if isinstance(model, Pipeline) else model
    if hasattr(estimator, "feature_importances_"):
        raw = np.asarray(estimator.feature_importances_, dtype=float)
    elif hasattr(estimator, "coef_"):
        raw = np.mean(np.abs(np.asarray(estimator.coef_, dtype=float)), axis=0)
    else:
        raw = np.ones(len(FEATURE_COLUMNS), dtype=float)
    if raw.sum() == 0:
        raw = np.ones(len(FEATURE_COLUMNS), dtype=float)
    weights = raw / raw.sum()
    return {feature_name: float(weight) for feature_name, weight in zip(FEATURE_COLUMNS, weights)}


def _model_contribution_values(model: object, features: pd.DataFrame, predicted_index: int) -> tuple[np.ndarray, str]:
    estimator = model.named_steps["clf"] if isinstance(model, Pipeline) else model
    class_count = len(getattr(estimator, "classes_", [])) or 1
    try:
        if isinstance(estimator, XGBClassifier):
            booster = estimator.get_booster()
            contributions = booster.predict(DMatrix(features, feature_names=FEATURE_COLUMNS), pred_contribs=True)
            values = np.asarray(contributions)[0]
            width = len(FEATURE_COLUMNS) + 1
            if values.shape[0] == width * class_count:
                values = values.reshape(class_count, width)[predicted_index]
            return values[:-1], "TreeSHAP"
        if isinstance(estimator, LGBMClassifier):
            booster = estimator.booster_
            contributions = booster.predict(features, pred_contrib=True)
            values = np.asarray(contributions)[0]
            width = len(FEATURE_COLUMNS) + 1
            if values.shape[0] == width * class_count:
                values = values.reshape(class_count, width)[predicted_index]
            return values[:-1], "TreeSHAP"
        if isinstance(model, Pipeline):
            scaler = model.named_steps["scaler"]
            classifier = model.named_steps["clf"]
            scaled = scaler.transform(features)[0]
            coefficients = classifier.coef_[predicted_index if classifier.coef_.ndim > 1 and predicted_index < classifier.coef_.shape[0] else 0]
            return scaled * coefficients, "Linear contribution"
    except Exception:
        pass
    return np.zeros(len(FEATURE_COLUMNS), dtype=float), "Statistical deviation"


def _normalize_contributions(contributions: np.ndarray, feature_stats: dict[str, dict[str, float]], features: dict[str, float]) -> dict[str, float]:
    raw = np.abs(np.asarray(contributions, dtype=float))
    if raw.shape[0] != len(FEATURE_COLUMNS):
        raw = np.zeros(len(FEATURE_COLUMNS), dtype=float)
    if raw.sum() == 0:
        fallback = []
        for feature_name in FEATURE_COLUMNS:
            stats = feature_stats.get(feature_name, {})
            mean = float(stats.get("mean", 0))
            std = float(stats.get("std", 1) or 1)
            value = float(features.get(feature_name, 0))
            fallback.append(abs((value - mean) / std))
        raw = np.asarray(fallback, dtype=float)
    if raw.sum() == 0:
        raw = np.ones(len(FEATURE_COLUMNS), dtype=float)
    weights = raw / raw.sum()
    return {feature_name: float(weight) for feature_name, weight in zip(FEATURE_COLUMNS, weights)}


def _infer_service_profile(features: dict[str, float], predicted_label: str) -> dict[str, Any]:
    packet_rate = float(features.get("packet_rate", 0))
    payload_mean = float(features.get("payload_mean", 0))
    failed_login_rate = float(features.get("failed_login_rate", 0))
    syn_rate = float(features.get("syn_rate", 0))
    if predicted_label == "PortScan":
        profile = SERVICE_PROFILES[2]
    elif predicted_label == "BruteForce" or failed_login_rate > 0.4:
        profile = SERVICE_PROFILES[2]
    elif predicted_label == "DoS" or syn_rate > 0.6:
        profile = SERVICE_PROFILES[0] if payload_mean < 500 else SERVICE_PROFILES[1]
    elif packet_rate < 90 and payload_mean < 250:
        profile = SERVICE_PROFILES[3]
    elif payload_mean > 900:
        profile = SERVICE_PROFILES[5]
    elif payload_mean > 450:
        profile = SERVICE_PROFILES[1]
    else:
        profile = SERVICE_PROFILES[0]
    return dict(profile)


def _build_explanation(features: dict[str, float], feature_stats: dict[str, dict[str, float]], model_contributions: dict[str, float], explanation_method: str) -> list[dict[str, Any]]:
    explanation = []
    for feature_name in FEATURE_COLUMNS:
        value = float(features.get(feature_name, 0))
        stats = feature_stats.get(feature_name, {})
        mean = float(stats.get("mean", 0))
        std = float(stats.get("std", 1) or 1)
        q1 = float(stats.get("q1", mean))
        q3 = float(stats.get("q3", mean))
        z_score = abs((value - mean) / std) if std else 0.0
        contribution = float(model_contributions.get(feature_name, 0))
        explanation.append({
            "feature": feature_name,
            "label": FEATURE_LABELS.get(feature_name, feature_name),
            "value": round(value, 4),
            "baseline": round(mean, 4),
            "z_score": round(z_score, 4),
            "importance": round(contribution, 4),
            "contribution": round(contribution, 4),
            "direction": "偏高" if value >= mean else "偏低",
            "is_abnormal": value < q1 or value > q3,
            "explanation_method": explanation_method,
        })
    explanation.sort(key=lambda item: item["contribution"], reverse=True)
    return explanation[:4]


def _dynamic_advice(label: str, stage: str, top_features: list[dict[str, Any]], service_profile: dict[str, Any], confidence: float, detector_flag: bool, conformal_p_value: float, requires_review: bool) -> list[str]:
    advice = [f"当前样本处于“{stage}”，建议优先围绕 {service_profile['protocol']}/{service_profile['port']} 服务开展排查。"]
    if top_features:
        feature_text = "、".join(f"{item['label']}{item['direction']}" for item in top_features[:2])
        advice.append(f"关键异常特征集中在 {feature_text}，可结合主机日志、应用日志和边界设备日志交叉验证。")
    if detector_flag:
        advice.append("Deep SVDD 已将该样本识别为正常流量分布之外的异常点，建议优先保留原始流量和终端侧证据。")
    if requires_review:
        advice.append(f"Conformal 可信度 p-value 为 {conformal_p_value:.3f}，当前预测不确定性较高，建议进入人工复核队列。")
    advice.append(MITIGATION_ADVICE.get(label, "建议结合上下文继续监测，并保留人工复核环节。"))
    if confidence >= 0.90 and conformal_p_value >= 0.2:
        advice.append("当前分类置信度和可信度均较高，可优先执行联动处置策略。")
    else:
        advice.append("建议先完成人工确认，再决定是否执行阻断、限流或隔离操作。")
    return advice


def _choose_production_model(results: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_results = sorted(results, key=lambda item: item["f1_score"], reverse=True)
    best_result = sorted_results[0]
    ft_result = next((item for item in results if item["name"] == "FT-Transformer"), None)
    if ft_result and ft_result["f1_score"] >= 0.92:
        return ft_result
    return best_result


def train(frame: pd.DataFrame) -> TrainingArtifacts:
    ensure_local_dirs()
    sampled_frame, original_size, sampled_training = _sample_training_frame(frame, MAX_TRAINING_ROWS)
    deep_frame, _, sampled_deep = _sample_training_frame(sampled_frame, MAX_DEEP_MODEL_ROWS)
    feature_stats = _feature_statistics(sampled_frame)

    x_all = sampled_frame[FEATURE_COLUMNS]
    label_encoder = LabelEncoder()
    encoded_all = label_encoder.fit_transform(sampled_frame["label"])

    x_train_all, x_test, y_train_all, y_test = train_test_split(x_all, encoded_all, test_size=0.25, random_state=42, stratify=encoded_all)
    x_train, x_calibration, y_train, y_calibration = train_test_split(x_train_all, y_train_all, test_size=0.18, random_state=42, stratify=y_train_all)

    results: list[dict[str, Any]] = []
    fitted_models: dict[str, Any] = {}
    class_count = len(np.unique(encoded_all))

    for model_name, model in _candidate_models(class_count):
        model.fit(x_train, y_train)
        test_predictions = model.predict(x_test)
        metrics = _evaluate_predictions(y_test, test_predictions)
        metrics.update({"name": model_name, "family": "tree" if model_name != "Logistic Regression" else "linear"})
        results.append(metrics)
        fitted_models[model_name] = {
            "type": "classical",
            "model": model,
            "calibration_probabilities": model.predict_proba(x_calibration),
            "test_predictions": test_predictions,
        }

    deep_features = deep_frame[FEATURE_COLUMNS]
    deep_labels = label_encoder.transform(deep_frame["label"])
    deep_train_all, deep_holdout, deep_targets_all, deep_targets_holdout = train_test_split(deep_features, deep_labels, test_size=0.25, random_state=42, stratify=deep_labels)
    deep_fit, deep_calibration, deep_targets_fit, deep_targets_calibration = train_test_split(deep_train_all, deep_targets_all, test_size=0.18, random_state=42, stratify=deep_targets_all)
    ft_bundle = _train_ft_transformer(deep_fit.to_numpy(), deep_targets_fit, deep_calibration.to_numpy(), deep_targets_calibration, class_count)
    ft_probabilities = _predict_ft_probabilities(ft_bundle, deep_holdout.to_numpy())
    ft_predictions = ft_probabilities.argmax(axis=1)
    ft_metrics = _evaluate_predictions(deep_targets_holdout, ft_predictions)
    ft_metrics.update({"name": "FT-Transformer", "family": "deep-tabular"})
    results.append(ft_metrics)
    fitted_models["FT-Transformer"] = {
        "type": "ft_transformer",
        "bundle": ft_bundle,
        "calibration_probabilities": _predict_ft_probabilities(ft_bundle, x_calibration.to_numpy()),
        "test_predictions": _predict_ft_probabilities(ft_bundle, x_test.to_numpy()).argmax(axis=1),
    }

    production_result = _choose_production_model(results)
    production_name = production_result["name"]
    benchmark_best = max(results, key=lambda item: item["f1_score"])
    production_payload = fitted_models[production_name]
    if production_payload["type"] == "classical":
        production_model = production_payload["model"]
        production_test_predictions = production_payload["test_predictions"]
        calibration_probabilities = production_payload["calibration_probabilities"]
        production_model_payload = {"kind": "classical", "model": production_model}
        explanation_engine = "TreeSHAP"
    else:
        production_model = production_payload["bundle"]
        production_test_predictions = _predict_ft_probabilities(production_model, x_test.to_numpy()).argmax(axis=1)
        calibration_probabilities = production_payload["calibration_probabilities"]
        production_model_payload = {"kind": "ft_transformer", "bundle": production_model}
        explanation_engine = "Attention rollout + gradient attribution"

    conformal_scores = _build_conformal_scores(calibration_probabilities, y_calibration)
    benign_index = int(np.where(label_encoder.classes_ == "BENIGN")[0][0]) if "BENIGN" in label_encoder.classes_ else None
    benign_train = x_train[y_train == benign_index] if benign_index is not None else x_train
    benign_eval = x_calibration[y_calibration == benign_index] if benign_index is not None else x_calibration
    attack_eval = x_calibration[y_calibration != benign_index] if benign_index is not None else x_calibration.iloc[:0]
    deep_svdd_bundle = _train_deep_svdd(benign_train.to_numpy(), benign_eval.to_numpy(), attack_eval.to_numpy())

    confusion = confusion_matrix(y_test, production_test_predictions).tolist()
    report = classification_report(y_test, production_test_predictions, target_names=label_encoder.classes_, output_dict=True, zero_division=0)

    summary = {
        "dataset_size": int(len(sampled_frame)),
        "source_dataset_size": int(original_size),
        "feature_count": len(FEATURE_COLUMNS),
        "class_count": int(sampled_frame["label"].nunique()),
        "best_model": production_name,
        "benchmark_best_model": benchmark_best["name"],
        "sampled_training": sampled_training,
        "sampled_deep_training": sampled_deep,
        "unknown_threshold": UNKNOWN_ANOMALY_THRESHOLD,
        "alert_threshold": ALERT_TRIGGER_THRESHOLD,
        "detector_name": "DeepSVDD",
        "detector_metrics": deep_svdd_bundle["metrics"],
        "conformal_significance": CALIBRATION_SIGNIFICANCE,
        "explanation_engine": explanation_engine,
        "primary_story": "FT-Transformer known attack classification + Deep SVDD unknown anomaly detection + conformal confidence calibration",
        "innovation_stack": [
            "FT-Transformer deep tabular classifier",
            "Deep SVDD unknown anomaly detector",
            "Conformal uncertainty calibration",
            "Attention-based explanation and feedback retraining",
        ],
    }

    joblib.dump({
        "model_name": production_name,
        "benchmark_best_model": benchmark_best["name"],
        "label_encoder": label_encoder,
        "feature_columns": FEATURE_COLUMNS,
        "feature_statistics": feature_stats,
        "production_model": production_model_payload,
        "deep_svdd": deep_svdd_bundle,
        "conformal": {"scores": conformal_scores, "significance": CALIBRATION_SIGNIFICANCE, "label_encoder": label_encoder},
        "feature_importances": _feature_importance_map(fitted_models["XGBoost"]["model"]),
        "detector_metrics": deep_svdd_bundle["metrics"],
    }, MODEL_PATH)

    payload = {
        "summary": summary,
        "models": results,
        "class_labels": label_encoder.classes_.tolist(),
        "confusion_matrix": confusion,
        "classification_report": report,
    }
    joblib.dump(payload, ARTIFACTS_PATH)
    return TrainingArtifacts(**payload)


def _predict_from_production_model(payload: dict[str, Any], features: pd.DataFrame) -> tuple[np.ndarray, str, np.ndarray, str]:
    production_model = payload["production_model"]
    if production_model["kind"] == "classical":
        model = production_model["model"]
        probabilities = model.predict_proba(features)[0]
        predicted_index = int(np.argmax(probabilities))
        contributions, method = _model_contribution_values(model, features, predicted_index)
        return probabilities, payload["model_name"], contributions, method
    bundle = production_model["bundle"]
    probabilities = _predict_ft_probabilities(bundle, features.to_numpy())[0]
    contributions, method = _compute_attention_contributions(bundle, features)
    return probabilities, payload["model_name"], contributions, method


def predict(features: dict[str, float]) -> dict[str, Any]:
    if not MODEL_PATH.exists():
        train(generate_dataset())
    payload = joblib.load(MODEL_PATH)
    label_encoder: LabelEncoder = payload["label_encoder"]
    feature_frame = pd.DataFrame([[float(features[feature_name]) for feature_name in payload["feature_columns"]]], columns=payload["feature_columns"])
    probabilities, classifier_name, contribution_values, explanation_method = _predict_from_production_model(payload, feature_frame)
    predicted_index = int(np.argmax(probabilities))
    raw_label = label_encoder.inverse_transform([predicted_index])[0]
    confidence = float(np.max(probabilities))

    detector_score = float(_score_deep_svdd(payload["deep_svdd"], feature_frame.to_numpy())[0])
    detector_threshold = float(payload["deep_svdd"]["threshold"])
    detector_baseline = float(payload["deep_svdd"]["baseline"])
    detector_spread = max(float(payload["deep_svdd"]["score_spread"]), 1e-6)
    detector_flag = detector_score > detector_threshold
    anomaly_score = float(1.0 / (1.0 + np.exp(-(detector_score - detector_threshold) / detector_spread)))
    conformal_p_value, prediction_set, requires_review, uncertainty_level = _conformal_inference(payload["conformal"], probabilities)

    binary_decision = "anomaly" if raw_label != "BENIGN" or detector_flag or anomaly_score >= ALERT_TRIGGER_THRESHOLD else "normal"
    unknown_flag = False
    final_label = raw_label
    if detector_flag and (raw_label == "BENIGN" or confidence < UNKNOWN_ANOMALY_THRESHOLD or conformal_p_value < CALIBRATION_SIGNIFICANCE):
        final_label = "UNKNOWN"
        unknown_flag = True
    elif requires_review and raw_label == "BENIGN" and anomaly_score >= 0.45:
        final_label = "UNKNOWN"
        unknown_flag = True

    service_profile = _infer_service_profile(features, final_label)
    contribution_map = _normalize_contributions(contribution_values, payload["feature_statistics"], features)
    top_features = _build_explanation(features, payload["feature_statistics"], contribution_map, explanation_method)
    stage = ATTACK_STAGES.get(final_label, "异常分析阶段")
    recommendations = _dynamic_advice(final_label, stage, top_features, service_profile, confidence, detector_flag, conformal_p_value, requires_review)

    return {
        "label": final_label,
        "raw_label": raw_label,
        "description": ATTACK_DESCRIPTIONS.get(final_label, "疑似异常流量"),
        "risk_level": RISK_LEVELS.get(final_label, "中"),
        "confidence": round(confidence, 4),
        "anomaly_score": round(max(anomaly_score, 1 - confidence), 4),
        "binary_decision": binary_decision,
        "attack_stage": stage,
        "unknown_flag": unknown_flag,
        "service_profile": service_profile,
        "top_features": top_features,
        "advice": recommendations[0] if recommendations else MITIGATION_ADVICE.get(final_label, "建议人工复核异常流量。"),
        "recommendations": recommendations,
        "features": {feature_name: float(value) for feature_name, value in features.items()},
        "explanation_method": explanation_method,
        "classifier_name": classifier_name,
        "detector_name": "DeepSVDD",
        "detector_score": round(detector_score, 6),
        "detector_threshold": round(detector_threshold, 6),
        "detector_baseline": round(detector_baseline, 6),
        "detector_flag": detector_flag,
        "conformal_p_value": round(conformal_p_value, 4),
        "prediction_set": prediction_set,
        "uncertainty_level": uncertainty_level,
        "requires_review": requires_review,
    }
