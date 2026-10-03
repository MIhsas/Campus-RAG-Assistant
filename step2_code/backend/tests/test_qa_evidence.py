"""Tests for evidence pack construction (T012).

Covers: excerpt/span consistency with the original block, request-scoped
E-ids, chunk dedup, whole-item char budget with skip counts, and the
budget_empty / no_hits / no_admissible_docs distinction.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from campus_assistant.corpus.chunk import chunk_documents
from campus_assistant.corpus.parse import parse_manifest
from campus_assistant.qa.evidence import build_evidence_pack


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _make_manifest(tmp_path: Path, docs: list[tuple[str, str, dict]]) -> Path:
    manifest_docs = []
    for fname, content, meta in docs:
        fpath = tmp_path / fname
        _write_text(fpath, content)
        sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        manifest_docs.append({
            "document_id": meta.get("document_id", fname.replace(".txt", "")),
            "policy_group_id": "g",
            "title": meta.get("title", fname),
            "source_url": "https://example.org/policy",
            "source_site": "测试站",
            "local_path": fname,
            "sha256": sha,
            "version_label": meta.get("version_label", "v1"),
            "published_at": meta.get("published_at"),
            "effective_from": meta.get("effective_from"),
            "effective_to": meta.get("effective_to"),
            "scope": meta.get("scope", {"campus": [], "student_type": [], "admission_years": []}),
            "is_synthetic": True,
        })
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps({"schema_version": "1.0", "documents": manifest_docs}, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp


def _hit(chunk: dict, rank: int) -> dict:
    doc_id = chunk["document_id"]
    block_id = chunk["block_id"]
    return {
        "rank": rank,
        "score": 1.0,
        "chunk": chunk,
        "preview_url": f"/preview#{quote(doc_id, safe='')}/{quote(block_id, safe='')}",
        "matched_terms": [],
        "bm25_rank": None,
        "dense_rank": None,
        "bm25_score": None,
        "dense_score": None,
    }


def _chunk(doc_id: str, text: str, *, chunk_id: str, start: int = 0, end: int | None = None) -> dict:
    return {
        "chunk_id": chunk_id,
        "document_id": doc_id,
        "block_id": "b1",
        "ordinal": 1,
        "kind": "paragraph",
        "text": text,
        "char_start": start,
        "char_end": end if end is not None else start + len(text),
        "locator": {},
        "cells": None,
        "metadata": {
            "sha256": "a" * 64,
            "title": f"文档{doc_id}",
            "source_url": "https://example.org/policy",
            "version_label": "v1",
            "scope": {"campus": ["成都校区"], "student_type": [], "admission_years": []},
            "published_at": "2025-01-01",
            "effective_from": "2025-03-01",
            "effective_to": None,
            "is_synthetic": True,
        },
        "parser_version": "1.0",
        "chunker_version": "1.0",
        "strategy": "block_window_v1",
        "max_chars": 500,
        "warnings": [],
    }


class TestExcerptConsistency:
    def test_span_matches_original_block(self, tmp_path: Path) -> None:
        content = "缓考申请须经所在学院批准。\n补考成绩最高记为60分。\n转专业需要满足成绩要求。"
        mp = _make_manifest(tmp_path, [("doc.txt", content, {"title": "跨度测试"})])
        parsed = parse_manifest(mp, tmp_path)
        assert parsed["valid"]
        chunks = chunk_documents(parsed["documents"], max_chars=500)
        blocks = {b["block_id"]: b for d in parsed["documents"] for b in d["blocks"]}

        pack = build_evidence_pack([_hit(c, i + 1) for i, c in enumerate(chunks)])
        assert pack["evidence_state"] == "ok"
        for ev in pack["evidence"]:
            block = blocks[ev["block_id"]]
            # half-open span reproduces the excerpt exactly — no rewrite/stitch
            assert block["text"][ev["char_start"]:ev["char_end"]] == ev["text"]
            assert ev["char_end"] - ev["char_start"] == len(ev["text"])

    def test_request_scoped_ids_and_fields(self) -> None:
        hits = [_hit(_chunk("d1", "第一条缓考规定", chunk_id="c1"), 1)]
        pack = build_evidence_pack(hits)
        ev = pack["evidence"][0]
        assert ev["evidence_id"] == "E1"
        assert ev["document_id"] == "d1"
        assert ev["chunk_id"] == "c1"
        assert ev["document_sha256"] == "a" * 64
        assert ev["title"] == "文档d1"
        assert ev["source_url"] == "https://example.org/policy"
        assert ev["version_label"] == "v1"
        assert ev["scope"] == {"campus": ["成都校区"], "student_type": [], "admission_years": []}
        assert ev["effective_from"] == "2025-03-01"
        assert ev["effective_to"] is None
        assert ev["is_synthetic"] is True
        assert ev["preview_url"].startswith("/preview#")

    def test_duplicate_chunks_removed(self) -> None:
        c = _chunk("d1", "重复命中同一条", chunk_id="c1")
        pack = build_evidence_pack([_hit(c, 1), _hit(c, 2), _hit(c, 3)])
        assert len(pack["evidence"]) == 1
        assert pack["budget"]["duplicate_chunks"] == 2


class TestBudget:
    def test_whole_in_or_out_and_skip_count(self) -> None:
        hits = [
            _hit(_chunk("d1", "x" * 5000, chunk_id="c1"), 1),
            _hit(_chunk("d2", "y" * 2500, chunk_id="c2"), 2),
            _hit(_chunk("d3", "z" * 400, chunk_id="c3"), 3),
        ]
        pack = build_evidence_pack(hits, max_items=5, max_total_chars=6000)
        ids = [e["evidence_id"] for e in pack["evidence"]]
        texts = [e["text"] for e in pack["evidence"]]
        # c1 fits, c2 does not fit the remainder (whole-out), c3 fits after it
        assert ids == ["E1", "E2"]
        assert texts[0] == "x" * 5000
        assert texts[1] == "z" * 400
        assert pack["budget"]["skipped_items"] == 1
        assert pack["budget"]["included_chars"] == 5400
        # included items are full — never truncated
        for e in pack["evidence"]:
            assert e["char_end"] - e["char_start"] == len(e["text"])

    def test_max_items_cap(self) -> None:
        hits = [_hit(_chunk("d1", f"第{i}条", chunk_id=f"c{i}"), i + 1) for i in range(7)]
        pack = build_evidence_pack(hits, max_items=5, max_total_chars=6000)
        assert len(pack["evidence"]) == 5
        assert pack["budget"]["skipped_items"] == 2

    def test_budget_empty_distinct_from_no_hits(self) -> None:
        overlong = [_hit(_chunk("d1", "w" * 7000, chunk_id="c1"), 1)]
        pack = build_evidence_pack(overlong)
        assert pack["evidence"] == []
        assert pack["evidence_state"] == "budget_empty"
        assert pack["budget"]["skipped_items"] == 1

        empty = build_evidence_pack([], filter_summary={"active": False, "allowed_count": 2})
        assert empty["evidence_state"] == "no_hits"

        filtered = build_evidence_pack(
            [], filter_summary={"active": True, "allowed_count": 0}
        )
        assert filtered["evidence_state"] == "no_admissible_docs"

    def test_no_summary_fabricated_for_skipped(self) -> None:
        # Skipped items simply leave the pack — no summary field is invented.
        pack = build_evidence_pack([_hit(_chunk("d1", "w" * 7000, chunk_id="c1"), 1)])
        assert pack["evidence"] == []
        assert "summaries" not in pack
        assert "summary" not in pack
