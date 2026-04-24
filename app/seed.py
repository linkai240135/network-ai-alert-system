from __future__ import annotations

from datetime import datetime

from .database import db
from .ml import ensure_dataset, ensure_trained
from .models import DatasetRecord, TrainingRun


def bootstrap_database() -> None:
    if DatasetRecord.query.count() == 0:
        df = ensure_dataset()
        records = [
            DatasetRecord(
                source="synthetic-cicids-style",
                label=item["label"],
                flow_duration=item["flow_duration"],
                packet_rate=item["packet_rate"],
                byte_rate=item["byte_rate"],
                syn_rate=item["syn_rate"],
                dst_port_entropy=item["dst_port_entropy"],
                failed_login_rate=item["failed_login_rate"],
                request_interval_std=item["request_interval_std"],
                payload_mean=item["payload_mean"],
                created_at=datetime.utcnow(),
            )
            for item in df.to_dict(orient="records")
        ]
        db.session.add_all(records)
        db.session.commit()

    ensure_trained()

    if TrainingRun.query.count() == 0:
        from .ml import persist_training_artifacts

        persist_training_artifacts()
