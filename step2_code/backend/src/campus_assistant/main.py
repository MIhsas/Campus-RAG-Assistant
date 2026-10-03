"""Application entry point.

Usage:
    uvicorn campus_assistant.main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, Request, Response

from campus_assistant.api.health import router as health_router


def create_app(
    manifest_path: Path | None = None,
    corpus_root: Path | None = None,
    embedding_model_path: str | None = None,
    answer_provider: object | None = None,
    procedures_path: Path | None = None,
    self_check_path: Path | None = None,
    asr_adapter: object | None = None,
    demo_home: bool = False,
    planner: object | None = None,
) -> FastAPI:
    """Application factory. Can be called multiple times for testing.

    answer_provider: optional AnswerProvider (qa.providers) for generated
    answers. None = extractive-only (the default) — generated mode returns
    503/GENERATOR_NOT_CONFIGURED. No fake provider ships with the product.

    procedures_path: optional procedures template (T016). Explicitly
    injected by tests/demos (synthetic templates) — not loaded by default.

    self_check_path: optional self-check rule config (T019). Explicitly
    injected by demos/tests — ordinary services never auto-enable the
    synthetic rule.

    asr_adapter: optional local ASR adapter (T020). Loads only from a
    configured local model directory; unconfigured services report ASR
    unavailable and never auto-download models.

    demo_home: serve the demo-flavoured home (with synthetic demo
    questions) at `/` — only for explicit demo entries (demo-campus).
    Normal runs use the neutral home.

    planner: optional planner for the restricted agent loop (T023).
    None (the default) keeps Agent mode OFF — normal runs expose only the
    deterministic fixed workflow. The simulated planner is injected only by
    explicit demo/test entries and is always labelled 模拟规划.
    """
    if (manifest_path is None) != (corpus_root is None):
        raise ValueError("manifest_path 和 corpus_root 必须同时提供或同时省略")

    application = FastAPI(
        title="校园教务智能问答系统",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    application.include_router(health_router)

    # Corpus state: default unconfigured
    application.state.corpus_status = "unconfigured"
    application.state.corpus_data = None
    application.state.corpus_errors = []
    application.state.document_count = 0
    application.state.parsed_count = 0

    # Search index state: default unconfigured
    application.state.search_status = "unconfigured"
    application.state.search_index = None
    application.state.search_chunks = []
    application.state.search_chunk_count = 0
    application.state.search_indexed_chunk_count = 0
    application.state.search_synthetic_count = 0
    application.state.search_errors = []

    # Embedding state
    application.state.embedding_service = None
    application.state.dense_index = None
    application.state.available_modes = ["bm25"]
    application.state.embedding_error = None
    application.state.search_truncated_chunk_count = None

    # Answer generation state (T012): injectable provider, extractive default
    application.state.answer_provider = answer_provider

    # Procedures templates (T016): explicitly injected, None = not configured
    application.state.procedures = None
    if procedures_path is not None:
        from campus_assistant.procedures.service import load_procedures

        application.state.procedures = load_procedures(procedures_path)

    # Self-check rule (T019): explicitly injected, None = not configured
    application.state.self_check_rule = None
    if self_check_path is not None:
        from campus_assistant.selfcheck.service import load_rule

        application.state.self_check_rule = load_rule(self_check_path)

    # Local ASR (T020): None = not configured (text Q&A stays available)
    application.state.asr_adapter = asr_adapter

    # Restricted orchestration (T023): planner None = Agent mode off
    application.state.agent_planner = planner

    # Filter options extracted from parsed corpus (for UI)
    application.state.filter_options = {"campus": [], "student_type": [], "admission_year": []}

    # Load corpus if configured
    if manifest_path is not None and corpus_root is not None:
        from campus_assistant.corpus.parse import parse_manifest

        result = parse_manifest(manifest_path, corpus_root)
        application.state.document_count = result["document_count"]
        application.state.corpus_errors = result["errors"]
        application.state.corpus_data = result["documents"]
        application.state.parsed_count = len(result["documents"])

        if result["valid"]:
            application.state.corpus_status = "ready"
        elif application.state.parsed_count > 0:
            application.state.corpus_status = "partial"
        else:
            application.state.corpus_status = "failed"

        # Build search index from parsed documents
        _build_search_index(application, embedding_model_path)

    # Register routers
    from campus_assistant.api.corpus import create_corpus_router
    from campus_assistant.api.search import create_search_router
    from campus_assistant.api.ask import create_ask_router
    from campus_assistant.api.procedures import create_procedures_router
    from campus_assistant.api.comparison import create_comparison_router
    from campus_assistant.api.selfcheck import create_selfcheck_router
    from campus_assistant.api.asr import create_asr_router
    from campus_assistant.api.agent import create_agent_router

    application.include_router(create_corpus_router())
    application.include_router(create_search_router())
    application.include_router(create_ask_router())
    application.include_router(create_procedures_router())
    application.include_router(create_comparison_router())
    application.include_router(create_selfcheck_router())
    application.include_router(create_asr_router())
    application.include_router(create_agent_router())

    # Serve pages
    from fastapi.responses import HTMLResponse

    _STATIC_DIR = Path(__file__).resolve().parent / "static"

    @application.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def home_page():
        name = "home-demo.html" if demo_home else "home.html"
        return HTMLResponse(content=(_STATIC_DIR / name).read_text(encoding="utf-8"))

    @application.get("/preview", response_class=HTMLResponse, include_in_schema=False)
    async def preview_page():
        return HTMLResponse(content=(_STATIC_DIR / "preview.html").read_text(encoding="utf-8"))

    @application.get("/search", response_class=HTMLResponse, include_in_schema=False)
    async def search_page():
        return HTMLResponse(content=(_STATIC_DIR / "search.html").read_text(encoding="utf-8"))

    @application.get("/ask", response_class=HTMLResponse, include_in_schema=False)
    async def ask_page():
        return HTMLResponse(content=(_STATIC_DIR / "ask.html").read_text(encoding="utf-8"))

    @application.get("/procedures", response_class=HTMLResponse, include_in_schema=False)
    async def procedures_page():
        return HTMLResponse(content=(_STATIC_DIR / "procedures.html").read_text(encoding="utf-8"))

    @application.get("/compare", response_class=HTMLResponse, include_in_schema=False)
    async def compare_page():
        return HTMLResponse(content=(_STATIC_DIR / "compare.html").read_text(encoding="utf-8"))

    @application.get("/self-check", response_class=HTMLResponse, include_in_schema=False)
    async def self_check_page():
        return HTMLResponse(content=(_STATIC_DIR / "self-check.html").read_text(encoding="utf-8"))

    @application.get("/workflow", response_class=HTMLResponse, include_in_schema=False)
    async def workflow_page():
        return HTMLResponse(content=(_STATIC_DIR / "workflow.html").read_text(encoding="utf-8"))

    @application.middleware("http")
    async def add_request_id(request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    return application


def _build_search_index(app: FastAPI, embedding_model_path: str | None = None) -> None:
    """Build BM25 index (and optionally dense index) from parsed corpus data."""
    from campus_assistant.corpus.chunk import chunk_documents
    from campus_assistant.retrieval.bm25 import BM25Index

    documents = app.state.corpus_data or []

    # Compute synthetic_count from parsed documents
    app.state.search_synthetic_count = sum(
        1 for d in documents if d.get("metadata", {}).get("is_synthetic", False)
    )

    # Filter options for the search page (deduplicated, sorted)
    from campus_assistant.retrieval.filters import extract_filter_options

    app.state.filter_options = extract_filter_options(documents)

    if not documents:
        app.state.search_status = app.state.corpus_status
        app.state.search_errors = list(app.state.corpus_errors)
        return

    try:
        chunks = chunk_documents(documents, max_chars=500)
    except Exception:
        app.state.search_status = "failed"
        app.state.search_errors = list(app.state.corpus_errors) + [{
            "code": "INDEX_BUILD_ERROR",
            "document_id": None,
            "field": "chunk",
            "message": "分块失败",
        }]
        return

    app.state.search_chunk_count = len(chunks)

    # Build BM25 index
    try:
        index = BM25Index(chunks, k1=1.5, b=0.75)
    except Exception:
        app.state.search_status = "failed"
        app.state.search_errors = list(app.state.corpus_errors) + [{
            "code": "INDEX_BUILD_ERROR",
            "document_id": None,
            "field": "index",
            "message": "BM25 索引构建失败",
        }]
        return

    app.state.search_index = index
    app.state.search_chunks = chunks
    app.state.search_indexed_chunk_count = index.valid_chunk_count
    app.state.search_errors = list(app.state.corpus_errors)
    app.state.search_status = app.state.corpus_status

    # Build dense index if embedding model is configured
    if embedding_model_path:
        try:
            from campus_assistant.retrieval.embedding import EmbeddingService
            from campus_assistant.retrieval.dense import DenseIndex

            emb_service = EmbeddingService(embedding_model_path)
            texts = [c.get("text", "") for c in chunks]
            # Count chunks that exceed the model token limit before encoding.
            # Long chunks may only partially participate in vector computation;
            # stored original/chunk text is never truncated or overwritten.
            app.state.search_truncated_chunk_count = emb_service.count_truncated(texts)
            doc_embeddings = emb_service.encode_documents(texts)

            dense_index = DenseIndex(chunks, doc_embeddings)
            app.state.embedding_service = emb_service
            app.state.dense_index = dense_index
            app.state.available_modes = ["bm25", "dense", "hybrid"]
            app.state.embedding_error = None
        except Exception as e:
            # Dense/hybrid unavailable but BM25 and preview still work
            app.state.available_modes = ["bm25"]
            app.state.embedding_service = None
            app.state.dense_index = None
            app.state.search_truncated_chunk_count = None
            app.state.embedding_error = str(e) or f"向量模型不可用：{type(e).__name__}"


def _answer_provider_from_env() -> object | None:
    """Explicit enable + complete local config → DeepSeek provider.

    None (extractive-only) otherwise. Reads env only — no probe request.
    """
    from campus_assistant.qa.deepseek import provider_from_env

    return provider_from_env()


def _asr_from_env() -> object | None:
    """Explicit enable + local model dir → ASR adapter. Never downloads."""
    from campus_assistant.asr.adapter import asr_from_env

    return asr_from_env()


def _planner_from_env() -> object | None:
    """Explicit enable (CAMPUS_PLANNER=deepseek) + key → DeepSeek planner.

    None (Agent mode off) otherwise. Independent of CAMPUS_GENERATOR;
    key from local env only, never printed; no probe request.
    """
    from campus_assistant.agent.deepseek_planner import planner_from_env

    return planner_from_env()


app = create_app(
    answer_provider=_answer_provider_from_env(),
    asr_adapter=_asr_from_env(),
    planner=_planner_from_env(),
)
