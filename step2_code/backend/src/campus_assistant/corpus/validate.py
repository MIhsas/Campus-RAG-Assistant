"""Offline corpus manifest validation.

Validates manifest structure, field rules, file existence, path safety,
and SHA-256 integrity. Does NOT parse file content, access the network,
or create any persistent state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from campus_assistant.corpus.models import Manifest

# Stable error codes
MANIFEST_READ_ERROR = "MANIFEST_READ_ERROR"
MANIFEST_SCHEMA_ERROR = "MANIFEST_SCHEMA_ERROR"
DUPLICATE_DOCUMENT_ID = "DUPLICATE_DOCUMENT_ID"
UNSAFE_LOCAL_PATH = "UNSAFE_LOCAL_PATH"
FILE_NOT_FOUND = "FILE_NOT_FOUND"
FILE_READ_ERROR = "FILE_READ_ERROR"
HASH_MISMATCH = "HASH_MISMATCH"

# Map Pydantic error types to concise Chinese messages
_PYDANTIC_TYPE_MESSAGES: dict[str, str] = {
    "string_type": "必须是字符串",
    "int_type": "必须是整数",
    "float_type": "必须是数字",
    "bool_type": "必须是布尔值",
    "list_type": "必须是数组",
    "dict_type": "必须是对象",
    "none_required": "必须为 null",
    "missing": "此字段为必填项",
    "extra_forbidden": "不允许的额外字段",
    "string_too_short": "字符串过短",
    "string_too_long": "字符串过长",
    "value_error": "",  # use the ValueError message directly (already Chinese)
}


def _pydantic_error_to_chinese(err: dict) -> str:
    """Convert a Pydantic error dict to a concise Chinese message."""
    err_type = err.get("type", "")
    if err_type == "value_error":
        msg = err.get("msg", "校验失败")
        # Strip Pydantic's English prefix if present
        for prefix in ("Value error, ", "Value error: "):
            if msg.startswith(prefix):
                msg = msg[len(prefix):]
                break
        return msg
    if err_type in _PYDANTIC_TYPE_MESSAGES:
        mapped = _PYDANTIC_TYPE_MESSAGES[err_type]
        if mapped:
            return mapped
    return "字段校验失败"


def _error(code: str, document_id: str | None, field: str, message: str) -> dict:
    return {
        "code": code,
        "document_id": document_id,
        "field": field,
        "message": message,
    }


def _is_safe_local_path(local_path: str) -> tuple[bool, str]:
    """Check if local_path is safe (relative, no traversal, no ADS, no NUL).

    Returns (is_safe, reason).
    """
    if not local_path or not local_path.strip():
        return False, "local_path 不能为空"

    # Reject NUL characters (causes ValueError in os.stat on Windows)
    if "\x00" in local_path:
        return False, "local_path 不得包含空字符"

    if local_path.startswith("/") or local_path.startswith("\\"):
        return False, "local_path 不得是绝对路径或 UNC 路径"

    parts: list[str] = []
    for segment in local_path.replace("\\", "/").split("/"):
        if segment:
            parts.append(segment)

    if not parts:
        return False, "local_path 不能为空"

    for part in parts:
        if part in (".", ".."):
            return False, f"local_path 不得包含 '{part}' 路径段"

    first = parts[0]
    if len(first) == 2 and first[1] == ":" and first[0].isalpha():
        return False, "local_path 不得包含盘符"

    for part in parts:
        if ":" in part:
            return False, "local_path 不得包含冒号（Windows ADS 形式）"

    return True, ""


def _resolve_within_root(corpus_root: Path, local_path: str) -> tuple[Path | None, str]:
    """Resolve local_path within corpus_root, checking for escape.

    Returns (resolved_path_or_None, error_message).
    """
    try:
        resolved_root = corpus_root.resolve()
    except OSError:
        return None, "无法解析 corpus-root"

    try:
        target = (resolved_root / local_path).resolve()
    except (ValueError, OSError):
        return None, "路径解析失败"

    try:
        target.relative_to(resolved_root)
    except ValueError:
        return None, "local_path 解析后位于 corpus-root 之外"

    return target, ""


def _sha256_file(path: Path) -> tuple[str | None, str]:
    """Compute SHA-256 of a file in chunks.

    Returns (hash_or_None, error_message).
    """
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest(), ""
    except PermissionError:
        return None, "无读取权限"
    except OSError:
        return None, "读取文件失败"


def validate_manifest(manifest_path: Path, corpus_root: Path) -> dict:
    """Validate a corpus manifest against its corpus root.

    Returns a dict with keys: valid (bool), document_count (int), errors (list).
    document_count = number of entries that passed structural validation;
    it does NOT count file-level successes.
    """
    errors: list[dict] = []

    # 1. Read manifest file
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "valid": False,
            "document_count": 0,
            "errors": [_error(MANIFEST_READ_ERROR, None, "manifest", "清单文件不存在")],
        }
    except PermissionError:
        return {
            "valid": False,
            "document_count": 0,
            "errors": [_error(MANIFEST_READ_ERROR, None, "manifest", "无读取权限")],
        }
    except UnicodeDecodeError:
        return {
            "valid": False,
            "document_count": 0,
            "errors": [_error(MANIFEST_READ_ERROR, None, "manifest", "清单文件编码不是 UTF-8")],
        }
    except OSError:
        return {
            "valid": False,
            "document_count": 0,
            "errors": [_error(MANIFEST_READ_ERROR, None, "manifest", "读取清单文件失败")],
        }

    # 2. Parse JSON
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "document_count": 0,
            "errors": [
                _error(
                    MANIFEST_SCHEMA_ERROR,
                    None,
                    "manifest",
                    f"JSON 解析失败: 第 {e.lineno} 行第 {e.colno} 列",
                )
            ],
        }

    # 3. Validate schema with Pydantic
    try:
        manifest = Manifest.model_validate(data)
    except ValidationError as ve:
        for err in ve.errors():
            loc = ".".join(str(x) for x in err.get("loc", ()))
            errors.append(
                _error(
                    MANIFEST_SCHEMA_ERROR,
                    None,
                    loc or "manifest",
                    _pydantic_error_to_chinese(err),
                )
            )
        return {
            "valid": False,
            "document_count": 0,
            "errors": errors,
        }

    # Structural validation passed. document_count = number of input entries.
    structurally_valid_count = len(manifest.documents)

    # 4. Check duplicate document_ids
    seen_ids: dict[str, int] = {}
    for i, doc in enumerate(manifest.documents):
        if doc.document_id in seen_ids:
            errors.append(
                _error(
                    DUPLICATE_DOCUMENT_ID,
                    doc.document_id,
                    "document_id",
                    f"document_id '{doc.document_id}' 与第 {seen_ids[doc.document_id] + 1} 项重复",
                )
            )
        else:
            seen_ids[doc.document_id] = i

    # 5. File-level checks for each document (continue collecting errors)
    for doc in manifest.documents:
        doc_id = doc.document_id

        # Path safety
        safe, reason = _is_safe_local_path(doc.local_path)
        if not safe:
            errors.append(_error(UNSAFE_LOCAL_PATH, doc_id, "local_path", reason))
            continue

        # Resolve within root
        resolved, reason = _resolve_within_root(corpus_root, doc.local_path)
        if resolved is None:
            errors.append(_error(UNSAFE_LOCAL_PATH, doc_id, "local_path", reason))
            continue

        # Must be a regular file
        try:
            exists = resolved.exists()
        except (ValueError, OSError):
            errors.append(_error(FILE_READ_ERROR, doc_id, "local_path", "路径状态检查失败"))
            continue

        if not exists:
            errors.append(
                _error(FILE_NOT_FOUND, doc_id, "local_path", f"文件不存在: {doc.local_path}")
            )
            continue

        try:
            is_regular = resolved.is_file()
        except (ValueError, OSError):
            errors.append(_error(FILE_READ_ERROR, doc_id, "local_path", "文件类型检查失败"))
            continue

        if not is_regular:
            errors.append(
                _error(FILE_NOT_FOUND, doc_id, "local_path", f"目标不是普通文件: {doc.local_path}")
            )
            continue

        # SHA-256
        actual_hash, reason = _sha256_file(resolved)
        if actual_hash is None:
            errors.append(_error(FILE_READ_ERROR, doc_id, "sha256", reason))
            continue

        if actual_hash != doc.sha256:
            errors.append(
                _error(
                    HASH_MISMATCH,
                    doc_id,
                    "sha256",
                    f"哈希不符: 预期 {doc.sha256[:16]}...，实际 {actual_hash[:16]}...",
                )
            )

    return {
        "valid": len(errors) == 0,
        "document_count": structurally_valid_count,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="校验语料登记清单（manifest.json）与文件完整性"
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="manifest.json 文件路径",
    )
    parser.add_argument(
        "--corpus-root",
        required=True,
        help="语料文件根目录",
    )
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)

    try:
        corpus_root = Path(args.corpus_root).resolve()
    except OSError:
        result = {
            "valid": False,
            "document_count": 0,
            "errors": [_error(MANIFEST_READ_ERROR, None, "corpus-root", "无法解析语料根目录")],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = validate_manifest(manifest_path, corpus_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
