"""Tests for applicability filters (T011).

Covers: filter semantics (scope/date, unknown = excluded), exclusion reason
counts, allowed_document_ids admission before truncation in all three modes
(hand-crafted vectors — no model download), and the search API filter loop.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app
from campus_assistant.retrieval.bm25 import BM25Index
from campus_assistant.retrieval.dense import DenseIndex
from campus_assistant.retrieval.filters import (
    compute_allowed_document_ids,
    extract_filter_options,
)
from campus_assistant.retrieval.hybrid import rrf_fusion


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_corpus(tmp_path: Path, docs: list[dict]) -> Path:
    """Build a manifest corpus. Each doc: file/content/scope/dates/years."""
    manifest_docs = []
    for d in docs:
        fname = d["file"]
        fpath = tmp_path / fname
        _write_text(fpath, d["content"])
        sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        manifest_docs.append({
            "document_id": d["document_id"],
            "policy_group_id": d.get("policy_group_id", "g"),
            "title": d["document_id"],
            "source_url": "https://example.org/",
            "source_site": "测试站",
            "local_path": fname,
            "sha256": sha,
            "version_label": "v1",
            "published_at": d.get("published_at"),
            "effective_from": d.get("effective_from"),
            "effective_to": d.get("effective_to"),
            "scope": d.get("scope", {"campus": [], "student_type": [], "admission_years": []}),
            "is_synthetic": True,
        })
    manifest = {"schema_version": "1.0", "documents": manifest_docs}
    mp = tmp_path / "manifest.json"
    _write_json(mp, manifest)
    return mp


def _doc(document_id: str, content: str, **kw) -> dict:
    return {"document_id": document_id, "file": f"{document_id}.txt", "content": content, **kw}


def _meta_docs() -> list[dict]:
    """Parsed-document shaped inputs for compute_allowed_document_ids."""
    def md(doc_id, scope, eff_from, eff_to):
        return {
            "document_id": doc_id,
            "metadata": {
                "scope": scope,
                "effective_from": eff_from,
                "effective_to": eff_to,
            },
        }

    full = {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2024]}
    return [
        md("d-match", dict(full), "2025-03-01", None),
        md("d-mismatch", {"campus": ["都江堰校区"], "student_type": ["全日制本科"], "admission_years": [2024]}, "2025-03-01", None),
        md("d-unknown", {"campus": [], "student_type": [], "admission_years": []}, "2025-03-01", None),
        md("d-future", dict(full), "2026-01-01", None),
        md("d-expired", dict(full), "2020-01-01", "2024-08-31"),
        md("d-nofrom", dict(full), None, None),
    ]


# --- Filter semantics ---

class TestComputeAllowed:
    def test_no_filters_unrestricted(self) -> None:
        r = compute_allowed_document_ids(_meta_docs(), None)
        assert r["active"] is False
        assert r["allowed_document_ids"] is None
        assert r["allowed_count"] == 6

    def test_empty_normalized_filters_unrestricted(self) -> None:
        r = compute_allowed_document_ids(_meta_docs(), {"campus": None, "student_type": None, "admission_year": None, "as_of_date": None})
        assert r["active"] is False
        assert r["allowed_document_ids"] is None

    def test_scope_match_mismatch_unknown(self) -> None:
        r = compute_allowed_document_ids(_meta_docs(), {"campus": "成都校区", "student_type": None, "admission_year": None, "as_of_date": None})
        assert r["active"] is True
        assert r["allowed_document_ids"] == {"d-match", "d-future", "d-expired", "d-nofrom"}
        assert r["excluded_counts"]["scope_unknown"] == 1  # d-unknown
        assert r["excluded_counts"]["scope_mismatch"] == 1  # d-mismatch

    def test_empty_scope_never_means_everyone(self) -> None:
        r = compute_allowed_document_ids(_meta_docs(), {"campus": "不存在校区", "student_type": None, "admission_year": None, "as_of_date": None})
        assert "d-unknown" not in r["allowed_document_ids"]

    def test_dimensions_anded(self) -> None:
        r = compute_allowed_document_ids(_meta_docs(), {"campus": "成都校区", "student_type": "全日制本科", "admission_year": 2024, "as_of_date": None})
        assert r["allowed_document_ids"] == {"d-match", "d-future", "d-expired", "d-nofrom"}
        r2 = compute_allowed_document_ids(_meta_docs(), {"campus": "成都校区", "student_type": "专科", "admission_year": 2024, "as_of_date": None})
        assert r2["allowed_document_ids"] == set()
        assert r2["allowed_count"] == 0

    def test_date_inclusive_interval(self) -> None:
        docs = [
            {"document_id": "a", "metadata": {"scope": {}, "effective_from": "2025-03-01", "effective_to": "2025-03-31"}},
        ]
        none = {"campus": None, "student_type": None, "admission_year": None, "as_of_date": None}
        at_from = compute_allowed_document_ids(docs, {**none, "as_of_date": "2025-03-01"})
        assert at_from["allowed_document_ids"] == {"a"}
        at_to = compute_allowed_document_ids(docs, {**none, "as_of_date": "2025-03-31"})
        assert at_to["allowed_document_ids"] == {"a"}
        before = compute_allowed_document_ids(docs, {**none, "as_of_date": "2025-02-28"})
        assert before["allowed_document_ids"] == set()
        assert before["excluded_counts"]["not_yet_effective"] == 1
        after = compute_allowed_document_ids(docs, {**none, "as_of_date": "2025-04-01"})
        assert after["allowed_document_ids"] == set()
        assert after["excluded_counts"]["expired"] == 1

    def test_date_filter_reasons(self) -> None:
        r = compute_allowed_document_ids(_meta_docs(), {"campus": None, "student_type": None, "admission_year": None, "as_of_date": "2025-09-01"})
        # d-match admitted (to=null noted), d-mismatch/unknown have known dates → admitted here
        assert r["allowed_document_ids"] == {"d-match", "d-mismatch", "d-unknown"}
        assert r["excluded_counts"]["date_unknown_from"] == 1  # d-nofrom
        assert r["excluded_counts"]["not_yet_effective"] == 1  # d-future
        assert r["excluded_counts"]["expired"] == 1  # d-expired
        assert any("未标注截止" in n for n in r["notes"])

    def test_no_date_filter_keeps_unknown_from(self) -> None:
        r = compute_allowed_document_ids(_meta_docs(), {"campus": "成都校区", "student_type": None, "admission_year": None, "as_of_date": None})
        assert "d-nofrom" in r["allowed_document_ids"]

    def test_counts_mutually_exclusive_sum(self) -> None:
        r = compute_allowed_document_ids(_meta_docs(), {"campus": "成都校区", "student_type": "全日制本科", "admission_year": 2024, "as_of_date": "2025-09-01"})
        assert sum(r["excluded_counts"].values()) + r["allowed_count"] == r["document_total"]

    def test_extract_filter_options(self) -> None:
        opts = extract_filter_options(_meta_docs())
        assert opts["campus"] == ["成都校区", "都江堰校区"]
        assert opts["student_type"] == ["全日制本科"]
        assert opts["admission_year"] == [2024]


# --- Retrieval admission before truncation ---

def _late_candidate_chunks() -> list[dict]:
    """5 high-tf chunks (excluded by year filter) + 1 legal low-tf chunk.

    Unfiltered Top-5 must be the five heavy chunks; the light chunk ranks 6th
    in the full corpus and must NOT be lost to early truncation when the
    heavy ones are filtered out.
    """
    chunks = []
    for i in range(1, 6):
        chunks.append({
            "chunk_id": f"heavy-{i}", "document_id": f"doc-heavy-{i}", "block_id": "b",
            "text": "缓考申请 " * 10, "ordinal": 1, "kind": "paragraph",
            "char_start": 0, "char_end": 1, "locator": {}, "cells": None,
            "metadata": {}, "parser_version": "1.0", "chunker_version": "1.0",
            "strategy": "s", "max_chars": 500, "warnings": [],
        })
    chunks.append({
        "chunk_id": "light-1", "document_id": "doc-light-1", "block_id": "b",
        "text": "缓考申请说明", "ordinal": 1, "kind": "paragraph",
        "char_start": 0, "char_end": 1, "locator": {}, "cells": None,
        "metadata": {}, "parser_version": "1.0", "chunker_version": "1.0",
        "strategy": "s", "max_chars": 500, "warnings": [],
    })
    return chunks


_ALLOWED = {"doc-light-1"}


class TestRetrieverAdmission:
    def test_bm25_unfiltered_unchanged(self) -> None:
        index = BM25Index(_late_candidate_chunks())
        hits = index.search("缓考申请", top_k=5)
        assert [h["chunk"]["chunk_id"] for h in hits] == ["heavy-1", "heavy-2", "heavy-3", "heavy-4", "heavy-5"]
        assert "light-1" not in [h["chunk"]["chunk_id"] for h in hits]

    def test_bm25_admission_before_truncation(self) -> None:
        index = BM25Index(_late_candidate_chunks())
        hits = index.search("缓考申请", top_k=5, allowed_document_ids=_ALLOWED)
        assert [h["chunk"]["chunk_id"] for h in hits] == ["light-1"]
        assert hits[0]["rank"] == 1

    def test_bm25_empty_and_none_distinct(self) -> None:
        index = BM25Index(_late_candidate_chunks())
        assert index.search("缓考申请", top_k=5, allowed_document_ids=set()) == []
        assert len(index.search("缓考申请", top_k=5, allowed_document_ids=None)) == 5

    def _vectors(self) -> np.ndarray:
        # Query [1, 0] → dot = x component; heavy docs rank above light.
        xs = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]
        vecs = [[x, float(np.sqrt(1 - x * x))] for x in xs]
        return np.array(vecs, dtype=np.float32)

    def test_dense_admission_before_truncation(self) -> None:
        index = DenseIndex(_late_candidate_chunks(), self._vectors())
        q = np.array([1.0, 0.0], dtype=np.float32)
        unfiltered = index.search(q, top_k=5)
        assert [h["chunk"]["chunk_id"] for h in unfiltered] == ["heavy-1", "heavy-2", "heavy-3", "heavy-4", "heavy-5"]
        filtered = index.search(q, top_k=5, allowed_document_ids=_ALLOWED)
        assert [h["chunk"]["chunk_id"] for h in filtered] == ["light-1"]
        assert filtered[0]["rank"] == 1
        assert index.search(q, top_k=5, allowed_document_ids=set()) == []

    def test_hybrid_admission_both_paths(self) -> None:
        chunks = _late_candidate_chunks()
        bm25 = BM25Index(chunks)
        dense = DenseIndex(chunks, self._vectors())
        q = np.array([1.0, 0.0], dtype=np.float32)
        bm25_hits = bm25.search("缓考申请", top_k=20, allowed_document_ids=_ALLOWED)
        dense_hits = dense.search(q, top_k=20, allowed_document_ids=_ALLOWED)
        fused = rrf_fusion(bm25_hits, dense_hits, top_k=5)
        assert [h["chunk"]["chunk_id"] for h in fused] == ["light-1"]
        assert fused[0]["bm25_rank"] == 1
        assert fused[0]["dense_rank"] == 1
        # unfiltered fusion keeps the full-corpus favorites
        fused_all = rrf_fusion(
            bm25.search("缓考申请", top_k=20), dense.search(q, top_k=20), top_k=5
        )
        assert "light-1" not in [h["chunk"]["chunk_id"] for h in fused_all]


# --- API level ---

class _FakeEmb:
    model_name = "fake-model"
    model_revision = "unknown"
    max_seq_length = 8

    def encode_query(self, query: str) -> np.ndarray:
        return np.array([1.0, 0.0], dtype=np.float32)


def _filtered_corpus_docs() -> list[dict]:
    full_scope = {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2024]}
    docs = []
    for i in range(1, 6):
        docs.append(_doc(
            f"heavy-{i}", "缓考申请 " * 10,
            scope={"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2023]},
            effective_from="2024-09-01", effective_to=None,
        ))
    docs.append(_doc(
        "light-1", "缓考申请说明",
        scope=full_scope, effective_from="2024-09-01", effective_to=None,
    ))
    return docs


class TestFilterAPI:
    @pytest.fixture()
    def app(self, tmp_path):
        mp = _make_corpus(tmp_path, _filtered_corpus_docs())
        application = create_app(manifest_path=mp, corpus_root=tmp_path)
        # Hand-crafted vectors — no model download in unit tests.
        xs = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]
        by_doc = {f"heavy-{i}": xs[i - 1] for i in range(1, 6)}
        by_doc["light-1"] = xs[5]
        chunks = application.state.search_chunks
        vecs = []
        for c in chunks:
            x = by_doc[c["document_id"]]
            vecs.append([x, float(np.sqrt(1 - x * x))])
        application.state.embedding_service = _FakeEmb()
        application.state.dense_index = DenseIndex(chunks, np.array(vecs, dtype=np.float32))
        application.state.available_modes = ["bm25", "dense", "hybrid"]
        return application

    @pytest.fixture()
    def client(self, app):
        return TestClient(app, raise_server_exceptions=False)

    @pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid"])
    def test_all_modes_exclude_and_keep_late_candidate(self, client, mode):
        r = client.post("/api/v1/search", json={
            "query": "缓考申请", "top_k": 5, "mode": mode,
            "filters": {"admission_year": 2024},
        })
        assert r.status_code == 200
        d = r.json()
        ids = {h["chunk"]["document_id"] for h in d["hits"]}
        assert ids == {"light-1"}, f"{mode} must exclude filtered docs and keep the late legal candidate"
        assert d["hits"][0]["rank"] == 1

    @pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid"])
    def test_unfiltered_keeps_t010_behavior(self, client, mode):
        r = client.post("/api/v1/search", json={"query": "缓考申请", "top_k": 5, "mode": mode})
        assert r.status_code == 200
        d = r.json()
        ids = {h["chunk"]["document_id"] for h in d["hits"]}
        assert "light-1" not in ids
        assert len(ids) == 5
        assert d["filter_summary"]["active"] is False
        assert d["filters"] is None

    def test_filters_echo_and_counts(self, client):
        r = client.post("/api/v1/search", json={
            "query": "缓考申请", "top_k": 5,
            "filters": {"campus": "成都校区", "admission_year": 2023, "as_of_date": "2025-09-01"},
        })
        assert r.status_code == 200
        d = r.json()
        assert d["filters"] == {"campus": "成都校区", "student_type": None, "admission_year": 2023, "as_of_date": "2025-09-01"}
        fs = d["filter_summary"]
        assert fs["active"] is True
        assert fs["document_total"] == 6
        assert fs["allowed_count"] == 5
        assert sum(fs["excluded_counts"].values()) == 1
        assert "口径" in fs["counting_rules"] or "统计对象为文档" in fs["counting_rules"]
        assert any("未标注截止" in n for n in fs["notes"])
        ids = {h["chunk"]["document_id"] for h in d["hits"]}
        assert ids == {f"heavy-{i}" for i in range(1, 6)}

    def test_no_match_does_not_cancel_filters(self, client):
        r = client.post("/api/v1/search", json={
            "query": "缓考申请", "top_k": 5,
            "filters": {"admission_year": 1900},
        })
        assert r.status_code == 200
        d = r.json()
        assert d["hits"] == []
        assert d["filters"] == {"campus": None, "student_type": None, "admission_year": 1900, "as_of_date": None}
        assert d["filter_summary"]["allowed_count"] == 0

    def test_status_filter_options(self, client):
        d = client.get("/api/v1/search/status").json()
        assert d["filter_options"]["admission_year"] == [2023, 2024]
        assert d["filter_options"]["campus"] == ["成都校区"]

    @pytest.mark.parametrize("body", [
        {"query": "x", "filters": {"as_of_date": "2025/09/01"}},
        {"query": "x", "filters": {"as_of_date": "2025-02-30"}},
        {"query": "x", "filters": {"admission_year": "2024"}},
        {"query": "x", "filters": {"campus": ""}},
        {"query": "x", "filters": {"unknown_field": "x"}},
        {"query": "x", "extra": 1},
    ])
    def test_invalid_filter_requests_422(self, client, body):
        r = client.post("/api/v1/search", json=body)
        assert r.status_code == 422
