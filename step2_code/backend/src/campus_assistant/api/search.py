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
    document_id: str | None = Field(
        default=None,
        description="可选的用户明确选择的单份来源文件（T031）；null/未传=全部资料。"
        "只支持单文件，不从查询自动猜测；非法值返回 422",
    )
    include_unknown_student_type: bool = Field(
        default=True,
        description="T043：是否将学生类型未标注资料纳入参考依据（正式 search/ask 默认开启，"
        "可关闭回 strict）。仅影响 student_type 未知一个维度；已知类型冲突与 "
        "campus/year/date 等其它检查保持；参考命中携带未核实状态说明。",
    )

    @field_validator("include_unknown_student_type", mode="before")
    @classmethod
    def validate_include_unknown(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        raise ValueError("include_unknown_student_type 必须是布尔值")

    @field_validator("document_id", mode="before")
    @classmethod
    def validate_document_id(cls, v: Any) -> str | None:
        from campus_assistant.retrieval.source_selection import normalize_document_id

        return normalize_document_id(v)

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
    student_type_status: str | None = Field(
        default=None,
        description="T043：仅参考纳入的学生类型未标注命中携带「学生类型未标注，适用范围尚未核实」；"
        "普通命中为 null（旧协议）",
    )


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
    include_unknown_student_type: bool = Field(
        default=False,
        description="T043 本次请求的参考准入模式（false=旧 strict）",
    )
    unknown_student_type_document_ids: list[str] = Field(
        default_factory=list,
        description="以参考纳入的学生类型未标注文档（适用范围尚未核实，非适用性已确认）",
    )
    confirmed_count: int | None = Field(
        default=None, description="学生类型已匹配的准入文档数"
    )
    reference_count: int | None = Field(
        default=None, description="学生类型未标注、作为参考的文档数（不计为适用性已确认）"
    )


class SourceSelectionSummary(BaseModel):
    """User-selected single-file scope (T031). Distinct from filter_summary:
    filter_summary counts the four applicability conditions only;
    allowed_after_selection counts the final intersection (conditions ∩
    selected file). The two counts are never interchangeable."""

    selected: bool = Field(description="是否指定了来源文件")
    document_id: str | None = None
    title: str | None = Field(default=None, description="服务端目录映射的标题；未知为 null")
    version_label: str | None = Field(default=None, description="版本标签；无版本如实为 null")
    policy_group_id: str | None = None
    is_admitted: bool | None = Field(
        default=None,
        description="所选文件是否通过现有适用条件；未选择时为 null。False=被条件排除，无准入依据",
    )
    allowed_before_selection: int = Field(
        description="仅四项适用条件下的可准入文档数（无条件=文档总数）"
    )
    allowed_after_selection: int = Field(
        description="再与所选文件求交后的可准入数（选中且通过=1；被排除=0）"
    )
    notes: list[str] = Field(default_factory=list)


class DocumentCatalogEntry(BaseModel):
    """Selection catalog entry — identity/metadata only, no paths or text."""

    document_id: str
    title: str | None = None
    version_label: str | None = None
    policy_group_id: str | None = None
    published_at: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    is_synthetic: bool = False


class DocumentCatalogResponse(BaseModel):
    status: str = Field(description="ok | unconfigured | failed")
    available: bool = Field(description="目录是否可用；false 时 documents 为空")
    documents: list[DocumentCatalogEntry]
    count: int
    request_id: str


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
    document_id: str | None = Field(
        default=None, description="回显的来源文件选择（与提交一致；null=全部资料）"
    )
    source_selection: SourceSelectionSummary | None = Field(
        default=None, description="来源选择摘要（与 filter_summary 四条件口径分开）"
    )
    include_unknown_student_type: bool = Field(
        default=False,
        description="回显本次实际准入模式（true=学生类型未标注资料可作参考；false=旧 strict）",
    )
    errors: list[dict[str, Any]]
    request_id: str



class CandidatesRequest(SearchRequest):
    """T038: explicit uncertain-source candidate search.

    Same query/mode/top_k/filters/document_id contract as /search (unknown
    document_id = explicit 422). uncertainty_dimensions accepts only
    'date' / 'student_type' (1-2 items); the request must have the
    corresponding filter (as_of_date / student_type) for each dimension
    actually used as a relaxation basis. Explicit request only — never runs
    from status/startup/normal search/ask.
    """

    uncertainty_dimensions: list[str] = Field(
        description="要查看的未核实维度：仅 date / student_type（可单项或两项）"
    )


class CandidateSearchHit(SearchHit):
    """Hit enriched with the uncertainty actually unknown for its document."""

    unknown_dimensions: list[str] = Field(default_factory=list)
    uncertainty_note: str = ""


class CandidateSummary(BaseModel):
    document_total: int
    strict_allowed_count: int
    candidate_document_count: int
    counting_rules: str


class CandidatesResponse(BaseModel):
    query: str
    query_tokens: list[str]
    mode: str
    status: str
    filters: SearchFilters | None = None
    document_id: str | None = None
    uncertainty_dimensions: list[str]
    active_dimensions: list[str]
    candidate_summary: CandidateSummary
    hits: list[CandidateSearchHit]
    disclaimer: str
    include_unknown_student_type: bool = Field(
        default=False,
        description="回显本次候选去重所依据的准入模式（true=排除本次含参考的实际准入集合）",
    )
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

    @router.get("/documents", response_model=DocumentCatalogResponse)
    async def search_documents(request: Request) -> dict:
        """Selection catalog of successfully parsed documents (T031).

        Identity/metadata fields only — no disk paths, no full text, no
        secrets. Unconfigured/failed corpora return a clear unavailable
        state with an empty catalog rather than an error page.
        """
        from campus_assistant.retrieval.source_selection import build_document_catalog

        status = request.app.state.search_status
        if status in ("unconfigured", "failed"):
            return {
                "status": status,
                "available": False,
                "documents": [],
                "count": 0,
                "request_id": request.state.request_id,
            }
        catalog = build_document_catalog(request.app.state.corpus_data or [])
        return {
            "status": "ok",
            "available": True,
            "documents": catalog,
            "count": len(catalog),
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

        # T031: user-selected source must name a currently parsed document.
        # Unknown IDs are an explicit 422 — never silently widened to "all".
        from campus_assistant.retrieval.source_selection import (
            SourceSelectionError,
            resolve_document_id,
        )

        try:
            document_id = resolve_document_id(
                body.document_id, request.app.state.corpus_data or []
            )
        except SourceSelectionError as e:
            return JSONResponse(
                status_code=422,
                content={
                    "code": e.code,
                    "message": str(e),
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
            document_id=document_id,
            include_unknown_student_type=body.include_unknown_student_type,
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
            "document_id": document_id,
            "source_selection": result["source_selection"],
            "include_unknown_student_type": body.include_unknown_student_type,
            "errors": request.app.state.search_errors,
            "request_id": request_id,
        }

    @router.post(
        "/candidates",
        response_model=CandidatesResponse,
        responses={
            422: {"model": ErrorResponse, "description": "维度/条件/文档 ID 不合法"},
            503: {"model": ErrorResponse, "description": "语料未配置或检索不可用"},
        },
    )
    async def search_candidates(request: Request, body: CandidatesRequest) -> dict:
        """T038: user-explicit read-only view of uncertain sources.

        Candidates are re-checked independently per document and never mix
        into strict results, ask evidence, generation messages or agent tools.
        """
        status = request.app.state.search_status
        request_id = request.state.request_id
        if status == "unconfigured":
            return JSONResponse(status_code=503, content={
                "code": "CORPUS_NOT_CONFIGURED", "message": "语料未配置", "request_id": request_id})
        if status == "failed":
            return JSONResponse(status_code=503, content={
                "code": "SEARCH_UNAVAILABLE", "message": "检索不可用：索引构建失败", "request_id": request_id})
        if body.mode not in request.app.state.available_modes:
            return JSONResponse(status_code=503, content={
                "code": "RETRIEVER_UNAVAILABLE",
                "message": f"检索模式 {body.mode} 不可用", "request_id": request_id})

        from campus_assistant.retrieval.filters import CandidateRequestError
        from campus_assistant.retrieval.service import execute_candidates
        from campus_assistant.retrieval.source_selection import (
            SourceSelectionError, resolve_document_id)

        try:
            document_id = resolve_document_id(body.document_id, request.app.state.corpus_data or [])
        except SourceSelectionError as e:
            return JSONResponse(status_code=422, content={
                "code": e.code, "message": str(e), "request_id": request_id})

        try:
            result = execute_candidates(
                query=body.query,
                mode=body.mode,
                top_k=body.top_k,
                filters_norm=body.filters.normalized() if body.filters else None,
                document_id=document_id,
                uncertainty_dimensions=body.uncertainty_dimensions,
                documents=request.app.state.corpus_data or [],
                bm25_index=request.app.state.search_index,
                dense_index=request.app.state.dense_index,
                embedding_service=request.app.state.embedding_service,
                include_unknown_student_type=body.include_unknown_student_type,
            )
        except CandidateRequestError as e:
            return JSONResponse(status_code=422, content={
                "code": e.code, "message": str(e), "request_id": request_id})

        return {
            "query": body.query,
            "query_tokens": result["query_tokens"],
            "mode": body.mode,
            "status": status,
            "filters": body.filters,
            "document_id": document_id,
            "uncertainty_dimensions": result["uncertainty_dimensions"],
            "active_dimensions": result["active_dimensions"],
            "candidate_summary": result["candidate_summary"],
            "hits": result["hits"],
            "disclaimer": result["disclaimer"],
            "include_unknown_student_type": body.include_unknown_student_type,
            "errors": request.app.state.search_errors,
            "request_id": request_id,
        }


    return router
