from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List
import json

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ALERTS_PATH = DATA_DIR / "alerts.json"


def _read() -> List[Dict]:
    if not ALERTS_PATH.exists():
        return []
    return json.loads(ALERTS_PATH.read_text(encoding="utf-8"))


def _write(alerts: List[Dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ALERTS_PATH.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8")


def list_alerts() -> List[Dict]:
    return sorted(_read(), key=lambda item: item["created_at"], reverse=True)[:20]


def add_alert(result: Dict) -> Dict:
    alerts = _read()
    alert = {
        "id": len(alerts) + 1,
        "title": f"{result['label']} 异常事件",
        "label": result["label"],
        "risk_level": result["risk_level"],
        "confidence": result["confidence"],
        "advice": result["advice"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    alerts.append(alert)
    _write(alerts)
    return alert
