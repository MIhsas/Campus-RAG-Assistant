"""Tests for search API endpoints (T008).

Covers: unconfigured, ready, partial, failed, punctuation-only, no hit,
strict params, request ID, multi-app isolation, init counts.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_corpus(tmp_path: Path, docs: list[tuple[str, str]]) -> Path:
    manifest_docs = []
    for fname, content in docs:
        fpath = tmp_path / fname
        _write_text(fpath, content)
        sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        manifest_docs.append({
            "document_id": fname.replace(".txt", "").replace(".docx", ""),
            "policy_group_id": "g", "title": fname,
            "source_url": "https://example.org/", "source_site": "测试站",
            "local_path": fname, "sha256": sha, "version_label": "v1",
            "published_at": None, "effective_from": None, "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": True,
        })
    manifest = {"schema_version": "1.0", "documents": manifest_docs}
    mp = tmp_path / "manifest.json"
    _write_json(mp, manifest)
    return mp


# --- Unconfigured ---

class TestUnconfigured:
    def test_status_unconfigured(self) -> None:
        c = TestClient(create_app(), raise_server_exceptions=False)
        r = c.get("/api/v1/search/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "unconfigured"
        assert d["indexed_chunk_count"] == 0

    def test_search_503(self) -> None:
        c = TestClient(create_app(), raise_server_exceptions=False)
        r = c.post("/api/v1/search", json={"query": "test", "top_k": 5})
        assert r.status_code == 503
        assert r.json()["code"] == "CORPUS_NOT_CONFIGURED"


# --- Ready state ---

class TestReadyState:
    @pytest.fixture()
    def client(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请材料\n\n成绩复核要求\n")])
        return TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)

    def test_status_ready(self, client):
        r = client.get("/api/v1/search/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ready"
        assert d["chunk_count"] > 0
        assert d["indexed_chunk_count"] > 0
        assert d["synthetic_count"] == 1

    def test_search_finds_match(self, client):
        r = client.post("/api/v1/search", json={"query": "缓考", "top_k": 5})
        assert r.status_code == 200
        d = r.json()
        assert len(d["hits"]) >= 1
        assert d["status"] == "ready"

    def test_search_no_hit(self, client):
        r = client.post("/api/v1/search", json={"query": "不存在的查询", "top_k": 5})
        assert r.status_code == 200
        d = r.json()
        assert d["hits"] == []

    def test_search_punctuation_only(self, client):
        """Pure punctuation query → tokenize=[] → 200, hits=[]."""
        r = client.post("/api/v1/search", json={"query": "!!!???", "top_k": 5})
        assert r.status_code == 200
        d = r.json()
        assert d["query_tokens"] == []
        assert d["hits"] == []

    def test_request_id_consistent(self, client):
        r = client.post("/api/v1/search", json={"query": "缓考", "top_k": 5})
        assert r.headers["X-Request-ID"] == r.json()["request_id"]


# --- Partial state ---

class TestPartialState:
    def test_partial_with_bad_docx(self, tmp_path):
        txt = tmp_path / "good.txt"
        _write_text(txt, "缓考申请\n")
        txt_sha = hashlib.sha256(txt.read_bytes()).hexdigest()
        bad = tmp_path / "bad.docx"
        bad.write_bytes(b"PK\x03\x04not real")
        bad_sha = hashlib.sha256(bad.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "1.0",
            "documents": [
                {"document_id": "good", "policy_group_id": "g", "title": "好",
                 "source_url": "https://example.org/", "source_site": "S",
                 "local_path": "good.txt", "sha256": txt_sha, "version_label": "v",
                 "published_at": None, "effective_from": None, "effective_to": None,
                 "scope": {"campus": [], "student_type": [], "admission_years": []}, "is_synthetic": True},
                {"document_id": "bad", "policy_group_id": "g", "title": "坏",
                 "source_url": "https://example.org/", "source_site": "S",
                 "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                 "published_at": None, "effective_from": None, "effective_to": None,
                 "scope": {"campus": [], "student_type": [], "admission_years": []}, "is_synthetic": True},
            ],
        }
        mp = tmp_path / "manifest.json"
        _write_json(mp, manifest)
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.get("/api/v1/search/status")
        assert r.json()["status"] == "partial"
        r2 = c.post("/api/v1/search", json={"query": "缓考", "top_k": 5})
        assert r2.status_code == 200
        assert len(r2.json()["hits"]) >= 1


# --- Failed state ---

class TestFailedState:
    def test_failed_invalid_manifest(self, tmp_path):
        mp = tmp_path / "manifest.json"
        mp.write_text("{bad json", encoding="utf-8")
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.get("/api/v1/search/status")
        assert r.json()["status"] == "failed"
        r2 = c.post("/api/v1/search", json={"query": "test", "top_k": 5})
        assert r2.status_code == 503
        assert r2.json()["code"] == "SEARCH_UNAVAILABLE"


# --- R2: Index build failure degradation ---

class TestBuildFailure:
    def test_chunk_runtime_error_still_serves(self, tmp_path, monkeypatch):
        """R2: RuntimeError in chunking → failed app, preview still works."""
        from campus_assistant.corpus import chunk as chunk_mod
        original = chunk_mod.chunk_documents

        def raising(*a, **kw):
            raise RuntimeError("synthetic failure with /tmp/path/trace")

        monkeypatch.setattr(chunk_mod, "chunk_documents", raising)
        mp = _make_corpus(tmp_path, [("doc.txt", "test content\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        # Search status should be failed
        r = c.get("/api/v1/search/status")
        assert r.json()["status"] == "failed"
        # Search should return 503
        r2 = c.post("/api/v1/search", json={"query": "test", "top_k": 5})
        assert r2.status_code == 503
        assert r2.json()["code"] == "SEARCH_UNAVAILABLE"
        # Error message should NOT contain exception text/path
        errors = r.json()["errors"]
        idx_errors = [e for e in errors if e.get("code") == "INDEX_BUILD_ERROR"]
        assert len(idx_errors) >= 1
        assert "/tmp/path" not in idx_errors[0]["message"]
        # Corpus preview should still work
        r3 = c.get("/api/v1/corpus/status")
        assert r3.status_code == 200
        # Health should still work
        r4 = c.get("/api/v1/health/live")
        assert r4.status_code == 200
        r5 = c.get("/api/v1/health/ready")
        assert r5.status_code == 503
        # synthetic_count should still be computed
        assert r.json()["synthetic_count"] == 1

    def test_index_runtime_error_still_serves(self, tmp_path, monkeypatch):
        """R2: RuntimeError in BM25Index → failed app, preview still works."""
        from campus_assistant.retrieval import bm25 as bm25_mod
        original_init = bm25_mod.BM25Index.__init__

        def raising(self_inner, *a, **kw):
            raise RuntimeError("index failure")

        monkeypatch.setattr(bm25_mod.BM25Index, "__init__", raising)
        mp = _make_corpus(tmp_path, [("doc.txt", "test content\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.get("/api/v1/search/status")
        assert r.json()["status"] == "failed"
        assert r.json()["synthetic_count"] == 1
        r2 = c.post("/api/v1/search", json={"query": "test", "top_k": 5})
        assert r2.status_code == 503


# --- R1: DOCX InvalidXmlError factory integration ---

class TestInvalidXmlDocxFactory:
    def _make_bad_docx(self, path):
        from docx import Document as D
        from docx.oxml.ns import qn
        d = D()
        d.add_paragraph("段落")
        t = d.add_table(rows=1, cols=2)
        t.rows[0].cells[0].text = "A"
        t.rows[0].cells[1].text = "B"
        tc = t._tbl.findall(qn("w:tr"))[0].findall(qn("w:tc"))[0]
        tc_pr = tc.find(qn("w:tcPr"))
        if tc_pr is None:
            tc_pr = tc.makeelement(qn("w:tcPr"), {})
            tc.insert(0, tc_pr)
        gs = tc_pr.makeelement(qn("w:gridSpan"), {})
        tc_pr.insert(0, gs)
        d.save(str(path))

    def test_bad_docx_with_good_txt_factory(self, tmp_path):
        """R1: Bad DOCX + good TXT → partial, factory creates, preview/live work."""
        txt = tmp_path / "good.txt"
        _write_text(txt, "缓考申请\n")
        txt_sha = hashlib.sha256(txt.read_bytes()).hexdigest()
        bad = tmp_path / "bad.docx"
        self._make_bad_docx(bad)
        bad_sha = hashlib.sha256(bad.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "1.0",
            "documents": [
                {"document_id": "good", "policy_group_id": "g", "title": "好",
                 "source_url": "https://example.org/", "source_site": "S",
                 "local_path": "good.txt", "sha256": txt_sha, "version_label": "v",
                 "published_at": None, "effective_from": None, "effective_to": None,
                 "scope": {"campus": [], "student_type": [], "admission_years": []}, "is_synthetic": True},
                {"document_id": "bad", "policy_group_id": "g", "title": "坏",
                 "source_url": "https://example.org/", "source_site": "S",
                 "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                 "published_at": None, "effective_from": None, "effective_to": None,
                 "scope": {"campus": [], "student_type": [], "admission_years": []}, "is_synthetic": True},
            ],
        }
        mp = tmp_path / "manifest.json"
        _write_json(mp, manifest)
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        assert c.get("/api/v1/corpus/status").json()["status"] == "partial"
        assert c.get("/api/v1/search/status").json()["status"] == "partial"
        assert c.get("/api/v1/health/live").status_code == 200
        assert c.get("/api/v1/health/ready").status_code == 503
        r = c.post("/api/v1/search", json={"query": "缓考", "top_k": 5})
        assert r.status_code == 200
        assert len(r.json()["hits"]) >= 1

    def test_only_bad_docx_factory(self, tmp_path):
        """R1: Only bad DOCX → failed, search 503, live 200."""
        bad = tmp_path / "bad.docx"
        self._make_bad_docx(bad)
        bad_sha = hashlib.sha256(bad.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "bad", "policy_group_id": "g", "title": "坏",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []}, "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        _write_json(mp, manifest)
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        assert c.get("/api/v1/search/status").json()["status"] == "failed"
        assert c.post("/api/v1/search", json={"query": "test", "top_k": 5}).status_code == 503
        assert c.get("/api/v1/health/live").status_code == 200
        assert c.get("/api/v1/health/ready").status_code == 503


# --- Strict params ---

class TestStrictParams:
    @pytest.fixture()
    def client(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        return TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)

    def test_extra_field_rejected(self, client):
        r = client.post("/api/v1/search", json={"query": "test", "top_k": 5, "extra": "bad"})
        assert r.status_code == 422

    def test_empty_query_rejected(self, client):
        r = client.post("/api/v1/search", json={"query": "", "top_k": 5})
        assert r.status_code == 422

    def test_blank_query_rejected(self, client):
        """R1: All-whitespace query must be rejected."""
        r = client.post("/api/v1/search", json={"query": "   ", "top_k": 5})
        assert r.status_code == 422

    def test_top_k_zero_rejected(self, client):
        r = client.post("/api/v1/search", json={"query": "test", "top_k": 0})
        assert r.status_code == 422

    def test_top_k_over_20_rejected(self, client):
        r = client.post("/api/v1/search", json={"query": "test", "top_k": 21})
        assert r.status_code == 422

    def test_top_k_bool_rejected(self, client):
        """R1: Boolean top_k must be rejected."""
        r = client.post("/api/v1/search", json={"query": "test", "top_k": True})
        assert r.status_code == 422

    def test_top_k_float_rejected(self, client):
        """R1: Float top_k must be rejected."""
        r = client.post("/api/v1/search", json={"query": "test", "top_k": 1.5})
        assert r.status_code == 422

    def test_top_k_string_rejected(self, client):
        """R1: String top_k must be rejected."""
        r = client.post("/api/v1/search", json={"query": "test", "top_k": "5"})
        assert r.status_code == 422

    def test_query_not_stripped(self, client):
        """R1: Query with leading/trailing spaces should be returned as-is."""
        r = client.post("/api/v1/search", json={"query": " 缓考 ", "top_k": 5})
        assert r.status_code == 200
        assert r.json()["query"] == " 缓考 "

    def test_request_id_on_422(self, client):
        r = client.post("/api/v1/search", json={"query": "", "top_k": 5})
        assert "X-Request-ID" in r.headers


# --- Multi-app isolation ---

class TestAppIsolation:
    def test_two_apps_independent(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请\n")])
        c1 = TestClient(create_app(), raise_server_exceptions=False)
        c2 = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        assert c1.get("/api/v1/search/status").json()["status"] == "unconfigured"
        assert c2.get("/api/v1/search/status").json()["status"] == "ready"


# --- Init counts ---

class TestInitCounts:
    def test_single_parse_chunk_index(self, tmp_path, monkeypatch):
        """parse_manifest, chunk_documents, BM25Index each called once."""
        from campus_assistant.corpus import parse as parse_mod
        from campus_assistant.corpus import chunk as chunk_mod
        from campus_assistant.retrieval import bm25 as bm25_mod

        counts = {"parse": 0, "chunk": 0, "index": 0}
        orig_parse = parse_mod.parse_manifest
        orig_chunk = chunk_mod.chunk_documents
        orig_init = bm25_mod.BM25Index.__init__

        def c_parse(*a, **kw):
            counts["parse"] += 1
            return orig_parse(*a, **kw)
        def c_chunk(*a, **kw):
            counts["chunk"] += 1
            return orig_chunk(*a, **kw)
        def c_init(self_inner, *a, **kw):
            counts["index"] += 1
            return orig_init(self_inner, *a, **kw)

        monkeypatch.setattr(parse_mod, "parse_manifest", c_parse)
        monkeypatch.setattr(chunk_mod, "chunk_documents", c_chunk)
        monkeypatch.setattr(bm25_mod.BM25Index, "__init__", c_init)

        mp = _make_corpus(tmp_path, [("doc.txt", "test content\n")])
        create_app(manifest_path=mp, corpus_root=tmp_path)
        assert counts["parse"] == 1
        assert counts["chunk"] == 1
        assert counts["index"] == 1

    def test_repeated_request_no_rebuild(self, tmp_path, monkeypatch):
        """R2: Multiple HTTP requests must not trigger rebuilds. Real call counting."""
        from campus_assistant.corpus import parse as parse_mod
        from campus_assistant.corpus import chunk as chunk_mod
        from campus_assistant.retrieval import bm25 as bm25_mod

        counts = {"parse": 0, "chunk": 0, "index": 0}
        orig_parse = parse_mod.parse_manifest
        orig_chunk = chunk_mod.chunk_documents
        orig_init = bm25_mod.BM25Index.__init__

        def c_parse(*a, **kw):
            counts["parse"] += 1
            return orig_parse(*a, **kw)
        def c_chunk(*a, **kw):
            counts["chunk"] += 1
            return orig_chunk(*a, **kw)
        def c_init(self_inner, *a, **kw):
            counts["index"] += 1
            return orig_init(self_inner, *a, **kw)

        monkeypatch.setattr(parse_mod, "parse_manifest", c_parse)
        monkeypatch.setattr(chunk_mod, "chunk_documents", c_chunk)
        monkeypatch.setattr(bm25_mod.BM25Index, "__init__", c_init)

        mp = _make_corpus(tmp_path, [("doc.txt", "test content\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        assert counts == {"parse": 1, "chunk": 1, "index": 1}

        # Multiple requests — counts must not increase
        c.get("/api/v1/search/status")
        c.get("/api/v1/search/status")
        c.post("/api/v1/search", json={"query": "test", "top_k": 5})
        c.post("/api/v1/search", json={"query": "test", "top_k": 5})
        assert counts == {"parse": 1, "chunk": 1, "index": 1}


# --- Mode support ---

class TestModeSupport:
    def test_status_has_available_modes(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.get("/api/v1/search/status")
        d = r.json()
        assert "available_modes" in d
        assert d["available_modes"] == ["bm25"]
        assert "embedding_model" in d
        assert d["embedding_model"] is None

    def test_bm25_mode_default(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.post("/api/v1/search", json={"query": "缓考", "top_k": 5})
        assert r.status_code == 200
        assert r.json()["mode"] == "bm25"

    def test_bm25_mode_explicit(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.post("/api/v1/search", json={"query": "缓考", "top_k": 5, "mode": "bm25"})
        assert r.status_code == 200
        assert r.json()["mode"] == "bm25"

    def test_dense_mode_unavailable_returns_503(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.post("/api/v1/search", json={"query": "test", "top_k": 5, "mode": "dense"})
        assert r.status_code == 503
        assert r.json()["code"] == "RETRIEVER_UNAVAILABLE"

    def test_hybrid_mode_unavailable_returns_503(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.post("/api/v1/search", json={"query": "test", "top_k": 5, "mode": "hybrid"})
        assert r.status_code == 503
        assert r.json()["code"] == "RETRIEVER_UNAVAILABLE"

    def test_invalid_mode_rejected(self, tmp_path):
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        c = TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)
        r = c.post("/api/v1/search", json={"query": "test", "top_k": 5, "mode": "invalid"})
        assert r.status_code == 422
