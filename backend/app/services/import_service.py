from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

from ..extensions import db
from ..models import DatasetImportJob, DatasetRecord, ModelMetric, TrainingRun

SUPPORTED_LABELS = {
    "BENIGN": "BENIGN",
    "DoS Hulk": "DoS",
    "DoS GoldenEye": "DoS",
    "DoS slowloris": "DoS",
    "DoS Slowhttptest": "DoS",
    "DDoS": "DoS",
    "PortScan": "PortScan",
    "Bot": "Bot",
    "FTP-Patator": "BruteForce",
    "SSH-Patator": "BruteForce",
    "Web Attack - Brute Force": "WebAttack",
    "Web Attack - XSS": "WebAttack",
    "Web Attack - Sql Injection": "WebAttack",
    "Infiltration": "Bot",
}


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame.columns = [column.strip() for column in frame.columns]
    return frame


def _map_labels(frame: pd.DataFrame) -> pd.DataFrame:
    label_column = "Label" if "Label" in frame.columns else "label"
    frame[label_column] = frame[label_column].astype(str).str.strip()
    frame["mapped_label"] = frame[label_column].map(SUPPORTED_LABELS)
    return frame.dropna(subset=["mapped_label"]).copy()


def _safe_col(frame: pd.DataFrame, name: str, default: float = 0.0) -> pd.Series:
    if name in frame.columns:
        return pd.to_numeric(frame[name], errors="coerce").fillna(default)
    return pd.Series(np.full(len(frame), default))


def _transform_cicids(frame: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_columns(frame)
    frame = _map_labels(frame)

    flow_duration = _safe_col(frame, "Flow Duration", 1.0).clip(lower=1.0)
    total_packets = _safe_col(frame, "Total Fwd Packets") + _safe_col(frame, "Total Backward Packets")
    total_bytes = _safe_col(frame, "Total Length of Fwd Packets") + _safe_col(frame, "Total Length of Bwd Packets")
    duration_sec = (flow_duration / 1_000_000).replace(0, 0.000001)

    result = pd.DataFrame(
        {
            "source": "cicids2017",
            "label": frame["mapped_label"],
            "flow_duration": flow_duration,
            "packet_rate": (total_packets / duration_sec).clip(lower=0),
            "byte_rate": (total_bytes / duration_sec).clip(lower=0),
            "syn_rate": (_safe_col(frame, "SYN Flag Count") / total_packets.replace(0, 1)).clip(lower=0, upper=1),
            "dst_port_entropy": (_safe_col(frame, "Destination Port", 0.0) / 65535.0).clip(lower=0, upper=1),
            "failed_login_rate": (_safe_col(frame, "Init_Win_bytes_forward") <= 0).astype(float).clip(lower=0, upper=1),
            "request_interval_std": (_safe_col(frame, "Flow IAT Std", 0.0) / 100000).clip(lower=0),
            "payload_mean": _safe_col(frame, "Average Packet Size", 0.0).clip(lower=0),
        }
    )
    return result.replace([np.inf, -np.inf], np.nan).dropna()


def _build_records(transformed: pd.DataFrame) -> list[DatasetRecord]:
    return [
        DatasetRecord(
            source=row["source"],
            label=row["label"],
            flow_duration=float(row["flow_duration"]),
            packet_rate=float(row["packet_rate"]),
            byte_rate=float(row["byte_rate"]),
            syn_rate=float(row["syn_rate"]),
            dst_port_entropy=float(row["dst_port_entropy"]),
            failed_login_rate=float(row["failed_login_rate"]),
            request_interval_std=float(row["request_interval_std"]),
            payload_mean=float(row["payload_mean"]),
        )
        for row in transformed.to_dict(orient="records")
    ]


def _save_import_job(filename: str, source_type: str, source_rows: int, imported_rows: int, labels: dict) -> dict:
    job = DatasetImportJob(
        filename=filename,
        source_type=source_type,
        imported_count=imported_rows,
        skipped_count=max(source_rows - imported_rows, 0),
        summary={
            "source_rows": int(source_rows),
            "imported_rows": int(imported_rows),
            "labels": labels,
        },
    )
    db.session.add(job)
    db.session.commit()
    return job.to_dict()


def reset_training_and_dataset() -> None:
    ModelMetric.query.delete(synchronize_session=False)
    TrainingRun.query.delete(synchronize_session=False)
    DatasetImportJob.query.delete(synchronize_session=False)
    DatasetRecord.query.delete(synchronize_session=False)
    db.session.commit()


def import_cicids_file(file_storage) -> dict:
    raw = file_storage.read()
    frame = pd.read_csv(BytesIO(raw), low_memory=False)
    transformed = _transform_cicids(frame)
    records = _build_records(transformed)
    db.session.add_all(records)
    db.session.commit()
    return _save_import_job(
        file_storage.filename or "cicids.csv",
        "cicids2017",
        len(frame),
        len(records),
        transformed["label"].value_counts().to_dict() if not transformed.empty else {},
    )


def import_cicids_files(files) -> dict:
    jobs = []
    total_imported = 0
    total_skipped = 0
    for file in files:
        if not file or not file.filename:
            continue
        job = import_cicids_file(file)
        jobs.append(job)
        total_imported += job["imported_count"]
        total_skipped += job["skipped_count"]
    return {
        "jobs": jobs,
        "fileCount": len(jobs),
        "importedCount": total_imported,
        "skippedCount": total_skipped,
    }


def import_cicids_parquet_directory(directory: str | Path, reset_existing: bool = True) -> dict:
    base = Path(directory)
    parquet_files = sorted(base.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {base}")

    if reset_existing:
        reset_training_and_dataset()

    jobs = []
    total_source_rows = 0
    total_imported = 0
    total_skipped = 0

    for parquet_file in parquet_files:
        frame = pd.read_parquet(parquet_file)
        transformed = _transform_cicids(frame)
        records = _build_records(transformed)
        db.session.add_all(records)
        db.session.commit()
        job = _save_import_job(
            parquet_file.name,
            "cicids2017-parquet",
            len(frame),
            len(records),
            transformed["label"].value_counts().to_dict() if not transformed.empty else {},
        )
        jobs.append(job)
        total_source_rows += len(frame)
        total_imported += len(records)
        total_skipped += max(len(frame) - len(records), 0)

    return {
        "fileCount": len(parquet_files),
        "sourceRows": total_source_rows,
        "importedCount": total_imported,
        "skippedCount": total_skipped,
        "jobs": jobs,
    }


def list_import_jobs(limit: int = 10) -> list[dict]:
    items = DatasetImportJob.query.order_by(DatasetImportJob.created_at.desc()).limit(limit).all()
    return [item.to_dict() for item in items]
