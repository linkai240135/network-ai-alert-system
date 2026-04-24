from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..config import INSTANCE_DIR


KNOWLEDGE_BASE_PATH = Path(__file__).resolve().parents[1] / "data" / "security_knowledge_base.json"
VECTOR_INDEX_PATH = INSTANCE_DIR / "security_kb_vector_index.joblib"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _allow_model_download() -> bool:
    return os.getenv("SECURITY_RAG_ALLOW_MODEL_DOWNLOAD", "0") == "1"


def load_knowledge_base() -> list[dict]:
    with KNOWLEDGE_BASE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.split(r"[^0-9A-Za-z\u4e00-\u9fff]+", text.lower()) if token}


def _entry_text(entry: dict) -> str:
    fields: list[Any] = [
        entry.get("title", ""),
        entry.get("category", ""),
        " ".join(entry.get("tags", [])),
        entry.get("content", ""),
        entry.get("severity", ""),
        entry.get("attack_stage", ""),
        " ".join(entry.get("applicable_services", [])),
        " ".join(entry.get("recommended_actions", [])),
        " ".join(entry.get("evidence_points", [])),
    ]
    return " ".join([str(item) for item in fields if item])


def extract_query_text(payload: dict) -> str:
    service = payload.get("service_profile") or {}
    summary = payload.get("summary") or {}
    fields: list[Any] = [
        payload.get("label", ""),
        payload.get("title", ""),
        payload.get("attack_type", ""),
        payload.get("attack_stage", ""),
        payload.get("risk_level", ""),
        payload.get("severity", ""),
        service.get("name", ""),
        service.get("protocol", ""),
        service.get("port", ""),
        service.get("keywords", ""),
        summary.get("classifier_name", ""),
        summary.get("detector_name", ""),
        " ".join(summary.get("prediction_set", []) or []),
    ]
    top_features = payload.get("top_features") or summary.get("top_features") or []
    for item in top_features[:5]:
        fields.extend([item.get("label", ""), item.get("feature", ""), item.get("direction", "")])
    return " ".join([str(item) for item in fields if item])


def _try_build_sentence_transformer_index(texts: list[str]) -> dict | None:
    if os.getenv("SECURITY_RAG_USE_SENTENCE_TRANSFORMERS", "1") == "0":
        return None
    try:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("SECURITY_RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        model = SentenceTransformer(model_name, local_files_only=not _allow_model_download())
        embeddings = model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
        return {
            "engine": "sentence-transformers",
            "model_name": model_name,
            "embeddings": np.asarray(embeddings, dtype=np.float32),
        }
    except Exception as exc:
        return {"engine": "tfidf", "fallback_reason": str(exc)}


def _build_vector_index(entries: list[dict]) -> dict:
    texts = [_entry_text(entry) for entry in entries]
    kb_stat = KNOWLEDGE_BASE_PATH.stat()
    st_index = _try_build_sentence_transformer_index(texts)
    if st_index and st_index.get("engine") == "sentence-transformers":
        index = {
            **st_index,
            "texts": texts,
            "entries_count": len(entries),
            "kb_mtime": kb_stat.st_mtime,
        }
        joblib.dump(index, VECTOR_INDEX_PATH)
        return index

    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b", ngram_range=(1, 2), max_features=12000)
    matrix = vectorizer.fit_transform(texts)
    index = {
        "engine": "tfidf",
        "model_name": "sklearn-tfidf",
        "vectorizer": vectorizer,
        "matrix": matrix,
        "texts": texts,
        "entries_count": len(entries),
        "kb_mtime": kb_stat.st_mtime,
        "fallback_reason": (st_index or {}).get("fallback_reason"),
        "st_attempted": os.getenv("SECURITY_RAG_USE_SENTENCE_TRANSFORMERS", "1") != "0",
        "allow_download": _allow_model_download(),
    }
    joblib.dump(index, VECTOR_INDEX_PATH)
    return index


def _load_or_build_vector_index(entries: list[dict]) -> dict:
    kb_stat = KNOWLEDGE_BASE_PATH.stat()
    if VECTOR_INDEX_PATH.exists():
        try:
            index = joblib.load(VECTOR_INDEX_PATH)
            if index.get("entries_count") == len(entries) and index.get("kb_mtime") == kb_stat.st_mtime:
                if (
                    os.getenv("SECURITY_RAG_USE_SENTENCE_TRANSFORMERS", "1") != "0"
                    and index.get("engine") != "sentence-transformers"
                    and not index.get("st_attempted")
                ):
                    return _build_vector_index(entries)
                return index
        except Exception:
            pass
    return _build_vector_index(entries)


def _encode_query(index: dict, query_text: str):
    if index.get("engine") == "sentence-transformers":
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(index.get("model_name", DEFAULT_EMBEDDING_MODEL), local_files_only=not _allow_model_download())
        query = model.encode([query_text], show_progress_bar=False, normalize_embeddings=True)
        return np.asarray(query[0], dtype=np.float32)
    return index["vectorizer"].transform([query_text])


def _vector_scores(index: dict, query_text: str) -> np.ndarray:
    query = _encode_query(index, query_text)
    if index.get("engine") == "sentence-transformers":
        return np.asarray(index["embeddings"] @ query, dtype=float)
    return np.asarray((index["matrix"] @ query.T).toarray()).ravel()


def _keyword_score(entry: dict, query_text: str, payload: dict) -> tuple[float, list[str]]:
    query_tokens = _tokenize(query_text)
    entry_tokens = _tokenize(_entry_text(entry))
    overlap = query_tokens & entry_tokens
    base = len(overlap) / max(len(query_tokens), 1)

    service = payload.get("service_profile") or {}
    summary = payload.get("summary") or {}
    payload_stage = payload.get("attack_stage") or summary.get("attack_stage")
    service_name = str(service.get("name", "")).lower()
    service_bonus = 0.0
    if service_name and service_name in [str(item).lower() for item in entry.get("applicable_services", [])]:
        service_bonus = 0.18
    stage_bonus = 0.12 if payload_stage and payload_stage == entry.get("attack_stage") else 0.0
    label = str(payload.get("label") or payload.get("attack_type") or "").lower()
    label_bonus = 0.15 if label and label in " ".join(entry.get("tags", [])).lower() else 0.0
    score = min(1.0, base + service_bonus + stage_bonus + label_bonus)
    return round(score, 4), sorted(list(overlap))[:8]


def retrieve_knowledge(payload: dict, limit: int = 3, candidate_pool: int = 50) -> list[dict]:
    entries = load_knowledge_base()
    query_text = extract_query_text(payload)
    index = _load_or_build_vector_index(entries)
    vector_scores = _vector_scores(index, query_text)

    vector_candidate_indexes = np.argsort(vector_scores)[::-1][:candidate_pool]
    candidates: dict[int, dict] = {}
    for index_no in vector_candidate_indexes:
        if vector_scores[index_no] <= 0:
            continue
        candidates[int(index_no)] = {"vector_score": float(vector_scores[index_no])}

    for index_no, entry in enumerate(entries):
        keyword_score, matched_terms = _keyword_score(entry, query_text, payload)
        if keyword_score > 0:
            item = candidates.setdefault(index_no, {"vector_score": float(vector_scores[index_no])})
            item["keyword_score"] = keyword_score
            item["matched_terms"] = matched_terms

    hits = []
    for index_no, scores in candidates.items():
        entry = entries[index_no]
        keyword_score = float(scores.get("keyword_score", 0.0))
        vector_score = max(0.0, float(scores.get("vector_score", 0.0)))
        fusion_score = round(min(1.0, 0.45 * keyword_score + 0.55 * vector_score), 4)
        if fusion_score <= 0:
            continue
        retrieval_method = "hybrid" if keyword_score > 0 and vector_score > 0 else ("keyword" if keyword_score > 0 else "vector")
        hits.append(
            {
                "id": entry["id"],
                "title": entry["title"],
                "category": entry["category"],
                "content": entry["content"],
                "source": entry["source"],
                "severity": entry.get("severity", "中"),
                "attack_stage": entry.get("attack_stage", "--"),
                "applicable_services": entry.get("applicable_services", []),
                "recommended_actions": entry.get("recommended_actions", []),
                "evidence_points": entry.get("evidence_points", []),
                "score": fusion_score,
                "fusion_score": fusion_score,
                "keyword_score": round(keyword_score, 4),
                "vector_score": round(vector_score, 4),
                "retrieval_method": retrieval_method,
                "retrieval_engine": index.get("engine", "unknown"),
                "embedding_model": index.get("model_name", "unknown"),
                "matched_terms": scores.get("matched_terms", []),
            }
        )
    hits.sort(key=lambda item: item["fusion_score"], reverse=True)
    return hits[:limit]
