"""Tests for evaluation metrics and models (T009).

Hand-calculated metrics tests, dataset validation, evidence reference checks.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from campus_assistant.evaluation.metrics import (
    _interval_overlap,
    _intervals_cover_target,
    compute_summary,
    evaluate_question,
)
from campus_assistant.evaluation.models import QuestionDataset


# ---------------------------------------------------------------------------
# Interval helpers
# ---------------------------------------------------------------------------

class TestIntervalOverlap:
    def test_no_overlap(self):
        assert _interval_overlap(0, 4, 5, 8) == 0

    def test_partial_overlap(self):
        assert _interval_overlap(0, 4, 2, 6) == 2

    def test_full_containment(self):
        assert _interval_overlap(0, 10, 2, 5) == 3

    def test_adjacent_no_overlap(self):
        assert _interval_overlap(0, 4, 4, 8) == 0

    def test_identical(self):
        assert _interval_overlap(2, 6, 2, 6) == 4


class TestIntervalsCoverTarget:
    def test_single_interval_covers(self):
        assert _intervals_cover_target([(0, 10)], 0, 10) is True

    def test_adjacent_intervals_cover(self):
        assert _intervals_cover_target([(0, 4), (4, 8)], 0, 8) is True

    def test_gap_not_covered(self):
        assert _intervals_cover_target([(0, 2), (6, 8)], 0, 8) is False

    def test_overlap_intervals_cover(self):
        assert _intervals_cover_target([(0, 5), (3, 8)], 0, 8) is True

    def test_partial_coverage(self):
        assert _intervals_cover_target([(0, 4)], 0, 8) is False

    def test_empty_target(self):
        assert _intervals_cover_target([], 5, 5) is True

    def test_empty_intervals(self):
        assert _intervals_cover_target([], 0, 10) is False


# ---------------------------------------------------------------------------
# Hand-calculated metrics (golden example from task)
# ---------------------------------------------------------------------------

class TestGoldenExample:
    """Gold: [0,4) and [6,8) in same block. Hits: rank1 wrong doc,
    rank2 same [0,2), rank3 same [2,4), rank4 same [6,8).
    """

    def _make_gold(self):
        return [
            {"evidence_id": "e1", "document_id": "d1", "document_sha256": "a" * 64,
             "parser_version": "1.0", "block_id": "b1", "char_start": 0, "char_end": 4, "quote": "ABCD"},
            {"evidence_id": "e2", "document_id": "d1", "document_sha256": "a" * 64,
             "parser_version": "1.0", "block_id": "b1", "char_start": 6, "char_end": 8, "quote": "EF"},
        ]

    def _make_hits(self, k):
        base_hits = [
            {"rank": 1, "score": 10.0, "chunk": {"document_id": "d2", "block_id": "b1", "chunk_id": "x", "char_start": 0, "char_end": 4}},
            {"rank": 2, "score": 8.0, "chunk": {"document_id": "d1", "block_id": "b1", "chunk_id": "y", "char_start": 0, "char_end": 2}},
            {"rank": 3, "score": 6.0, "chunk": {"document_id": "d1", "block_id": "b1", "chunk_id": "z", "char_start": 2, "char_end": 4}},
            {"rank": 4, "score": 4.0, "chunk": {"document_id": "d1", "block_id": "b1", "chunk_id": "w", "char_start": 6, "char_end": 8}},
        ]
        return base_hits[:k]

    def test_k2(self):
        q = {"question_id": "q1", "query": "test", "answerable": True, "evidence": self._make_gold()}
        r = evaluate_question(q, self._make_hits(2), top_k=2)
        assert r["recall"] == 0.0  # no evidence fully covered
        assert r["hit"] == 1.0     # rank2 has overlap with [0,4)
        assert r["mrr"] == 0.5     # first relevant at rank 2

    def test_k3(self):
        q = {"question_id": "q1", "query": "test", "answerable": True, "evidence": self._make_gold()}
        r = evaluate_question(q, self._make_hits(3), top_k=3)
        assert r["recall"] == 0.5  # [0,4) covered by ranks 2+3, [6,8) not
        assert r["hit"] == 1.0
        assert r["mrr"] == 0.5

    def test_k4(self):
        q = {"question_id": "q1", "query": "test", "answerable": True, "evidence": self._make_gold()}
        r = evaluate_question(q, self._make_hits(4), top_k=4)
        assert r["recall"] == 1.0  # both evidence covered
        assert r["hit"] == 1.0
        assert r["mrr"] == 0.5

    def test_duplicate_hit_no_extra_coverage(self):
        """Duplicate [0,2) should not cover [2,4)."""
        hits = [
            {"rank": 1, "score": 10.0, "chunk": {"document_id": "d1", "block_id": "b1", "chunk_id": "x", "char_start": 0, "char_end": 2}},
            {"rank": 2, "score": 8.0, "chunk": {"document_id": "d1", "block_id": "b1", "chunk_id": "y", "char_start": 0, "char_end": 2}},
        ]
        q = {"question_id": "q1", "query": "test", "answerable": True, "evidence": [
            {"evidence_id": "e1", "document_id": "d1", "document_sha256": "a" * 64,
             "parser_version": "1.0", "block_id": "b1", "char_start": 0, "char_end": 4, "quote": "ABCD"},
        ]}
        r = evaluate_question(q, hits, top_k=5)
        assert r["recall"] == 0.0  # only [0,2) x2, not covering [0,4)


# ---------------------------------------------------------------------------
# Additional metric edge cases
# ---------------------------------------------------------------------------

class TestMetricEdgeCases:
    def test_no_hits(self):
        q = {"question_id": "q1", "query": "test", "answerable": True,
             "evidence": [{"evidence_id": "e1", "document_id": "d1", "document_sha256": "a" * 64,
                           "parser_version": "1.0", "block_id": "b1", "char_start": 0, "char_end": 4, "quote": "ABCD"}]}
        r = evaluate_question(q, [], top_k=5)
        assert r["recall"] == 0.0
        assert r["hit"] == 0.0
        assert r["mrr"] == 0.0

    def test_unanswerable_no_gold(self):
        q = {"question_id": "q1", "query": "test", "answerable": False, "evidence": []}
        r = evaluate_question(q, [], top_k=5)
        assert r["answerable"] is False
        assert r["recall"] is None
        assert r["hit"] is None
        assert r["mrr"] is None
        assert r["gold_count"] == 0

    def test_two_evidence_units(self):
        hits = [
            {"rank": 1, "score": 10.0, "chunk": {"document_id": "d1", "block_id": "b1", "chunk_id": "x", "char_start": 0, "char_end": 5}},
            {"rank": 2, "score": 8.0, "chunk": {"document_id": "d1", "block_id": "b1", "chunk_id": "y", "char_start": 10, "char_end": 15}},
        ]
        q = {"question_id": "q1", "query": "test", "answerable": True, "evidence": [
            {"evidence_id": "e1", "document_id": "d1", "document_sha256": "a" * 64,
             "parser_version": "1.0", "block_id": "b1", "char_start": 0, "char_end": 5, "quote": "ABCDE"},
            {"evidence_id": "e2", "document_id": "d1", "document_sha256": "a" * 64,
             "parser_version": "1.0", "block_id": "b1", "char_start": 10, "char_end": 15, "quote": "FGHIJ"},
        ]}
        r = evaluate_question(q, hits, top_k=5)
        assert r["recall"] == 1.0
        assert r["hit"] == 1.0
        assert r["mrr"] == 1.0
        assert set(r["covered_evidence_ids"]) == {"e1", "e2"}

    def test_different_block_not_covered(self):
        hits = [
            {"rank": 1, "score": 10.0, "chunk": {"document_id": "d1", "block_id": "b2", "chunk_id": "x", "char_start": 0, "char_end": 10}},
        ]
        q = {"question_id": "q1", "query": "test", "answerable": True, "evidence": [
            {"evidence_id": "e1", "document_id": "d1", "document_sha256": "a" * 64,
             "parser_version": "1.0", "block_id": "b1", "char_start": 0, "char_end": 4, "quote": "ABCD"},
        ]}
        r = evaluate_question(q, hits, top_k=5)
        assert r["recall"] == 0.0
        assert r["hit"] == 0.0


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------

class TestComputeSummary:
    def test_mixed_questions(self):
        per_q = [
            {"answerable": True, "recall": 1.0, "hit": 1.0, "mrr": 0.5, "returned_count": 3},
            {"answerable": True, "recall": 0.5, "hit": 1.0, "mrr": 1.0, "returned_count": 2},
            {"answerable": False, "recall": None, "hit": None, "mrr": None, "returned_count": 0},
        ]
        s = compute_summary(per_q)
        assert abs(s["evidence_recall"] - 0.75) < 1e-9
        assert abs(s["hit"] - 1.0) < 1e-9
        assert abs(s["mrr"] - 0.75) < 1e-9
        assert s["answerable_count"] == 2
        assert s["unanswerable_count"] == 1
        assert abs(s["empty_result_rate"] - 1.0) < 1e-9

    def test_no_answerable(self):
        per_q = [{"answerable": False, "recall": None, "hit": None, "mrr": None, "returned_count": 1}]
        s = compute_summary(per_q)
        assert s["evidence_recall"] is None
        assert s["hit"] is None
        assert s["mrr"] is None

    def test_no_unanswerable(self):
        per_q = [{"answerable": True, "recall": 0.8, "hit": 1.0, "mrr": 0.5, "returned_count": 3}]
        s = compute_summary(per_q)
        assert s["empty_result_rate"] is None


# ---------------------------------------------------------------------------
# Dataset model validation
# ---------------------------------------------------------------------------

class TestDatasetValidation:
    def _valid_dataset(self, **overrides):
        d = {
            "schema_version": "1.0",
            "dataset_id": "test-ds",
            "dataset_version": "1.0",
            "split": "dev",
            "is_synthetic": True,
            "questions": [
                {
                    "question_id": "q1",
                    "query": "测试问题",
                    "answerable": True,
                    "evidence": [
                        {
                            "evidence_id": "e1",
                            "document_id": "doc1",
                            "document_sha256": "a" * 64,
                            "parser_version": "1.0",
                            "block_id": "b1",
                            "char_start": 0,
                            "char_end": 5,
                            "quote": "测试内容",
                        }
                    ],
                }
            ],
        }
        d.update(overrides)
        return d

    def test_valid_dataset(self):
        ds = QuestionDataset.model_validate(self._valid_dataset())
        assert ds.dataset_id == "test-ds"
        assert len(ds.questions) == 1

    def test_missing_field_rejected(self):
        d = self._valid_dataset()
        del d["dataset_id"]
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_unknown_field_rejected(self):
        d = self._valid_dataset()
        d["unknown_field"] = "value"
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_duplicate_question_id_rejected(self):
        d = self._valid_dataset()
        d["questions"].append(d["questions"][0].copy())
        with pytest.raises(Exception, match="重复"):
            QuestionDataset.model_validate(d)

    def test_empty_questions_rejected(self):
        d = self._valid_dataset(questions=[])
        with pytest.raises(Exception, match="空"):
            QuestionDataset.model_validate(d)

    def test_answerable_with_empty_evidence_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["evidence"] = []
        with pytest.raises(Exception, match="evidence"):
            QuestionDataset.model_validate(d)

    def test_unanswerable_with_evidence_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["answerable"] = False
        # evidence is still non-empty
        with pytest.raises(Exception, match="evidence"):
            QuestionDataset.model_validate(d)

    def test_unanswerable_empty_evidence_passes(self):
        d = self._valid_dataset()
        d["questions"][0]["answerable"] = False
        d["questions"][0]["evidence"] = []
        ds = QuestionDataset.model_validate(d)
        assert ds.questions[0].answerable is False

    def test_non_bool_answerable_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["answerable"] = "true"
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_non_integer_char_start_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["evidence"][0]["char_start"] = 1.5
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_start_ge_end_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["evidence"][0]["char_start"] = 10
        d["questions"][0]["evidence"][0]["char_end"] = 5
        with pytest.raises(Exception, match="char_start"):
            QuestionDataset.model_validate(d)

    def test_start_eq_end_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["evidence"][0]["char_start"] = 5
        d["questions"][0]["evidence"][0]["char_end"] = 5
        with pytest.raises(Exception, match="char_start"):
            QuestionDataset.model_validate(d)

    def test_bad_sha256_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["evidence"][0]["document_sha256"] = "not_hex"
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_bad_question_id_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["question_id"] = "bad id!"
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_empty_query_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["query"] = "   "
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_whitespace_only_evidence_id_rejected(self):
        d = self._valid_dataset()
        d["questions"][0]["evidence"][0]["evidence_id"] = "  "
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_empty_quote_passes(self):
        """Empty quote is a valid string."""
        d = self._valid_dataset()
        d["questions"][0]["evidence"][0]["quote"] = ""
        ds = QuestionDataset.model_validate(d)
        assert ds.questions[0].evidence[0].quote == ""

    def test_synthetic_false_with_synthetic_corpus_detected(self):
        """is_synthetic=false but corpus has synthetic docs — detected at eval level, not model."""
        d = self._valid_dataset(is_synthetic=False)
        ds = QuestionDataset.model_validate(d)
        assert ds.is_synthetic is False

    # R3: Strict is_synthetic
    def test_synthetic_string_true_rejected(self):
        d = self._valid_dataset()
        d["is_synthetic"] = "true"
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_synthetic_string_false_rejected(self):
        d = self._valid_dataset()
        d["is_synthetic"] = "false"
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_synthetic_int_rejected(self):
        d = self._valid_dataset()
        d["is_synthetic"] = 1
        with pytest.raises(Exception):
            QuestionDataset.model_validate(d)

    def test_synthetic_bool_accepted(self):
        d = self._valid_dataset(is_synthetic=True)
        ds = QuestionDataset.model_validate(d)
        assert ds.is_synthetic is True

    # R3: split must be "dev"
    def test_split_test_rejected(self):
        d = self._valid_dataset(split="test")
        with pytest.raises(Exception, match="dev"):
            QuestionDataset.model_validate(d)

    def test_split_unknown_rejected(self):
        d = self._valid_dataset(split="train")
        with pytest.raises(Exception, match="dev"):
            QuestionDataset.model_validate(d)

    def test_split_dev_accepted(self):
        d = self._valid_dataset(split="dev")
        ds = QuestionDataset.model_validate(d)
        assert ds.split == "dev"

    # R3: Duplicate evidence_id within question
    def test_duplicate_evidence_id_rejected(self):
        d = self._valid_dataset()
        ev1 = d["questions"][0]["evidence"][0].copy()
        ev1["evidence_id"] = "e01"
        ev2 = ev1.copy()
        ev2["evidence_id"] = "e01"  # same ID
        ev2["char_start"] = 20
        ev2["char_end"] = 30
        ev2["quote"] = "different"
        d["questions"][0]["evidence"] = [ev1, ev2]
        with pytest.raises(Exception, match="重复.*evidence_id"):
            QuestionDataset.model_validate(d)

    # R3: Duplicate source span within question
    def test_duplicate_source_span_rejected(self):
        d = self._valid_dataset()
        ev1 = d["questions"][0]["evidence"][0].copy()
        ev1["evidence_id"] = "e01"
        ev2 = ev1.copy()
        ev2["evidence_id"] = "e02"  # different ID, same span
        d["questions"][0]["evidence"] = [ev1, ev2]
        with pytest.raises(Exception, match="重复.*来源区间"):
            QuestionDataset.model_validate(d)

    # R3: Same block different span is OK
    def test_same_block_different_span_accepted(self):
        d = self._valid_dataset()
        ev1 = d["questions"][0]["evidence"][0].copy()
        ev1["evidence_id"] = "e01"
        ev1["char_start"] = 0
        ev1["char_end"] = 5
        ev1["quote"] = "abcde"
        ev2 = ev1.copy()
        ev2["evidence_id"] = "e02"
        ev2["char_start"] = 10
        ev2["char_end"] = 15
        ev2["quote"] = "fghij"
        d["questions"][0]["evidence"] = [ev1, ev2]
        ds = QuestionDataset.model_validate(d)
        assert len(ds.questions[0].evidence) == 2
