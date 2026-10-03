"""T027 evaluation adaptation tests — focused, no unrelated suites.

T027-R1 coverage:
- fact-group semantics: alternative sources OR within a fact (first-hit
  alternative scores), multiple necessary facts AND across groups (partial
  coverage cannot get full marks), legacy no-fact_id keeps per-evidence
  behavior;
- old 8-question set behavior unchanged (compat);
- v2 dataset fields (fact_id / metric_semantics / revision_note) and
  filter admission assertions on the committed synthetic fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

from campus_assistant.evaluation.metrics import evaluate_question
from campus_assistant.evaluation.models import QuestionDataset

BACKEND = Path(__file__).resolve().parents[1]
V2 = BACKEND / "examples" / "evaluation-v2"
OLD_Q = BACKEND / "examples" / "evaluation" / "questions.json"


def _hit(doc, block, start, end, rank):
    return {"score": 1.0, "chunk": {
        "document_id": doc, "block_id": block, "chunk_id": f"c{rank}",
        "char_start": start, "char_end": end,
    }}


def _ev(eid, doc, block, s, e, quote, fact=None):
    d = {"evidence_id": eid, "document_id": doc, "document_sha256": "a" * 64,
         "parser_version": "1.0", "block_id": block,
         "char_start": s, "char_end": e, "quote": quote}
    if fact is not None:
        d["fact_id"] = fact
    return d


class TestFactGroupSemantics:
    """T027-R1：可替代证据组——组内 OR、组间 AND。"""

    def test_alternative_second_source_scores_full(self):
        # 同一事实两个逐字等价来源（q05 型）：只命中第二个也算覆盖该事实
        q = {"question_id": "t1", "query": "x", "answerable": True,
             "evidence": [
                 _ev("e1", "d1", "b1", 0, 10, "AAAAAAAAAA", fact="f1"),
                 _ev("e2", "d2", "b1", 0, 10, "AAAAAAAAAA", fact="f1"),
             ]}
        hits = [_hit("d2", "b1", 0, 10, 1)]  # 只命中替代来源 e2
        r = evaluate_question(q, hits, top_k=5)
        assert r["fact_count"] == 1 and r["covered_fact_count"] == 1
        assert r["recall"] == 1.0, "替代来源命中应记满该事实"
        assert r["hit"] == 1.0 and r["mrr"] == 1.0

    def test_two_facts_partial_coverage_half(self):
        # 两个必要事实：只覆盖一组 → recall 0.5，不得满分
        q = {"question_id": "t2", "query": "x", "answerable": True,
             "evidence": [
                 _ev("e1", "d1", "b1", 0, 10, "AAAAAAAAAA", fact="f1"),
                 _ev("e2", "d1", "b2", 0, 10, "BBBBBBBBBB", fact="f2"),
             ]}
        hits = [_hit("d1", "b1", 0, 10, 1)]  # 仅 f1
        r = evaluate_question(q, hits, top_k=5)
        assert r["fact_count"] == 2 and r["covered_fact_count"] == 1
        assert r["recall"] == 0.5

    def test_alternatives_do_not_dilute_denominator(self):
        # 三个替代来源是同一事实：分母是 1 不是 3
        q = {"question_id": "t3", "query": "x", "answerable": True,
             "evidence": [
                 _ev(f"e{i}", f"d{i}", "b1", 0, 5, "AAAAA", fact="f1") for i in range(3)
             ]}
        hits = [_hit("d1", "b1", 0, 5, 1), _hit("d2", "b1", 0, 5, 2)]
        r = evaluate_question(q, hits, top_k=5)
        assert r["fact_count"] == 1
        assert r["recall"] == 1.0, "重复来源不得作为多个必须找齐的事实稀释 Recall"

    def test_legacy_no_fact_id_per_evidence_semantics(self):
        # 旧口径：未标 fact_id 时逐证据，两条覆盖一条 = 0.5
        q = {"question_id": "t4", "query": "x", "answerable": True,
             "evidence": [
                 _ev("e1", "d1", "b1", 0, 10, "AAAAAAAAAA"),
                 _ev("e2", "d1", "b2", 0, 10, "BBBBBBBBBB"),
             ]}
        hits = [_hit("d1", "b1", 0, 10, 1)]
        r = evaluate_question(q, hits, top_k=5)
        assert r["fact_count"] == 2 and r["recall"] == 0.5


class TestDatasetCompat:
    def test_old_eight_questions_still_validate_and_score_identically(self):
        from campus_assistant.evaluation.run import _run_eval

        ds = QuestionDataset.model_validate(json.loads(OLD_Q.read_text(encoding="utf-8")))
        assert len(ds.questions) == 8 and ds.authoring_note is None
        assert ds.metric_semantics is None  # 旧集无新字段亦合法（unit 口径）
        out = _run_eval(
            manifest_path=BACKEND / "examples" / "parse-corpus" / "manifest.json",
            corpus_root=BACKEND / "examples" / "parse-corpus",
            questions_path=OLD_Q, top_k=5, mode="bm25",
        )
        assert out["valid"] and out["metrics_semantics"] == "unit_evidence_v1.0"
        s = out["summary"]
        # 与 rev1 记录逐项一致（8 题/6 可答/2 不足）
        assert s["evidence_recall"] == 1.0 and s["hit"] == 1.0
        assert abs(s["mrr"] - 0.9166666666666666) < 1e-12
        assert s["answerable_count"] == 6 and s["unanswerable_count"] == 2

    def test_v2_dataset_fields(self):
        ds = QuestionDataset.model_validate(
            json.loads((V2 / "questions.json").read_text(encoding="utf-8")))
        assert len(ds.questions) == 24
        assert ds.dataset_version == "2.1" and ds.metric_semantics == "fact_group_or_v1.1"
        assert ds.is_synthetic is True and "模型" in (ds.authoring_note or "")
        for q in ds.questions:
            assert q.question_type in {
                "direct", "paraphrase", "low_keyword", "multi_evidence",
                "distractor", "filtered", "unanswerable",
            }
            for e in q.evidence:
                assert e.fact_id, f"{q.question_id}/{e.evidence_id} v2 标注须带 fact_id"
            if not q.answerable:
                assert q.missing and q.evidence == []
        # 消歧修订：q12 题面带版本限定；q20/q21 同对同题
        by_id = {q.question_id: q for q in ds.questions}
        assert "2024版" in by_id["v2-q12"].query
        assert by_id["v2-q20"].query == by_id["v2-q21"].query
        assert "线上" in by_id["v2-q20"].query
        # 修订留痕
        for qid in ("v2-q05", "v2-q12", "v2-q15", "v2-q20"):
            assert by_id[qid].revision_note


class TestR2FactPrecision:
    """T027-R2：OR 来源须独立支持组的完整事实——不同要求/不同精度不互替。"""

    def _load(self):
        ds = QuestionDataset.model_validate(
            json.loads((V2 / "questions.json").read_text(encoding="utf-8")))
        return {q.question_id: q for q in ds.questions}

    def test_q10_material_sources_same_requirement_no_mix(self):
        # q10 f2 组只能是医院证明要求；书面说明/“或”口径不并入（不同材料要求不互替）
        by_id = self._load()
        q10 = by_id["v2-q10"]
        assert q10.conditions["admission_year"] == 2024
        f2 = [e for e in q10.evidence if e.fact_id == "f2"]
        assert len(f2) == 2
        for e in f2:
            assert "医院证明" in e.quote and "书面说明" not in e.quote
        # Astra 探针误判消除：命中 f1 + 书面情况说明句（不在组内）不得记满
        f1 = [e for e in q10.evidence if e.fact_id == "f1"]
        q = {"question_id": "probe", "query": q10.query, "answerable": True,
             "evidence": [e.model_dump() for e in q10.evidence]}
        hits = [_hit(f1[0].document_id, f1[0].block_id, f1[0].char_start, f1[0].char_end, 1),
                _hit("cmp-defer-v1", "f35e800308f2c324", 0, 100, 2)]  # 书面说明块（非 f2 来源）
        r = evaluate_question(q, hits, top_k=5)
        assert r["fact_count"] == 2
        assert r["covered_fact_count"] == 1 and r["recall"] == 0.5, "书面说明不得满足医院证明事实"

    def test_q16_q17_precision_not_interchangeable(self):
        # 宽泛「考前」与「考前 3 个工作日」不同精度，不互替
        by_id = self._load()
        q16, q17 = by_id["v2-q16"], by_id["v2-q17"]
        assert q16.query == q17.query and "按入学年级适用" in q16.query
        assert "3 个工作日" in q17.evidence[0].quote
        assert "3" not in q16.evidence[0].quote, "q16 gold 为该版完整规定（考前），不含精确天数"
        # 宽泛考前句命中不得满足 q17 的 3 个工作日完整要求
        q = {"question_id": "probe17", "query": q17.query, "answerable": True,
             "evidence": [e.model_dump() for e in q17.evidence]}
        broad = [e for e in q16.evidence][0]
        hits = [_hit(broad.document_id, broad.block_id, broad.char_start, broad.char_end, 1)]
        r = evaluate_question(q, hits, top_k=5)
        assert r["recall"] == 0.0, "「考前」不能替代「考前 3 个工作日」"
        # 反向：精确 3 日句命中也不满足 q16 的来源系列事实（fd-2024 跨度未覆盖）
        q16d = {"question_id": "probe16", "query": q16.query, "answerable": True,
                "evidence": [e.model_dump() for e in q16.evidence]}
        exact = [e for e in q17.evidence][0]
        hits2 = [_hit(exact.document_id, exact.block_id, exact.char_start, exact.char_end, 1)]
        r2 = evaluate_question(q16d, hits2, top_k=5)
        assert r2["recall"] == 0.0, "其他来源系列的时限句不替代 q16 的来源系列事实"


class TestConditionsAdmission:
    def test_same_query_different_conditions_admit_different_evidence(self):
        from campus_assistant.evaluation.run import _run_eval

        out = _run_eval(
            manifest_path=V2 / "corpus" / "manifest.json",
            corpus_root=V2 / "corpus",
            questions_path=V2 / "questions.json", top_k=5, mode="bm25",
        )
        assert out["valid"], out.get("errors")
        by_id = {r["question_id"]: r for r in out["per_question"]}
        q16, q17 = by_id["v2-q16"], by_id["v2-q17"]
        assert q16["conditions"]["admission_year"] == 2024
        assert q17["conditions"]["admission_year"] == 2025
        # 同题不同筛选：各自覆盖自己的事实组
        assert q16["covered_fact_count"] == q16["fact_count"] == 1
        assert q17["covered_fact_count"] == q17["fact_count"] == 1
        docs16 = {h["document_id"] for h in q16["hit_summary"]}
        docs17 = {h["document_id"] for h in q17["hit_summary"]}
        assert "fd-2025" not in docs16, "年级筛选须排除 2025 级文档"
        assert "fd-2024" not in docs17, "年级筛选须排除 2024 级文档"

    def test_unanswerable_not_in_recall_denominator(self):
        from campus_assistant.evaluation.metrics import compute_summary

        per = [
            {"question_id": "a", "answerable": True, "recall": 1.0, "hit": 1.0, "mrr": 1.0, "returned_count": 2},
            {"question_id": "u", "answerable": False, "recall": None, "hit": None, "mrr": None, "returned_count": 5},
        ]
        s = compute_summary(per)
        assert s["answerable_count"] == 1 and s["unanswerable_count"] == 1
        assert s["evidence_recall"] == 1.0  # 分母仅可回答题
        assert s["empty_result_rate"] == 0.0  # 不足题有命中——有命中≠有依据
