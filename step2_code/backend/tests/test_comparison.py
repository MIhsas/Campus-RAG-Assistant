"""Tests for deterministic policy version comparison (T017).

Covers: added/deleted/modified/unchanged classification on the comparison
fixture, insertion without index-shift misalignment, left/right swap
symmetry, citation spans matching parsed blocks, and selection constraints
(same doc / cross policy group rejection). No model calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.comparison.service import compare_documents, group_versions
from campus_assistant.main import create_app

BACKEND = Path(__file__).resolve().parents[1]
CMP_CORPUS = BACKEND / "examples" / "comparison-corpus"


@pytest.fixture(scope="module")
def cmp_documents():
    from campus_assistant.corpus.parse import parse_manifest

    r = parse_manifest(CMP_CORPUS / "manifest.json", CMP_CORPUS)
    assert r["valid"]
    return {d["document_id"]: d for d in r["documents"]}


class TestFixtureClassification:
    def test_four_categories(self, cmp_documents):
        d = compare_documents(cmp_documents["cmp-defer-v1"], cmp_documents["cmp-defer-v2"])
        counts = d["counts"]
        assert counts == {"added": 1, "deleted": 1, "modified": 1, "unchanged": 3}
        by_key = {e["clause_key"]: e for e in d["entries"] if e["clause_key"]}
        assert by_key["第一条"]["change_type"] == "unchanged"
        assert by_key["第二条"]["change_type"] == "modified"
        assert by_key["第三条"]["change_type"] == "deleted"
        assert by_key["第四条"]["change_type"] == "added"
        # 修改条款句内差异：5 → 3
        segs = by_key["第二条"]["diff_segments"]
        assert any(s["op"] == "delete" and s["text"] == "5" for s in segs)
        assert any(s["op"] == "insert" and s["text"] == "3" for s in segs)

    def test_verbatim_texts_and_spans(self, cmp_documents):
        d = compare_documents(cmp_documents["cmp-defer-v1"], cmp_documents["cmp-defer-v2"])
        docs = {"cmp-defer-v1": cmp_documents["cmp-defer-v1"], "cmp-defer-v2": cmp_documents["cmp-defer-v2"]}
        for e in d["entries"]:
            for side in ("left", "right"):
                ref = e[side]
                if ref is None:
                    continue
                block = next(
                    b for b in docs[ref["document_id"]]["blocks"] if b["block_id"] == ref["block_id"]
                )
                assert block["text"][ref["char_start"]:ref["char_end"]] == ref["text"]
                assert ref["document_sha256"]
                assert ref["preview_url"].startswith("/preview#")

    def test_swap_exchanges_added_deleted(self, cmp_documents):
        d12 = compare_documents(cmp_documents["cmp-defer-v1"], cmp_documents["cmp-defer-v2"])
        d21 = compare_documents(cmp_documents["cmp-defer-v2"], cmp_documents["cmp-defer-v1"])
        assert d21["counts"]["added"] == d12["counts"]["deleted"]
        assert d21["counts"]["deleted"] == d12["counts"]["added"]
        assert d21["counts"]["modified"] == d12["counts"]["modified"]
        assert d21["counts"]["unchanged"] == d12["counts"]["unchanged"]
        # 同条款修改仍为修改（方向对调体现在 segments 左右）
        by_key_21 = {e["clause_key"]: e for e in d21["entries"] if e["clause_key"]}
        assert by_key_21["第二条"]["change_type"] == "modified"


class TestAlignmentRobustness:
    def test_insertion_does_not_shift_later_clauses(self):
        # in-memory docs: v1 A/B/C，v2 A/插入块/B/C —— 插入一条后 B/C 不得假修改
        def mk(doc_id, lines):
            return {
                "document_id": doc_id,
                "metadata": {"policy_group_id": "g", "sha256": "a" * 64, "title": "t",
                             "version_label": "v", "published_at": None,
                             "effective_from": None, "effective_to": None,
                             "scope": {}, "is_synthetic": True},
                "blocks": [
                    {"block_id": f"{doc_id}-b{i}", "ordinal": i + 1, "kind": "paragraph",
                     "text": t, "locator": {}, "cells": None}
                    for i, t in enumerate(lines)
                ],
            }

        left = mk("L", ["第一条 内容甲。", "第二条 内容乙。", "第三条 内容丙。"])
        right = mk("R", ["第一条 内容甲。", "补充 无标识插入文本示例一二三四五六七八九十。", "第二条 内容乙。", "第三条 内容丙。"])
        d = compare_documents(left, right)
        by_key = {e["clause_key"]: e for e in d["entries"] if e["clause_key"]}
        assert by_key["第一条"]["change_type"] == "unchanged"
        assert by_key["第二条"]["change_type"] == "unchanged"
        assert by_key["第三条"]["change_type"] == "unchanged"
        assert d["counts"] == {"added": 1, "deleted": 0, "modified": 0, "unchanged": 3}

    def test_modified_unnumbered_pairing(self):
        def mk(doc_id, lines):
            return {
                "document_id": doc_id,
                "metadata": {"policy_group_id": "g", "sha256": "b" * 64, "title": "t",
                             "version_label": "v", "published_at": None,
                             "effective_from": None, "effective_to": None,
                             "scope": {}, "is_synthetic": True},
                "blocks": [
                    {"block_id": f"{doc_id}-b{i}", "ordinal": i + 1, "kind": "paragraph",
                     "text": t, "char_start": 0, "char_end": len(t), "locator": {}, "cells": None}
                    for i, t in enumerate(lines)
                ],
            }

        left = mk("L", ["前言说明文本完全一致。", "本条说明为申请材料须知内容较多的一段文字说明。"])
        right = mk("R", ["前言说明文本完全一致。", "本条说明为申请材料须知内容略有改动的一段文字说明。"])
        d = compare_documents(left, right)
        assert d["counts"]["unchanged"] == 1
        assert d["counts"]["modified"] == 1


class TestT017R1Lookahead:
    """T017-R1：无编号相似度前瞻分支方向（新增+修改场景）。"""

    @staticmethod
    def _mk(doc_id, texts):
        return {
            "document_id": doc_id,
            "metadata": {"policy_group_id": "same"},
            "blocks": [
                {"block_id": str(i), "kind": "paragraph", "ordinal": i, "text": t}
                for i, t in enumerate(texts)
            ],
        }

    @pytest.fixture()
    def pair(self):
        left = self._mk("v1", ["申请材料须交所在学院审核。"])
        right = self._mk("v2", ["这是一段完全不同的新公告。", "申请材料须交所在学院审核，并签字。"])
        return left, right

    def test_forward_add_plus_modify(self, pair):
        left, right = pair
        d = compare_documents(left, right)
        assert d["counts"] == {"added": 1, "deleted": 0, "modified": 1, "unchanged": 0}
        mod = next(e for e in d["entries"] if e["change_type"] == "modified")
        assert mod["left"]["text"] == "申请材料须交所在学院审核。"
        assert mod["right"]["text"] == "申请材料须交所在学院审核，并签字。"
        added = next(e for e in d["entries"] if e["change_type"] == "added")
        assert added["right"]["text"] == "这是一段完全不同的新公告。"
        for e in d["entries"]:
            for side in ("left", "right"):
                ref = e[side]
                if ref is not None:
                    assert ref["char_start"] == 0
                    assert ref["char_end"] == len(ref["text"])  # 跨度与解析块逐字一致

    def test_backward_delete_plus_modify(self, pair):
        left, right = pair
        d = compare_documents(right, left)
        assert d["counts"] == {"added": 0, "deleted": 1, "modified": 1, "unchanged": 0}
        mod = next(e for e in d["entries"] if e["change_type"] == "modified")
        assert mod["left"]["text"] == "申请材料须交所在学院审核，并签字。"
        assert mod["right"]["text"] == "申请材料须交所在学院审核。"
        deleted = next(e for e in d["entries"] if e["change_type"] == "deleted")
        assert deleted["left"]["text"] == "这是一段完全不同的新公告。"

    def test_unrelated_blocks_not_force_paired(self):
        left = self._mk("v1", ["甲乙丙丁戊戌庚辛壬癸子丑寅卯辰巳午未申酉戌亥甲乙丙丁戊戌庚辛壬癸。"])
        right = self._mk("v2", ["一二三四五六七八九十十一十二十三十四十五十六十七十八十九二十廿一廿二廿三。"])
        d = compare_documents(left, right)
        assert d["counts"] == {"added": 1, "deleted": 1, "modified": 0, "unchanged": 0}

    def test_paragraph_only_limitation_documented(self):
        from campus_assistant.comparison.service import LIMITATIONS

        assert any("表格" in x for x in LIMITATIONS)
        assert any("直接归入新增/删除" in x for x in LIMITATIONS)


class TestSelectionConstraints:
    def test_same_document_rejected(self, cmp_documents):
        with pytest.raises(ValueError, match="LEFT_RIGHT_SAME"):
            compare_documents(cmp_documents["cmp-defer-v1"], cmp_documents["cmp-defer-v1"])

    def test_cross_policy_group_rejected(self, cmp_documents):
        with pytest.raises(ValueError, match="CROSS_POLICY_GROUP"):
            compare_documents(cmp_documents["cmp-defer-v1"], cmp_documents["cmp-grades-1"])

    def test_group_versions_listing(self, cmp_documents):
        groups = group_versions(list(cmp_documents.values()))
        by_id = {g["policy_group_id"]: g for g in groups}
        assert set(by_id) == {"syn-cmp-defer", "syn-cmp-grades"}
        assert {v["document_id"] for v in by_id["syn-cmp-defer"]["versions"]} == {"cmp-defer-v1", "cmp-defer-v2"}
        assert len(by_id["syn-cmp-grades"]["versions"]) == 1


class TestApiRoutes:
    def test_not_configured_503(self, tmp_path):
        c = TestClient(create_app(), raise_server_exceptions=False)
        assert c.get("/api/v1/comparison/groups").status_code == 503
        r = c.post("/api/v1/comparison", json={"left_document_id": "a", "right_document_id": "b"})
        assert r.status_code == 503

    def test_configured_flow(self, tmp_path):
        c = TestClient(
            create_app(manifest_path=CMP_CORPUS / "manifest.json", corpus_root=CMP_CORPUS),
            raise_server_exceptions=False,
        )
        g = c.get("/api/v1/comparison/groups")
        assert g.status_code == 200
        assert len(g.json()["groups"]) == 2
        r = c.post("/api/v1/comparison", json={"left_document_id": "cmp-defer-v1", "right_document_id": "cmp-defer-v2"})
        assert r.status_code == 200
        d = r.json()
        assert d["counts"]["modified"] == 1
        assert d["left"]["version_label"] == "虚构 2024 版"
        assert d["right"]["version_label"] == "虚构 2025 版"
        assert d["disclaimer"]
        assert d["algorithm"]["limitations"]
        r2 = c.post("/api/v1/comparison", json={"left_document_id": "cmp-defer-v1", "right_document_id": "cmp-grades-1"})
        assert r2.status_code == 400
        assert r2.json()["code"] == "CROSS_POLICY_GROUP"
        r3 = c.post("/api/v1/comparison", json={"left_document_id": "cmp-defer-v1", "right_document_id": "cmp-defer-v1"})
        assert r3.status_code == 400
        assert r3.json()["code"] == "LEFT_RIGHT_SAME"
        r4 = c.post("/api/v1/comparison", json={"left_document_id": "nope", "right_document_id": "cmp-defer-v2"})
        assert r4.status_code == 404
