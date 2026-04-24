from __future__ import annotations

from ..extensions import db
from ..models import SystemSetting

DEFAULT_SETTINGS = {
    "site_name": ("通信网络异常检测与智能告警系统", "系统名称"),
    "auto_train_after_import": ("true", "数据导入后是否自动触发训练"),
    "alert_confidence_threshold": ("0.70", "生成告警的最低置信度阈值"),
    "default_dataset_source": ("cicids2017", "默认数据集来源"),
    "allow_sqlite_fallback": ("true", "未配置 MySQL 时是否允许使用 SQLite"),
    "incident_auto_escalation": ("true", "高风险告警是否自动升级为安全事件"),
    "stream_detection_window": ("12", "实时流模拟检测窗口大小"),
    "conformal_significance": ("0.10", "Conformal 可信校准显著性水平"),
    "deep_detector_quantile": ("0.95", "Deep SVDD 异常阈值分位数"),
    "deepseek_enabled": ("false", "DeepSeek 智能研判开关，配置 DEEPSEEK_API_KEY 后可启用在线能力"),
    "deepseek_model": ("deepseek-chat", "DeepSeek 在线研判模型名称"),
}


def ensure_default_settings() -> None:
    existing_items = {item.setting_key: item for item in SystemSetting.query.all()}
    for key, (value, description) in DEFAULT_SETTINGS.items():
        if key in existing_items:
            item = existing_items[key]
            if item.description != description or "?" in (item.setting_value or ""):
                item.description = description
                if "?" in (item.setting_value or ""):
                    item.setting_value = value
            continue
        db.session.add(SystemSetting(setting_key=key, setting_value=value, description=description))
    db.session.commit()


def get_settings() -> list[dict]:
    ensure_default_settings()
    return [item.to_dict() for item in SystemSetting.query.order_by(SystemSetting.setting_key.asc()).all()]


def update_settings(payload: dict) -> list[dict]:
    ensure_default_settings()
    for key, value in payload.items():
        item = SystemSetting.query.filter_by(setting_key=key).first()
        if item:
            item.setting_value = str(value)
    db.session.commit()
    return get_settings()


def get_setting_map() -> dict[str, str]:
    ensure_default_settings()
    return {item.setting_key: item.setting_value for item in SystemSetting.query.all()}
