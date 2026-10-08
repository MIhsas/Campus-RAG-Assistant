"""Focused tests for T031 source selection.

Business causal chain only: no-selection compatibility; single-file
restriction across bm25/dense/hybrid; intersection with the four
applicability conditions (never relaxed); explicit 422 for unknown or
invalid document_id; /search and /ask consistency through the shared
service; catalog endpoint (identity fields only, stable order); a call
counter proving selection switches never re-encode documents; and a
generated-answer mock proving evidence stays inside the selected file
with zero real model calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app


# --- corpus fixtures (synthetic, tiny, test-only) ---

_DOCS = [
    {
        "document_id": "doc-2023",
        "file": "doc-2023.txt",
        "title": "转专业实施办法（2023）",
        "content": "转专业申请条件：所修读必修课加权平均成绩专业排名前40%。课程要求无补考记录。",
        "version_label": "校教发〔2023〕1号",
        "scope": {"campus": [], "student_type": ["本科"], "admission_years": []},
        "effective_from": "2023-05-09",
    },
    {
        "document_id": "doc-2026",
        "file": "doc-2026.txt",
        "title": "转专业实施办法（2026）",
        "content": "转专业申请条件：已修读的所有课程均合格。课程要求均合格。",
        "version_label": "校教发〔2026〕1号",
        "scope": {"campus": [], "student_type": ["本科"], "admission_years": []},
        "effective_from": "2026-01-08",
    },
    {
        "document_id": "doc-unknown-scope",
        "file": "doc-unknown-scope.txt",
        "title": "学籍办理指南",
        "content": "学籍信息更正由学生本人到教务科办理。缓考申请另见相关规定。",
        "version_label": "未标注",
        "scope": {"campus": [], "student_type": [], "admission_years": []},
        "effective_from": None,
    },
]


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _make_corpus(tmp_path: Path) -> Path:
    manifest_docs = []
    for spec in _DOCS:
        fpath = tmp_path / spec["file"]
        _write_text(fpath, spec["content"])
        sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        manifest_docs.append(
            {
                "document_id": spec["document_id"],
                "policy_group_id": "g-" + spec["document_id"],
                "title": spec["title"],
                "source_url": "https://example.org/",
                "source_site": "测试站",
                "local_path": spec["file"],
                "sha256": sha,
                "version_label": spec["version_label"],
                "published_at": None,
                "effective_from": spec["effective_from"],
                "effective_to": None,
                "scope": spec["scope"],
                "is_synthetic": True,
            }
        )
    manifest = {"schema_version": "1.0", "documents": manifest_docs}
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp


class StubEmbeddingService:
    """Deterministic local stub — no model download, no network.

    Documents are encoded through encode_documents; a class-level counter
    proves selection switches never re-encode them.
    """

    doc_encode_calls = 0

    def __init__(self, model_path: str | None = None):
        self.model_name = "stub-embedding"
        self.model_revision = "unknown"
        self.max_seq_length = 512

    def count_truncated(self, texts: list[str]) -> int:
        return 0

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        StubEmbeddingService.doc_encode_calls += 1
        return self._vectors(texts)

    def encode_query(self, query: str) -> np.ndarray:
        return self._vectors([query])[0]

    @staticmethod
    def _vectors(texts: list[str]) -> np.ndarray:
        rows = []
        for t in texts:
            v = np.zeros(8, dtype=float)
            for i, ch in enumerate(t[:64]):
                v[i % 8] += (ord(ch) % 31) / 31.0
            rows.append(v)
        return np.array(rows, dtype=float)


class RecordingProvider:
    """Generated-mode mock — records what evidence it receives."""

    provider_id = "fake-recording"

    def __init__(self):
        self.calls: list[dict] = []

    def generate(self, *, query, evidence, filters):
        self.calls.append(
            {
                "query": query,
                "document_ids": sorted({e["document_id"] for e in evidence}),
                "evidence_ids": [e["evidence_id"] for e in evidence],
            }
        )
        return {
            "type": "answer",
            "paragraphs": [{"text": "mock 结论", "evidence_ids": [e["evidence_id"] for e in evidence][:1]}],
        }


@pytest.fixture()
def client(tmp_path):
    mp = _make_corpus(tmp_path)
    return TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)


@pytest.fixture()
def stub_client(tmp_path, monkeypatch):
    StubEmbeddingService.doc_encode_calls = 0
    monkeypatch.setattr(
        "campus_assistant.retrieval.embedding.EmbeddingService", StubEmbeddingService
    )
    mp = _make_corpus(tmp_path)
    app = create_app(manifest_path=mp, corpus_root=tmp_path, embedding_model_path="stub")
    return TestClient(app, raise_server_exceptions=False)


def _search(client, **kw):
    body = {"query": "转专业 课程要求", "top_k": 5, "mode": "bm25"}
    body.update(kw)
    return client.post("/api/v1/search", json=body)


# --- 1. compatibility: no selection = previous behaviour ---

class TestNoSelectionCompatible:
    def test_no_document_id_hits_all(self, client):
        r = _search(client)
        assert r.status_code == 200
        d = r.json()
        assert d["document_id"] is None
        assert d["source_selection"]["selected"] is False
        docs = {h["chunk"]["document_id"] for h in d["hits"]}
        assert "doc-2023" in docs and "doc-2026" in docs  # mixed, as before
        assert d["filter_summary"] is not None  # legacy shape preserved

    def test_explicit_null_same_as_missing(self, client):
        a = _search(client).json()
        b = _search(client, document_id=None).json()
        assert [h["chunk"]["chunk_id"] for h in a["hits"]] == [
            h["chunk"]["chunk_id"] for h in b["hits"]
        ]
        assert a["source_selection"] == b["source_selection"]


# --- 2. single-file restriction, all three modes ---

class TestSingleFileRestriction:
    @pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid"])
    def test_only_selected_document_returned(self, stub_client, mode):
        r = _search(stub_client, mode=mode, query="课程", document_id="doc-2023")
        assert r.status_code == 200
        d = r.json()
        assert d["hits"], "selected file should yield hits"
        assert {h["chunk"]["document_id"] for h in d["hits"]} == {"doc-2023"}
        ss = d["source_selection"]
        assert ss["selected"] is True
        assert ss["document_id"] == "doc-2023"
        assert ss["title"] == "转专业实施办法（2023）"
        assert ss["version_label"] == "校教发〔2023〕1号"
        assert ss["is_admitted"] is True
        assert ss["allowed_after_selection"] == 1

    def test_selection_switch_does_not_reencode_documents(self, stub_client):
        assert StubEmbeddingService.doc_encode_calls == 1  # startup only
        _search(stub_client, mode="dense", query="课程", document_id="doc-2023")
        _search(stub_client, mode="hybrid", query="课程", document_id="doc-2026")
        _search(stub_client, mode="dense", query="课程", document_id=None)
        _search(stub_client, mode="dense", query="课程")
        assert StubEmbeddingService.doc_encode_calls == 1


# --- 3. intersection with the four conditions ---

class TestIntersectionWithFilters:
    def test_selection_and_student_type_intersect(self, client):
        r = _search(
            client,
            query="课程",
            document_id="doc-2026",
            filters={"student_type": "本科"},
        )
        d = r.json()
        assert d["status"] == "ready"
        assert {h["chunk"]["document_id"] for h in d["hits"]} == {"doc-2026"}
        assert d["source_selection"]["allowed_after_selection"] == 1
        # filter_summary keeps its four-condition meaning
        assert d["filter_summary"]["active"] is True
        assert d["filter_summary"]["allowed_count"] == 2  # doc-2023+doc-2026
        assert d["source_selection"]["allowed_before_selection"] == 2

    def test_selected_file_excluded_by_filter_no_relaxation(self, client):
        # doc-unknown-scope has empty scope arrays → excluded under student_type
        r = _search(
            client,
            query="更正",
            document_id="doc-unknown-scope",
            filters={"student_type": "本科"},
        )
        d = r.json()
        assert r.status_code == 200
        assert d["hits"] == []  # never falls back to other documents
        ss = d["source_selection"]
        assert ss["selected"] is True
        assert ss["is_admitted"] is False
        assert ss["allowed_after_selection"] == 0
        assert ss["allowed_before_selection"] == 2
        assert any("未通过" in n or "0" in n for n in ss["notes"])
        # four-condition summary is not repurposed as the final count
        assert d["filter_summary"]["allowed_count"] == 2

    def test_selected_file_excluded_by_date_filter(self, client):
        r = _search(
            client,
            query="课程",
            document_id="doc-2026",
            filters={"as_of_date": "2024-01-01"},
        )
        d = r.json()
        assert d["hits"] == []
        assert d["source_selection"]["is_admitted"] is False
        assert d["source_selection"]["allowed_after_selection"] == 0


# --- 4. explicit 422 on unknown / invalid ids ---

class TestDocumentIdValidation:
    def test_unknown_id_422_search(self, client):
        r = _search(client, document_id="doc-not-exist")
        assert r.status_code == 422
        assert r.json()["code"] == "SOURCE_DOCUMENT_NOT_FOUND"

    def test_unknown_id_422_ask(self, client):
        r = client.post(
            "/api/v1/ask",
            json={"query": "缓考", "mode": "bm25", "document_id": "doc-not-exist"},
        )
        assert r.status_code == 422
        assert r.json()["code"] == "SOURCE_DOCUMENT_NOT_FOUND"

    def test_empty_string_422(self, client):
        r = _search(client, document_id="  ")
        assert r.status_code == 422

    def test_wrong_type_422(self, client):
        r = _search(client, document_id=123)
        assert r.status_code == 422

    def test_no_silent_widening(self, client):
        r = _search(client, document_id="")
        assert r.status_code == 422  # empty ≠ "all"


# --- 5. shared service consistency /search vs /ask ---

class TestSearchAskConsistency:
    def test_same_source_selection(self, client):
        body = {"query": "课程", "mode": "bm25", "top_k": 5, "document_id": "doc-2023"}
        rs = client.post("/api/v1/search", json=body).json()
        ra = client.post("/api/v1/ask", json=body).json()
        assert rs["source_selection"] == ra["source_selection"]
        assert rs["document_id"] == ra["document_id"] == "doc-2023"
        assert {e["document_id"] for e in ra["evidence"]} <= {"doc-2023"}

    def test_ask_empty_state_selected_excluded(self, client):
        r = client.post(
            "/api/v1/ask",
            json={
                "query": "更正",
                "mode": "bm25",
                "document_id": "doc-unknown-scope",
                "filters": {"student_type": "本科"},
            },
        )
        d = r.json()
        assert d["evidence_state"] == "no_admissible_docs"  # not "no_hits"

    def test_ask_empty_state_in_file_no_hits(self, tmp_path):
        mp = _make_corpus(tmp_path)
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.post(
            "/api/v1/ask",
            json={
                "query": "完全无关的稀有词组合xyzzy",
                "mode": "bm25",
                "document_id": "doc-2023",
            },
        )
        d = r.json()
        assert d["evidence_state"] == "no_hits"  # file admitted, nothing matched
        assert d["source_selection"]["is_admitted"] is True


# --- 6. catalog endpoint ---

class TestDocumentCatalog:
    def test_catalog_fields_and_order(self, client):
        r = client.get("/api/v1/search/documents")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok" and d["available"] is True
        assert d["count"] == 3
        ids = [e["document_id"] for e in d["documents"]]
        assert ids == sorted(ids)  # stable order
        entry = next(e for e in d["documents"] if e["document_id"] == "doc-2023")
        assert entry["title"] == "转专业实施办法（2023）"
        assert entry["version_label"] == "校教发〔2023〕1号"
        assert entry["effective_from"] == "2023-05-09"
        assert entry["is_synthetic"] is True
        unknown = next(e for e in d["documents"] if e["document_id"] == "doc-unknown-scope")
        assert unknown["version_label"] == "未标注"  # shown as-is, never guessed
        assert unknown["effective_from"] is None  # missing dates stay null
        # identity/metadata only — no paths, text or secrets
        for e in d["documents"]:
            assert "local_path" not in e and "sha256" not in e and "content" not in e

    def test_catalog_unconfigured(self):
        c = TestClient(create_app(), raise_server_exceptions=False)
        d = c.get("/api/v1/search/documents").json()
        assert d["available"] is False
        assert d["documents"] == [] and d["count"] == 0
        assert d["status"] in ("unconfigured", "failed")


# --- 7. generated mock: evidence stays inside the selected file ---

class TestGeneratedMockScope:
    def test_provider_receives_only_selected_file_evidence(self, tmp_path):
        provider = RecordingProvider()
        mp = _make_corpus(tmp_path)
        c = TestClient(
            create_app(manifest_path=mp, corpus_root=tmp_path, answer_provider=provider),
            raise_server_exceptions=False,
        )
        r = c.post(
            "/api/v1/ask",
            json={
                "query": "课程",
                "mode": "bm25",
                "document_id": "doc-2026",
                "answer_mode": "generated",
            },
        )
        d = r.json()
        assert d["status"] == "generated"
        assert provider.calls, "mock provider should be invoked once"
        assert provider.calls[0]["document_ids"] == ["doc-2026"]
        assert d["source_selection"]["document_id"] == "doc-2026"
        # the "model" is the in-process mock — zero external calls by construction
        assert provider.provider_id == "fake-recording"
