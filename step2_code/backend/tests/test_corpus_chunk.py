"""Tests for corpus chunker (T006).

Covers: parameter validation, paragraph windowing, table_row passthrough,
chunk_id stability, metadata isolation, CLI behavior.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from campus_assistant.corpus.chunk import (
    CHUNKER_VERSION,
    TABLE_ROW_EXCEEDS_MAX_CHARS,
    chunk_documents,
    chunk_manifest,
)


# --- Helpers ---

def _make_doc(document_id="doc-1", blocks=None, warnings=None, **meta_overrides):
    """Build a minimal parse_manifest-format document dict."""
    meta = {
        "document_id": document_id,
        "policy_group_id": "g1",
        "title": "测试文档",
        "source_url": "https://example.org/doc",
        "source_site": "测试站",
        "local_path": "doc.txt",
        "sha256": "a" * 64,
        "version_label": "v1",
        "published_at": None,
        "effective_from": None,
        "effective_to": None,
        "scope": {"campus": [], "student_type": [], "admission_years": []},
        "is_synthetic": True,
    }
    meta.update(meta_overrides)
    return {
        "document_id": document_id,
        "metadata": meta,
        "parser_version": "1.0",
        "blocks": blocks or [],
        "warnings": warnings or [],
    }


def _make_para_block(block_id="b1", ordinal=1, text="甲乙丙丁戊"):
    return {
        "block_id": block_id,
        "ordinal": ordinal,
        "kind": "paragraph",
        "text": text,
        "locator": {"type": "lines", "line_start": 1, "line_end": 1},
    }


def _make_table_block(block_id="t1", ordinal=1, cells=None, text=None):
    if cells is None:
        cells = ["A", "B"]
    if text is None:
        text = "\t".join(cells)
    return {
        "block_id": block_id,
        "ordinal": ordinal,
        "kind": "table_row",
        "text": text,
        "locator": {"type": "table_row", "table_index": 1, "row_index": 1},
        "cells": cells,
    }


# --- Basic paragraph windowing ---

class TestParagraphWindowing:
    def test_exact_split(self):
        """text='甲乙丙丁戊', max_chars=2 → ['甲乙','丙丁','戊']"""
        doc = _make_doc(blocks=[_make_para_block(text="甲乙丙丁戊")])
        chunks = chunk_documents([doc], max_chars=2)
        texts = [c["text"] for c in chunks]
        assert texts == ["甲乙", "丙丁", "戊"]

    def test_char_ranges(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙丙丁戊")])
        chunks = chunk_documents([doc], max_chars=2)
        ranges = [(c["char_start"], c["char_end"]) for c in chunks]
        assert ranges == [(0, 2), (2, 4), (4, 5)]

    def test_concat_equals_original(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙丙丁戊")])
        chunks = chunk_documents([doc], max_chars=2)
        assert "".join(c["text"] for c in chunks) == "甲乙丙丁戊"

    def test_text_shorter_than_max(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙")])
        chunks = chunk_documents([doc], max_chars=100)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "甲乙"
        assert chunks[0]["char_start"] == 0
        assert chunks[0]["char_end"] == 2

    def test_exact_boundary(self):
        """Text exactly max_chars → single chunk."""
        text = "甲" * 500
        doc = _make_doc(blocks=[_make_para_block(text=text)])
        chunks = chunk_documents([doc], max_chars=500)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text

    def test_newlines_preserved(self):
        doc = _make_doc(blocks=[_make_para_block(text="第一行\n第二行\n第三行")])
        chunks = chunk_documents([doc], max_chars=5)
        assert "".join(c["text"] for c in chunks) == "第一行\n第二行\n第三行"

    def test_emoji_preserved(self):
        doc = _make_doc(blocks=[_make_para_block(text="A😀B😂C")])
        chunks = chunk_documents([doc], max_chars=3)
        assert "".join(c["text"] for c in chunks) == "A😀B😂C"

    def test_empty_text_no_chunk(self):
        doc = _make_doc(blocks=[_make_para_block(text="")])
        chunks = chunk_documents([doc], max_chars=100)
        assert len(chunks) == 0


# --- Table row ---

class TestTableRow:
    def test_one_chunk_per_row(self):
        block = _make_table_block(cells=["张三", "85", "高等数学"])
        doc = _make_doc(blocks=[block])
        chunks = chunk_documents([doc], max_chars=10)
        assert len(chunks) == 1
        assert chunks[0]["cells"] == ["张三", "85", "高等数学"]
        assert chunks[0]["kind"] == "table_row"

    def test_table_not_split(self):
        """Even if text exceeds max_chars, table_row is not split."""
        cells = ["很长的单元格内容" * 20, "B"]
        block = _make_table_block(cells=cells)
        doc = _make_doc(blocks=[block])
        chunks = chunk_documents([doc], max_chars=10)
        assert len(chunks) == 1
        assert TABLE_ROW_EXCEEDS_MAX_CHARS in chunks[0]["warnings"]

    def test_table_exceeds_warning(self):
        block = _make_table_block(cells=["A" * 600, "B"])
        doc = _make_doc(blocks=[block])
        chunks = chunk_documents([doc], max_chars=100)
        assert len(chunks) == 1
        assert any(TABLE_ROW_EXCEEDS_MAX_CHARS in w for w in chunks[0]["warnings"])

    def test_empty_cells_text_raises(self):
        """Empty text but non-empty cells → ValueError."""
        block = _make_table_block(cells=["A", "B"], text="  ")
        doc = _make_doc(blocks=[block])
        with pytest.raises(ValueError, match="cells"):
            chunk_documents([doc], max_chars=100)

    def test_table_char_range_covers_full_text(self):
        block = _make_table_block(text="A\tB\tC")
        doc = _make_doc(blocks=[block])
        chunks = chunk_documents([doc], max_chars=100)
        c = chunks[0]
        assert c["char_start"] == 0
        assert c["char_end"] == len("A\tB\tC")


# --- Multiple blocks and documents ---

class TestMultipleBlocks:
    def test_ordering(self):
        b1 = _make_para_block(block_id="b1", ordinal=1, text="甲乙丙丁戊")
        b2 = _make_table_block(block_id="t1", ordinal=2)
        b3 = _make_para_block(block_id="b2", ordinal=3, text="庚辛壬癸")
        doc = _make_doc(blocks=[b1, b2, b3])
        chunks = chunk_documents([doc], max_chars=2)
        # b1: "甲乙丙丁戊" → 3 chunks, t1: 1 chunk, b2: "庚辛壬癸" → 2 chunks = 6
        assert len(chunks) == 6
        # Verify block ordering: all b1 chunks before t1, t1 before b2
        b1_last = max(i for i, c in enumerate(chunks) if c["block_id"] == "b1")
        t1_idx = next(i for i, c in enumerate(chunks) if c["block_id"] == "t1")
        b2_first = min(i for i, c in enumerate(chunks) if c["block_id"] == "b2")
        assert b1_last < t1_idx < b2_first

    def test_ordinal_sequential(self):
        b1 = _make_para_block(text="甲乙丙丁戊")
        b2 = _make_para_block(block_id="b2", text="庚辛")
        doc = _make_doc(blocks=[b1, b2])
        chunks = chunk_documents([doc], max_chars=2)
        for i, c in enumerate(chunks):
            assert c["ordinal"] == i + 1

    def test_multi_document_ordering(self):
        d1 = _make_doc(document_id="d1", blocks=[_make_para_block(text="甲乙丙")])
        d2 = _make_doc(document_id="d2", blocks=[_make_para_block(text="丁戊己")])
        chunks = chunk_documents([d1, d2], max_chars=2)
        ids = [c["document_id"] for c in chunks]
        d1_indices = [i for i, x in enumerate(ids) if x == "d1"]
        d2_indices = [i for i, x in enumerate(ids) if x == "d2"]
        assert max(d1_indices) < min(d2_indices)

    def test_unsorted_blocks_sorted_by_ordinal(self):
        """R3: Blocks provided out of ordinal order must be sorted before chunking."""
        b_high = _make_para_block(block_id="b2", ordinal=3, text="后文")
        b_low = _make_para_block(block_id="b1", ordinal=1, text="前文")
        b_mid = _make_table_block(block_id="t1", ordinal=2)
        # Input: ordinal 3, 1, 2 — should be sorted to 1, 2, 3
        doc = _make_doc(blocks=[b_high, b_low, b_mid])
        chunks = chunk_documents([doc], max_chars=100)
        texts = [c["text"] for c in chunks]
        assert texts[0] == "前文"
        assert texts[-1] == "后文"
        # Verify input order unchanged
        assert doc["blocks"][0]["ordinal"] == 3
        assert doc["blocks"][1]["ordinal"] == 1


# --- Metadata isolation ---

class TestMetadataIsolation:
    def test_metadata_deep_copied(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙")])
        original_meta = copy.deepcopy(doc["metadata"])
        chunks = chunk_documents([doc], max_chars=100)
        chunks[0]["metadata"]["title"] = "CHANGED"
        assert doc["metadata"]["title"] == original_meta["title"]

    def test_metadata_fields_preserved(self):
        doc = _make_doc(
            blocks=[_make_para_block(text="甲乙")],
            published_at="2025-01-01",
            effective_from="2025-03-01",
        )
        chunks = chunk_documents([doc], max_chars=100)
        m = chunks[0]["metadata"]
        assert m["published_at"] == "2025-01-01"
        assert m["effective_from"] == "2025-03-01"
        assert m["scope"] == {"campus": [], "student_type": [], "admission_years": []}

    def test_sibling_metadata_independent(self):
        """R1: Modifying one chunk's metadata must not affect sibling."""
        doc = _make_doc(blocks=[_make_para_block(text="甲乙丙丁戊己庚辛壬癸")])
        chunks = chunk_documents([doc], max_chars=5)
        assert len(chunks) >= 2
        chunks[0]["metadata"]["scope"]["campus"].append("合成校区")
        assert chunks[1]["metadata"]["scope"]["campus"] == []
        assert doc["metadata"]["scope"]["campus"] == []

    def test_sibling_locator_independent(self):
        """R1: Modifying one chunk's locator must not affect sibling or input."""
        doc = _make_doc(blocks=[_make_para_block(text="甲乙丙丁戊己")])
        chunks = chunk_documents([doc], max_chars=3)
        assert len(chunks) >= 2
        original_loc = copy.deepcopy(chunks[1]["locator"])
        chunks[0]["locator"]["line_start"] = 999
        assert chunks[1]["locator"] == original_loc
        assert doc["blocks"][0]["locator"].get("line_start", 1) != 999


# --- Chunk ID stability ---

class TestChunkId:
    def test_deterministic(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙丙")])
        c1 = chunk_documents([doc], max_chars=2)
        c2 = chunk_documents([doc], max_chars=2)
        assert c1[0]["chunk_id"] == c2[0]["chunk_id"]

    def test_changes_with_text(self):
        """Different source text → different chunk_id (even if first window overlaps)."""
        doc1 = _make_doc(document_id="d1", blocks=[_make_para_block(text="甲乙丙")])
        doc2 = _make_doc(document_id="d2", blocks=[_make_para_block(text="丁戊己")])
        c1 = chunk_documents([doc1], max_chars=2)
        c2 = chunk_documents([doc2], max_chars=2)
        assert c1[0]["chunk_id"] != c2[0]["chunk_id"]

    def test_changes_with_max_chars(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙丙丁戊")])
        c1 = chunk_documents([doc], max_chars=2)
        c2 = chunk_documents([doc], max_chars=3)
        assert c1[0]["chunk_id"] != c2[0]["chunk_id"]

    def test_changes_with_sha256(self):
        doc1 = _make_doc(blocks=[_make_para_block(text="甲乙")], sha256="a" * 64)
        doc2 = _make_doc(blocks=[_make_para_block(text="甲乙")], sha256="b" * 64)
        c1 = chunk_documents([doc1], max_chars=100)
        c2 = chunk_documents([doc2], max_chars=100)
        assert c1[0]["chunk_id"] != c2[0]["chunk_id"]


# --- Chunk fields ---

class TestChunkFields:
    def test_required_fields(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙")])
        chunks = chunk_documents([doc], max_chars=100)
        c = chunks[0]
        required = [
            "chunk_id", "document_id", "block_id", "ordinal", "kind", "text",
            "char_start", "char_end", "locator", "cells", "metadata",
            "parser_version", "chunker_version", "strategy", "max_chars", "warnings",
        ]
        for f in required:
            assert f in c, f"missing field: {f}"

    def test_paragraph_cells_null(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙")])
        chunks = chunk_documents([doc], max_chars=100)
        assert chunks[0]["cells"] is None

    def test_strategy_and_version(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙")])
        chunks = chunk_documents([doc], max_chars=100)
        assert chunks[0]["chunker_version"] == CHUNKER_VERSION
        assert chunks[0]["strategy"] == "block_window_v1"
        assert chunks[0]["max_chars"] == 100

    def test_parser_version_from_doc(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙")])
        doc["parser_version"] = "2.0"
        chunks = chunk_documents([doc], max_chars=100)
        assert chunks[0]["parser_version"] == "2.0"


# --- Warnings ---

class TestWarnings:
    def test_doc_warnings_copied(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙")], warnings=["原始警告"])
        chunks = chunk_documents([doc], max_chars=100)
        assert "原始警告" in chunks[0]["warnings"]

    def test_warnings_independent(self):
        doc = _make_doc(blocks=[_make_para_block(text="甲乙")], warnings=["共享警告"])
        chunks = chunk_documents([doc], max_chars=100)
        chunks[0]["warnings"].append("新警告")
        # Re-chunk should not have the appended warning
        chunks2 = chunk_documents([doc], max_chars=100)
        assert "新警告" not in chunks2[0]["warnings"]


# --- Parameter validation ---

class TestParamValidation:
    def test_max_chars_zero(self):
        with pytest.raises(ValueError):
            chunk_documents([], max_chars=0)

    def test_max_chars_negative(self):
        with pytest.raises(ValueError):
            chunk_documents([], max_chars=-1)

    def test_max_chars_over_10000(self):
        with pytest.raises(ValueError):
            chunk_documents([], max_chars=10001)

    def test_max_chars_float(self):
        with pytest.raises(ValueError):
            chunk_documents([], max_chars=1.5)

    def test_max_chars_string(self):
        with pytest.raises(ValueError):
            chunk_documents([], max_chars="500")

    def test_max_chars_bool(self):
        with pytest.raises(ValueError):
            chunk_documents([], max_chars=True)

    def test_unknown_kind_raises(self):
        block = _make_para_block(text="甲乙")
        block["kind"] = "unknown_kind"
        doc = _make_doc(blocks=[block])
        with pytest.raises(ValueError, match="未知"):
            chunk_documents([doc], max_chars=100)


# --- Empty / edge cases ---

class TestEdgeCases:
    def test_empty_documents(self):
        assert chunk_documents([], max_chars=100) == []

    def test_doc_with_no_blocks(self):
        doc = _make_doc(blocks=[])
        assert chunk_documents([doc], max_chars=100) == []


# --- CLI ---

class TestCLI:
    @pytest.fixture()
    def corpus_dir(self, tmp_path):
        """Create a minimal corpus for CLI testing."""
        txt = tmp_path / "doc.txt"
        txt.write_text("第一条 内容\n\n第二条 内容\n", encoding="utf-8")
        sha = hashlib.sha256(txt.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "cli-doc",
                "policy_group_id": "g",
                "title": "CLI测试",
                "source_url": "https://example.org/",
                "source_site": "测试站",
                "local_path": "doc.txt",
                "sha256": sha,
                "version_label": "v1",
                "published_at": None,
                "effective_from": None,
                "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return tmp_path

    def _run_cli(self, tmp_path, mp, extra_args=None):
        args = [sys.executable, "-m", "campus_assistant.corpus.chunk",
                "--manifest", str(mp), "--corpus-root", str(tmp_path)]
        if extra_args:
            args.extend(extra_args)
        return subprocess.run(
            args, capture_output=True, encoding="utf-8", cwd=str(tmp_path),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_success(self, corpus_dir):
        mp = corpus_dir / "manifest.json"
        proc = self._run_cli(corpus_dir, mp)
        assert proc.returncode == 0
        out = json.loads(proc.stdout)
        assert out["valid"] is True
        assert out["chunk_count"] > 0
        assert out["chunker_version"] == "1.0"

    def test_custom_max_chars(self, corpus_dir):
        mp = corpus_dir / "manifest.json"
        proc = self._run_cli(corpus_dir, mp, ["--max-chars", "5"])
        assert proc.returncode == 0
        out = json.loads(proc.stdout)
        assert out["max_chars"] == 5

    def test_usage_error(self):
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.chunk"],
            capture_output=True, encoding="utf-8",
        )
        assert proc.returncode == 2

    def test_max_chars_zero_exits_2(self, corpus_dir):
        """R2: Invalid max_chars must exit 2 (argparse error), not 1."""
        mp = corpus_dir / "manifest.json"
        proc = self._run_cli(corpus_dir, mp, ["--max-chars", "0"])
        assert proc.returncode == 2
        assert proc.stdout.strip() == ""  # no JSON output

    def test_max_chars_negative_exits_2(self, corpus_dir):
        mp = corpus_dir / "manifest.json"
        proc = self._run_cli(corpus_dir, mp, ["--max-chars", "-1"])
        assert proc.returncode == 2
        assert proc.stdout.strip() == ""

    def test_max_chars_over_limit_exits_2(self, corpus_dir):
        mp = corpus_dir / "manifest.json"
        proc = self._run_cli(corpus_dir, mp, ["--max-chars", "10001"])
        assert proc.returncode == 2
        assert proc.stdout.strip() == ""

    def test_max_chars_non_integer_exits_2(self, corpus_dir):
        mp = corpus_dir / "manifest.json"
        proc = self._run_cli(corpus_dir, mp, ["--max-chars", "abc"])
        assert proc.returncode == 2

    def test_max_chars_boundary_1_valid(self, corpus_dir):
        """R2: max_chars=1 is valid lower boundary."""
        mp = corpus_dir / "manifest.json"
        proc = self._run_cli(corpus_dir, mp, ["--max-chars", "1"])
        assert proc.returncode == 0

    def test_max_chars_boundary_10000_valid(self, corpus_dir):
        """R2: max_chars=10000 is valid upper boundary."""
        mp = corpus_dir / "manifest.json"
        proc = self._run_cli(corpus_dir, mp, ["--max-chars", "10000"])
        assert proc.returncode == 0

    def test_manifest_not_found(self, tmp_path):
        proc = self._run_cli(tmp_path, tmp_path / "nope.json")
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert out["valid"] is False

    def test_parse_called_once(self, corpus_dir, monkeypatch):
        """Verify parse_manifest is called exactly once via chunk_manifest."""
        from campus_assistant.corpus import chunk as chunk_mod
        call_count = {"n": 0}
        original = chunk_mod._get_parse_result

        def counting(*args, **kwargs):
            call_count["n"] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(chunk_mod, "_get_parse_result", counting)
        mp = corpus_dir / "manifest.json"
        chunk_mod.chunk_manifest(mp, corpus_dir, max_chars=500)
        assert call_count["n"] == 1

    def test_partial_failure_preserves_chunks(self, tmp_path):
        """One good TXT + one bad DOCX → valid=false, good chunks preserved."""
        txt = tmp_path / "good.txt"
        txt.write_text("好内容\n", encoding="utf-8")
        txt_sha = hashlib.sha256(txt.read_bytes()).hexdigest()

        bad = tmp_path / "bad.docx"
        bad.write_bytes(b"PK\x03\x04not real")
        bad_sha = hashlib.sha256(bad.read_bytes()).hexdigest()

        manifest = {
            "schema_version": "1.0",
            "documents": [
                {
                    "document_id": "good", "policy_group_id": "g", "title": "好",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "good.txt", "sha256": txt_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
                {
                    "document_id": "bad", "policy_group_id": "g", "title": "坏",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
            ],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        proc = self._run_cli(tmp_path, mp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert out["valid"] is False
        assert out["chunk_count"] > 0  # good doc chunks preserved

    def test_output_is_utf8(self, corpus_dir):
        mp = corpus_dir / "manifest.json"
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.chunk",
             "--manifest", str(mp), "--corpus-root", str(corpus_dir)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={},
        )
        assert proc.returncode == 0
        text = proc.stdout.decode("utf-8")
        out = json.loads(text)
        assert out["valid"] is True


# --- chunk_manifest integration ---

class TestChunkManifest:
    def test_chunk_manifest_success(self, tmp_path):
        txt = tmp_path / "doc.txt"
        txt.write_text("段落一\n\n段落二\n", encoding="utf-8")
        sha = hashlib.sha256(txt.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "m-doc", "policy_group_id": "g", "title": "T",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "doc.txt", "sha256": sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        result = chunk_manifest(mp, tmp_path, max_chars=500)
        assert result["valid"] is True
        assert result["chunk_count"] >= 2
