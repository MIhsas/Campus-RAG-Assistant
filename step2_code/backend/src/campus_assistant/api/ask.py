"""Ask API endpoints (T012).

POST /api/v1/ask        — single-turn evidence organizing (+ optional generation)
GET  /api/v1/ask/status — runtime mode and generator configuration

Default answer_mode=extractive: returns original-text excerpts only
(status=evidence_only, answer=null). Generated mode requires an injected
AnswerProvider; without one it is 503/GENERATOR_NOT_CONFIGURED — excerpts
are never dressed up as a generated answer. Retrieval failures stay errors.

This endpoint does not turn health/ready into "fully ready"; see /health.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from campus_assistant.api.search import SearchFilters, SearchRequest

ANSWER_MODES = ("extractive", "generated")

EXTRACTIVE_DISCLAIMER = "以下是相关原文摘录，尚未生成答案，需核对适用条件。"

EMPTY_STATE_MESSAGES = {
    "no_admissible_docs": "没有满足所选条件的资料，无法整理依据；可清除条件后重试。",
    "no_hits": "满足条件的资料中没有检索命中，无法整理依据。",
    "budget_empty": "命中内容均超出本次整理的字符预算（整条无法装入），未截取或拼接原文。",
}


class AskRequest(SearchRequest):
    """query/mode/top_k/filters follow the exact /search rules."""

    answer_mode: str = Field(default="extractive")

    @field_validator("answer_mode", mode="before")
    @classmethod
    def validate_answer_mode(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("answer_mode 必须是字符串")
        if v not in ANSWER_MODES:
            raise ValueError(f"answer_mode 必须是 extractive/generated，收到: {v}")
        return v


class EvidenceItem(BaseModel):
    evidence_id: str
    text: str
    document_id: str
    block_id: str
    chunk_id: str
    char_start: int
    char_end: int
    document_sha256: str | None = None
    title: str | None = None
    source_url: str | None = None
    version_label: str | None = None
    scope: dict[str, Any] | None = None
    published_at: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    is_synthetic: bool = False
    locator: dict[str, Any] | None = Field(
        default=None, description="原文定位（如 PDF 页码）；来源跳转见 preview_url"
    )
    preview_url: str


class BudgetSummary(BaseModel):
    max_items: int
    max_total_chars: int
    included_items: int
    included_chars: int
    skipped_items: int
    duplicate_chunks: int = 0


class CitationRef(BaseModel):
    evidence_id: str
    document_id: str
    block_id: str
    preview_url: str


class AnswerParagraph(BaseModel):
    text: str
    evidence_ids: list[str]
    citations: list[CitationRef] = Field(
        default_factory=list,
        description="由服务从证据映射解析，不接受生成器提供的路径或链接",
    )


class AnswerBody(BaseModel):
    paragraphs: list[AnswerParagraph]


class AskResponse(BaseModel):
    query: str
    query_tokens: list[str]
    mode: str
    answer_mode: str
    status: str = Field(
        description="evidence_only | generated | insufficient_evidence"
    )
    answer: AnswerBody | None = None
    answer_error: str | None = Field(
        default=None, description="生成失败时的中文原因（不输出部分坏答案）"
    )
    generation_meta: dict[str, Any] | None = Field(
        default=None,
        description="可选审计信息（model/request_id/usage/耗时/max_tokens 等非敏感字段）；"
        "供应商未返回的字段为 null，不伪造",
    )
    disclaimer: str | None = None
    evidence: list[EvidenceItem]
    evidence_state: str = Field(
        description="ok | no_admissible_docs | no_hits | budget_empty"
    )
    empty_message: str | None = None
    insufficient_reason: str | None = None
    budget: BudgetSummary
    filters: SearchFilters | None = None
    filter_summary: dict[str, Any] | None = None
    request_id: str


class AskStatusResponse(BaseModel):
    corpus_status: str
    answer_mode_default: str = "extractive"
    answer_modes_available: list[str]
    generator_configured: bool
    generator_identity: str | None = Field(
        default=None, description="已配置生成器的简短标识；不暴露路径或密钥"
    )
    available_modes: list[str]
    filter_options: dict[str, list]
    request_id: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


def create_ask_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/ask", tags=["ask"])

    @router.get("/status", response_model=AskStatusResponse)
    async def ask_status(request: Request) -> dict:
        provider = getattr(request.app.state, "answer_provider", None)
        configured = provider is not None
        identity = getattr(provider, "provider_id", None) if configured else None
        modes = ["extractive"] + (["generated"] if configured else [])
        return {
            "corpus_status": request.app.state.search_status,
            "answer_mode_default": "extractive",
            "answer_modes_available": modes,
            "generator_configured": configured,
            "generator_identity": identity if isinstance(identity, str) else None,
            "available_modes": request.app.state.available_modes,
            "filter_options": getattr(request.app.state, "filter_options", {}),
            "request_id": request.state.request_id,
        }

    @router.post(
        "",
        response_model=AskResponse,
        responses={
            503: {"model": ErrorResponse, "description": "语料/检索/生成器不可用"},
            502: {"model": ErrorResponse, "description": "生成器执行或输出校验失败"},
        },
    )
    async def ask(request: Request, body: AskRequest):
        status = request.app.state.search_status
        request_id = request.state.request_id

        # Retrieval failures stay errors — never dressed up as "no answer".
        if status == "unconfigured":
            return JSONResponse(
                status_code=503,
                content={"code": "CORPUS_NOT_CONFIGURED", "message": "语料未配置", "request_id": request_id},
            )
        if status == "failed":
            return JSONResponse(
                status_code=503,
                content={"code": "SEARCH_UNAVAILABLE", "message": "检索不可用：索引构建失败", "request_id": request_id},
            )
        available = request.app.state.available_modes
        if body.mode not in available:
            return JSONResponse(
                status_code=503,
                content={"code": "RETRIEVER_UNAVAILABLE", "message": f"检索模式 {body.mode} 不可用", "request_id": request_id},
            )

        from campus_assistant.qa.evidence import build_evidence_pack
        from campus_assistant.retrieval.service import execute_search

        filters_norm = body.filters.normalized() if body.filters else None
        result = execute_search(
            query=body.query,
            mode=body.mode,
            top_k=body.top_k,
            filters_norm=filters_norm,
            documents=request.app.state.corpus_data or [],
            bm25_index=request.app.state.search_index,
            dense_index=request.app.state.dense_index,
            embedding_service=request.app.state.embedding_service,
        )
        pack = build_evidence_pack(result["hits"], filter_summary=result["filter_summary"])

        base = {
            "query": body.query,
            "query_tokens": result["query_tokens"],
            "mode": body.mode,
            "answer_mode": body.answer_mode,
            "evidence": pack["evidence"],
            "evidence_state": pack["evidence_state"],
            "budget": pack["budget"],
            "filters": body.filters,
            "filter_summary": result["filter_summary"],
            "request_id": request_id,
        }

        if body.answer_mode == "extractive":
            empty_msg = None if pack["evidence_state"] == "ok" else EMPTY_STATE_MESSAGES[pack["evidence_state"]]
            return {
                **base,
                "status": "evidence_only",
                "answer": None,
                "answer_error": None,
                "disclaimer": EXTRACTIVE_DISCLAIMER,
                "empty_message": empty_msg,
                "insufficient_reason": None,
            }

        # answer_mode == "generated" — requires an injected provider.
        provider = getattr(request.app.state, "answer_provider", None)
        if provider is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "GENERATOR_NOT_CONFIGURED",
                    "message": "自动作答未配置；可使用原文摘录（answer_mode=extractive）。运行时模型 API/预算需由用户之后提供。",
                    "request_id": request_id,
                },
            )

        # Nothing to ground on — do not call the provider and do not guess.
        if not pack["evidence"]:
            empty_msg = EMPTY_STATE_MESSAGES[pack["evidence_state"]]
            return {
                **base,
                "status": "insufficient_evidence",
                "answer": None,
                "answer_error": None,
                "disclaimer": None,
                "empty_message": empty_msg,
                "insufficient_reason": "无可用证据，未调用生成器。",
            }

        from campus_assistant.qa.providers import validate_generation

        allowed_ids = {e["evidence_id"] for e in pack["evidence"]}
        from starlette.concurrency import run_in_threadpool

        try:
            # Sync provider HTTP must not block the event loop.
            raw = await run_in_threadpool(
                lambda: provider.generate(
                    query=body.query, evidence=pack["evidence"], filters=filters_norm
                )
            )
        except Exception as e:  # provider bugs must not affect search/preview
            # Safe mapped message only (user_message); never raw exception
            # content, Authorization headers or API keys.
            safe = getattr(e, "user_message", None) or f"生成器执行失败：{type(e).__name__}"
            return JSONResponse(
                status_code=502,
                content={
                    "code": "GENERATOR_ERROR",
                    "message": f"{safe}；可改用原文摘录（answer_mode=extractive）。",
                    "request_id": request_id,
                },
            )

        generation_meta = None
        if isinstance(raw, dict) and isinstance(raw.get("metadata"), dict):
            generation_meta = dict(raw["metadata"])

        kind, normalized, error = validate_generation(raw, allowed_ids)
        if kind == "invalid":
            return JSONResponse(
                status_code=502,
                content={
                    "code": "GENERATOR_INVALID_OUTPUT",
                    "message": f"生成结果校验失败（{error}），未返回给用户；可改用原文摘录（answer_mode=extractive）。",
                    "request_id": request_id,
                },
            )
        if kind == "insufficient_evidence":
            return {
                **base,
                "status": "insufficient_evidence",
                "answer": None,
                "answer_error": None,
                "generation_meta": generation_meta,
                "disclaimer": None,
                "empty_message": None,
                "insufficient_reason": normalized["reason"],
            }

        # kind == "answer": resolve citations from the evidence mapping —
        # the provider never supplies paths or links.
        by_id = {e["evidence_id"]: e for e in pack["evidence"]}
        paragraphs = []
        for p in normalized["paragraphs"]:
            paragraphs.append({
                "text": p["text"],
                "evidence_ids": p["evidence_ids"],
                "citations": [
                    {
                        "evidence_id": ev_id,
                        "document_id": by_id[ev_id]["document_id"],
                        "block_id": by_id[ev_id]["block_id"],
                        "preview_url": by_id[ev_id]["preview_url"],
                    }
                    for ev_id in p["evidence_ids"]
                ],
            })
        return {
            **base,
            "status": "generated",
            "answer": {"paragraphs": paragraphs},
            "answer_error": None,
            "generation_meta": generation_meta,
            "disclaimer": "自动生成内容仅供参考，引用仅证明定位有效，需人工核对适用条件与语义支持。",
            "empty_message": None,
            "insufficient_reason": None,
        }

    return router
