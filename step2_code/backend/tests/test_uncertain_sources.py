"""T038 focused tests: uncertain-source candidates + generation prompt rules.

Isolated synthetic fixtures only (no real pack). Covers the candidate
admission contract: user-selected unknown dimensions viewable; other known
conflicts / unselected unknowns / expired / wrong document_id excluded;
strict admission unchanged; candidates never enter strict search/ask or
generation messages. Plus: the actual SYSTEM_PROMPT / PROMPT_TEMPLATE carry
the T038 expression rules (verifiable via build_messages).
"""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app
from campus_assistant.retrieval.filters import (
    CandidateRequestError,
    compute_allowed_document_ids,
    compute_candidate_document_ids,
)


def _doc(doc_id: str, *, eff_from, eff_to=None, student_type=(), campus=(), years=()):
    return {
        "document_id": doc_id,
        "parser_version": "1.0",
        "metadata": {
            "document_id": doc_id,
            "sha256": hashlib.sha256(doc_id.encode()).hexdigest(),
            "title": f"资料-{doc_id}",
            "version_label": "未标注",
            "published_at": None,
            "effective_from": eff_from,
            "effective_to": eff_to,
            "scope": {"campus": list(campus), "student_type": list(student_type),
                      "admission_years": list(years)},
            "is_synthetic": True,
        },
        "warnings": [],
        "blocks": [{"block_id": f"b-{doc_id}", "ordinal": 1, "kind": "paragraph",
                    "text": f"{doc_id} 的正文内容", "locator": None, "cells": None}],
    }


DOCS = [
    _doc("docA-strict", eff_from="2020-01-01", student_type=["本科"]),      # 严格准入
    _doc("docB-date-unknown", eff_from=None, student_type=["本科"]),        # 日期未知
    _doc("docC-both-unknown", eff_from=None, student_type=[]),             # 双未知
    _doc("docD-expired", eff_from=None, eff_to="2015-01-01", student_type=["本科"]),  # 已失效
    _doc("docE-type-mismatch", eff_from=None, student_type=["硕士"]),      # 已知不匹配
    _doc("docF-campus-unknown", eff_from=None, student_type=["本科"], campus=[]),     # campus 未知
    _doc("docG-type-unknown-expired", eff_from=None, eff_to="2015-01-01", student_type=[]),  # scope_unknown 掩盖失效
]
AS_OF = {"campus": None, "student_type": "本科", "admission_year": None, "as_of_date": "2026-10-03"}


class TestCandidateAdmission:
    def test_strict_admission_unchanged(self):
        res = compute_allowed_document_ids(DOCS, AS_OF)
        assert res["allowed_document_ids"] == {"docA-strict"}

    def test_date_dimension_only(self):
        res = compute_candidate_document_ids(DOCS, AS_OF, ["date"])
        ids = res["candidate_document_ids"]
        # C 双未知未全选被排除；D/E/G 排除；F 日期未知且未筛 campus → 合法日期维度候选
        assert ids == {"docB-date-unknown", "docF-campus-unknown"}

    def test_both_dimensions_admit_double_unknown(self):
        res = compute_candidate_document_ids(DOCS, AS_OF, ["date", "student_type"])
        ids = res["candidate_document_ids"]
        assert ids == {"docB-date-unknown", "docC-both-unknown", "docF-campus-unknown"}

    def test_known_conflicts_never_relaxed(self):
        res = compute_candidate_document_ids(DOCS, AS_OF, ["date", "student_type"])
        ids = res["candidate_document_ids"]
        assert "docD-expired" not in ids          # 已失效（即使 effective_from 未知）
        assert "docE-type-mismatch" not in ids    # 已知 scope 不匹配
        assert "docG-type-unknown-expired" not in ids  # scope_unknown 不掩盖已失效
        assert "docA-strict" not in ids           # 严格已准入不是候选

    def test_campus_unknown_excluded_under_campus_filter(self):
        f = dict(AS_OF, campus="成都校区")
        res = compute_candidate_document_ids(DOCS, f, ["date", "student_type"])
        assert "docF-campus-unknown" not in res["candidate_document_ids"]  # campus 严格保留

    def test_no_relevant_filter_dimension_rejected(self):
        with pytest.raises(CandidateRequestError):
            compute_candidate_document_ids(DOCS, {"campus": None, "student_type": None,
                                                  "admission_year": None, "as_of_date": None},
                                           ["date"])
        with pytest.raises(CandidateRequestError):
            compute_candidate_document_ids(DOCS, AS_OF, [])
        with pytest.raises(CandidateRequestError):
            compute_candidate_document_ids(DOCS, AS_OF, ["campus"])
        with pytest.raises(CandidateRequestError):
            compute_candidate_document_ids(DOCS, AS_OF, ["date", "date"])


def _client(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("占位正文", encoding="utf-8")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    def _entry(doc_id, eff_from, eff_to, stype):
        return {"document_id": doc_id, "policy_group_id": "g", "title": f"资料-{doc_id}",
                "source_url": "https://example.org/p", "source_site": "s",
                "local_path": "doc.txt", "sha256": sha,
                "version_label": "未标注", "published_at": None, "effective_from": eff_from,
                "effective_to": eff_to, "scope": {"campus": [], "student_type": stype, "admission_years": []},
                "is_synthetic": True}
    manifest = {"schema_version": "1.0", "documents": [
        _entry("docB-date-unknown", None, None, ["本科"]),
        _entry("docA-strict", "2020-01-01", None, ["本科"]),
    ]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return TestClient(create_app(manifest_path=tmp_path / "manifest.json", corpus_root=tmp_path),
                      raise_server_exceptions=False)


class TestCandidatesApi:
    def test_candidates_explicit_and_disclaimed(self, tmp_path):
        c = _client(tmp_path)
        r = c.post("/api/v1/search/candidates", json={
            "query": "正文", "mode": "bm25", "top_k": 5,
            "filters": {"student_type": "本科", "as_of_date": "2026-10-03"},
            "uncertainty_dimensions": ["date"]})
        assert r.status_code == 200
        d = r.json()
        assert d["uncertainty_dimensions"] == ["date"]
        assert d["active_dimensions"] == ["date"]
        assert d["candidate_summary"]["candidate_document_count"] == 1
        assert "未通过所选日期或学生类型条件核实" in d["disclaimer"]
        assert d["hits"] and d["hits"][0]["unknown_dimensions"] == ["date"]

    def test_invalid_dimensions_422(self, tmp_path):
        c = _client(tmp_path)
        for dims in ([], ["campus"], ["date", "date"]):
            r = c.post("/api/v1/search/candidates", json={
                "query": "q", "mode": "bm25",
                "filters": {"as_of_date": "2026-10-03"}, "uncertainty_dimensions": dims})
            assert r.status_code == 422, dims
        # 无对应筛选的维度不能放宽
        r = c.post("/api/v1/search/candidates", json={
            "query": "q", "mode": "bm25", "uncertainty_dimensions": ["date"]})
        assert r.status_code == 422
        # 未知 document_id 仍 422
        r = c.post("/api/v1/search/candidates", json={
            "query": "q", "mode": "bm25", "filters": {"as_of_date": "2026-10-03"},
            "document_id": "doc-not-exist", "uncertainty_dimensions": ["date"]})
        assert r.status_code == 422

    def test_no_candidates_returns_empty_and_strict_untouched(self, tmp_path):
        c = _client(tmp_path)
        # 该夹具文档 student_type=本科 已知匹配且日期未知：选 student_type 维度=无实际未知→空
        r = c.post("/api/v1/search/candidates", json={
            "query": "q", "mode": "bm25",
            "filters": {"student_type": "本科", "as_of_date": "2026-10-03"},
            "uncertainty_dimensions": ["student_type"]})
        assert r.status_code == 200
        d = r.json()
        assert d["candidate_summary"]["candidate_document_count"] == 0
        assert d["hits"] == []
        # 严格 search/ask 不受候选影响
        rs = c.post("/api/v1/search", json={"query": "q", "mode": "bm25",
                                            "filters": {"student_type": "本科", "as_of_date": "2026-10-03"}})
        assert rs.status_code == 200
        assert "candidates" not in rs.json() and "disclaimer" not in rs.json()
        ra = c.post("/api/v1/ask", json={"query": "q", "mode": "bm25",
                                         "filters": {"student_type": "本科", "as_of_date": "2026-10-03"}})
        assert ra.status_code == 200
        assert "candidate" not in ra.json()

    def test_document_id_intersection_no_fallback(self, tmp_path):
        c = _client(tmp_path)
        # 指定一个不存在于候选的文档=空，不回退
        r = c.post("/api/v1/search/candidates", json={
            "query": "正文", "mode": "bm25",
            "filters": {"student_type": "本科", "as_of_date": "2026-10-03"},
            "document_id": "docB-date-unknown", "uncertainty_dimensions": ["date"]})
        assert r.status_code == 200
        assert r.json()["candidate_summary"]["candidate_document_count"] == 1  # 候选命中该文档
        r2 = c.post("/api/v1/search/candidates", json={
            "query": "正文", "mode": "bm25",
            "filters": {"student_type": "本科", "as_of_date": "2026-10-03"},
            "document_id": "docA-strict", "uncertainty_dimensions": ["date"]})
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["hits"] == []  # 严格已准入/非候选→空
        assert d2["candidate_summary"]["candidate_document_count"] == 0  # 不回退其他文件


class TestPromptRules:
    def test_build_messages_contains_t038_rules(self):
        from campus_assistant.qa.deepseek import SYSTEM_PROMPT, build_messages
        from campus_assistant.qa.providers import PROMPT_TEMPLATE

        msgs = build_messages(query="q", evidence=[{"evidence_id": "E1", "text": "t"}], filters=None)
        s = msgs[0]["content"]
        assert s is SYSTEM_PROMPT
        for needle in ("修订决定措辞", "不同前提", "旧版本废止", "逐字保留"):
            assert needle in s, needle
            assert needle in PROMPT_TEMPLATE, needle
        # 不硬编码具体答案
        assert "带小抄" not in s and "50/50" not in s
        assert "带小抄" not in PROMPT_TEMPLATE and "50/50" not in PROMPT_TEMPLATE
