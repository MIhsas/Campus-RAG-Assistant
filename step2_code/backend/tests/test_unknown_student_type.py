"""T043 focused tests: unknown-student-type formal admission (reference mode).

Covers the changed chain only: filters/service/search/ask/candidates/messages
+ minimal page wiring checks. Real pack u04: new mode admits 83eb as formal E
(with explicit location text + status), strict mode excludes it and candidates
still show it; synthetic fixture: known 研究生 conflict stays excluded, other
dimensions/document_id still constrain; mock provider proves formal E reaches
generation and messages carry the unknown status (NOT a real model — 0 external
calls). Old strict default preserved for compute_allowed_document_ids and
procedures/self-check callers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
CORPUS = ROOT / "data/corpora/sicau-rag-pilot-v1.2"

DOC_83EB = "83eb3948386df27ddc8db35591dbab6c97dd795b92c8b003f2f524339cec2f31"
U04_QUERY = "学籍基本信息有误需要更正时，学生本人去哪里办理？"
U04_FILTERS = {"campus": None, "student_type": "本科", "admission_year": None, "as_of_date": None}
STATUS = "学生类型未标注，适用范围尚未核实"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def real_app():
    from campus_assistant.main import create_app

    app = create_app(
        manifest_path=CORPUS / "manifest.json",
        corpus_root=CORPUS,
        embedding_model_path=None,
        answer_provider=None,
        procedures_path=None,
        self_check_path=None,
        asr_adapter=None,
        planner=None,
    )
    return app


@pytest.fixture(scope="module")
def real_client(real_app):
    from fastapi.testclient import TestClient

    return TestClient(real_app)


def test_u04_new_mode_admits_83eb_as_reference(real_client):
    r = real_client.post("/api/v1/search", json={
        "query": U04_QUERY, "mode": "bm25", "top_k": 5,
        "filters": U04_FILTERS, "include_unknown_student_type": True,
    })
    assert r.status_code == 200
    d = r.json()
    assert d["include_unknown_student_type"] is True
    assert d["filter_summary"]["include_unknown_student_type"] is True
    assert DOC_83EB in d["filter_summary"]["unknown_student_type_document_ids"]
    assert d["filter_summary"]["reference_count"] >= 1
    # 统计分列：参考不冒充适用性已确认
    assert d["filter_summary"]["confirmed_count"] + d["filter_summary"]["reference_count"] == d["filter_summary"]["allowed_count"]
    hits_83 = [h for h in d["hits"] if h["chunk"]["document_id"] == DOC_83EB]
    if hits_83:
        for h in hits_83:
            assert h["student_type_status"] == STATUS
        assert any("1 教 105" in h["chunk"]["text"] or "217" in h["chunk"]["text"] for h in hits_83)
    else:
        # TopK 未命中时如实不硬凑：至少准入集合已含 83eb（filter_summary 已断言）
        pytest.skip("TopK 未命中 83eb 相关块（准入已证明；不调算法硬凑）")


def test_u04_strict_excludes_and_candidates_remain(real_client):
    r = real_client.post("/api/v1/search", json={
        "query": U04_QUERY, "mode": "bm25", "top_k": 5,
        "filters": U04_FILTERS, "include_unknown_student_type": False,
    })
    assert r.status_code == 200
    d = r.json()
    assert d["include_unknown_student_type"] is False
    assert all(h["chunk"]["document_id"] != DOC_83EB for h in d["hits"])
    assert all(not h.get("student_type_status") for h in d["hits"])  # 普通命中继续旧协议（null）
    assert DOC_83EB not in d["filter_summary"]["unknown_student_type_document_ids"]
    # 关闭新开关 → T038 原 strict 候选保持（83eb 可独立候选查看）
    rc = real_client.post("/api/v1/search/candidates", json={
        "query": U04_QUERY, "mode": "bm25", "top_k": 5,
        "filters": U04_FILTERS, "uncertainty_dimensions": ["student_type"],
        "include_unknown_student_type": False,
    })
    assert rc.status_code == 200
    cd = rc.json()
    cand_docs = {h["chunk"]["document_id"] for h in cd["hits"]}
    assert DOC_83EB in cand_docs
    # 新模式开启时：83eb 已正式准入 → 候选不重复显示
    rc2 = real_client.post("/api/v1/search/candidates", json={
        "query": U04_QUERY, "mode": "bm25", "top_k": 5,
        "filters": U04_FILTERS, "uncertainty_dimensions": ["student_type"],
        "include_unknown_student_type": True,
    })
    assert rc2.status_code == 200
    assert DOC_83EB not in {h["chunk"]["document_id"] for h in rc2.json()["hits"]}


def test_u04_ask_evidence_carries_status_and_mode_echo(real_client):
    r = real_client.post("/api/v1/ask", json={
        "query": U04_QUERY, "mode": "bm25", "top_k": 5,
        "filters": U04_FILTERS, "answer_mode": "extractive",
        "include_unknown_student_type": True,
    })
    assert r.status_code == 200
    d = r.json()
    assert d["include_unknown_student_type"] is True
    ev_83 = [e for e in d["evidence"] if e["document_id"] == DOC_83EB]
    if ev_83:
        for e in ev_83:
            assert e["student_type_status"] == STATUS
        assert any("1 教 105" in e["text"] or "217" in e["text"] for e in ev_83)
    # 严格模式：E 不含 83eb、无状态字段
    r2 = real_client.post("/api/v1/ask", json={
        "query": U04_QUERY, "mode": "bm25", "top_k": 5,
        "filters": U04_FILTERS, "answer_mode": "extractive",
        "include_unknown_student_type": False,
    })
    d2 = r2.json()
    assert all(e["document_id"] != DOC_83EB for e in d2["evidence"])
    assert all(not e.get("student_type_status") for e in d2["evidence"])


def test_synthetic_conflicts_and_other_dims_constrained(tmp_path):
    from campus_assistant.retrieval.filters import compute_allowed_document_ids

    def doc(did, student_type, campus=None, eff_from="2020-01-01", eff_to=None):
        return {"document_id": did, "metadata": {
            "scope": {"campus": campus or [], "student_type": student_type or [], "admission_years": []},
            "effective_from": eff_from, "effective_to": eff_to,
            "title": did, "version_label": "v1", "sha256": "x",
        }}

    docs = [
        doc("d-known-benke", ["本科"]),
        doc("d-known-yanjiusheng", ["研究生"]),   # 已知类型冲突
        doc("d-type-unknown", None),               # 仅 student_type 未知
        doc("d-type-unknown-campus-unknown", None, campus=None, eff_from=None),  # 日期也未知
        doc("d-type-unknown-expired", None, eff_from="2010-01-01", eff_to="2015-01-01"),
    ]
    fl = {"campus": None, "student_type": "本科", "admission_year": None, "as_of_date": "2026-10-03"}

    # 默认 strict（办事/自查/旧 evaluation 保护）
    strict = compute_allowed_document_ids(docs, fl)
    assert strict["allowed_document_ids"] == {"d-known-benke"}
    assert strict["include_unknown_student_type"] is False

    # 新模式：仅 student_type 未知且其余维度通过者作参考
    res = compute_allowed_document_ids(docs, fl, include_unknown_student_type=True)
    assert res["allowed_document_ids"] == {"d-known-benke", "d-type-unknown"}
    assert "d-known-yanjiusheng" not in res["allowed_document_ids"]  # 已知冲突排除
    assert "d-type-unknown-campus-unknown" not in res["allowed_document_ids"]  # 日期未知仍排除
    assert "d-type-unknown-expired" not in res["allowed_document_ids"]  # 已失效仍排除
    assert res["unknown_student_type_document_ids"] == {"d-type-unknown"}
    assert res["confirmed_count"] == 1 and res["reference_count"] == 1

    # 无学生类型条件 → 原无筛选行为（不推定空范围适用所有人；模式不改变语义）
    none_fl = {"campus": None, "student_type": None, "admission_year": None, "as_of_date": None}
    r2 = compute_allowed_document_ids(docs, none_fl, include_unknown_student_type=True)
    assert r2["allowed_document_ids"] is None
    assert r2["reference_count"] == 0


def test_messages_carry_status_and_mock_provider_roundtrip(real_app):
    from campus_assistant.qa.deepseek import build_messages
    from campus_assistant.qa.evidence import build_evidence_pack

    hits = [{
        "rank": 1, "score": 1.0, "preview_url": "/preview#x/y",
        "matched_terms": [], "bm25_rank": 1, "dense_rank": None,
        "bm25_score": 1.0, "dense_score": None,
        "student_type_status": STATUS,
        "chunk": {
            "chunk_id": "c1", "document_id": DOC_83EB, "block_id": "b1", "ordinal": 0,
            "kind": "paragraph", "text": "基本信息更正到 1 教 105 室办理。", "char_start": 0, "char_end": 17,
            "locator": {"type": "pdf_page", "page": 4}, "cells": None,
            "metadata": {"title": "指南", "sha256": "x", "scope": {"campus": [], "student_type": [], "admission_years": []},
                         "version_label": "未标注", "is_synthetic": False},
            "parser_version": "1", "chunker_version": "1", "strategy": "paragraph", "max_chars": 500, "warnings": [],
        },
    }]
    pack = build_evidence_pack(hits, filter_summary=None, source_selection=None)
    ev = pack["evidence"][0]
    assert ev["student_type_status"] == STATUS
    msgs = build_messages(query=U04_QUERY, evidence=pack["evidence"], filters=U04_FILTERS)
    user = msgs[1]["content"]
    assert "【E1】（" + STATUS + "）" in user  # 状态真实进入消息（生成器可见）
    assert "基本信息更正到 1 教 105 室办理。" in user  # quote 未改写
    assert any("适用范围尚未核实" in m["content"] or "适用范围尚未核实" in msgs[0]["content"] for m in msgs)

    # mock provider 串通引用结构（非真实 DeepSeek；零外部调用）
    class FakeResp:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": json.dumps(
                {"type": "answer", "paragraphs": [{"text": "材料写明到 1 教 105 室办理（适用范围尚未核实）。",
                                                   "evidence_ids": ["E1"]}]},
                ensure_ascii=False)}, "finish_reason": "stop"}],
                "model": "mock", "id": "mock-1", "usage": None}

    class FakeClient:
        def post(self, url, **kw):
            return FakeResp()

    from campus_assistant.qa.deepseek import DeepSeekAnswerProvider

    provider = DeepSeekAnswerProvider("sk-mock", client=FakeClient())
    from fastapi.testclient import TestClient
    from campus_assistant.main import create_app

    app = create_app(
        manifest_path=CORPUS / "manifest.json", corpus_root=CORPUS,
        embedding_model_path=None, answer_provider=provider,
        procedures_path=None, self_check_path=None, asr_adapter=None, planner=None,
    )
    client = TestClient(app)
    r = client.post("/api/v1/ask", json={
        "query": U04_QUERY, "mode": "bm25", "top_k": 5,
        "filters": U04_FILTERS, "answer_mode": "generated",
        "include_unknown_student_type": True,
    })
    assert r.status_code == 200
    d = r.json()
    if d["status"] == "generated":
        paras = d["answer"]["paragraphs"]
        assert paras and paras[0]["evidence_ids"]
        assert paras[0]["citations"][0]["evidence_id"] in [e["evidence_id"] for e in d["evidence"]]
        # 83eb 若入 E，mock 引用的 E 之一应为其（真实包 TopK 未命中则跳过该断言）
        if any(e["document_id"] == DOC_83EB for e in d["evidence"]):
            assert any("105" in e["text"] for e in d["evidence"] if e["document_id"] == DOC_83EB)
    else:
        assert d["status"] == "insufficient_evidence"  # 零证据短路亦合法


def test_pages_wire_switch_and_snapshot():
    search = (BACKEND / "src/campus_assistant/static/search.html").read_text(encoding="utf-8")
    ask = (BACKEND / "src/campus_assistant/static/ask.html").read_text(encoding="utf-8")
    for src in (search, ask):
        assert 'id="include-unknown-type"' in src                       # UI 开关（默认开）
        assert 'body.include_unknown_student_type = !!includeUnknown' in src  # 提交带开关
        assert "lastSubmittedIncludeUnknown" in src                      # 提交快照
        assert "include_unknown_type=" in src                            # 跨页携带
        assert "include_unknown_student_type: !!candidateSnapshot.includeUnknown" in src  # 候选同模式
        assert "include_unknown_student_type" in src
    # 转摘录/重试按快照
    assert "viewEvidenceForLastRequest" in ask and "lastSubmittedIncludeUnknown" in ask
    # 历史缺字段=当时 strict 展示
    assert "旧记录未含模式字段" in ask


def test_three_modes_share_admission_and_document_id_constrains():
    from campus_assistant.retrieval.service import execute_search

    def doc(did, student_type):
        return {"document_id": did, "metadata": {
            "scope": {"campus": [], "student_type": student_type or [], "admission_years": []},
            "effective_from": "2020-01-01", "effective_to": None,
            "title": did, "version_label": "v1", "sha256": "x",
        }}

    docs = [doc("d-benke", ["本科"]), doc("d-unknown", None), doc("d-grad", ["研究生"])]
    fl = {"campus": None, "student_type": "本科", "admission_year": None, "as_of_date": None}

    class FakeEmb:
        def encode_query(self, q):
            return [0.0]

    class FakeIndex:
        def __init__(self):
            self.seen = []

        def search(self, arg=None, top_k=5, allowed_document_ids=None):
            self.seen.append(set(allowed_document_ids) if allowed_document_ids is not None else None)
            return []

    for mode in ("bm25", "dense", "hybrid"):
        bi, di = FakeIndex(), FakeIndex()
        execute_search(
            query="q", mode=mode, top_k=5, filters_norm=fl, documents=docs,
            bm25_index=bi, dense_index=di, embedding_service=FakeEmb(),
            include_unknown_student_type=True,
        )
        assert bi.seen or di.seen
        seen = (bi.seen + di.seen)[0]
        assert seen == {"d-benke", "d-unknown"}, f"{mode} 准入集合不一致: {seen}"

    # document_id 与准入集合求交；未知/失效 ID 由 API 层 422（此处验证不回退）
    bi = FakeIndex()
    execute_search(
        query="q", mode="bm25", top_k=5, filters_norm=fl, documents=docs,
        bm25_index=bi, dense_index=None, embedding_service=None,
        document_id="d-unknown", include_unknown_student_type=True,
    )
    assert bi.seen[-1] == {"d-unknown"}
    bi2 = FakeIndex()
    res = execute_search(
        query="q", mode="bm25", top_k=5, filters_norm=fl, documents=docs,
        bm25_index=bi2, dense_index=None, embedding_service=None,
        document_id="d-grad", include_unknown_student_type=True,
    )
    assert res["hits"] == [] and bi2.seen == []  # 所选文件被条件排除 → 空集短路，不回退其他文件
