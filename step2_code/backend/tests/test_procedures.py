"""Tests for procedure guides (T016).

Covers: valid citations for both synthetic items under proper filters,
no ineligible sources mixed in (2023 vs 2024-only DOCX), hash-change/missing
sources on an ISOLATED fixture (product corpus untouched), saveability gate,
verify verdicts, and route/factory registration. No model calls.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app
from campus_assistant.procedures.service import (
    build_draft,
    load_procedures,
    verify_snapshot,
)

BACKEND = Path(__file__).resolve().parents[1]
PROCEDURES_PATH = BACKEND / "examples" / "procedures" / "procedures.json"
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"


@pytest.fixture(scope="module")
def procedures():
    return load_procedures(PROCEDURES_PATH)


@pytest.fixture(scope="module")
def documents():
    from campus_assistant.corpus.parse import parse_manifest

    r = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)
    assert r["valid"]
    return r["documents"]


def _f(campus=None, year=None, as_of=None):
    return {"campus": campus, "student_type": None, "admission_year": year, "as_of_date": as_of}


class TestDraftCitations:
    def test_defer_ok_for_2023_without_docx_content(self, procedures, documents):
        d = build_draft(procedures, "proc-apply-defer", _f(year=2023), documents)
        assert d["saveable"] is True and d["status"] == "ready"
        # required TXT steps ok; the 2024-only optional citation degrades
        by_id = {s["step_id"]: s for s in d["steps"]}
        assert by_id["d1"]["status"] == "ok"
        assert by_id["d4"]["status"] == "degraded"
        assert by_id["d4"]["fallback"] and "资料未说明" in by_id["d4"]["fallback"]
        # ineligible DOCX content must NOT be presented as usable info
        for c in by_id["d4"]["citations"]:
            assert c["status"] == "source_excluded"
            assert c["note"] and "不符合当前筛选条件" in c["note"]
        text = json.dumps(d, ensure_ascii=False)
        assert "需医院证明" not in by_id["d4"]["detail"]

    def test_defer_ok_for_2024_with_materials(self, procedures, documents):
        d = build_draft(procedures, "proc-apply-defer", _f(year=2024), documents)
        assert d["saveable"] is True
        by_id = {s["step_id"]: s for s in d["steps"]}
        assert by_id["d4"]["status"] == "ok"
        assert any("需医院证明" in c["quote"] for c in by_id["d4"]["citations"])

    def test_grade_review_ok_2024_and_refused_2023(self, procedures, documents):
        ok = build_draft(procedures, "proc-review-grade", _f(year=2024), documents)
        assert ok["saveable"] is True
        for s in ok["steps"]:
            assert s["status"] == "ok"

        refused = build_draft(procedures, "proc-review-grade", _f(year=2023), documents)
        assert refused["saveable"] is False
        assert refused["status"] == "insufficient"
        assert any("不符合当前筛选条件" in i for i in refused["issues"])
        # no 2024-only content presented as usable in the refused draft
        for s in refused["steps"]:
            if s["status"] == "failed":
                for c in s["citations"]:
                    if c["status"] == "source_excluded":
                        assert c["note"]

    def test_all_citation_spans_match_original(self, procedures, documents):
        d = build_draft(procedures, "proc-review-grade", None, documents)
        blocks = {b["block_id"]: b for doc in documents for b in doc["blocks"]}
        for s in d["steps"]:
            for c in s["citations"]:
                block = blocks[c["block_id"]]
                assert block["text"][c["char_start"]:c["char_end"]] == c["quote"]

    def test_filters_never_relaxed(self, procedures, documents):
        d = build_draft(procedures, "proc-apply-defer", _f(campus="不存在校区"), documents)
        assert d["saveable"] is False
        assert all(
            c["status"] == "source_excluded"
            for s in d["steps"] for c in s["citations"] if c["required"]
        )


class TestIsolatedSourceChanges:
    """Hash change / missing source on copied fixtures — product corpus untouched."""

    def test_hash_changed_and_missing(self, procedures, tmp_path):
        dst = tmp_path / "corpus"
        shutil.copytree(PARSE_CORPUS, dst)
        # tamper one file and delete the other — parse then skips both
        (dst / "sample.txt").write_text("tampered", encoding="utf-8")
        (dst / "sample.docx").unlink()
        from campus_assistant.corpus.parse import parse_manifest

        docs = parse_manifest(dst / "manifest.json", dst)["documents"]
        d = build_draft(procedures, "proc-apply-defer", None, docs)
        assert d["saveable"] is False
        reasons = {c["status"] for s in d["steps"] for c in s["citations"]}
        assert "source_missing" in reasons
        assert any("缺失" in i for i in d["issues"])

    def test_verify_unchanged(self, procedures, documents):
        draft = build_draft(procedures, "proc-review-grade", _f(year=2024), documents)
        snapshot = {
            "template_version": draft["template_version"],
            "filters": _f(year=2024),
            "steps": [
                {"step_id": s["step_id"], "title": s["title"], "citations": s["citations"]}
                for s in draft["steps"]
            ],
        }
        v = verify_snapshot(procedures, "proc-review-grade", snapshot, documents)
        assert v["status"] == "unchanged"

    def test_verify_changed_missing_source(self, procedures, documents, tmp_path):
        draft = build_draft(procedures, "proc-review-grade", _f(year=2024), documents)
        snapshot = {
            "template_version": draft["template_version"],
            "filters": _f(year=2024),
            "steps": [
                {"step_id": s["step_id"], "title": s["title"], "citations": s["citations"]}
                for s in draft["steps"]
            ],
        }
        # DOCX removed from an isolated copy → previously-ok required citation
        # now has no source → needs review
        dst = tmp_path / "corpus2"
        shutil.copytree(PARSE_CORPUS, dst)
        (dst / "sample.docx").unlink()
        import hashlib as _h

        txt = (dst / "sample.txt").read_bytes()
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "syn-parse-txt-001", "policy_group_id": "syn-parse-group",
                "title": "合成测试教务管理办法（正文解析示例）",
                "source_url": "https://example.org/policy/parse/txt", "source_site": "合成测试示例站",
                "local_path": "sample.txt", "sha256": _h.sha256(txt).hexdigest(),
                "version_label": "解析示例 v1", "published_at": "2025-01-15",
                "effective_from": "2025-03-01", "effective_to": None,
                "scope": {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2023, 2024]},
                "is_synthetic": True,
            }],
        }
        (dst / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        from campus_assistant.corpus.parse import parse_manifest

        docs2 = parse_manifest(dst / "manifest.json", dst)["documents"]
        v = verify_snapshot(procedures, "proc-review-grade", snapshot, docs2)
        assert v["status"] == "changed"
        assert any("缺失" in i for i in v["issues"])

    def test_verify_changed_hash_update(self, procedures, documents, tmp_path):
        # content tampered AND manifest updated to the new hash (parses clean)
        # → saved citation's sha no longer matches → hash_changed
        draft = build_draft(procedures, "proc-review-grade", _f(year=2024), documents)
        snapshot = {
            "template_version": draft["template_version"],
            "filters": _f(year=2024),
            "steps": [
                {"step_id": s["step_id"], "title": s["title"], "citations": s["citations"]}
                for s in draft["steps"]
            ],
        }
        dst = tmp_path / "corpus3"
        shutil.copytree(PARSE_CORPUS, dst)
        (dst / "sample.docx").unlink()
        new_txt = (dst / "sample.txt").read_text(encoding="utf-8") + "\n第六条 新增内容。"
        (dst / "sample.txt").write_text(new_txt, encoding="utf-8")
        # hash the FILE bytes (Windows text write may translate newlines)
        new_sha = hashlib.sha256((dst / "sample.txt").read_bytes()).hexdigest()
        manifest = json.loads((dst / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["documents"]:
            entry["local_path"] = "sample.txt"  # keep manifest valid, reuse file
            entry["sha256"] = new_sha
        (dst / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        from campus_assistant.corpus.parse import parse_manifest

        docs3 = parse_manifest(dst / "manifest.json", dst)["documents"]
        v = verify_snapshot(procedures, "proc-review-grade", snapshot, docs3)
        assert v["status"] == "changed"
        assert any("哈希" in i for i in v["issues"])

    def test_verify_unavailable_and_version_change(self, procedures, documents):
        v3 = verify_snapshot(procedures, "proc-review-grade", {"template_version": "1.0", "steps": "bad"}, documents)
        assert v3["status"] == "unavailable"

        draft = build_draft(procedures, "proc-apply-defer", None, documents)
        snapshot = {
            "template_version": "0.9",
            "filters": None,
            "steps": [{"step_id": s["step_id"], "title": s["title"], "citations": s["citations"]} for s in draft["steps"]],
        }
        v = verify_snapshot(procedures, "proc-apply-defer", snapshot, documents)
        assert v["status"] == "changed"
        assert any("模板版本" in i for i in v["issues"])


class TestT016R1Fixes:
    """T016-R1 targeted regressions (three causal chains)."""

    def test_excluded_content_never_in_draft_output(self, procedures, documents):
        # 2023 草稿：被筛除的 2024 材料内容不得出现在任何可用输出中
        d = build_draft(procedures, "proc-apply-defer", _f(year=2023), documents)
        assert d["saveable"] is True
        full = json.dumps(d, ensure_ascii=False)
        assert "需医院证明" not in full
        assert "3个工作日" not in full
        # 保留未说明/待核实状态与诊断标识（“未作为可用办理依据”由页面渲染）
        assert "资料未说明" in full
        assert "来源不符合当前筛选条件" in full
        by_id = {s["step_id"]: s for s in d["steps"]}
        d4 = by_id["d4"]
        assert d4["status"] == "degraded" and d4["fallback"]
        for c in d4["citations"]:
            assert c["usable"] is False and c["quote"] is None
        # 横幅语义：部分未知时不得宣称全部已核对
        assert d["status"] == "ready"

        # 2024 对照：有效材料引用正常给出原文
        d4_ok = build_draft(procedures, "proc-apply-defer", _f(year=2024), documents)
        full4 = json.dumps(d4_ok, ensure_ascii=False)
        assert "需医院证明" in full4
        ok_steps = {s["step_id"]: s for s in d4_ok["steps"]}
        assert all(c["usable"] for c in ok_steps["d4"]["citations"])

        # 失效必要步骤不展示具体办理要求（成绩复核 2023）
        refused = build_draft(procedures, "proc-review-grade", _f(year=2023), documents)
        full_r = json.dumps(refused, ensure_ascii=False)
        assert "10个工作日内向所在学院提出复核申请" not in full_r
        assert "仅查分不查卷" not in full_r
        for s in refused["steps"]:
            if s["status"] == "failed":
                assert s["detail"] is None
                assert all(c["quote"] is None for c in s["citations"] if not c["usable"])

    def test_verify_checks_adopted_optional_citations(self, procedures, documents, tmp_path):
        # 2024 缓考快照：d4 可选引用在保存时已采用（usable）→ 必须被跟踪
        draft = build_draft(procedures, "proc-apply-defer", _f(year=2024), documents)
        adopted = [
            {"step_id": s["step_id"], "title": s["title"],
             "citations": [c for c in s["citations"] if c.get("usable")]}
            for s in draft["steps"]
        ]
        assert any(
            not c["required"] for s in adopted for c in s["citations"]
        ), "快照含已采用的可选引用"
        snapshot = {"template_version": "1.0", "filters": _f(year=2024), "steps": adopted}
        v = verify_snapshot(procedures, "proc-apply-defer", snapshot, documents)
        assert v["status"] == "unchanged"

        # 隔离夹具：DOCX 缺失 → 已采用的可选依据失效 → changed（提示复核）
        dst = tmp_path / "corpus-no-docx"
        shutil.copytree(PARSE_CORPUS, dst)
        (dst / "sample.docx").unlink()
        (dst / "manifest.json").write_text(
            json.dumps({
                "schema_version": "1.0",
                "documents": [{
                    "document_id": "syn-parse-txt-001", "policy_group_id": "syn-parse-group",
                    "title": "合成测试教务管理办法（正文解析示例）",
                    "source_url": "https://example.org/policy/parse/txt", "source_site": "合成测试示例站",
                    "local_path": "sample.txt",
                    "sha256": hashlib.sha256((dst / "sample.txt").read_bytes()).hexdigest(),
                    "version_label": "解析示例 v1", "published_at": "2025-01-15",
                    "effective_from": "2025-03-01", "effective_to": None,
                    "scope": {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2023, 2024]},
                    "is_synthetic": True,
                }],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        from campus_assistant.corpus.parse import parse_manifest

        docs2 = parse_manifest(dst / "manifest.json", dst)["documents"]
        v2 = verify_snapshot(procedures, "proc-apply-defer", snapshot, docs2)
        assert v2["status"] == "changed"
        assert any("确认材料与办理时点" in i for i in v2["issues"])

        # 隔离夹具：哈希更新（内容变化）→ changed
        dst2 = tmp_path / "corpus-hash"
        shutil.copytree(PARSE_CORPUS, dst2)
        (dst2 / "sample.docx").unlink()
        new_txt = (dst2 / "sample.txt").read_text(encoding="utf-8") + "\n第六条 新增内容。"
        (dst2 / "sample.txt").write_text(new_txt, encoding="utf-8")
        new_sha = hashlib.sha256((dst2 / "sample.txt").read_bytes()).hexdigest()
        manifest = json.loads((dst2 / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["documents"]:
            entry["local_path"] = "sample.txt"
            entry["sha256"] = new_sha
        (dst2 / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        docs3 = parse_manifest(dst2 / "manifest.json", dst2)["documents"]
        v3 = verify_snapshot(procedures, "proc-apply-defer", snapshot, docs3)
        assert v3["status"] == "changed"
        assert any("哈希" in i for i in v3["issues"])
class TestRoutesAndFactory:
    def _client(self, tmp_path, with_procedures: bool):
        # minimal valid corpus
        f = tmp_path / "doc.txt"
        f.write_text("缓考申请说明。", encoding="utf-8")
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "doc-1", "policy_group_id": "g", "title": "t",
                "source_url": "https://example.org/p", "source_site": "s",
                "local_path": "doc.txt", "sha256": sha, "version_label": "v1",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return TestClient(
            create_app(
                manifest_path=tmp_path / "manifest.json",
                corpus_root=tmp_path,
                procedures_path=PROCEDURES_PATH if with_procedures else None,
            ),
            raise_server_exceptions=False,
        )

    def test_not_configured_by_default(self, tmp_path):
        c = self._client(tmp_path, with_procedures=False)
        r = c.get("/api/v1/procedures")
        assert r.status_code == 503
        assert r.json()["code"] == "PROCEDURES_NOT_CONFIGURED"
        r2 = c.post("/api/v1/procedures/proc-apply-defer/draft", json={})
        assert r2.status_code == 503

    def test_configured_routes(self, tmp_path):
        c = self._client(tmp_path, with_procedures=True)
        r = c.get("/api/v1/procedures")
        assert r.status_code == 200
        d = r.json()
        assert d["is_synthetic"] is True
        ids = {p["procedure_id"] for p in d["procedures"]}
        assert ids == {"proc-apply-defer", "proc-review-grade"}
        r2 = c.post("/api/v1/procedures/proc-apply-defer/draft", json={"filters": {"admission_year": 2024}})
        assert r2.status_code == 200
        assert "template_version" in r2.json()
        r3 = c.post("/api/v1/procedures/nope/draft", json={})
        assert r3.status_code == 404
        # other endpoints unaffected
        assert c.get("/api/v1/search/status").status_code == 200


class TestEntryMetadata:
    """T033: listing exposes entry metadata derived from the template itself."""

    def test_list_includes_keywords_and_source_ids(self, tmp_path):
        c = TestRoutesAndFactory()._client(tmp_path, with_procedures=True)
        d = c.get("/api/v1/procedures").json()
        by_id = {p["procedure_id"]: p for p in d["procedures"]}
        defer = by_id["proc-apply-defer"]
        assert defer["related_keywords"] == ["缓考"]
        grade = by_id["proc-review-grade"]
        assert grade["related_keywords"] == ["复核"]
        # source ids derived from template citations (never guessed)
        for p in (defer, grade):
            assert isinstance(p["source_document_ids"], list) and p["source_document_ids"]
            for did in p["source_document_ids"]:
                assert did.startswith("syn-") or len(did) > 0
        # identity fields only — no local paths or full text
        for p in d["procedures"]:
            assert "local_path" not in p and "quote" not in p

    def test_loader_accepts_missing_keywords_and_validates(self, tmp_path):
        from campus_assistant.procedures.service import load_procedures

        def write_and_load(proc):
            data = {"schema_version": "1.0", "is_synthetic": True, "procedures": [proc]}
            p = tmp_path / "t.json"
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return load_procedures(p)

        base = {
            "procedure_id": "p1", "title": "t", "template_version": "1.0",
            "steps": [{"step_id": "s1", "title": "a", "citations": []}],
        }
        # no related_keywords -> loads unchanged
        assert write_and_load(base)["procedures"][0].get("related_keywords") is None
        ok = dict(base, related_keywords=["转专业"])
        assert write_and_load(ok)["procedures"][0]["related_keywords"] == ["转专业"]
        for bad in (dict(base, related_keywords="转专业"), dict(base, related_keywords=[""]),
                    dict(base, related_keywords=[1]), dict(base, related_keywords=["  "])):
            with pytest.raises(ValueError):
                write_and_load(bad)
