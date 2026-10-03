"""Tests for document body parsing (T004).

Each negative test uses a valid baseline, breaks ONE target field,
asserts the exact error code. Positive tests verify block structure and locators.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from campus_assistant.corpus.parse import (
    DOCUMENT_PARSE_ERROR,
    EMPTY_DOCUMENT,
    PARSER_VERSION,
    UNSUPPORTED_FORMAT,
    parse_docx,
    parse_manifest,
    parse_txt,
)
from campus_assistant.corpus.validate import (
    FILE_NOT_FOUND,
    HASH_MISMATCH,
    MANIFEST_READ_ERROR,
    MANIFEST_SCHEMA_ERROR,
    UNSAFE_LOCAL_PATH,
)

# --- Helpers ---

_BOM = b"\xef\xbb\xbf"


def _write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.write_text(content, encoding=encoding)


def _write_bytes(path: Path, content: bytes) -> None:
    path.write_bytes(content)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _make_docx(path: Path, paragraphs: list[str] | None = None,
               tables: list[list[list[str]]] | None = None,
               interleaved: list[tuple[str, str]] | None = None) -> None:
    """Create a DOCX file with specified content.

    interleaved: list of ("para", text) or ("table", rows_spec) tuples.
    """
    doc = DocxDocument()
    if interleaved:
        for kind, content in interleaved:
            if kind == "para":
                doc.add_paragraph(content)
            elif kind == "table":
                # content is list of lists
                rows = content
                if rows:
                    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
                    t.style = "Table Grid"
                    for r, row in enumerate(rows):
                        for c, val in enumerate(row):
                            t.rows[r].cells[c].text = val
    else:
        for p in (paragraphs or []):
            doc.add_paragraph(p)
        for table_data in (tables or []):
            if table_data:
                t = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                t.style = "Table Grid"
                for r, row in enumerate(table_data):
                    for c, val in enumerate(row):
                        t.rows[r].cells[c].text = val
    doc.save(str(path))


def _valid_txt_manifest(tmp_path: Path, content: str = "段落一\n\n段落二\n") -> tuple[Path, Path]:
    """Create a valid TXT + manifest. Returns (manifest_path, corpus_root)."""
    txt_path = tmp_path / "doc.txt"
    _write_text(txt_path, content)
    sha = _hash_file(txt_path)
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "test-txt",
            "policy_group_id": "g",
            "title": "测试TXT",
            "source_url": "https://example.org/doc",
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
    return mp, tmp_path


def _valid_docx_manifest(tmp_path: Path, **docx_kwargs) -> tuple[Path, Path]:
    """Create a valid DOCX + manifest. Returns (manifest_path, corpus_root)."""
    docx_path = tmp_path / "doc.docx"
    _make_docx(docx_path, **docx_kwargs)
    sha = _hash_file(docx_path)
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "test-docx",
            "policy_group_id": "g",
            "title": "测试DOCX",
            "source_url": "https://example.org/doc",
            "source_site": "测试站",
            "local_path": "doc.docx",
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
    return mp, tmp_path


def _has_error(result: dict, code: str, field: str | None = None) -> bool:
    for e in result["errors"]:
        if e["code"] == code:
            if field is None or field in e["field"]:
                return True
    return False


# ===================================================================
# TXT parsing
# ===================================================================

class TestTxtChinese:
    def test_multi_paragraph(self, tmp_path: Path) -> None:
        mp, root = _valid_txt_manifest(tmp_path, "第一条 内容\n\n第二条 内容\n\n第三条 内容\n")
        result = parse_manifest(mp, root)
        assert result["valid"] is True
        assert len(result["documents"]) == 1
        blocks = result["documents"][0]["blocks"]
        assert len(blocks) == 3
        assert blocks[0]["kind"] == "paragraph"
        assert "第一条" in blocks[0]["text"]
        assert blocks[0]["ordinal"] == 1
        assert blocks[1]["ordinal"] == 2

    def test_chinese_content_preserved(self, tmp_path: Path) -> None:
        content = "高等数学A1 成绩：85分\n\n缓考申请须在考前3个工作日提交\n"
        mp, root = _valid_txt_manifest(tmp_path, content)
        result = parse_manifest(mp, root)
        blocks = result["documents"][0]["blocks"]
        assert "高等数学A1" in blocks[0]["text"]
        assert "85分" in blocks[0]["text"]
        assert "缓考" in blocks[1]["text"]


class TestTxtBom:
    def test_bom_accepted(self, tmp_path: Path) -> None:
        content = _BOM + "带BOM的内容\n\n第二段\n".encode("utf-8")
        txt_path = tmp_path / "bom.txt"
        _write_bytes(txt_path, content)
        sha = _hash_file(txt_path)
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "bom-test", "policy_group_id": "g", "title": "BOM",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "bom.txt", "sha256": sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is True
        blocks = result["documents"][0]["blocks"]
        assert "带BOM的内容" in blocks[0]["text"]


class TestTxtCRLF:
    def test_cRLF_normalized(self, tmp_path: Path) -> None:
        content = "第一段\r\n\r\n第二段\r\n"
        mp, root = _valid_txt_manifest(tmp_path, content)
        result = parse_manifest(mp, root)
        assert result["valid"] is True
        blocks = result["documents"][0]["blocks"]
        assert len(blocks) == 2
        assert "\r" not in blocks[0]["text"]


class TestTxtLineLocator:
    def test_line_numbers_correct(self, tmp_path: Path) -> None:
        # Lines 1-2: paragraph 1, line 3: blank, lines 4-5: paragraph 2
        content = "第一行\n第二行\n\n第四行\n第五行\n"
        mp, root = _valid_txt_manifest(tmp_path, content)
        result = parse_manifest(mp, root)
        blocks = result["documents"][0]["blocks"]
        assert blocks[0]["locator"]["line_start"] == 1
        assert blocks[0]["locator"]["line_end"] == 2
        assert blocks[1]["locator"]["line_start"] == 4
        assert blocks[1]["locator"]["line_end"] == 5

    def test_locator_type_is_lines(self, tmp_path: Path) -> None:
        mp, root = _valid_txt_manifest(tmp_path, "内容\n")
        result = parse_manifest(mp, root)
        assert result["documents"][0]["blocks"][0]["locator"]["type"] == "lines"


# ===================================================================
# DOCX parsing
# ===================================================================

class TestDocxInterleaving:
    def test_para_table_para_order(self, tmp_path: Path) -> None:
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[
            ("para", "段落一"),
            ("table", [["A", "B"], ["1", "2"]]),
            ("para", "段落二"),
        ])
        result = parse_manifest(mp, root)
        assert result["valid"] is True
        blocks = result["documents"][0]["blocks"]
        assert len(blocks) == 4  # para + header row + data row + para
        assert blocks[0]["kind"] == "paragraph"
        assert "段落一" in blocks[0]["text"]
        assert blocks[1]["kind"] == "table_row"
        assert blocks[2]["kind"] == "table_row"
        assert blocks[3]["kind"] == "paragraph"
        assert "段落二" in blocks[3]["text"]

    def test_ordinals_sequential(self, tmp_path: Path) -> None:
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[
            ("para", "P1"),
            ("table", [["H1", "H2"], ["C1", "C2"]]),
            ("para", "P2"),
        ])
        result = parse_manifest(mp, root)
        blocks = result["documents"][0]["blocks"]
        for i, b in enumerate(blocks):
            assert b["ordinal"] == i + 1


class TestDocxTableRows:
    def test_table_cells_array(self, tmp_path: Path) -> None:
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[
            ("table", [["姓名", "成绩"], ["张三", "85"], ["李四", "92"]]),
        ])
        result = parse_manifest(mp, root)
        blocks = result["documents"][0]["blocks"]
        assert len(blocks) == 3
        assert blocks[0]["cells"] == ["姓名", "成绩"]
        assert blocks[1]["cells"] == ["张三", "85"]
        assert blocks[0]["text"] == "姓名\t成绩"

    def test_table_locator(self, tmp_path: Path) -> None:
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[
            ("table", [["A", "B"], ["1", "2"]]),
        ])
        result = parse_manifest(mp, root)
        blocks = result["documents"][0]["blocks"]
        assert blocks[0]["locator"]["type"] == "table_row"
        assert blocks[0]["locator"]["table_index"] == 1
        assert blocks[0]["locator"]["row_index"] == 1
        assert blocks[1]["locator"]["row_index"] == 2


class TestDocxEmptyParagraph:
    def test_empty_para_skipped_but_index_counts(self, tmp_path: Path) -> None:
        """Empty paragraph should not produce a block but should increment index."""
        doc = DocxDocument()
        doc.add_paragraph("第一段")
        doc.add_paragraph("")  # empty
        doc.add_paragraph("第三段")
        docx_path = tmp_path / "empty_para.docx"
        doc.save(str(docx_path))
        sha = _hash_file(docx_path)
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "ep-test", "policy_group_id": "g", "title": "T",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "empty_para.docx", "sha256": sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        blocks = result["documents"][0]["blocks"]
        assert len(blocks) == 2
        assert blocks[0]["locator"]["paragraph_index"] == 1
        assert blocks[1]["locator"]["paragraph_index"] == 3  # index 2 was empty


# ===================================================================
# Block ID stability
# ===================================================================

class TestBlockIdStability:
    def test_deterministic_across_runs(self, tmp_path: Path) -> None:
        mp, root = _valid_txt_manifest(tmp_path, "段落A\n\n段落B\n")
        r1 = parse_manifest(mp, root)
        r2 = parse_manifest(mp, root)
        b1 = r1["documents"][0]["blocks"]
        b2 = r2["documents"][0]["blocks"]
        assert b1[0]["block_id"] == b2[0]["block_id"]
        assert b1[1]["block_id"] == b2[1]["block_id"]

    def test_different_content_different_id(self, tmp_path: Path) -> None:
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        mp1, root1 = _valid_txt_manifest(dir_a, "内容一\n")
        mp2, root2 = _valid_txt_manifest(dir_b, "内容二\n")
        r1 = parse_manifest(mp1, root1)
        r2 = parse_manifest(mp2, root2)
        # Different document_id → different block_id
        assert r1["documents"][0]["blocks"][0]["block_id"] != r2["documents"][0]["blocks"][0]["block_id"]

    def test_same_doc_id_same_hash_stable(self, tmp_path: Path) -> None:
        """Same document_id + same sha256 + same content → same block_id."""
        mp, root = _valid_txt_manifest(tmp_path, "稳定内容\n")
        result = parse_manifest(mp, root)
        bid = result["documents"][0]["blocks"][0]["block_id"]
        # Parse again
        result2 = parse_manifest(mp, root)
        assert result2["documents"][0]["blocks"][0]["block_id"] == bid


# ===================================================================
# Negative cases
# ===================================================================

class TestEmptyFile:
    def test_empty_txt(self, tmp_path: Path) -> None:
        mp, root = _valid_txt_manifest(tmp_path, "")
        result = parse_manifest(mp, root)
        assert result["valid"] is False
        assert _has_error(result, EMPTY_DOCUMENT)

    def test_whitespace_only_txt(self, tmp_path: Path) -> None:
        mp, root = _valid_txt_manifest(tmp_path, "   \n\n  \n")
        result = parse_manifest(mp, root)
        assert result["valid"] is False
        assert _has_error(result, EMPTY_DOCUMENT)


class TestCorruptDocx:
    def test_corrupt_docx(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "bad.docx"
        _write_bytes(bad_path, b"PK\x03\x04not a real docx")
        sha = _hash_file(bad_path)
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "bad-docx", "policy_group_id": "g", "title": "T",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "bad.docx", "sha256": sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert _has_error(result, DOCUMENT_PARSE_ERROR)


class TestUnsupportedFormat:
    def test_unsupported_extension_rejected(self, tmp_path: Path) -> None:
        # T021 起 .pdf 已受支持（文本 PDF）；不支持格式仍应明确拒绝
        bin_path = tmp_path / "doc.png"
        _write_bytes(bin_path, b"\x89PNG fake")
        sha = _hash_file(bin_path)
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "png-test", "policy_group_id": "g", "title": "T",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "doc.png", "sha256": sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert _has_error(result, UNSUPPORTED_FORMAT)


class TestHashMismatchNoParse:
    def test_bad_hash_no_parse(self, tmp_path: Path) -> None:
        """When hash doesn't match, parsing should not execute."""
        txt_path = tmp_path / "doc.txt"
        _write_text(txt_path, "内容\n")
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "hm-test", "policy_group_id": "g", "title": "T",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "doc.txt", "sha256": "0" * 64, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is False
        # Should fail at validation (hash mismatch), not at parsing
        assert _has_error(result, HASH_MISMATCH)


class TestNonUtf8Txt:
    def test_non_utf8_rejected(self, tmp_path: Path) -> None:
        txt_path = tmp_path / "bad.txt"
        _write_bytes(txt_path, b"\xff\xfe\x00\x00not-utf8")
        sha = _hash_file(txt_path)
        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "enc-test", "policy_group_id": "g", "title": "T",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "bad.txt", "sha256": sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert _has_error(result, DOCUMENT_PARSE_ERROR)


class TestBatchPartialFailure:
    def test_one_good_one_bad(self, tmp_path: Path) -> None:
        """One valid TXT, one corrupt DOCX. Valid one still parsed."""
        txt_path = tmp_path / "good.txt"
        _write_text(txt_path, "好内容\n")
        txt_sha = _hash_file(txt_path)

        bad_path = tmp_path / "bad.docx"
        _write_bytes(bad_path, b"PK\x03\x04not real")
        bad_sha = _hash_file(bad_path)

        manifest = {
            "schema_version": "1.0",
            "documents": [
                {
                    "document_id": "good-doc", "policy_group_id": "g", "title": "好",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "good.txt", "sha256": txt_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
                {
                    "document_id": "bad-doc", "policy_group_id": "g", "title": "坏",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
            ],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert _has_error(result, DOCUMENT_PARSE_ERROR)
        # Good doc should still be parsed
        assert len(result["documents"]) == 1
        assert result["documents"][0]["document_id"] == "good-doc"


# --- R1: InvalidXmlError isolation ---

class TestInvalidXmlDocxIsolation:
    def _make_bad_docx(self, path: Path) -> None:
        """Create a DOCX with malformed gridSpan that triggers InvalidXmlError."""
        from docx import Document as D
        from docx.oxml.ns import qn
        d = D()
        d.add_paragraph("段落")
        t = d.add_table(rows=1, cols=2)
        t.rows[0].cells[0].text = "A"
        t.rows[0].cells[1].text = "B"
        # Inject malformed gridSpan missing required w:val
        tc = t._tbl.findall(qn("w:tr"))[0].findall(qn("w:tc"))[0]
        tc_pr = tc.find(qn("w:tcPr"))
        if tc_pr is None:
            tc_pr = tc.makeelement(qn("w:tcPr"), {})
            tc.insert(0, tc_pr)
        gs = tc_pr.makeelement(qn("w:gridSpan"), {})
        tc_pr.insert(0, gs)
        d.save(str(path))

    def test_invalid_xml_with_good_txt(self, tmp_path: Path) -> None:
        """R1: Bad DOCX (InvalidXmlError) + good TXT → partial, good doc preserved."""
        txt_path = tmp_path / "good.txt"
        _write_text(txt_path, "好内容\n")
        txt_sha = _hash_file(txt_path)

        bad_path = tmp_path / "bad.docx"
        self._make_bad_docx(bad_path)
        bad_sha = _hash_file(bad_path)

        manifest = {
            "schema_version": "1.0",
            "documents": [
                {
                    "document_id": "good-txt", "policy_group_id": "g", "title": "好",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "good.txt", "sha256": txt_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
                {
                    "document_id": "bad-docx", "policy_group_id": "g", "title": "坏",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
            ],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert _has_error(result, DOCUMENT_PARSE_ERROR)
        assert len(result["documents"]) == 1
        assert result["documents"][0]["document_id"] == "good-txt"

    def test_only_bad_docx(self, tmp_path: Path) -> None:
        """R1: Only bad DOCX → failed, no documents."""
        bad_path = tmp_path / "bad.docx"
        self._make_bad_docx(bad_path)
        bad_sha = _hash_file(bad_path)

        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "bad-docx", "policy_group_id": "g", "title": "坏",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert len(result["documents"]) == 0


class TestSourceNotModified:
    def test_txt_not_modified(self, tmp_path: Path) -> None:
        content = "原始内容\n\n第二段\n"
        mp, root = _valid_txt_manifest(tmp_path, content)
        txt_path = tmp_path / "doc.txt"
        before = txt_path.read_bytes()
        parse_manifest(mp, root)
        after = txt_path.read_bytes()
        assert before == after

    def test_docx_not_modified(self, tmp_path: Path) -> None:
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[("para", "内容")])
        docx_path = tmp_path / "doc.docx"
        before = docx_path.read_bytes()
        parse_manifest(mp, root)
        after = docx_path.read_bytes()
        assert before == after


# ===================================================================
# CLI subprocess
# ===================================================================

class TestCLI:
    def _run_cli(self, tmp_path: Path, mp: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.parse",
             "--manifest", str(mp), "--corpus-root", str(tmp_path)],
            capture_output=True, encoding="utf-8", cwd=str(tmp_path),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_success_txt(self, tmp_path: Path) -> None:
        mp, root = _valid_txt_manifest(tmp_path, "段落一\n\n段落二\n")
        proc = self._run_cli(root, mp)
        assert proc.returncode == 0
        out = json.loads(proc.stdout)
        assert out["valid"] is True
        assert len(out["documents"]) == 1
        assert len(out["documents"][0]["blocks"]) == 2

    def test_success_docx(self, tmp_path: Path) -> None:
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[
            ("para", "段落"), ("table", [["A", "B"], ["1", "2"]]),
        ])
        proc = self._run_cli(root, mp)
        assert proc.returncode == 0
        out = json.loads(proc.stdout)
        assert out["valid"] is True
        assert len(out["documents"][0]["blocks"]) == 3

    def test_empty_file_exit_1(self, tmp_path: Path) -> None:
        mp, root = _valid_txt_manifest(tmp_path, "")
        proc = self._run_cli(root, mp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert out["valid"] is False
        assert _has_error(out, EMPTY_DOCUMENT)

    def test_usage_error_exit_2(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.parse"],
            capture_output=True, encoding="utf-8",
        )
        assert proc.returncode == 2

    def test_manifest_not_found(self, tmp_path: Path) -> None:
        proc = self._run_cli(tmp_path, tmp_path / "nope.json")
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert _has_error(out, MANIFEST_READ_ERROR)


# ===================================================================
# R1: Table row locator offset
# ===================================================================

class TestTableRowLocator:
    def test_empty_first_row(self, tmp_path: Path) -> None:
        """First row empty: second row should have row_index=2."""
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[
            ("table", [["", ""], ["A", "B"], ["C", "D"]]),
        ])
        result = parse_manifest(mp, root)
        blocks = result["documents"][0]["blocks"]
        # Empty first row skipped, A/B = row 2, C/D = row 3
        assert len(blocks) == 2
        assert blocks[0]["locator"]["row_index"] == 2
        assert blocks[1]["locator"]["row_index"] == 3

    def test_empty_middle_row(self, tmp_path: Path) -> None:
        """Middle row empty: locator reflects source positions."""
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[
            ("table", [["A", "B"], ["", ""], ["C", "D"]]),
        ])
        result = parse_manifest(mp, root)
        blocks = result["documents"][0]["blocks"]
        assert len(blocks) == 2
        assert blocks[0]["locator"]["row_index"] == 1
        assert blocks[1]["locator"]["row_index"] == 3

    def test_consecutive_empty_rows(self, tmp_path: Path) -> None:
        """Multiple consecutive empty rows: locator gaps correctly."""
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[
            ("table", [["A", "B"], ["", ""], ["", ""], ["C", "D"]]),
        ])
        result = parse_manifest(mp, root)
        blocks = result["documents"][0]["blocks"]
        assert blocks[0]["locator"]["row_index"] == 1
        assert blocks[1]["locator"]["row_index"] == 4


# ===================================================================
# R2: DOCX parse exception isolation
# ===================================================================

class TestDocxParseIsolation:
    def _make_truncated_docx(self, path: Path) -> None:
        """Create a DOCX with truncated document.xml (fails at open)."""
        import zipfile, io
        from docx import Document as D
        d = D()
        d.add_paragraph("test")
        d.save(str(path))
        # Rewrite ZIP with truncated document.xml
        with zipfile.ZipFile(str(path), "r") as zin:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename == "word/document.xml":
                        data = data[: len(data) // 2]
                    zout.writestr(item, data)
            path.write_bytes(buf.getvalue())

    def test_corrupt_docx_with_good_txt(self, tmp_path: Path) -> None:
        """Corrupt DOCX + good TXT: valid=false, good doc preserved."""
        txt_path = tmp_path / "good.txt"
        _write_text(txt_path, "好内容\n")
        txt_sha = _hash_file(txt_path)

        bad_path = tmp_path / "bad.docx"
        self._make_truncated_docx(bad_path)
        bad_sha = _hash_file(bad_path)

        manifest = {
            "schema_version": "1.0",
            "documents": [
                {
                    "document_id": "good-txt", "policy_group_id": "g", "title": "好",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "good.txt", "sha256": txt_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
                {
                    "document_id": "bad-docx", "policy_group_id": "g", "title": "坏",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
            ],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        result = parse_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert _has_error(result, DOCUMENT_PARSE_ERROR)
        assert len(result["documents"]) == 1
        assert result["documents"][0]["document_id"] == "good-txt"

    def test_corrupt_docx_subprocess_no_traceback(self, tmp_path: Path) -> None:
        """R2: Corrupt DOCX via subprocess: JSON output, no traceback."""
        bad_path = tmp_path / "bad.docx"
        self._make_truncated_docx(bad_path)
        bad_sha = _hash_file(bad_path)

        manifest = {
            "schema_version": "1.0",
            "documents": [{
                "document_id": "bad", "policy_group_id": "g", "title": "T",
                "source_url": "https://example.org/", "source_site": "S",
                "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                "published_at": None, "effective_from": None, "effective_to": None,
                "scope": {"campus": [], "student_type": [], "admission_years": []},
                "is_synthetic": True,
            }],
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.parse",
             "--manifest", str(mp), "--corpus-root", str(tmp_path)],
            capture_output=True, encoding="utf-8", cwd=str(tmp_path),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert out["valid"] is False
        assert _has_error(out, DOCUMENT_PARSE_ERROR)
        assert "Traceback" not in (proc.stderr or "")


# ===================================================================
# R3: CLI UTF-8 output without PYTHONIOENCODING
# ===================================================================

class TestCliUtf8Output:
    def test_utf8_output_without_env_var(self, tmp_path: Path) -> None:
        """R3: CLI should output UTF-8 even without PYTHONIOENCODING set."""
        content = "高等数学A1成绩：85分，含α系数\n\n第二段\n"
        mp, root = _valid_txt_manifest(tmp_path, content)
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.parse",
             "--manifest", str(mp), "--corpus-root", str(tmp_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(tmp_path),
            env={},  # minimal env, no PYTHONIOENCODING
        )
        assert proc.returncode == 0
        # stdout must be valid UTF-8
        text = proc.stdout.decode("utf-8")
        out = json.loads(text)
        assert out["valid"] is True
        assert "高等数学" in out["documents"][0]["blocks"][0]["text"]

    def test_utf8_failure_without_env_var(self, tmp_path: Path) -> None:
        """R3: Error output is also UTF-8 without env var."""
        mp, root = _valid_txt_manifest(tmp_path, "")
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.parse",
             "--manifest", str(mp), "--corpus-root", str(tmp_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(tmp_path),
            env={},
        )
        assert proc.returncode == 1
        text = proc.stdout.decode("utf-8")
        out = json.loads(text)
        assert out["valid"] is False


# ===================================================================
# R4: Undetected content warnings
# ===================================================================

def _make_docx_and_parse(tmp_path: Path, docx_builder) -> dict:
    """Helper: build DOCX, create manifest, parse, return result."""
    from docx import Document as D
    d = D()
    docx_builder(d)
    docx_path = tmp_path / "test.docx"
    d.save(str(docx_path))
    sha = _hash_file(docx_path)
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "w-test", "policy_group_id": "g", "title": "T",
            "source_url": "https://example.org/", "source_site": "S",
            "local_path": "test.docx", "sha256": sha, "version_label": "v",
            "published_at": None, "effective_from": None, "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": True,
        }],
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    return parse_manifest(mp, tmp_path)


class TestDocxWarnings:
    def test_horizontal_merge_detected(self, tmp_path: Path) -> None:
        def build(d):
            d.add_paragraph("内容")
            t = d.add_table(rows=2, cols=3)
            t.rows[0].cells[0].text = "A"
            t.rows[0].cells[1].text = "B"
            t.rows[0].cells[2].text = "C"
            t.rows[1].cells[0].text = "D"
            t.rows[1].cells[1].text = "E"
            t.rows[1].cells[2].text = "F"
            t.cell(0, 0).merge(t.cell(0, 1))  # horizontal merge
        result = _make_docx_and_parse(tmp_path, build)
        assert result["valid"] is True
        w = result["documents"][0]["warnings"]
        assert any("水平合并" in x for x in w)

    def test_vertical_merge_detected(self, tmp_path: Path) -> None:
        def build(d):
            d.add_paragraph("内容")
            t = d.add_table(rows=3, cols=2)
            for r in range(3):
                for c in range(2):
                    t.rows[r].cells[c].text = f"R{r}C{c}"
            t.cell(0, 0).merge(t.cell(1, 0))  # vertical merge
        result = _make_docx_and_parse(tmp_path, build)
        assert result["valid"] is True
        w = result["documents"][0]["warnings"]
        assert any("合并" in x for x in w)

    def test_header_detected(self, tmp_path: Path) -> None:
        def build(d):
            d.add_paragraph("正文")
            d.sections[0].header.paragraphs[0].text = "这是页眉"
        result = _make_docx_and_parse(tmp_path, build)
        assert result["valid"] is True
        assert any("页眉" in w for w in result["documents"][0]["warnings"])

    def test_inline_image_detected(self, tmp_path: Path) -> None:
        """Inline picture should trigger image warning."""
        import io, struct, zlib
        # Create minimal valid PNG (2x2 red pixels) without PIL
        def _minimal_png() -> bytes:
            sig = b"\x89PNG\r\n\x1a\n"
            ihdr_data = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
            ihdr = b"IHDR" + ihdr_data
            ihdr_chunk = struct.pack(">I", len(ihdr_data)) + ihdr + struct.pack(">I", zlib.crc32(ihdr) & 0xFFFFFFFF)
            raw = b"\x00\xff\x00\x00\x00\xff\x00\x00"  # filter byte + RGB per row
            compressed = zlib.compress(raw)
            idat = b"IDAT" + compressed
            idat_chunk = struct.pack(">I", len(compressed)) + idat + struct.pack(">I", zlib.crc32(idat) & 0xFFFFFFFF)
            iend = b"IEND"
            iend_chunk = struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend) & 0xFFFFFFFF)
            return sig + ihdr_chunk + idat_chunk + iend_chunk
        buf = io.BytesIO(_minimal_png())
        def build(d):
            d.add_paragraph("带图段落")
            d.add_picture(buf, width=100000)
        result = _make_docx_and_parse(tmp_path, build)
        assert result["valid"] is True
        w = result["documents"][0]["warnings"]
        assert any("内联图片" in x for x in w)

    def test_no_warnings_for_simple_doc(self, tmp_path: Path) -> None:
        mp, root = _valid_docx_manifest(tmp_path, interleaved=[("para", "简单段落")])
        result = parse_manifest(mp, root)
        doc = result["documents"][0]
        assert doc["warnings"] == []


# ===================================================================
# Example corpus CLI
# ===================================================================

class TestExampleCorpus:
    def test_parse_example_success(self) -> None:
        example_dir = Path(__file__).parent.parent / "examples" / "parse-corpus"
        mp = example_dir / "manifest.json"
        if not mp.exists():
            pytest.skip("示例目录不存在")
        result = parse_manifest(mp, example_dir)
        assert result["valid"] is True
        assert result["document_count"] == 2
        assert len(result["documents"]) == 2

        txt_doc = next(d for d in result["documents"] if "txt" in d["document_id"])
        assert len(txt_doc["blocks"]) >= 5
        assert any("第一条" in b["text"] for b in txt_doc["blocks"])

        docx_doc = next(d for d in result["documents"] if "docx" in d["document_id"])
        kinds = [b["kind"] for b in docx_doc["blocks"]]
        assert "paragraph" in kinds
        assert "table_row" in kinds
        # warnings key always present
        assert "warnings" in docx_doc
