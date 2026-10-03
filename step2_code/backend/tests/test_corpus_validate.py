"""Tests for corpus manifest validation.

R2 rewrite: each negative test uses a valid baseline, breaks ONE target field,
asserts the exact error code and field. Positive tests confirm the baseline works.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from campus_assistant.corpus.validate import (
    DUPLICATE_DOCUMENT_ID,
    FILE_NOT_FOUND,
    FILE_READ_ERROR,
    HASH_MISMATCH,
    MANIFEST_READ_ERROR,
    MANIFEST_SCHEMA_ERROR,
    UNSAFE_LOCAL_PATH,
    validate_manifest,
)


# --- Helpers ---

def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _valid_doc(tmp_path: Path, **overrides) -> tuple[dict, Path]:
    """Create a valid document with a real file and matching sha256.

    Scope overrides (campus, student_type, admission_years) are applied inside
    the scope dict, not as top-level keys.

    Returns (doc_dict, manifest_path).
    """
    file_path = tmp_path / "doc.txt"
    _write_text(file_path, "test content for baseline")
    sha = _hash_file(file_path)

    # Extract scope-related overrides
    scope_keys = {"campus", "student_type", "admission_years"}
    scope_overrides = {k: overrides.pop(k) for k in list(overrides) if k in scope_keys}

    doc = {
        "document_id": "test-doc-1",
        "policy_group_id": "test-group",
        "title": "测试文档",
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
    }
    doc.update(overrides)
    if scope_overrides:
        doc["scope"] = {**doc["scope"], **scope_overrides}
    return doc, file_path


def _make_manifest_and_validate(
    tmp_path: Path, docs: list[dict], write_files: bool = True
) -> dict:
    """Write manifest and optionally create files, then validate."""
    manifest = {"schema_version": "1.0", "documents": docs}
    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, manifest)

    if write_files:
        for d in docs:
            lp = d.get("local_path", "")
            if lp:
                fpath = tmp_path / lp
                if not fpath.exists():
                    fpath.parent.mkdir(parents=True, exist_ok=True)
                    _write_text(fpath, f"synthetic content for {d.get('document_id', '')}")

    return validate_manifest(manifest_path, tmp_path)


def _has_error(result: dict, code: str, field: str | None = None) -> bool:
    for e in result["errors"]:
        if e["code"] == code:
            if field is None or field in e["field"]:
                return True
    return False


# --- Baseline sanity ---

class TestBaseline:
    def test_valid_doc_passes(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True
        assert result["document_count"] == 1
        assert result["errors"] == []

    def test_valid_doc_with_real_file(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True

    def test_valid_doc_with_chinese_path(self, tmp_path: Path) -> None:
        file_path = tmp_path / "教务.txt"
        _write_text(file_path, "中文路径")
        sha = _hash_file(file_path)
        doc, _ = _valid_doc(tmp_path, local_path="教务.txt", sha256=sha)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True

    def test_valid_doc_empty_scope_arrays(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True


# --- R1: is_synthetic strict bool ---

class TestBooleanStrict:
    def test_string_false_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, is_synthetic="false")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_string_true_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, is_synthetic="true")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_real_bool_true_passes(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, is_synthetic=True)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True

    def test_real_bool_false_passes(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, is_synthetic=False)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True


# --- R1: Real date validation ---

class TestDateValidation:
    def test_invalid_month_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, published_at="2024-13-01")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR, "published_at")

    def test_invalid_day_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, published_at="2024-02-30")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR, "published_at")

    def test_leap_day_non_leap_year_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, published_at="2025-02-29")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR, "published_at")

    def test_valid_date_passes(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, published_at="2024-09-01")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True

    def test_timestamp_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, published_at="2024-09-01T12:00:00")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR, "published_at")

    def test_reversed_date_range(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, effective_from="2025-01-01", effective_to="2024-01-01")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False

    # R2-A: missing date fields (required, no default)
    def test_missing_published_at_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        del doc["published_at"]
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_missing_effective_from_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        del doc["effective_from"]
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False

    def test_explicit_null_dates_pass(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, published_at=None, effective_from=None, effective_to=None)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True

    # R2-A: compact format and week date rejected
    def test_compact_date_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, published_at="20240901")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR, "published_at")

    def test_week_date_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, published_at="2024-W36-7")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR, "published_at")


# --- R1: Required fields (no defaults) ---

class TestRequiredFields:
    def test_missing_scope_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        del doc["scope"]
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_missing_published_at_passes(self, tmp_path: Path) -> None:
        """published_at is Optional, missing is OK (defaults to None in JSON)."""
        doc, _ = _valid_doc(tmp_path)
        doc["published_at"] = None  # explicit null
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True

    def test_empty_scope_object_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, scope={})
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)


# --- R1: admission_years strict int + range ---

class TestAdmissionYears:
    def test_string_in_years_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, admission_years=["2024"])
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_bool_in_years_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, admission_years=[True])
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_out_of_range_low_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, admission_years=[1899])
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_out_of_range_high_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, admission_years=[2101])
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_valid_years_pass(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, admission_years=[2022, 2023, 2024])
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True


# --- R1: campus/student_type element validation ---

class TestScopeStringElements:
    def test_whitespace_only_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, campus=["  "])
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_non_list_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, campus="abc")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_null_campus_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, campus=None)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_non_string_element_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, campus=[123])
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_valid_campus_passes(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, campus=["成都校区"])
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True


# --- R1: URL host validation ---

class TestUrlHost:
    def test_no_host_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, source_url="https://?query")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR, "source_url")

    def test_credentials_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, source_url="https://user:pass@example.org/doc")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR, "source_url")

    def test_valid_url_passes(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, source_url="https://example.org/path?q=1")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True


# --- Schema errors (retain and improve) ---

class TestSchemaErrors:
    def test_missing_document_id(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        del doc["document_id"]
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_unknown_field_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, typo_field="oops")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_unknown_scope_field_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        doc["scope"]["bogus"] = ["x"]
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False

    def test_empty_documents_rejected(self, tmp_path: Path) -> None:
        result = _make_manifest_and_validate(tmp_path, [])
        assert result["valid"] is False

    def test_wrong_schema_version(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        manifest = {"schema_version": "2.0", "documents": [doc]}
        mp = tmp_path / "manifest.json"
        _write_json(mp, manifest)
        result = validate_manifest(mp, tmp_path)
        assert result["valid"] is False

    def test_invalid_json(self, tmp_path: Path) -> None:
        mp = tmp_path / "manifest.json"
        mp.write_text("{bad json", encoding="utf-8")
        result = validate_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_missing_required_title(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        del doc["title"]
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)


# --- R3: ID validation strict matching ---

class TestIdValidation:
    def test_valid_id_1_char(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, document_id="a")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True

    def test_valid_id_64_chars(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, document_id="a" * 64)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True

    def test_id_too_long_65_chars(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, document_id="a" * 65)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_id_trailing_newline_rejected(self, tmp_path: Path) -> None:
        """R3: \\n at end must be rejected."""
        doc, _ = _valid_doc(tmp_path, document_id="good\n")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_id_trailing_crlf_rejected(self, tmp_path: Path) -> None:
        """R3: \\r\\n at end must be rejected."""
        doc, _ = _valid_doc(tmp_path, document_id="good\r\n")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)

    def test_id_internal_newline_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, document_id="go\nod")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False

    def test_id_leading_trailing_space_rejected(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, document_id=" good ")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False

    def test_policy_group_id_same_rules(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, policy_group_id="bad\n")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, MANIFEST_SCHEMA_ERROR)


# --- Duplicate IDs ---

class TestDuplicateIds:
    def test_duplicate_detected_with_file_errors(self, tmp_path: Path) -> None:
        """Duplicate ID + bad hash: both errors collected, count = structurally valid entries."""
        file1 = tmp_path / "a.txt"
        _write_text(file1, "content a")
        sha1 = _hash_file(file1)

        doc1 = _minimal_valid(document_id="dup-id", local_path="a.txt", sha256=sha1)
        doc2 = _minimal_valid(document_id="dup-id", local_path="nope.txt", sha256="a" * 64)
        manifest = {"schema_version": "1.0", "documents": [doc1, doc2]}
        mp = tmp_path / "manifest.json"
        _write_json(mp, manifest)
        result = validate_manifest(mp, tmp_path)
        assert result["valid"] is False
        assert _has_error(result, DUPLICATE_DOCUMENT_ID)
        assert _has_error(result, FILE_NOT_FOUND)
        assert result["document_count"] == 2  # both structurally valid


def _minimal_valid(**overrides) -> dict:
    """Create a minimal structurally-valid doc (no file needed for schema tests).

    Scope overrides (campus, student_type, admission_years) are applied inside scope.
    """
    scope_keys = {"campus", "student_type", "admission_years"}
    scope_overrides = {k: overrides.pop(k) for k in list(overrides) if k in scope_keys}

    doc = {
        "document_id": "test-doc-1",
        "policy_group_id": "test-group",
        "title": "测试",
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
    doc.update(overrides)
    if scope_overrides:
        doc["scope"] = {**doc["scope"], **scope_overrides}
    return doc


# --- Path safety ---

class TestPathSafety:
    def test_absolute_path(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="/etc/passwd")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, UNSAFE_LOCAL_PATH)

    def test_drive_letter(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="C:\\Windows\\system32")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, UNSAFE_LOCAL_PATH)

    def test_unc_path(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="\\\\server\\share\\file.txt")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, UNSAFE_LOCAL_PATH)

    def test_dotdot_traversal(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="../escape.txt")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, UNSAFE_LOCAL_PATH)

    def test_single_dot(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path=".")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False

    def test_ads_colon(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="file.txt:hidden:$DATA")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, UNSAFE_LOCAL_PATH)

    def test_nul_character_rejected(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="bad\x00name.txt")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, UNSAFE_LOCAL_PATH)


# --- R5: Symlink escape test ---

class TestSymlinkEscape:
    def test_symlink_to_outside_rejected(self, tmp_path: Path) -> None:
        """Create a symlink inside corpus-root pointing outside. Should be rejected."""
        outside = tmp_path.parent / "outside_target.txt"
        _write_text(outside, "outside content")
        link_path = tmp_path / "escape_link.txt"
        try:
            os.symlink(str(outside), str(link_path))
        except OSError as e:
            pytest.skip(f"无法创建符号链接: {type(e).__name__} winerror={getattr(e, 'winerror', 'N/A')} errno={e.errno}")
            return

        outside_sha = _hash_file(outside)
        doc = _minimal_valid(local_path="escape_link.txt", sha256=outside_sha)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, UNSAFE_LOCAL_PATH)

        link_path.unlink(missing_ok=True)
        outside.unlink(missing_ok=True)


# --- File checks ---

class TestFileChecks:
    def test_missing_file(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="nonexistent.txt")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, FILE_NOT_FOUND)

    def test_directory_as_file(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        doc = _minimal_valid(local_path="subdir")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, FILE_NOT_FOUND)

    def test_hash_mismatch(self, tmp_path: Path) -> None:
        fp = tmp_path / "doc.txt"
        _write_text(fp, "actual content")
        doc = _minimal_valid(local_path="doc.txt", sha256="0" * 64)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert _has_error(result, HASH_MISMATCH)


# --- R4: document_count contract ---

class TestDocumentCount:
    def test_count_is_structurally_valid_not_file_success(self, tmp_path: Path) -> None:
        """Two structurally valid docs, one bad hash => count=2, not 1."""
        fp = tmp_path / "good.txt"
        _write_text(fp, "good")
        good_sha = _hash_file(fp)

        doc1 = _minimal_valid(document_id="good-doc", local_path="good.txt", sha256=good_sha)
        doc2 = _minimal_valid(document_id="bad-hash-doc", local_path="good.txt", sha256="0" * 64)
        result = _make_manifest_and_validate(tmp_path, [doc1, doc2], write_files=False)
        assert result["document_count"] == 2
        assert _has_error(result, HASH_MISMATCH)

    def test_count_zero_on_schema_failure(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, is_synthetic="invalid")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["document_count"] == 0

    def test_duplicate_id_count_not_zero(self, tmp_path: Path) -> None:
        """Duplicate IDs + file errors: count = structurally valid entries."""
        fp = tmp_path / "a.txt"
        _write_text(fp, "a")
        sha = _hash_file(fp)

        doc1 = _minimal_valid(document_id="dup", local_path="a.txt", sha256=sha)
        doc2 = _minimal_valid(document_id="dup", local_path="nope.txt", sha256="a" * 64)
        result = _make_manifest_and_validate(tmp_path, [doc1, doc2], write_files=False)
        assert result["document_count"] == 2


# --- Multiple errors collected ---

class TestMultipleErrors:
    def test_all_file_errors_collected(self, tmp_path: Path) -> None:
        fp = tmp_path / "good.txt"
        _write_text(fp, "good content")
        good_sha = _hash_file(fp)

        doc1 = _minimal_valid(document_id="good", local_path="good.txt", sha256=good_sha)
        doc2 = _minimal_valid(document_id="missing", local_path="nope.txt", sha256="a" * 64)
        doc3 = _minimal_valid(document_id="badhash", local_path="good.txt", sha256="0" * 64)
        result = _make_manifest_and_validate(tmp_path, [doc1, doc2, doc3], write_files=False)
        assert result["valid"] is False
        assert _has_error(result, FILE_NOT_FOUND)
        assert _has_error(result, HASH_MISMATCH)
        assert result["document_count"] == 3


# --- Validation does not modify input ---

class TestNoModifyInput:
    def test_manifest_not_modified(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        mp = tmp_path / "manifest.json"
        manifest = {"schema_version": "1.0", "documents": [doc]}
        _write_json(mp, manifest)
        before = mp.read_text(encoding="utf-8")
        validate_manifest(mp, tmp_path)
        after = mp.read_text(encoding="utf-8")
        assert before == after


# --- Error output format ---

class TestErrorFormat:
    def test_error_has_required_fields(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="nonexistent.txt")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        for err in result["errors"]:
            assert "code" in err
            assert "document_id" in err
            assert "field" in err
            assert "message" in err


# --- CLI subprocess ---

class TestCLI:
    def _run_cli(self, tmp_path: Path, manifest_path: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.validate",
             "--manifest", str(manifest_path), "--corpus-root", str(tmp_path)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )

    def test_success(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        mp = tmp_path / "manifest.json"
        _write_json(mp, {"schema_version": "1.0", "documents": [doc]})
        proc = self._run_cli(tmp_path, mp)
        assert proc.returncode == 0
        out = json.loads(proc.stdout)
        assert out["valid"] is True
        assert out["document_count"] == 1

    def test_failure(self, tmp_path: Path) -> None:
        doc = _minimal_valid(local_path="missing.txt")
        mp = tmp_path / "manifest.json"
        _write_json(mp, {"schema_version": "1.0", "documents": [doc]})
        proc = self._run_cli(tmp_path, mp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert out["valid"] is False

    def test_usage_error(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.corpus.validate"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 2

    def test_manifest_not_found(self, tmp_path: Path) -> None:
        proc = self._run_cli(tmp_path, tmp_path / "nonexistent.json")
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert _has_error(out, MANIFEST_READ_ERROR)

    def test_non_utf8_manifest(self, tmp_path: Path) -> None:
        """R3: Non-UTF-8 bytes should produce MANIFEST_READ_ERROR, not a crash."""
        mp = tmp_path / "manifest.json"
        mp.write_bytes(b"\xff\xfe\x00{")
        proc = self._run_cli(tmp_path, mp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert _has_error(out, MANIFEST_READ_ERROR)
        # No absolute paths in output
        assert "tmp" not in out["errors"][0]["message"].lower()

    def test_null_campus_produces_json(self, tmp_path: Path) -> None:
        """R3: scope.campus=null should not crash CLI; should produce valid JSON."""
        doc = _minimal_valid(campus=None)
        mp = tmp_path / "manifest.json"
        _write_json(mp, {"schema_version": "1.0", "documents": [doc]})
        proc = self._run_cli(tmp_path, mp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout)
        assert out["valid"] is False

    def test_nul_path_produces_json(self, tmp_path: Path) -> None:
        """R2-B: NUL in path must produce JSON, not a traceback."""
        doc = _minimal_valid(local_path="bad\x00name.txt")
        mp = tmp_path / "manifest.json"
        _write_json(mp, {"schema_version": "1.0", "documents": [doc]})
        proc = self._run_cli(tmp_path, mp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout)  # must be parseable
        assert out["valid"] is False
        assert _has_error(out, UNSAFE_LOCAL_PATH)
        assert "Traceback" not in (proc.stderr or "")


# --- R2-C: Chinese error messages ---

class TestChineseErrorMessages:
    def test_missing_field_chinese(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        del doc["title"]
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        msgs = [e["message"] for e in result["errors"]]
        assert any("必填" in m for m in msgs)

    def test_type_error_chinese(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path)
        doc["scope"]["admission_years"] = "not a list"
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        msgs = [e["message"] for e in result["errors"]]
        assert any("数组" in m for m in msgs)

    def test_unknown_field_chinese(self, tmp_path: Path) -> None:
        doc, _ = _valid_doc(tmp_path, bogus_field="x")
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is False
        msgs = [e["message"] for e in result["errors"]]
        assert any("不允许" in m or "额外" in m for m in msgs)


# --- Hash computation ---

class TestHashComputation:
    def test_large_file_hash(self, tmp_path: Path) -> None:
        content = b"x" * 20000
        fp = tmp_path / "big.txt"
        fp.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        doc = _minimal_valid(local_path="big.txt", sha256=expected)
        result = _make_manifest_and_validate(tmp_path, [doc], write_files=False)
        assert result["valid"] is True
