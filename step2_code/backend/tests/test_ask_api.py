"""Tests for the /ask API and the injectable AnswerProvider contract (T012).

Fake providers prove the protocol only — they are not real model demos.
Covers: extractive evidence_only shape, citation/span consistency with
/search, filter pass-through, context-vs-citation consistency, generator
not configured, one valid fake output, illegal/empty/citation-less outputs,
insufficient_evidence, provider failure isolation, and retrieval failures
staying errors (never dressed up as "no answer").
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _make_corpus(tmp_path: Path, docs: list[dict]) -> Path:
    manifest_docs = []
    for d in docs:
        fpath = tmp_path / d["file"]
        _write_text(fpath, d["content"])
        sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        manifest_docs.append({
            "document_id": d["document_id"],
            "policy_group_id": d.get("policy_group_id", "g"),
            "title": d.get("title", d["document_id"]),
            "source_url": "https://example.org/policy",
            "source_site": "测试站",
            "local_path": d["file"],
            "sha256": sha,
            "version_label": "v1",
            "published_at": d.get("published_at"),
            "effective_from": d.get("effective_from"),
            "effective_to": d.get("effective_to"),
            "scope": d.get("scope", {"campus": [], "student_type": [], "admission_years": []}),
            "is_synthetic": True,
        })
    mp = tmp_path / "manifest.json"
    mp.write_text(
        json.dumps({"schema_version": "1.0", "documents": manifest_docs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return mp


_CORPUS = [
    {
        "document_id": "doc-2023",
        "file": "doc-2023.txt",
        "title": "缓考申请办法（2023 级）",
        "content": "缓考申请须经所在学院批准，附医院证明。补考成绩最高记为60分。",
        "scope": {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2023]},
        "effective_from": "2023-09-01",
        "effective_to": None,
    },
    {
        "document_id": "doc-2024",
        "file": "doc-2024.txt",
        "title": "缓考申请办法（2024 级）",
        "content": "缓考申请须在考前 3 个工作日提交。取消补考资格的情况另行规定。",
        "scope": {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2024]},
        "effective_from": "2024-09-01",
        "effective_to": "2025-08-31",
    },
]


class RecordingProvider:
    """Controlled fake — proves the contract, nothing more."""

    provider_id = "fake-recording"

    def __init__(self, result):
        self.result = result
        self.calls: list[dict] = []

    def generate(self, *, query, evidence, filters):
        self.calls.append({
            "query": query,
            "evidence_ids": [e["evidence_id"] for e in evidence],
            "evidence_texts": [e["text"] for e in evidence],
            "filters": filters,
        })
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture()
def client(tmp_path):
    mp = _make_corpus(tmp_path, _CORPUS)
    return TestClient(create_app(manifest_path=mp, corpus_root=tmp_path), raise_server_exceptions=False)


def _ask(client, **kw):
    body = {"query": "缓考申请", "top_k": 5, "mode": "bm25"}
    body.update(kw)
    return client.post("/api/v1/ask", json=body)


class TestExtractive:
    def test_evidence_only_shape(self, client):
        r = _ask(client)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "evidence_only"
        assert d["answer"] is None  # excerpts are never dressed up as answers
        assert "尚未生成答案" in d["disclaimer"]
        assert d["evidence_state"] == "ok"
        assert [e["evidence_id"] for e in d["evidence"]] == ["E1", "E2"]
        for e in d["evidence"]:
            assert e["text"]
            assert e["preview_url"].startswith("/preview#")
            assert e["document_sha256"]

    def test_citation_span_matches_search_hits(self, client):
        ask_d = _ask(client).json()
        search_d = client.post("/api/v1/search", json={"query": "缓考申请", "top_k": 5, "mode": "bm25"}).json()
        # evidence comes from the same chunks — spans match the original mapping
        for ev, hit in zip(ask_d["evidence"], search_d["hits"]):
            chunk = hit["chunk"]
            assert ev["chunk_id"] == chunk["chunk_id"]
            assert ev["text"] == chunk["text"]
            assert ev["char_start"] == chunk["char_start"]
            assert ev["char_end"] == chunk["char_end"]
            assert ev["char_end"] - ev["char_start"] == len(ev["text"])
            assert ev["preview_url"] == hit["preview_url"]

    def test_filters_pass_through(self, client):
        r = _ask(client, filters={"admission_year": 2023})
        d = r.json()
        assert d["filters"] == {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None}
        assert d["filter_summary"]["allowed_count"] == 1
        assert {e["document_id"] for e in d["evidence"]} == {"doc-2023"}
        # exclusion behaves like /search: no qualifying docs is explained, not answered
        r2 = _ask(client, filters={"admission_year": 1900})
        d2 = r2.json()
        assert d2["status"] == "evidence_only"
        assert d2["answer"] is None
        assert d2["evidence_state"] == "no_admissible_docs"
        assert d2["empty_message"]
        assert "没有满足所选条件" in d2["empty_message"]

    def test_e_ids_scoped_per_request(self, client):
        d1 = _ask(client).json()
        d2 = _ask(client, filters={"admission_year": 2024}).json()
        assert d1["evidence"][0]["evidence_id"] == "E1"
        assert d2["evidence"][0]["evidence_id"] == "E1"  # restarted, not cumulative
        assert d1["evidence"][0]["chunk_id"] != d2["evidence"][0]["chunk_id"]

    def test_retrieval_failure_is_not_no_answer(self, tmp_path):
        bare = TestClient(create_app(), raise_server_exceptions=False)
        r = bare.post("/api/v1/ask", json={"query": "缓考申请"})
        assert r.status_code == 503
        assert r.json()["code"] == "CORPUS_NOT_CONFIGURED"

    def test_invalid_answer_mode_422(self, client):
        r = _ask(client, answer_mode="chat")
        assert r.status_code == 422


class TestGeneratedContract:
    def test_not_configured_503(self, client):
        r = _ask(client, answer_mode="generated")
        assert r.status_code == 503
        d = r.json()
        assert d["code"] == "GENERATOR_NOT_CONFIGURED"
        assert "原文摘录" in d["message"]

    def test_status_reports_generator_absent(self, client):
        d = client.get("/api/v1/ask/status").json()
        assert d["generator_configured"] is False
        assert d["answer_modes_available"] == ["extractive"]
        assert d["answer_mode_default"] == "extractive"

    def _client_with(self, tmp_path, provider):
        mp = _make_corpus(tmp_path, _CORPUS)
        return TestClient(
            create_app(manifest_path=mp, corpus_root=tmp_path, answer_provider=provider),
            raise_server_exceptions=False,
        )

    def test_valid_fake_output_and_context_consistency(self, tmp_path):
        provider = RecordingProvider({
            "type": "answer",
            "paragraphs": [{"text": "缓考申请须经学院批准。", "evidence_ids": ["E1"]}],
        })
        client = self._client_with(tmp_path, provider)
        st = client.get("/api/v1/ask/status").json()
        assert st["generator_configured"] is True
        assert st["answer_modes_available"] == ["extractive", "generated"]

        r = _ask(client, answer_mode="generated", filters={"admission_year": 2023})
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "generated"
        p = d["answer"]["paragraphs"][0]
        assert p["evidence_ids"] == ["E1"]
        # citations resolved by the service from the evidence mapping
        assert p["citations"][0]["preview_url"] == d["evidence"][0]["preview_url"]
        assert p["citations"][0]["document_id"] == "doc-2023"
        # context actually sent == evidence returned == citation domain
        sent_ids = provider.calls[0]["evidence_ids"]
        assert sent_ids == [e["evidence_id"] for e in d["evidence"]]
        assert set(p["evidence_ids"]) <= set(sent_ids)
        assert provider.calls[0]["filters"] == {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None}

    @pytest.mark.parametrize("bad", [
        {"type": "answer", "paragraphs": [{"text": "结论", "evidence_ids": ["E99"]}]},
        {"type": "answer", "paragraphs": [{"text": "结论", "evidence_ids": []}]},
        {"type": "answer", "paragraphs": []},
        {"type": "answer", "paragraphs": [{"text": "", "evidence_ids": ["E1"]}]},
        {"type": "chat", "paragraphs": []},
        "not-a-dict",
    ])
    def test_invalid_output_rejected_without_partial_answer(self, tmp_path, bad):
        client = self._client_with(tmp_path, RecordingProvider(bad))
        r = _ask(client, answer_mode="generated")
        assert r.status_code == 502
        d = r.json()
        assert d["code"] == "GENERATOR_INVALID_OUTPUT"
        assert "可改用原文摘录" in d["message"]
        assert "answer" not in d  # no partially bad answer leaks out

    def test_insufficient_evidence_is_independent_status(self, tmp_path):
        provider = RecordingProvider({"type": "insufficient_evidence", "reason": "摘录未覆盖证明材料要求"})
        client = self._client_with(tmp_path, provider)
        r = _ask(client, answer_mode="generated")
        assert r.status_code == 200
        d = r.json()
        # retrieval was non-empty — the provider's verdict is respected
        assert d["status"] == "insufficient_evidence"
        assert d["answer"] is None
        assert d["insufficient_reason"] == "摘录未覆盖证明材料要求"
        assert d["evidence_state"] == "ok"
        assert len(d["evidence"]) > 0

    def test_provider_failure_isolated_from_search(self, tmp_path):
        client = self._client_with(tmp_path, RecordingProvider(RuntimeError("boom")))
        r = _ask(client, answer_mode="generated")
        assert r.status_code == 502
        assert r.json()["code"] == "GENERATOR_ERROR"
        # search/preview unaffected
        s = client.post("/api/v1/search", json={"query": "缓考申请", "top_k": 5})
        assert s.status_code == 200
        assert len(s.json()["hits"]) > 0

    def test_empty_pack_short_circuits_without_provider(self, tmp_path):
        provider = RecordingProvider({"type": "answer", "paragraphs": [{"text": "x", "evidence_ids": ["E1"]}]})
        client = self._client_with(tmp_path, provider)
        r = _ask(client, answer_mode="generated", filters={"admission_year": 1900})
        d = r.json()
        assert r.status_code == 200
        assert d["status"] == "insufficient_evidence"
        assert "无可用证据" in d["insufficient_reason"]
        assert provider.calls == []  # never called without grounding material
