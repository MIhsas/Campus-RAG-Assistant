"""Tests for BM25 index (T007).

Arithmetic golden example, isolation, ordering, edge cases.
"""

from __future__ import annotations

import math
import copy
import pytest
from campus_assistant.retrieval.bm25 import BM25Index


def _chunk(chunk_id="c1", text="apple", **extra):
    c = {"chunk_id": chunk_id, "text": text, "document_id": "d1", "block_id": "b1"}
    c.update(extra)
    return c


class TestArithmeticGolden:
    def test_two_apple_chunks(self):
        """Two chunks both text='apple'. N=2, df=2, dl=avgdl=1, tf=1.
        idf = ln(1 + (2-2+0.5)/(2+0.5)) = ln(1.2) ≈ 0.1823215568
        contrib = idf * 1*2.5 / (1 + 1.5*(1-0.75+0.75*1/1)) = idf * 2.5 / 2.5 = idf
        """
        idx = BM25Index([_chunk("c1", "apple"), _chunk("c2", "apple")])
        hits = idx.search("apple", top_k=10)
        assert len(hits) == 2
        expected_idf = math.log(1 + (2 - 2 + 0.5) / (2 + 0.5))
        for h in hits:
            assert abs(h["score"] - expected_idf) < 1e-10

    def test_tie_break_by_id(self):
        """Same score → sorted by chunk_id ascending."""
        idx = BM25Index([_chunk("z-chunk", "apple"), _chunk("a-chunk", "apple")])
        hits = idx.search("apple", top_k=10)
        assert hits[0]["chunk"]["chunk_id"] == "a-chunk"
        assert hits[1]["chunk"]["chunk_id"] == "z-chunk"


class TestTermFrequencySaturation:
    def test_repeated_term(self):
        """Higher tf should give higher score, but saturates."""
        idx = BM25Index([_chunk("c1", "apple"), _chunk("c2", "apple apple apple")])
        hits = idx.search("apple", top_k=10)
        # c2 has tf=3, c1 has tf=1 → c2 should score higher
        assert hits[0]["chunk"]["chunk_id"] == "c2"


class TestLengthNormalization:
    def test_longer_doc_penalized(self):
        """Longer doc (more tokens) gets length penalty when b>0."""
        idx = BM25Index([
            _chunk("short", "apple"),
            _chunk("long", "apple banana cherry date elderberry"),
        ])
        hits = idx.search("apple", top_k=10)
        # short doc should score higher due to length normalization
        assert hits[0]["chunk"]["chunk_id"] == "short"


class TestUnknownTerm:
    def test_no_match(self):
        idx = BM25Index([_chunk("c1", "apple")])
        hits = idx.search("banana", top_k=10)
        assert hits == []


class TestEmptyIndex:
    def test_empty_chunks(self):
        idx = BM25Index([])
        assert idx.search("anything", top_k=5) == []

    def test_all_empty_text(self):
        idx = BM25Index([_chunk("c1", ""), _chunk("c2", "")])
        assert idx.search("test", top_k=5) == []


class TestValidChunkCount:
    def test_all_valid(self):
        idx = BM25Index([_chunk("c1", "apple"), _chunk("c2", "banana")])
        assert idx.valid_chunk_count == 2

    def test_empty_excluded(self):
        idx = BM25Index([_chunk("c1", "apple"), _chunk("c2", ""), _chunk("c3", "banana")])
        assert idx.valid_chunk_count == 2

    def test_all_empty(self):
        idx = BM25Index([_chunk("c1", ""), _chunk("c2", "")])
        assert idx.valid_chunk_count == 0

    def test_punctuation_only_excluded(self):
        idx = BM25Index([_chunk("c1", "!!!"), _chunk("c2", "apple")])
        assert idx.valid_chunk_count == 1


class TestTopK:
    def test_top_k_limits(self):
        chunks = [_chunk(f"c{i}", f"word{i}") for i in range(10)]
        idx = BM25Index(chunks)
        hits = idx.search("word1", top_k=3)
        assert len(hits) <= 3


class TestDuplicateQueryTerms:
    def test_repeated_query_not_double_weighted(self):
        """Query 'apple apple' should not double-count."""
        idx = BM25Index([_chunk("c1", "apple")])
        hits_single = idx.search("apple", top_k=5)
        hits_double = idx.search("apple apple", top_k=5)
        assert abs(hits_single[0]["score"] - hits_double[0]["score"]) < 1e-10


class TestContributionSum:
    def test_contributions_match_score(self):
        idx = BM25Index([_chunk("c1", "apple banana"), _chunk("c2", "apple cherry")])
        hits = idx.search("apple banana", top_k=10)
        for h in hits:
            contrib_sum = sum(mt["contribution"] for mt in h["matched_terms"])
            assert abs(contrib_sum - h["score"]) < 1e-10


class TestDuplicateChunkId:
    def test_duplicate_id_raises(self):
        with pytest.raises(ValueError, match="重复"):
            BM25Index([_chunk("c1", "a"), _chunk("c1", "b")])


class TestDeepCopyIsolation:
    def test_input_not_modified(self):
        chunks = [_chunk("c1", "apple")]
        original = copy.deepcopy(chunks)
        idx = BM25Index(chunks)
        chunks[0]["text"] = "CHANGED"
        assert idx._chunks[0]["text"] == "apple"

    def test_result_isolation(self):
        idx = BM25Index([_chunk("c1", "apple")])
        hits = idx.search("apple", top_k=5)
        hits[0]["chunk"]["text"] = "MODIFIED"
        hits2 = idx.search("apple", top_k=5)
        assert hits2[0]["chunk"]["text"] == "apple"


class TestParamValidation:
    def test_k1_zero(self):
        with pytest.raises(ValueError, match="k1"):
            BM25Index([], k1=0)

    def test_k1_negative(self):
        with pytest.raises(ValueError, match="k1"):
            BM25Index([], k1=-1)

    def test_k1_bool(self):
        with pytest.raises(ValueError, match="k1"):
            BM25Index([], k1=True)  # type: ignore

    def test_b_negative(self):
        with pytest.raises(ValueError, match="b"):
            BM25Index([], b=-0.1)

    def test_b_over_one(self):
        with pytest.raises(ValueError, match="b"):
            BM25Index([], b=1.1)

    def test_b_bool(self):
        with pytest.raises(ValueError, match="b"):
            BM25Index([], b=False)  # type: ignore

    def test_top_k_zero(self):
        idx = BM25Index([_chunk("c1", "a")])
        with pytest.raises(ValueError, match="top_k"):
            idx.search("a", top_k=0)

    def test_top_k_bool(self):
        idx = BM25Index([_chunk("c1", "a")])
        with pytest.raises(ValueError, match="top_k"):
            idx.search("a", top_k=True)  # type: ignore


class TestMatchedTerms:
    def test_matched_terms_fields(self):
        idx = BM25Index([_chunk("c1", "apple banana")])
        hits = idx.search("apple", top_k=5)
        mt = hits[0]["matched_terms"]
        assert len(mt) == 1
        assert mt[0]["term"] == "apple"
        assert mt[0]["tf"] == 1
        assert mt[0]["df"] == 1
        assert "idf" in mt[0]
        assert "contribution" in mt[0]

    def test_only_positive_matches(self):
        idx = BM25Index([_chunk("c1", "apple")])
        hits = idx.search("apple banana", top_k=5)
        terms = [mt["term"] for mt in hits[0]["matched_terms"]]
        assert "banana" not in terms
        assert "apple" in terms


class TestPreviewUrl:
    def test_url_encoded(self):
        idx = BM25Index([_chunk("c1", "apple", document_id="d/1", block_id="b#1")])
        hits = idx.search("apple", top_k=5)
        url = hits[0]["preview_url"]
        assert url.startswith("/preview#")
        assert "d%2F1" in url or "d/1" not in url  # encoded
        assert "%23" in url  # # encoded
