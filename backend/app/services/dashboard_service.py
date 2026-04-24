from __future__ import annotations

from ..models import Alert, Asset, DetectionLog, SecurityIncident
from ..utils.constants import FEATURE_COLUMNS
from .asset_service import get_asset_overview
from .dataset_service import get_dataset_overview
from .detection_service import get_alert_trends, get_service_portrait, list_alerts, list_detection_logs
from .incident_service import get_incident_board
from .training_service import get_latest_training


def build_dashboard_summary() -> dict:
    dataset = get_dataset_overview()
    training = get_latest_training()
    service_portrait = get_service_portrait()
    alert_trend = get_alert_trends()
    incident_board = get_incident_board()
    asset_overview = get_asset_overview(limit=6)

    return {
        "stats": {
            "datasetRecords": dataset["total"],
            "featureCount": len(FEATURE_COLUMNS),
            "alertCount": Alert.query.count(),
            "detectionCount": DetectionLog.query.count(),
            "unknownCount": service_portrait["unknownCount"],
            "highRiskCount": alert_trend["highRiskCount"],
            "incidentCount": SecurityIncident.query.count(),
            "assetCount": Asset.query.count(),
        },
        "dataset": dataset,
        "training": training,
        "alertTrend": alert_trend,
        "servicePortrait": service_portrait,
        "incidentBoard": incident_board,
        "assetOverview": asset_overview,
        "recentAlerts": list_alerts(limit=6),
        "recentLogs": list_detection_logs(limit=6),
        "system": {
            "architecture": [
                {"name": "frontend", "value": "Vue 3 + Vite + Element Plus + ECharts"},
                {"name": "backend", "value": "Flask REST API + Service Layer"},
                {"name": "database", "value": "MySQL / SQLite Compatible"},
                {"name": "algorithm", "value": "FT-Transformer + Deep SVDD + Conformal + Attention Explainability"},
                {"name": "capability", "value": "Data Governance + Detection + Alert + Incident + Feedback Retraining"},
            ]
        },
    }
