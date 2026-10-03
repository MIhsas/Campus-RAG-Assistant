"""Offline BM25 retrieval CLI.

Combines chunk_manifest + BM25Index for keyword search over corpus chunks.
No model, no persistence, no external API.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

RETRIEVER_VERSION = "1.0"
TOKENIZER_VERSION = "cjk_bigram_ascii_v1"


def _ensure_utf8_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") == "utf8":
        return
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )
    except (AttributeError, OSError):
        pass


def _validate_cli_args(max_chars: int, top_k: int) -> str | None:
    """Validate CLI-specific params. Returns error message or None."""
    from campus_assistant.corpus.chunk import _validate_max_chars
    try:
        _validate_max_chars(max_chars)
    except ValueError as e:
        return str(e)
    from campus_assistant.retrieval.bm25 import _validate_params
    try:
        _validate_params(1.5, 0.75, top_k)
    except ValueError as e:
        return str(e)
    return None


def _run_search(
    manifest_path: Path, corpus_root: Path, *,
    query: str, max_chars: int = 500, top_k: int = 5,
    k1: float = 1.5, b: float = 0.75,
) -> dict[str, Any]:
    """Core search logic. Returns output dict."""
    from campus_assistant.corpus.chunk import chunk_manifest
    from campus_assistant.retrieval.bm25 import BM25Index
    from campus_assistant.retrieval.tokenize import tokenize

    chunk_result = chunk_manifest(manifest_path, corpus_root, max_chars=max_chars)

    documents = chunk_result.get("documents", [])  # not used directly
    chunks = chunk_result.get("chunks", [])
    errors = list(chunk_result.get("errors", []))

    # Build index
    try:
        index = BM25Index(chunks, k1=k1, b=b)
    except ValueError as e:
        errors.append({
            "code": "INDEX_ERROR",
            "document_id": None,
            "field": "chunks",
            "message": str(e),
        })
        return _make_output(
            query=query, max_chars=max_chars, top_k=top_k, k1=k1, b=b,
            chunk_result=chunk_result, hits=[], errors=errors,
            indexed_chunk_count=0,
        )

    query_tokens = tokenize(query) if isinstance(query, str) else []
    hits = index.search(query, top_k=top_k)

    return _make_output(
        query=query, max_chars=max_chars, top_k=top_k, k1=k1, b=b,
        chunk_result=chunk_result, hits=hits, errors=errors,
        indexed_chunk_count=index.valid_chunk_count,
    )


def _make_output(
    *, query: str, max_chars: int, top_k: int, k1: float, b: float,
    chunk_result: dict, hits: list, errors: list, indexed_chunk_count: int,
) -> dict[str, Any]:
    from campus_assistant.retrieval.tokenize import tokenize
    return {
        "schema_version": "1.0",
        "retriever_version": RETRIEVER_VERSION,
        "tokenizer_version": TOKENIZER_VERSION,
        "query": query,
        "query_tokens": tokenize(query) if isinstance(query, str) else [],
        "parameters": {
            "max_chars": max_chars,
            "top_k": top_k,
            "k1": k1,
            "b": b,
        },
        "valid": chunk_result.get("valid", False) and len(errors) == len(chunk_result.get("errors", [])),
        "document_count": chunk_result.get("document_count", 0),
        "parsed_count": chunk_result.get("parsed_count", 0),
        "chunk_count": chunk_result.get("chunk_count", 0),
        "indexed_chunk_count": indexed_chunk_count,
        "hits": hits,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="离线 BM25 关键词检索")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-chars", type=int, default=500)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(argv)

    # Validate params before file operations
    err = _validate_cli_args(args.max_chars, args.top_k)
    if err:
        parser.error(err)  # exit 2, stderr, no stdout JSON

    manifest_path = Path(args.manifest)
    try:
        corpus_root = Path(args.corpus_root).resolve()
    except OSError:
        # Can't resolve root — output JSON error, exit 1
        result = _make_output(
            query=args.query, max_chars=args.max_chars, top_k=args.top_k,
            k1=1.5, b=0.75,
            chunk_result={"valid": False, "document_count": 0, "parsed_count": 0, "chunk_count": 0, "errors": []},
            hits=[], errors=[{"code": "MANIFEST_READ_ERROR", "document_id": None, "field": "corpus-root", "message": "无法解析语料根目录"}],
            indexed_chunk_count=0,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        result = _run_search(
            manifest_path, corpus_root,
            query=args.query, max_chars=args.max_chars, top_k=args.top_k,
        )
    except Exception as e:
        result = _make_output(
            query=args.query, max_chars=args.max_chars, top_k=args.top_k,
            k1=1.5, b=0.75,
            chunk_result={"valid": False, "document_count": 0, "parsed_count": 0, "chunk_count": 0, "errors": []},
            hits=[], errors=[{"code": "SEARCH_ERROR", "document_id": None, "field": "search", "message": f"检索异常: {type(e).__name__}"}],
            indexed_chunk_count=0,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
