"""Offline corpus chunker.

Converts parsed document blocks into retrieval candidate chunks.
Block-internal fixed-character sliding window for paragraphs;
one chunk per table_row (soft max_chars limit).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

CHUNKER_VERSION = "1.0"
STRATEGY = "block_window_v1"
STRATEGY_OVERLAP = "block_window_overlap_v1"
TABLE_ROW_EXCEEDS_MAX_CHARS = "TABLE_ROW_EXCEEDS_MAX_CHARS"


def _make_chunk_id(
    document_id: str,
    sha256: str,
    parser_version: str,
    block_id: str,
    max_chars: int,
    char_start: int,
    char_end: int,
    text: str,
    *,
    strategy: str = STRATEGY,
    overlap_chars: int = 0,
) -> str:
    """Deterministic chunk ID from content and configuration.

    T034: the overlap strategy/params carry an explicit identity in the key —
    but only for overlap runs. The default (overlap=0) key is byte-identical
    to the historical one, so legacy chunk IDs never change.
    """
    key_items = [document_id, sha256, parser_version, block_id,
                 CHUNKER_VERSION, strategy, max_chars, char_start, char_end, text]
    if overlap_chars:
        key_items.append(overlap_chars)
    key = json.dumps(
        key_items,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(key).hexdigest()


def _validate_max_chars(max_chars: int) -> None:
    """Validate max_chars parameter. Raises ValueError with Chinese message."""
    if not isinstance(max_chars, int) or isinstance(max_chars, bool):
        raise ValueError("max_chars 必须是整数")
    if max_chars < 1 or max_chars > 10000:
        raise ValueError("max_chars 必须在 1—10000 之间")


def _validate_overlap_chars(overlap_chars: int, max_chars: int) -> None:
    """Validate overlap_chars parameter (0 = historical behaviour)."""
    if not isinstance(overlap_chars, int) or isinstance(overlap_chars, bool):
        raise ValueError("overlap_chars 必须是整数")
    if overlap_chars < 0:
        raise ValueError("overlap_chars 不能为负数")
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars 必须小于 max_chars")


def chunk_documents(
    documents: list[dict], *, max_chars: int = 500, overlap_chars: int = 0
) -> list[dict]:
    """Chunk parsed documents into retrieval candidates.

    Args:
        documents: Output of parse_manifest['documents'].
        max_chars: Maximum characters per paragraph chunk (1-10000).
        overlap_chars: T034 optional window overlap for paragraph blocks
            (0 = historical behaviour, byte/ID identical). Must be in
            [0, max_chars); window step = max_chars - overlap_chars. Applies
            only to in-block paragraph windows — table_row chunks and parsed
            blocks are untouched. The last window ends at the block tail and
            the loop stops there (no redundant extra tail window).

    Returns:
        Ordered list of chunk dicts. Each chunk's metadata, locator, cells,
        and warnings are independent deep copies — modifying one chunk does
        not affect its siblings or the input documents. Chunks keep the
        original document_id/block_id and the true in-block [char_start,
        char_end); text equals the block slice verbatim.
    """
    _validate_max_chars(max_chars)
    _validate_overlap_chars(overlap_chars, max_chars)

    step = max_chars - overlap_chars
    strategy = STRATEGY_OVERLAP if overlap_chars else STRATEGY
    all_chunks: list[dict] = []

    for doc in documents:
        doc_id = doc["document_id"]
        parser_version = doc.get("parser_version", "1.0")
        meta = doc.get("metadata", {})
        sha256 = meta.get("sha256", "")
        doc_warnings = list(doc.get("warnings", []))

        ordinal = 0

        # R3: Sort blocks by ordinal without mutating input
        blocks = sorted(doc.get("blocks", []), key=lambda b: b.get("ordinal", 0))

        for block in blocks:
            kind = block["kind"]
            block_id = block["block_id"]

            # R1: Deepcopy locator per chunk to isolate from input
            locator = copy.deepcopy(block.get("locator", {}))

            if kind == "paragraph":
                text = block.get("text", "")
                if not text:
                    continue

                pos = 0
                while pos < len(text):
                    end = min(pos + max_chars, len(text))
                    chunk_text = text[pos:end]
                    ordinal += 1

                    # R1: Independent copies per chunk
                    chunk_warnings = list(doc_warnings)
                    chunk = {
                        "chunk_id": _make_chunk_id(
                            doc_id, sha256, parser_version, block_id,
                            max_chars, pos, end, chunk_text,
                            strategy=strategy, overlap_chars=overlap_chars,
                        ),
                        "document_id": doc_id,
                        "block_id": block_id,
                        "ordinal": ordinal,
                        "kind": kind,
                        "text": chunk_text,
                        "char_start": pos,
                        "char_end": end,
                        "locator": copy.deepcopy(locator),
                        "cells": None,
                        "metadata": copy.deepcopy(meta),
                        "parser_version": parser_version,
                        "chunker_version": CHUNKER_VERSION,
                        "strategy": strategy,
                        "max_chars": max_chars,
                        "warnings": chunk_warnings,
                    }
                    if overlap_chars:
                        # identity field only on overlap runs — default dicts
                        # stay byte-identical to the historical schema
                        chunk["overlap_chars"] = overlap_chars
                    all_chunks.append(chunk)
                    if end >= len(text):
                        break  # tail window reached block end — stop, no extra window
                    pos = end - overlap_chars

            elif kind == "table_row":
                cells = block.get("cells")
                text = block.get("text", "")

                if cells and not text.strip():
                    raise ValueError(
                        f"表格行 block_id={block_id} cells 非空但 text 为空白，输入契约异常"
                    )

                ordinal += 1
                chunk_warnings = list(doc_warnings)
                if len(text) > max_chars:
                    chunk_warnings.append(TABLE_ROW_EXCEEDS_MAX_CHARS)

                # R1: Independent copies per chunk
                chunk = {
                    "chunk_id": _make_chunk_id(
                        doc_id, sha256, parser_version, block_id,
                        max_chars, 0, len(text), text,
                    ),
                    "document_id": doc_id,
                    "block_id": block_id,
                    "ordinal": ordinal,
                    "kind": kind,
                    "text": text,
                    "char_start": 0,
                    "char_end": len(text),
                    "locator": copy.deepcopy(locator),
                    "cells": list(cells) if cells else None,
                    "metadata": copy.deepcopy(meta),
                    "parser_version": parser_version,
                    "chunker_version": CHUNKER_VERSION,
                    "strategy": STRATEGY,
                    "max_chars": max_chars,
                    "warnings": chunk_warnings,
                }
                all_chunks.append(chunk)

            else:
                raise ValueError(f"未知 block kind: {kind}")

    return all_chunks


def _get_parse_result(manifest_path: Path, corpus_root: Path) -> dict:
    """Call parse_manifest once. Separated for testability."""
    from campus_assistant.corpus.parse import parse_manifest
    return parse_manifest(manifest_path, corpus_root)


def chunk_manifest(
    manifest_path: Path, corpus_root: Path, *, max_chars: int = 500, overlap_chars: int = 0
) -> dict:
    """Validate, parse, then chunk all documents.

    Validates max_chars/overlap_chars before calling parse_manifest to avoid
    inconsistent behavior with different document counts.
    """
    _validate_max_chars(max_chars)
    _validate_overlap_chars(overlap_chars, max_chars)

    parse_result = _get_parse_result(manifest_path, corpus_root)

    documents = parse_result.get("documents", [])
    errors = parse_result.get("errors", [])
    document_count = parse_result.get("document_count", 0)
    parsed_count = len(documents)

    all_chunks: list[dict] = []
    chunk_errors = list(errors)

    for doc in documents:
        try:
            doc_chunks = chunk_documents(
                [doc], max_chars=max_chars, overlap_chars=overlap_chars
            )
            all_chunks.extend(doc_chunks)
        except ValueError as e:
            chunk_errors.append({
                "code": "CHUNK_ERROR",
                "document_id": doc.get("document_id"),
                "field": "chunk",
                "message": str(e),
            })

    valid = parse_result.get("valid", False) and len(chunk_errors) == len(errors)

    return {
        "schema_version": "1.0",
        "chunker_version": CHUNKER_VERSION,
        "strategy": STRATEGY_OVERLAP if overlap_chars else STRATEGY,
        "max_chars": max_chars,
        "overlap_chars": overlap_chars,
        "valid": valid,
        "document_count": document_count,
        "parsed_count": parsed_count,
        "chunk_count": len(all_chunks),
        "chunks": all_chunks,
        "errors": chunk_errors,
    }


def _ensure_utf8_stdout() -> None:
    """Ensure stdout outputs UTF-8 regardless of system locale."""
    import io
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") == "utf8":
        return
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="将解析正文分块为检索候选单元")
    parser.add_argument("--manifest", required=True, help="manifest.json 路径")
    parser.add_argument("--corpus-root", required=True, help="语料文件根目录")
    parser.add_argument("--max-chars", type=int, default=500, help="段落块最大字符数 (1-10000)")
    parser.add_argument("--overlap-chars", type=int, default=0,
                        help="段落块窗口重叠字符数（0=默认无重叠；须小于 max-chars）")
    args = parser.parse_args(argv)

    # R2: Validate max_chars before any path resolution or parse_manifest
    try:
        _validate_max_chars(args.max_chars)
        _validate_overlap_chars(args.overlap_chars, args.max_chars)
    except ValueError as e:
        parser.error(str(e))  # exits with code 2, stderr message, no stdout JSON

    manifest_path = Path(args.manifest)

    try:
        corpus_root = Path(args.corpus_root).resolve()
    except OSError:
        result = {
            "schema_version": "1.0",
            "chunker_version": CHUNKER_VERSION,
            "strategy": STRATEGY_OVERLAP if args.overlap_chars else STRATEGY,
            "max_chars": args.max_chars,
            "overlap_chars": args.overlap_chars,
            "valid": False,
            "document_count": 0,
            "parsed_count": 0,
            "chunk_count": 0,
            "chunks": [],
            "errors": [{"code": "MANIFEST_READ_ERROR", "document_id": None,
                        "field": "corpus-root", "message": "无法解析语料根目录"}],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        result = chunk_manifest(
            manifest_path, corpus_root,
            max_chars=args.max_chars, overlap_chars=args.overlap_chars,
        )
    except ValueError as e:
        result = {
            "schema_version": "1.0",
            "chunker_version": CHUNKER_VERSION,
            "strategy": STRATEGY_OVERLAP if args.overlap_chars else STRATEGY,
            "max_chars": args.max_chars,
            "overlap_chars": args.overlap_chars,
            "valid": False,
            "document_count": 0,
            "parsed_count": 0,
            "chunk_count": 0,
            "chunks": [],
            "errors": [{"code": "PARAM_ERROR", "document_id": None,
                        "field": "max_chars", "message": str(e)}],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
