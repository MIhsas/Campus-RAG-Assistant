"""Procedure guide API endpoints (T016).

GET  /api/v1/procedures                      — list templates
POST /api/v1/procedures/{id}/draft           — citation-checked draft (filters like /search)
POST /api/v1/procedures/{id}/verify          — compare a saved basis snapshot with current

Templates are explicitly injected at app creation (synthetic ones only in
tests/demos). No model calls; sources are verified against the parsed corpus.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from campus_assistant.api.search import SearchFilters


class DraftRequest(BaseModel):
    model_config = {"extra": "forbid"}

    filters: SearchFilters | None = None


class SavedCitation(BaseModel):
    model_config = {"extra": "allow"}

    required: bool = True
    document_id: str
    block_id: str
    char_start: int
    char_end: int
    quote: str
    document_sha256: str


class SavedStep(BaseModel):
    model_config = {"extra": "allow"}

    step_id: str | None = None
    title: str | None = None
    citations: list[SavedCitation] = Field(default_factory=list)


class VerifyRequest(BaseModel):
    model_config = {"extra": "forbid"}

    template_version: str
    filters: SearchFilters | None = None
    steps: list[SavedStep] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


def create_procedures_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/procedures", tags=["procedures"])

    def _procedures(request: Request):
        return getattr(request.app.state, "procedures", None)

    @router.get("")
    async def list_procedures(request: Request):
        procedures = _procedures(request)
        if procedures is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "PROCEDURES_NOT_CONFIGURED",
                    "message": "办事模板未配置（合成模板仅由测试/演示显式启用）",
                    "request_id": request.state.request_id,
                },
            )

        def _entry(p: dict) -> dict:
            # T033: entry metadata for the ask-page related entry.
            # source_document_ids is derived from the template's own citations
            # (never model-guessed); identity fields only — no paths or text.
            src_ids: list[str] = []
            for s in p.get("steps", []):
                for c in s.get("citations", []):
                    did = c.get("document_id")
                    if did and did not in src_ids:
                        src_ids.append(did)
            return {
                "procedure_id": p["procedure_id"],
                "title": p.get("title"),
                "summary": p.get("summary"),
                "template_version": p["template_version"],
                "is_synthetic": bool(p.get("is_synthetic", False)),
                "step_count": len(p.get("steps", [])),
                "related_keywords": list(p.get("related_keywords") or []),
                "source_document_ids": src_ids,
            }

        return {
            "configured": True,
            "is_synthetic": bool(procedures.get("is_synthetic", False)),
            "procedures": [_entry(p) for p in procedures["procedures"]],
            "request_id": request.state.request_id,
        }

    @router.post(
        "/{procedure_id}/draft",
        responses={503: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def draft(procedure_id: str, body: DraftRequest, request: Request):
        procedures = _procedures(request)
        if procedures is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "PROCEDURES_NOT_CONFIGURED",
                    "message": "办事模板未配置（合成模板仅由测试/演示显式启用）",
                    "request_id": request.state.request_id,
                },
            )
        from campus_assistant.procedures.service import build_draft

        try:
            result = build_draft(
                procedures,
                procedure_id,
                body.filters.normalized() if body.filters else None,
                request.app.state.corpus_data or [],
            )
        except KeyError:
            return JSONResponse(
                status_code=404,
                content={
                    "code": "PROCEDURE_NOT_FOUND",
                    "message": f"未找到事项：{procedure_id}",
                    "request_id": request.state.request_id,
                },
            )
        return result

    @router.post(
        "/{procedure_id}/verify",
        responses={503: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    async def verify(procedure_id: str, body: VerifyRequest, request: Request):
        procedures = _procedures(request)
        if procedures is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "PROCEDURES_NOT_CONFIGURED",
                    "message": "办事模板未配置（合成模板仅由测试/演示显式启用）",
                    "request_id": request.state.request_id,
                },
            )
        from campus_assistant.procedures.service import verify_snapshot

        snapshot = {
            "template_version": body.template_version,
            "filters": body.filters.normalized() if body.filters else None,
            "steps": [s.model_dump() for s in body.steps],
        }
        result = verify_snapshot(procedures, procedure_id, snapshot, request.app.state.corpus_data or [])
        if result["status"] == "unavailable" and result.get("current_template_version") is None:
            return JSONResponse(
                status_code=404,
                content={
                    "code": "PROCEDURE_NOT_FOUND",
                    "message": f"未找到事项：{procedure_id}",
                    "request_id": request.state.request_id,
                },
            )
        return result

    return router
