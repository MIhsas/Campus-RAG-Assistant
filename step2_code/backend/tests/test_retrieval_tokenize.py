"""Tests for retrieval tokenizer (T007).

Hand-crafted cases per task contract.
"""

from __future__ import annotations

import pytest
from campus_assistant.retrieval.tokenize import tokenize


class TestCJK:
    def test_bigrams(self):
        assert tokenize("缓考申请") == ["缓考", "考申", "申请"]

    def test_single_char(self):
        assert tokenize("考") == ["考"]

    def test_separated_cjk(self):
        assert tokenize("缓，考") == ["缓", "考"]


class TestASCII:
    def test_lowercase(self):
        assert tokenize("ABC2024") == ["abc2024"]

    def test_number(self):
        assert tokenize("2024") == ["2024"]


class TestMixed:
    def test_contract_example(self):
        """缓考申请 2024 ABC → ['缓考','考申','申请','2024','abc']"""
        assert tokenize("缓考申请 2024 ABC") == ["缓考", "考申", "申请", "2024", "abc"]


class TestEdgeCases:
    def test_empty(self):
        assert tokenize("") == []

    def test_whitespace_only(self):
        assert tokenize("   ") == []

    def test_punctuation_only(self):
        assert tokenize("，。！？") == []

    def test_emoji_only(self):
        assert tokenize("😀😂") == []

    def test_mixed_separators(self):
        assert tokenize("缓考\n申请\t2024") == ["缓考", "申请", "2024"]


class TestValidation:
    def test_non_str_raises(self):
        with pytest.raises(ValueError, match="字符串"):
            tokenize(123)  # type: ignore

    def test_none_raises(self):
        with pytest.raises(ValueError, match="字符串"):
            tokenize(None)  # type: ignore
