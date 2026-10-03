"""Tests for the limited self-check (T019).

Deterministic verdicts (all-satisfied / unknown / unsatisfied+unknown /
insufficient basis), unknown-never-satisfied, citation spans matching the
original block, server-bound citations, and route/config gating.
No models, no persistence.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app
from campus_assistant.selfcheck.service import evaluate_self_check, load_rule

BACKEND = Path(__file__).resolve().parents[1]
RULE_PATH = BACKEND / "examples" / "self-check" / "rule.json"
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"


@pytest.fixture(scope="module")
def rule():
    return load_rule(RULE_PATH)


@pytest.fixture(scope="module")
def documents():
    from campus_assistant.corpus.parse import parse_manifest

    r = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)
    assert r["valid"]
    return r["documents"]


ALL_YES = {
    "apply_at_first_year_end": "yes",
    "no_discipline_record": "yes",
    "rank_top_30": "yes",
    "passed_assessment": "yes",
}


class TestRuleBinding:
    def test_citation_spans_match_original(self, rule, documents):
        blocks = {b["block_id"]: b for d in documents for b in d["blocks"]}
        for c in rule["citations"]:
            block = blocks[c["block_id"]]
            assert block["text"][c["char_start"]:c["char_end"]] == c["quote"]
        assert rule["rule_version"] == "1.0"
        assert rule["is_synthetic"] is True

    def test_items_cover_four_conditions(self, rule):
        assert len(rule["items"]) == 4
        titles = " ".join(i["title"] for i in rule["items"])
        assert "第一学年末" in titles and "违纪" in titles
        assert "前 30%" in titles and "考核" in titles
        # 肯否方向与原文一致
        assert all(i["satisfied_when"] == "yes" for i in rule["items"])


class TestVerdicts:
    def test_all_satisfied(self, rule, documents):
        r = evaluate_self_check(rule, ALL_YES, None, documents)
        assert r["summary_status"] == "all_satisfied"
        assert "仍需学校审核" in r["summary_text"]
        assert "不构成录取、批准或申请成功" in r["summary_text"]
        assert all(i["status"] == "satisfied" for i in r["items"])

    def test_unknown_never_satisfied(self, rule, documents):
        answers = dict(ALL_YES)
        answers["passed_assessment"] = "unknown"  # 未参加考核 → 待核实
        r = evaluate_self_check(rule, answers, None, documents)
        assert r["summary_status"] == "has_unknown"
        assert "仍有待核实项" in r["summary_text"]
        by_field = {i["item_id"]: i for i in r["items"]}
        assert by_field["t4"]["status"] == "unknown"
        assert "未知不计为满足" in by_field["t4"]["explanation"]

    def test_unsatisfied_plus_unknown(self, rule, documents):
        answers = {
            "apply_at_first_year_end": "yes",
            "no_discipline_record": "no",   # 明确不满足
            "rank_top_30": "unknown",
            "passed_assessment": "unknown",
        }
        r = evaluate_self_check(rule, answers, None, documents)
        assert r["summary_status"] == "has_unsatisfied"
        assert "存在未满足项" in r["summary_text"]
        statuses = {i["item_id"]: i["status"] for i in r["items"]}
        assert statuses["t2"] == "unsatisfied"
        assert statuses["t3"] == "unknown"
        # 未参加（unknown）与明确未通过（no）区分
        assert statuses["t4"] == "unknown"

    def test_missing_answers_count_as_unknown(self, rule, documents):
        r = evaluate_self_check(rule, {}, None, documents)
        assert r["summary_status"] == "has_unknown"
        assert all(i["status"] == "unknown" for i in r["items"])

    def test_basis_insufficient_on_filter_exclusion(self, rule, documents):
        # 2024 专属 DOCX 无关；用不放宽的筛选排除唯一依据文档（年级 1900）
        r = evaluate_self_check(rule, ALL_YES, {"admission_year": 1900}, documents)
        assert r["summary_status"] == "insufficient_basis"
        assert "依据不足，无法完成自查" in r["summary_text"]
        assert all(i["status"] == "basis_unavailable" for i in r["items"])
        for c in r["basis"]["citations"]:
            assert c["usable"] is False
            assert c["quote"] is None  # 失效引用不携带原文

    def test_basis_insufficient_on_hash_change(self, rule, documents, tmp_path):
        dst = tmp_path / "corpus"
        shutil.copytree(PARSE_CORPUS, dst)
        (dst / "sample.docx").unlink()
        new_txt = (dst / "sample.txt").read_text(encoding="utf-8") + "\n第六条 新增。"
        (dst / "sample.txt").write_text(new_txt, encoding="utf-8")
        new_sha = hashlib.sha256((dst / "sample.txt").read_bytes()).hexdigest()
        manifest = json.loads((dst / "manifest.json").read_text(encoding="utf-8"))
        for e in manifest["documents"]:
            e["local_path"] = "sample.txt"
            e["sha256"] = new_sha
        (dst / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        from campus_assistant.corpus.parse import parse_manifest

        docs2 = parse_manifest(dst / "manifest.json", dst)["documents"]
        r = evaluate_self_check(rule, ALL_YES, None, docs2)
        assert r["summary_status"] == "insufficient_basis"
        assert any(c["status"] == "hash_changed" for c in r["basis"]["citations"])

    def test_citations_server_bound_with_preview(self, rule, documents):
        r = evaluate_self_check(rule, ALL_YES, None, documents)
        for i in r["items"]:
            c = i["citation"]
            assert c["preview_url"].startswith("/preview#")
            assert c["quote"]  # 通过核对时给出原文
        assert r["not_collected"] == ["姓名", "学号", "违纪详情"]


class TestApiRoutes:
    def test_not_configured_503(self, tmp_path):
        c = TestClient(create_app(), raise_server_exceptions=False)
        assert c.get("/api/v1/self-check/rule").status_code == 503
        assert c.post("/api/v1/self-check", json={}).status_code == 503

    def test_configured_flow(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("缓考申请说明。", encoding="utf-8")
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "doc-1", "policy_group_id": "g", "title": "t",
                "source_url": "https://example.org/p", "source_site": "s",
                "local_path": "doc.txt",
                "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                "version_label": "v1", "published_at": None, "effective_from": None,
                "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        c = TestClient(
            create_app(
                manifest_path=tmp_path / "manifest.json",
                corpus_root=tmp_path,
                self_check_path=RULE_PATH,
            ),
            raise_server_exceptions=False,
        )
        g = c.get("/api/v1/self-check/rule")
        assert g.status_code == 200
        d = g.json()
        assert d["rule_id"] == "rule-transfer-major"
        assert len(d["items"]) == 4
        assert d["answer_options"][2]["value"] == "unknown"
        r = c.post("/api/v1/self-check", json={"answers": ALL_YES})
        assert r.status_code == 200
        body = r.json()
        # 依据在该最小语料中缺失 → 依据不足（不利用失效原文）
        assert body["summary_status"] == "insufficient_basis"
        assert "不受理申请" in body["disclaimer"]
        # 非法答案值 422
        r2 = c.post("/api/v1/self-check", json={"answers": {"rank_top_30": "maybe"}})
        assert r2.status_code == 422
