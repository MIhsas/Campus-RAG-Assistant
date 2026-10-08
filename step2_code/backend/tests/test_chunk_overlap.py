"""T034 focused regressions for optional window overlap in chunking.

Covers exactly the task's required facts: default bytes/ID compatibility;
overlap spans verbatim with tail-window termination; one cross-hard-boundary
fact fully covered in the candidate but not the baseline; table_row handling
unchanged. Scoring semantics untouched — no gold-driven tuning here.
"""

from __future__ import annotations

import pytest

from campus_assistant.corpus.chunk import (
    STRATEGY,
    STRATEGY_OVERLAP,
    chunk_documents,
)

# Golden values captured from the historical default path (T034 pre-change).
GOLDEN_ID_FIRST = "5d015d30076156ab77c481b3880ba15488d88db27f5a15c047d7a8b6a0568db8"


def _para_doc(text: str, *, sha: str = "a" * 64) -> dict:
    return {
        "document_id": "d-golden",
        "parser_version": "1.0",
        "metadata": {"sha256": sha, "title": "t"},
        "warnings": [],
        "blocks": [{
            "block_id": "b1", "ordinal": 1, "kind": "paragraph", "text": text,
            "locator": {"type": "pdf_page", "page": 1}, "cells": None,
        }],
    }


def _table_doc(text: str, cells: list[str]) -> dict:
    return {
        "document_id": "d1",
        "parser_version": "1.0",
        "metadata": {"sha256": "a" * 64, "title": "t"},
        "warnings": [],
        "blocks": [{
            "block_id": "t1", "ordinal": 1, "kind": "table_row", "text": text,
            "locator": {"type": "pdf_page", "page": 1}, "cells": cells,
        }],
    }


class TestDefaultCompatibility:
    def test_default_ids_and_bytes_unchanged(self):
        doc = _para_doc("甲乙丙丁戊己庚辛壬癸" * 6)
        chunks = chunk_documents([doc], max_chars=7)
        assert chunks[0]["chunk_id"] == GOLDEN_ID_FIRST
        assert chunks[0]["strategy"] == STRATEGY
        assert "overlap_chars" not in chunks[0]
        # default dict schema unchanged (no new keys)
        expected_keys = {
            "chunk_id", "document_id", "block_id", "ordinal", "kind", "text",
            "char_start", "char_end", "locator", "cells", "metadata",
            "parser_version", "chunker_version", "strategy", "max_chars", "warnings",
        }
        assert set(chunks[0].keys()) == expected_keys

    def test_default_explicit_zero_matches_missing_param(self):
        doc = _para_doc("甲乙丙丁戊己庚辛")
        a = chunk_documents([doc], max_chars=5)
        b = chunk_documents([doc], max_chars=5, overlap_chars=0)
        assert [c["chunk_id"] for c in a] == [c["chunk_id"] for c in b]

    def test_overlap_ids_differ_from_default(self):
        doc = _para_doc("甲乙丙丁戊己庚辛")
        a = chunk_documents([doc], max_chars=5)
        b = chunk_documents([doc], max_chars=5, overlap_chars=2)
        assert a[0]["chunk_id"] != b[0]["chunk_id"]
        assert b[0]["strategy"] == STRATEGY_OVERLAP
        assert b[0]["overlap_chars"] == 2


class TestOverlapWindows:
    def test_spans_verbatim_and_step(self):
        text = "甲乙丙丁戊己庚辛壬癸" * 10  # 100 chars
        doc = _para_doc(text)
        chunks = chunk_documents([doc], max_chars=50, overlap_chars=10)
        assert [(c["char_start"], c["char_end"]) for c in chunks[:3]] == [
            (0, 50), (40, 90), (80, 100),
        ]
        for c in chunks:
            assert c["text"] == text[c["char_start"]:c["char_end"]]
            assert c["block_id"] == "b1" and c["document_id"] == "d-golden"

    def test_tail_window_terminates_no_extra(self):
        text = "x" * 950
        doc = _para_doc(text)
        chunks = chunk_documents([doc], max_chars=500, overlap_chars=100)
        spans = [(c["char_start"], c["char_end"]) for c in chunks]
        assert spans == [(0, 500), (400, 900), (800, 950)]  # stops at block tail

    def test_no_redundant_window_when_tail_exact(self):
        text = "x" * 900
        doc = _para_doc(text)
        chunks = chunk_documents([doc], max_chars=500, overlap_chars=100)
        assert [(c["char_start"], c["char_end"]) for c in chunks] == [(0, 500), (400, 900)]

    def test_invalid_overlap_rejected(self):
        doc = _para_doc("甲乙丙丁")
        for bad in (-1, 5, "1", True):
            with pytest.raises(ValueError):
                chunk_documents([doc], max_chars=5, overlap_chars=bad)


class TestBoundaryFactCoverage:
    def test_cross_hard_boundary_fact_covered_only_by_candidate(self):
        # Fact span [480, 560) crosses the 500-char hard boundary.
        text = "a" * 1000
        doc = _para_doc(text)
        baseline = chunk_documents([doc], max_chars=500, overlap_chars=0)
        candidate = chunk_documents([doc], max_chars=500, overlap_chars=100)
        target = (480, 560)

        def covers(chunks):
            return any(
                c["char_start"] <= target[0] and target[1] <= c["char_end"]
                for c in chunks
            )

        assert not covers(baseline), "baseline must split this fact at the hard boundary"
        assert covers(candidate), "candidate window must cover the whole fact"

    def test_table_row_unchanged_by_overlap(self):
        doc = _table_doc("成绩复核\t公布后10个工作日", ["成绩复核", "公布后10个工作日"])
        base = chunk_documents([doc], max_chars=100)
        cand = chunk_documents([doc], max_chars=100, overlap_chars=2)
        for chunks in (base, cand):
            assert len(chunks) == 1
            c = chunks[0]
            assert c["kind"] == "table_row"
            assert c["char_start"] == 0 and c["char_end"] == len(c["text"])
            assert c["cells"] == ["成绩复核", "公布后10个工作日"]
            assert c["warnings"] == []
        # overlap does not split or alter the row; only identity fields differ
        assert base[0]["text"] == cand[0]["text"]
        for f in ("document_id", "block_id", "kind", "char_start", "char_end", "cells", "max_chars"):
            assert base[0][f] == cand[0][f]
