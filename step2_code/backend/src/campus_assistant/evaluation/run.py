"""Offline retrieval evaluation CLI.

Runs BM25/dense/hybrid retrieval over a question dataset, computes metrics,
and outputs results as UTF-8 JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any

EVALUATOR_VERSION = "1.0"
RETRIEVER_VERSION = "1.0"
TOKENIZER_VERSION = "cjk_bigram_ascii_v1"
CHUNKER_VERSION = "1.0"
EMBEDDING_MODEL_VERSION = "bge-small-zh-v1.5"


def _ensure_utf8_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") == "utf8":
        return
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )
    except (AttributeError, OSError):
        pass


def _error(code: str, question_id: str | None, evidence_id: str | None,
           field: str, message: str) -> dict:
    return {
        "code": code,
        "question_id": question_id,
        "evidence_id": evidence_id,
        "field": field,
        "message": message,
    }


def _file_sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError):
        return None


def _run_eval(
    manifest_path: Path,
    corpus_root: Path,
    questions_path: Path,
    top_k: int,
    mode: str = "bm25",
    model_path: str | None = None,
) -> dict[str, Any]:
    """Core evaluation logic. Returns output dict."""
    from campus_assistant.corpus.chunk import chunk_documents
    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.evaluation.metrics import compute_summary, evaluate_question
    from campus_assistant.evaluation.models import QuestionDataset
    from campus_assistant.retrieval.bm25 import BM25Index

    errors: list[dict] = []

    # Load and validate question dataset
    try:
        raw_q = questions_path.read_text(encoding="utf-8")
    except Exception:
        return _make_failure(
            errors=[_error("DATASET_READ_ERROR", None, None, "questions", "无法读取问题集文件")],
            manifest_path=manifest_path, questions_path=questions_path,
        )

    try:
        data_q = json.loads(raw_q)
    except json.JSONDecodeError as e:
        return _make_failure(
            errors=[_error("DATASET_SCHEMA_ERROR", None, None, "questions", f"JSON 解析失败: {e}")],
            manifest_path=manifest_path, questions_path=questions_path,
        )

    if not isinstance(data_q, dict):
        return _make_failure(
            errors=[_error("DATASET_SCHEMA_ERROR", None, None, "questions", "问题集顶层必须是 JSON 对象")],
            manifest_path=manifest_path, questions_path=questions_path,
        )

    try:
        dataset = QuestionDataset.model_validate(data_q)
    except Exception as e:
        schema_errors = []
        if hasattr(e, "errors"):
            for err in e.errors():
                loc = ".".join(str(x) for x in err.get("loc", []))
                msg = err.get("msg", str(e))
                if msg == "Input should be a valid boolean":
                    msg = "必须是布尔值"
                elif "valid integer" in msg:
                    msg = "必须是整数"
                schema_errors.append(
                    _error("DATASET_SCHEMA_ERROR", None, None, loc or "questions", msg)
                )
        else:
            schema_errors.append(_error("DATASET_SCHEMA_ERROR", None, None, "questions", "问题集结构校验失败"))
        return _make_failure(
            errors=schema_errors,
            manifest_path=manifest_path, questions_path=questions_path,
            dataset_id=data_q.get("dataset_id"),
            dataset_version=data_q.get("dataset_version"),
        )

    # Validate corpus
    parse_result = parse_manifest(manifest_path, corpus_root)
    if not parse_result.get("valid", False):
        return _make_failure(
            errors=[_error("CORPUS_ERROR", None, None, "manifest", "语料校验失败")] + parse_result.get("errors", []),
            manifest_path=manifest_path, questions_path=questions_path,
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
        )

    documents = parse_result.get("documents", [])
    corpus_doc_ids = {d["document_id"] for d in documents}
    corpus_doc_hashes = {d["document_id"]: d.get("metadata", {}).get("sha256", "") for d in documents}
    corpus_doc_parsers = {d["document_id"]: d.get("parser_version", "") for d in documents}
    corpus_blocks: dict[str, dict[str, dict]] = {}
    for d in documents:
        doc_id = d["document_id"]
        corpus_blocks[doc_id] = {}
        for b in d.get("blocks", []):
            corpus_blocks[doc_id][b["block_id"]] = b

    # Validate ALL evidence references
    for q in dataset.questions:
        for ev in q.evidence:
            if ev.document_id not in corpus_doc_ids:
                errors.append(_error("EVIDENCE_REFERENCE_ERROR", q.question_id, ev.evidence_id, "document_id", f"文档 {ev.document_id} 不在语料中"))
                continue
            if ev.document_sha256 != corpus_doc_hashes.get(ev.document_id, ""):
                errors.append(_error("EVIDENCE_REFERENCE_ERROR", q.question_id, ev.evidence_id, "document_sha256", f"文档 {ev.document_id} 哈希不匹配"))
                continue
            if ev.parser_version != corpus_doc_parsers.get(ev.document_id, ""):
                errors.append(_error("EVIDENCE_REFERENCE_ERROR", q.question_id, ev.evidence_id, "parser_version", f"文档 {ev.document_id} 解析器版本不匹配"))
                continue
            doc_blocks = corpus_blocks.get(ev.document_id, {})
            block = doc_blocks.get(ev.block_id)
            if block is None:
                errors.append(_error("EVIDENCE_REFERENCE_ERROR", q.question_id, ev.evidence_id, "block_id", f"文档 {ev.document_id} 中不存在块 {ev.block_id}"))
                continue
            block_text = block.get("text", "")
            block_len = len(block_text)
            if ev.char_start < 0 or ev.char_end > block_len or ev.char_start >= ev.char_end:
                errors.append(_error("EVIDENCE_REFERENCE_ERROR", q.question_id, ev.evidence_id, "char_start/char_end", f"字符区间 [{ev.char_start},{ev.char_end}) 超出块长度 {block_len}"))
                continue
            actual_slice = block_text[ev.char_start:ev.char_end]
            if ev.quote != actual_slice:
                errors.append(_error("EVIDENCE_REFERENCE_ERROR", q.question_id, ev.evidence_id, "quote", f"quote 与原块切片不一致: 标注长度 {len(ev.quote)}，实际长度 {len(actual_slice)}"))

    if not dataset.is_synthetic:
        for d in documents:
            if d.get("metadata", {}).get("is_synthetic", False):
                errors.append(_error("EVIDENCE_REFERENCE_ERROR", None, None, "is_synthetic", "数据集 is_synthetic=false 但语料包含合成文档"))
                break

    if errors:
        return _make_failure(
            errors=errors,
            manifest_path=manifest_path, questions_path=questions_path,
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            question_count=len(dataset.questions),
        )

    # Chunk and build indexes
    import time as _time

    _t_index0 = _time.perf_counter()
    chunks = chunk_documents(documents, max_chars=500)
    bm25_index = BM25Index(chunks, k1=1.5, b=0.75)
    _t_index_bm25 = _time.perf_counter() - _t_index0

    # Build dense index if needed
    dense_index = None
    emb_service = None
    truncated_chunk_count = None
    _t_index_dense = None
    if mode in ("dense", "hybrid"):
        if not model_path:
            return _make_failure(
                errors=[_error("PARAM_ERROR", None, None, "model_path", "dense/hybrid 模式需要 --model-path")],
                manifest_path=manifest_path, questions_path=questions_path,
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.dataset_version,
                question_count=len(dataset.questions),
            )
        from campus_assistant.retrieval.embedding import EmbeddingService
        from campus_assistant.retrieval.dense import DenseIndex

        _t_dense0 = _time.perf_counter()
        try:
            emb_service = EmbeddingService(model_path)
            texts = [c.get("text", "") for c in chunks]
            truncated_chunk_count = emb_service.count_truncated(texts)
            doc_embeddings = emb_service.encode_documents(texts)
            dense_index = DenseIndex(chunks, doc_embeddings)
        except Exception as e:
            return _make_failure(
                errors=[_error("INDEX_BUILD_ERROR", None, None, "embedding", f"向量索引构建失败: {type(e).__name__}")],
                manifest_path=manifest_path, questions_path=questions_path,
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.dataset_version,
                question_count=len(dataset.questions),
            )
        _t_index_dense = _time.perf_counter() - _t_dense0

    # Evaluate each question（T027：按题应用产品同一 T011 筛选规则）
    from campus_assistant.retrieval.filters import compute_allowed_document_ids

    per_question = []
    _t_query0 = _time.perf_counter()
    for q in dataset.questions:
        q_dict = q.model_dump()
        allowed = compute_allowed_document_ids(documents, q.conditions or None)["allowed_document_ids"]

        if mode == "bm25":
            hits = bm25_index.search(q.query, top_k=top_k, allowed_document_ids=allowed)
        elif mode == "dense":
            q_emb = emb_service.encode_query(q.query)
            hits = dense_index.search(q_emb, top_k=top_k, allowed_document_ids=allowed)
        elif mode == "hybrid":
            from campus_assistant.retrieval.hybrid import rrf_fusion
            bm25_hits = bm25_index.search(q.query, top_k=20, allowed_document_ids=allowed)
            q_emb = emb_service.encode_query(q.query)
            dense_hits = dense_index.search(q_emb, top_k=20, allowed_document_ids=allowed)
            hits = rrf_fusion(bm25_hits, dense_hits, top_k=top_k)
        else:
            hits = []

        result = evaluate_question(q_dict, hits, top_k=top_k)
        result["question_type"] = q.question_type
        result["group_id"] = q.group_id
        result["conditions"] = q_dict.get("conditions")
        result["rationale"] = q.rationale
        result["missing"] = q.missing
        per_question.append(result)
    _t_query_total = _time.perf_counter() - _t_query0

    summary = compute_summary(per_question)

    # T027：按题型/筛选分组聚合（含题数与分母；不足题单独分母）
    def _group_summary(items: list[dict]) -> dict:
        s = compute_summary(items)
        s["question_count"] = len(items)
        s["question_ids"] = [x["question_id"] for x in items]
        return s

    by_type: dict[str, dict] = {}
    for item in per_question:
        key = item.get("question_type") or "untyped"
        by_type.setdefault(key, []).append(item)
    summary_by_type = {k: _group_summary(v) for k, v in by_type.items()}

    by_filter_group: dict[str, dict] = {}
    for item in per_question:
        cond = item.get("conditions")
        has_filter = bool(cond and any(cond.get(f) is not None for f in
                                       ("campus", "student_type", "admission_year", "as_of_date")))
        key = (item.get("group_id") + "|filtered") if (item.get("group_id") and has_filter) else \
            ("filtered" if has_filter else "no_filter")
        by_filter_group.setdefault(key, []).append(item)
    summary_by_filter_group = {k: _group_summary(v) for k, v in by_filter_group.items()}

    answerable_count = sum(1 for q in dataset.questions if q.answerable)
    unanswerable_count = len(dataset.questions) - answerable_count

    return {
        "schema_version": "1.0",
        "evaluator_version": EVALUATOR_VERSION,
        "valid": True,
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "split": dataset.split,
        "is_synthetic": dataset.is_synthetic,
        "retriever_version": RETRIEVER_VERSION,
        "tokenizer_version": TOKENIZER_VERSION,
        "chunker_version": CHUNKER_VERSION,
        "parser_version": "1.0",
        "mode": mode,
        "model": model_path if model_path else None,
        "embedding_model_id": emb_service.model_name if emb_service else None,
        "embedding_model_revision": emb_service.model_revision if emb_service else None,
        "truncated_chunk_count": truncated_chunk_count if emb_service else None,
        "truncation_note": (
            "超出模型 token 上限的长块在向量计算中可能仅部分参与；"
            "原文与 chunk 文本未被截短或覆盖。"
            if emb_service
            else None
        ),
        "embedding_normalization": "l2" if mode in ("dense", "hybrid") else None,
        "query_prefix": "为这个句子生成表示以用于检索相关文章：" if mode in ("dense", "hybrid") else None,
        "rrf_k": 60 if mode == "hybrid" else None,
        "parameters": {
            "max_chars": 500,
            "k1": 1.5,
            "b": 0.75,
            "top_k": top_k,
        },
        "question_count": len(dataset.questions),
        "answerable_count": answerable_count,
        "unanswerable_count": unanswerable_count,
        "manifest_sha256": _file_sha256(manifest_path),
        "questions_sha256": _file_sha256(questions_path),
        "corpus_documents": [
            {"document_id": d["document_id"], "sha256": d.get("metadata", {}).get("sha256", "")}
            for d in documents
        ],
        "authoring_note": dataset.authoring_note,
        # T027-R1：指标语义与分母显式声明（v2 fact-group OR 口径 / 旧 unit 口径兼容）
        "metrics_semantics": dataset.metric_semantics or "unit_evidence_v1.0",
        "recall_definition": (
            "evidence_recall = 被完整覆盖的必要事实数 / 必要事实总数"
            "（同 fact_id 的可替代来源组内 OR；不同 fact_id 组间 AND；"
            "未标 fact_id 的旧数据等价于逐证据口径）"
        ),
        "summary": summary,
        "summary_by_type": summary_by_type,
        "summary_by_filter_group": summary_by_filter_group,
        "timing_seconds": {
            "note": "仅记录本轮单次运行的分段耗时（索引构建/查询），非统计稳定性能，不作速度结论",
            "index_build_bm25": round(_t_index_bm25, 4),
            "index_build_dense": round(_t_index_dense, 4) if _t_index_dense is not None else None,
            "query_total": round(_t_query_total, 4),
            "query_scope": f"{len(dataset.questions)} 题串行查询（含编码查询向量的耗时）",
        },
        "per_question": per_question,
        "errors": [],
    }


def _make_failure(
    *,
    errors: list[dict],
    manifest_path: Path | None = None,
    questions_path: Path | None = None,
    dataset_id: str | None = None,
    dataset_version: str | None = None,
    question_count: int | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "evaluator_version": EVALUATOR_VERSION,
        "valid": False,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "split": None,
        "is_synthetic": None,
        "retriever_version": RETRIEVER_VERSION,
        "tokenizer_version": TOKENIZER_VERSION,
        "chunker_version": CHUNKER_VERSION,
        "parser_version": "1.0",
        "mode": None,
        "model": None,
        "embedding_model_id": None,
        "embedding_model_revision": None,
        "truncated_chunk_count": None,
        "truncation_note": None,
        "embedding_normalization": None,
        "query_prefix": None,
        "rrf_k": None,
        "parameters": {"max_chars": 500, "k1": 1.5, "b": 0.75, "top_k": None},
        "question_count": question_count,
        "answerable_count": None,
        "unanswerable_count": None,
        "manifest_sha256": _file_sha256(manifest_path) if manifest_path else None,
        "questions_sha256": _file_sha256(questions_path) if questions_path else None,
        "corpus_documents": [],
        "summary": None,
        "per_question": [],
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="离线检索评测")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="bm25")
    parser.add_argument("--model-path", default=None, help="Embedding model directory path")
    args = parser.parse_args(argv)

    if not isinstance(args.top_k, int) or isinstance(args.top_k, bool):
        print(json.dumps(_make_failure(
            errors=[_error("PARAM_ERROR", None, None, "top_k", "top_k 必须是整数")],
        ), ensure_ascii=False, indent=2))
        return 2
    if args.top_k < 1 or args.top_k > 20:
        print(json.dumps(_make_failure(
            errors=[_error("PARAM_ERROR", None, None, "top_k", "top_k 必须在 1-20 之间")],
        ), ensure_ascii=False, indent=2))
        return 2

    if args.mode in ("dense", "hybrid") and not args.model_path:
        print(json.dumps(_make_failure(
            errors=[_error("PARAM_ERROR", None, None, "model_path", f"{args.mode} 模式需要 --model-path")],
        ), ensure_ascii=False, indent=2))
        return 2

    manifest_path = Path(args.manifest)
    questions_path = Path(args.questions)

    try:
        corpus_root = Path(args.corpus_root).resolve()
    except OSError:
        print(json.dumps(_make_failure(
            errors=[_error("MANIFEST_READ_ERROR", None, None, "corpus-root", "无法解析语料根目录")],
        ), ensure_ascii=False, indent=2))
        return 1

    try:
        result = _run_eval(manifest_path, corpus_root, questions_path, args.top_k, args.mode, args.model_path)
    except Exception as e:
        print(json.dumps(_make_failure(
            errors=[_error("EVALUATION_ERROR", None, None, "run", f"评测异常: {type(e).__name__}")],
        ), ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
