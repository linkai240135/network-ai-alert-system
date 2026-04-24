from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from ..extensions import db
from ..models import DatasetImportJob, DatasetRecord
from .ml_engine import generate_dataset


def bootstrap_dataset() -> None:
    if DatasetRecord.query.count() > 0:
        return
    frame = generate_dataset()
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
        )
        for item in frame.to_dict(orient="records")
    ]
    db.session.add_all(records)
    db.session.commit()


def get_dataset_frame() -> pd.DataFrame:
    if DatasetRecord.query.count() == 0:
        bootstrap_dataset()
    query = text(
        """
        SELECT flow_duration, packet_rate, byte_rate, syn_rate,
               dst_port_entropy, failed_login_rate, request_interval_std,
               payload_mean, label
        FROM dataset_records
        """
    )
    with db.engine.connect() as connection:
        rows = connection.execute(query).fetchall()
    return pd.DataFrame(
        rows,
        columns=[
            "flow_duration",
            "packet_rate",
            "byte_rate",
            "syn_rate",
            "dst_port_entropy",
            "failed_login_rate",
            "request_interval_std",
            "payload_mean",
            "label",
        ],
    )


def _source_distribution() -> dict:
    rows = (
        db.session.query(DatasetRecord.source, db.func.count(DatasetRecord.id))
        .group_by(DatasetRecord.source)
        .order_by(DatasetRecord.source.asc())
        .all()
    )
    return {source: count for source, count in rows}


def get_dataset_overview() -> dict:
    records = DatasetRecord.query.order_by(DatasetRecord.id.asc()).limit(12).all()
    total = DatasetRecord.query.count()
    distribution_rows = (
        db.session.query(DatasetRecord.label, db.func.count(DatasetRecord.id))
        .group_by(DatasetRecord.label)
        .order_by(DatasetRecord.label.asc())
        .all()
    )
    distribution = {label: count for label, count in distribution_rows}
    sources = _source_distribution()
    source_name = "CICIDS2017 Real Flow Dataset" if "cicids2017" in "".join(sources.keys()).lower() else "Synthetic CICIDS-style Flow Dataset"
    return {
        "name": source_name,
        "total": total,
        "preview": [row.to_dict() for row in records],
        "distribution": distribution,
        "source": "支持 CICIDS2017 / CSE-CIC-IDS2018 等真实流量数据导入",
        "sources": sources,
    }


def get_import_overview(limit: int = 10) -> dict:
    jobs = DatasetImportJob.query.order_by(DatasetImportJob.created_at.desc()).limit(limit).all()
    return {"items": [item.to_dict() for item in jobs]}
