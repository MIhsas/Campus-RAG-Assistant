"""Corpus preview API endpoints.

GET /api/v1/corpus/status      — corpus loading status (always 200)
GET /api/v1/corpus/documents   — document list (503 if unconfigured)
GET /api/v1/corpus/documents/{document_id} — document detail (503/404/200)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class CorpusStatusResponse(BaseModel):
    status: str
    document_count: int
    parsed_count: int
    errors: list[dict[str, Any]]
    request_id: str


class DocumentListItem(BaseModel):
    document_id: str
    title: str
    source_site: str
    source_url: str
    version_label: str
    is_synthetic: bool
    block_count: int
    warnings: list[str]
    format: str


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    request_id: str


class DocumentDetailResponse(BaseModel):
    document: dict[str, Any]
    request_id: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


def create_corpus_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/corpus", tags=["corpus"])

    @router.get(
        "/status",
        status_code=200,
        response_model=CorpusStatusResponse,
    )
    async def corpus_status(request: Request) -> dict:
        return {
            "status": request.app.state.corpus_status,
            "document_count": request.app.state.document_count,
            "parsed_count": request.app.state.parsed_count,
            "errors": request.app.state.corpus_errors,
            "request_id": request.state.request_id,
        }

    @router.get(
        "/documents",
        response_model=DocumentListResponse,
        responses={
            503: {"model": ErrorResponse, "description": "语料未配置"},
        },
    )
    async def document_list(request: Request) -> dict:
        if request.app.state.corpus_status == "unconfigured":
            return JSONResponse(
                status_code=503,
                content={
                    "code": "CORPUS_NOT_CONFIGURED",
                    "message": "语料未配置",
                    "request_id": request.state.request_id,
                },
            )
        items = []
        for doc in (request.app.state.corpus_data or []):
            meta = doc.get("metadata", {})
            ext = meta.get("local_path", "")
            fmt = ext.rsplit(".", 1)[-1].upper() if "." in ext else ""
            items.append({
                "document_id": doc["document_id"],
                "title": meta.get("title", ""),
                "source_site": meta.get("source_site", ""),
                "source_url": meta.get("source_url", ""),
                "version_label": meta.get("version_label", ""),
                "is_synthetic": meta.get("is_synthetic", False),
                "block_count": len(doc.get("blocks", [])),
                "warnings": doc.get("warnings", []),
                "format": fmt,
            })
        return {
            "items": items,
            "request_id": request.state.request_id,
        }

    @router.get(
        "/documents/{document_id}",
        response_model=DocumentDetailResponse,
        responses={
            503: {"model": ErrorResponse, "description": "语料未配置"},
            404: {"model": ErrorResponse, "description": "文档不存在"},
        },
    )
    async def document_detail(request: Request, document_id: str) -> dict:
        if request.app.state.corpus_status == "unconfigured":
            return JSONResponse(
                status_code=503,
                content={
                    "code": "CORPUS_NOT_CONFIGURED",
                    "message": "语料未配置",
                    "request_id": request.state.request_id,
                },
            )
        for doc in (request.app.state.corpus_data or []):
            if doc["document_id"] == document_id:
                return {
                    "document": doc,
                    "request_id": request.state.request_id,
                }
        return JSONResponse(
            status_code=404,
            content={
                "code": "DOCUMENT_NOT_FOUND",
                "message": f"文档不存在: {document_id}",
                "request_id": request.state.request_id,
            },
        )

    return router
