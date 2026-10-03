"""Search API endpoints.

GET  /api/v1/search/status — search index status (always 200)
POST /api/v1/search        — keyword/dense/hybrid search (requires configured corpus)

Optional filters (campus / student_type / admission_year / as_of_date) restrict
document admission BEFORE candidate truncation. Empty scope arrays mean
"unknown" and are excluded when that dimension is filtered. All selected
conditions are AND-ed. This is applicability screening for evidence retrieval,
not a qualification decision.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

RETRIEVER_VERSION = "1.1"
TOKENIZER_VERSION = "cjk_bigram_ascii_v1"
CHUNKER_VERSION = "1.0"


# --- Request model ---

class SearchFilters(BaseModel):
    """Optional applicability filters. None = that dimension unrestricted."""

    model_config = {"extra": "forbid"}

    campus: str | None = None
    student_type: str | None = None
    admission_year: int | None = None
    as_of_date: str | None = None

    @field_validator("campus", "student_type", mode="before")
    @classmethod
    def validate_scope_value(cls, v: Any) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("必须是字符串或 null")
        v = v.strip()
        if not v:
            raise ValueError("不能为空字符串；不限制该维度请用 null 或不传")
        if len(v) > 64:
            raise ValueError("长度不能超过 64")
        return v

    @field_validator("admission_year", mode="before")
    @classmethod
    def validate_admission_year(cls, v: Any) -> int | None:
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("必须是整数或 null")
        if v < 1900 or v > 2100:
            raise ValueError("超出 1900—2100 范围")
        return v

    @field_validator("as_of_date", mode="before")
    @classmethod
    def validate_as_of_date(cls, v: Any) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("必须是 YYYY-MM-DD 字符串或 null")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError("必须是 YYYY-MM-DD 格式")
        try:
            date.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError(f"不是有效日历日期: {v}")
        return v

    def normalized(self) -> dict[str, Any]:
        return {
            "campus": self.campus,
            "student_type": self.student_type,
            "admission_year": self.admission_year,
            "as_of_date": self.as_of_date,
        }


class SearchRequest(BaseModel):
    model_config = {"extra": "forbid"}

    query: str = Field(...)
    top_k: int = Field(default=5)
    mode: str = Field(default="bm25")
    filters: SearchFilters | None = Field(default=None)

    @field_validator("query", mode="before")
    @classmethod
    def validate_query(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("query 必须是字符串")
        if len(v) < 1 or len(v) > 500:
            raise ValueError("query 长度必须在 1—500 之间")
        if not v.strip():
            raise ValueError("query 不能全为空白")
        return v

    @field_validator("top_k", mode="before")
    @classmethod
    def validate_top_k(cls, v: Any) -> int:
        if isinstance(v, bool):
            raise ValueError("top_k 必须是整数，不能是布尔值")
        if isinstance(v, float):
            raise ValueError("top_k 必须是整数，不能是浮点数")
        if isinstance(v, str):
            raise ValueError("top_k 必须是整数")
        if not isinstance(v, int):
            raise ValueError("top_k 必须是整数")
        if v < 1 or v > 20:
            raise ValueError("top_k 必须在 1—20 之间")
        return v

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("mode 必须是字符串")
        if v not in ("bm25", "dense", "hybrid"):
            raise ValueError(f"mode 必须是 bm25/dense/hybrid，收到: {v}")
        return v


# --- Response models ---

class MatchedTerm(BaseModel):
    term: str
    tf: int
    df: int
    idf: float
    contribution: float


class SearchHitChunk(BaseModel):
    chunk_id: str
    document_id: str
    block_id: str
    ordinal: int
    kind: str
    text: str
    char_start: int
    char_end: int
    locator: dict[str, Any]
    cells: list[str] | None = None
    metadata: dict[str, Any]
    parser_version: str
    chunker_version: str
    strategy: str
    max_chars: int
    warnings: list[str]


class SearchHit(BaseModel):
    rank: int
    score: float
    chunk: SearchHitChunk
    preview_url: str
    matched_terms: list[MatchedTerm]
    bm25_rank: int | None = None
    dense_rank: int | None = None
    bm25_score: float | None = None
    dense_score: float | None = None


class SearchStatusResponse(BaseModel):
    status: str
    document_count: int
    parsed_count: int
    chunk_count: int
    indexed_chunk_count: int
    synthetic_count: int
    retriever_version: str
    tokenizer_version: str
    chunker_version: str
    max_chars: int
    k1: float
    b: float
    available_modes: list[str]
    embedding_model: str | None = Field(
        default=None, description="简洁模型身份（本地目录名），不含本机路径"
    )
    embedding_model_revision: str | None = Field(
        default=None, description="下载元数据核实的 revision；无法核实为 unknown"
    )
    embedding_max_seq_length: int | None = Field(
        default=None, description="模型 token 上限；长块编码时可能被截断"
    )
    truncated_chunk_count: int | None = Field(
        default=None,
        description="正文编码时超出 token 上限的块数；原文与 chunk 文本未被截短",
    )
    embedding_error: str | None = Field(
        default=None, description="向量模型不可用的中文原因；BM25/预览不受影响"
    )
    filter_options: dict[str, list] = Field(
        default_factory=dict,
        description="从已解析语料提取的筛选选项（campus/student_type/admission_year）",
    )
    errors: list[dict[str, Any]]
    request_id: str


class FilterSummary(BaseModel):
    """Applicability screening accounting. Not a qualification decision."""

    active: bool = Field(description="是否启用了筛选；false 时不限制任何文档")
    document_total: int = Field(description="语料文档总数")
    allowed_count: int = Field(description="通过筛选的文档数")
    excluded_counts: dict[str, int] = Field(
        description="按排除原因的文档计数，互斥；见 counting_rules"
    )
    counting_rules: str = Field(description="各筛选计数的口径说明")
    notes: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    query_tokens: list[str]
    mode: str
    status: str
    chunk_count: int
    indexed_chunk_count: int
    hits: list[SearchHit]
    filters: SearchFilters | None = Field(
        default=None, description="回显的规范化筛选条件（与提交一致）"
    )
    filter_summary: FilterSummary | None = None
    errors: list[dict[str, Any]]
    request_id: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


# --- Router factory ---

def create_search_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/search", tags=["search"])

    @router.get("/status", response_model=SearchStatusResponse)
    async def search_status(request: Request) -> dict:
        emb = request.app.state.embedding_service
        return {
            "status": request.app.state.search_status,
            "document_count": request.app.state.document_count,
            "parsed_count": request.app.state.parsed_count,
            "chunk_count": request.app.state.search_chunk_count,
            "indexed_chunk_count": request.app.state.search_indexed_chunk_count,
            "synthetic_count": request.app.state.search_synthetic_count,
            "retriever_version": RETRIEVER_VERSION,
            "tokenizer_version": TOKENIZER_VERSION,
            "chunker_version": CHUNKER_VERSION,
            "max_chars": 500,
            "k1": 1.5,
            "b": 0.75,
            "available_modes": request.app.state.available_modes,
            "embedding_model": emb.model_name if emb else None,
            "embedding_model_revision": emb.model_revision if emb else None,
            "embedding_max_seq_length": emb.max_seq_length if emb else None,
            "truncated_chunk_count": getattr(
                request.app.state, "search_truncated_chunk_count", None
            ),
            "embedding_error": getattr(request.app.state, "embedding_error", None),
            "filter_options": getattr(request.app.state, "filter_options", {}),
            "errors": request.app.state.search_errors,
            "request_id": request.state.request_id,
        }

    @router.post(
        "",
        response_model=SearchResponse,
        responses={
            503: {"model": ErrorResponse, "description": "语料未配置或检索不可用"},
        },
    )
    async def search(request: Request, body: SearchRequest) -> dict:
        status = request.app.state.search_status
        request_id = request.state.request_id

        if status == "unconfigured":
            return JSONResponse(
                status_code=503,
                content={
                    "code": "CORPUS_NOT_CONFIGURED",
                    "message": "语料未配置",
                    "request_id": request_id,
                },
            )

        if status == "failed":
            return JSONResponse(
                status_code=503,
                content={
                    "code": "SEARCH_UNAVAILABLE",
                    "message": "检索不可用：索引构建失败",
                    "request_id": request_id,
                },
            )

        # Check if requested mode is available
        available = request.app.state.available_modes
        if body.mode not in available:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "RETRIEVER_UNAVAILABLE",
                    "message": f"检索模式 {body.mode} 不可用",
                    "request_id": request_id,
                },
            )

        from campus_assistant.retrieval.service import execute_search

        query = body.query

        # Shared pipeline with /ask: mode dispatch + T011 filters + hit format.
        result = execute_search(
            query=query,
            mode=body.mode,
            top_k=body.top_k,
            filters_norm=body.filters.normalized() if body.filters else None,
            documents=request.app.state.corpus_data or [],
            bm25_index=request.app.state.search_index,
            dense_index=request.app.state.dense_index,
            embedding_service=request.app.state.embedding_service,
        )

        return {
            "query": query,
            "query_tokens": result["query_tokens"],
            "mode": body.mode,
            "status": status,
            "chunk_count": request.app.state.search_chunk_count,
            "indexed_chunk_count": request.app.state.search_indexed_chunk_count,
            "hits": result["hits"],
            "filters": body.filters,
            "filter_summary": result["filter_summary"],
            "errors": request.app.state.search_errors,
            "request_id": request_id,
        }

    return router
