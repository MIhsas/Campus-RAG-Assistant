"""Tests for text-PDF parsing and corpus intake (T021).

Covers: multi-page extraction with stable block IDs and page locators,
verbatim citation spans, no-text/corrupt PDF handling, old TXT/DOCX block
IDs and template citations remaining unchanged, search/ask wiring, and the
registration CLI (success + missing metadata). No OCR, no network.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.corpus.parse import (
    PDF_PARSER_VERSION,
    PARSER_VERSION,
    parse_manifest,
)
from campus_assistant.main import create_app

BACKEND = Path(__file__).resolve().parents[1]
PDF_CORPUS = BACKEND / "examples" / "pdf-corpus"
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"
PROCEDURES = BACKEND / "examples" / "procedures" / "procedures.json"


@pytest.fixture(scope="module")
def pdf_parsed():
    r = parse_manifest(PDF_CORPUS / "manifest.json", PDF_CORPUS)
    return r


class TestPdfExtraction:
    def test_multispage_blocks_and_locators(self, pdf_parsed):
        docs = {d["document_id"]: d for d in pdf_parsed["documents"]}
        assert "syn-pdf-text-001" in docs
        doc = docs["syn-pdf-text-001"]
        assert doc["parser_version"] == PDF_PARSER_VERSION
        pages = {b["locator"]["page"] for b in doc["blocks"]}
        assert pages == {1, 2}, "两页均应有块"
        for b in doc["blocks"]:
            assert b["locator"]["type"] == "pdf_page"
            assert b["locator"]["part"] >= 1
            assert b["text"].strip()
        # 含数字与否定词的原文被逐字提取
        joined = "\n".join(b["text"] for b in doc["blocks"])
        assert "10 个工作日" in joined
        assert "2024 级" in joined
        assert "不重新评阅试卷" in joined
        assert "不得由他人代办" in joined

    def test_block_ids_stable_across_parses(self):
        r1 = parse_manifest(PDF_CORPUS / "manifest.json", PDF_CORPUS)
        r2 = parse_manifest(PDF_CORPUS / "manifest.json", PDF_CORPUS)
        ids1 = [b["block_id"] for d in r1["documents"] for b in d["blocks"]]
        ids2 = [b["block_id"] for d in r2["documents"] for b in d["blocks"]]
        assert ids1 == ids2 and len(ids1) == 2

    def test_citation_spans_match_parsed_blocks(self, pdf_parsed):
        # T021-R1：API evidence 跨度与解析块独立对照（非自证式切片）
        c = TestClient(
            create_app(manifest_path=PDF_CORPUS / "manifest.json", corpus_root=PDF_CORPUS),
            raise_server_exceptions=False,
        )
        a = c.post("/api/v1/ask", json={
            "query": "复核 分数", "top_k": 5, "mode": "bm25", "answer_mode": "extractive",
        }).json()
        blocks = {b["block_id"]: b for d in pdf_parsed["documents"] for b in d["blocks"]}
        assert a["evidence"]
        for ev in a["evidence"]:
            block = blocks[ev["block_id"]]
            assert block["text"][ev["char_start"]:ev["char_end"]] == ev["text"]
            assert ev["locator"]["type"] == "pdf_page"

    def test_no_text_pdf_not_indexed(self, pdf_parsed):
        ids = {d["document_id"] for d in pdf_parsed["documents"]}
        assert "syn-pdf-notext-001" not in ids
        errs = [e for e in pdf_parsed["errors"] if e.get("document_id") == "syn-pdf-notext-001"]
        assert errs and "未提取到文本" in errs[0]["message"]
        assert "OCR" in errs[0]["message"]

    def test_corrupt_pdf_fails_clearly(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"%PDF-1.7 this is not really a pdf")
        (tmp_path / "manifest.json").write_text(json.dumps({
            "schema_version": "1.0",
            "documents": [{
                "document_id": "bad-1", "policy_group_id": "g", "title": "t",
                "source_url": "https://example.org/p", "source_site": "s",
                "local_path": "bad.pdf",
                "sha256": hashlib.sha256(bad.read_bytes()).hexdigest(),
                "version_label": "v", "published_at": None, "effective_from": None,
                "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }), encoding="utf-8")
        r = parse_manifest(tmp_path / "manifest.json", tmp_path)
        assert not r["valid"]
        msgs = " ".join(e["message"] for e in r["errors"])
        assert "无法打开" in msgs or "损坏" in msgs or "提取" in msgs


class TestLegacyCompatibility:
    def test_txt_docx_block_ids_unchanged(self):
        # 旧块 ID（gold/模板引用所依赖）不得因 PDF 支持而改变
        r = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)
        ids = {b["block_id"] for d in r["documents"] for b in d["blocks"]}
        assert "9df6bfbd98df733e" in ids   # TXT 第二条（T012 起固定）
        assert "f28ee3e4c5372f7c" in ids   # DOCX 复核说明
        for d in r["documents"]:
            assert d["parser_version"] == PARSER_VERSION

    def test_template_citations_still_validate(self, tmp_path):
        # procedures 模板引用在旧语料上仍可通过核查（跨度与哈希不变）
        from campus_assistant.procedures.service import build_draft, load_procedures

        procedures = load_procedures(PROCEDURES)
        r = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)
        d = build_draft(procedures, "proc-apply-defer", {"admission_year": 2024}, r["documents"])
        assert d["saveable"] is True


class TestSearchAskWiring:
    def test_pdf_hits_carry_page_and_jump(self):
        c = TestClient(
            create_app(manifest_path=PDF_CORPUS / "manifest.json", corpus_root=PDF_CORPUS),
            raise_server_exceptions=False,
        )
        s = c.post("/api/v1/search", json={"query": "复核 分数", "top_k": 5, "mode": "bm25"}).json()
        assert s["hits"], "PDF 文本应可检索"
        hit = s["hits"][0]
        assert hit["chunk"]["locator"]["type"] == "pdf_page"
        assert hit["preview_url"].startswith("/preview#")
        a = c.post("/api/v1/ask", json={
            "query": "复核 分数", "top_k": 5, "mode": "bm25", "answer_mode": "extractive",
        }).json()
        assert a["status"] == "evidence_only"
        ev = a["evidence"][0]
        assert ev["locator"]["type"] == "pdf_page"
        assert ev["preview_url"].startswith("/preview#")
        assert ev["text"]


class TestRegisterCli:
    def _meta(self, doc_id="reg-001"):
        return {
            "document_id": doc_id, "policy_group_id": "reg-group", "title": "登记测试",
            "source_url": "https://example.org/p", "source_site": "测试站",
            "version_label": "v1", "published_at": None, "effective_from": None,
            "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": True,
        }

    def test_register_success(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("第一条 登记测试文本。", encoding="utf-8")
        meta = tmp_path / "meta.json"
        meta.write_text(json.dumps(self._meta()), encoding="utf-8")
        out = tmp_path / "pkg"
        proc = subprocess.run(
            [sys.executable, str(BACKEND / "scripts" / "register-corpus.py"),
             "--input", str(src), "--meta", str(meta), "--out-dir", str(out)],
            capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(BACKEND),
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert (out / "manifest.json").is_file()
        assert (out / "doc.txt").is_file()
        assert "启动命令" in proc.stdout
        m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert m["documents"][0]["sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
        # 输入文件未被修改
        assert src.read_text(encoding="utf-8") == "第一条 登记测试文本。"

    def test_register_missing_metadata_lists_fields(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("内容", encoding="utf-8")
        meta = tmp_path / "meta.json"
        meta.write_text(json.dumps({"document_id": "x"}), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(BACKEND / "scripts" / "register-corpus.py"),
             "--input", str(src), "--meta", str(meta), "--out-dir", str(tmp_path / "pkg")],
            capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(BACKEND),
        )
        assert proc.returncode == 2
        assert "缺少必填元数据字段" in proc.stdout
        assert "policy_group_id" in proc.stdout
        assert not (tmp_path / "pkg").exists()

    def test_register_refuses_nonempty_outdir(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("内容", encoding="utf-8")
        meta = tmp_path / "meta.json"
        meta.write_text(json.dumps(self._meta()), encoding="utf-8")
        out = tmp_path / "pkg"
        out.mkdir()
        (out / "existing.txt").write_text("x", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(BACKEND / "scripts" / "register-corpus.py"),
             "--input", str(src), "--meta", str(meta), "--out-dir", str(out)],
            capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(BACKEND),
        )
        assert proc.returncode == 2
        assert "拒绝覆盖" in proc.stdout
