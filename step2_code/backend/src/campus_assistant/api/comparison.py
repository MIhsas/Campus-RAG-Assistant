"""Policy version comparison API (T017).

GET  /api/v1/comparison/groups — policy groups with versions
POST /api/v1/comparison        — deterministic diff of two versions

Works on the currently parsed corpus only (comparison demo injects the
comparison corpus explicitly at app creation). Text differences only — no
applicability or validity judgment.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    model_config = {"extra": "forbid"}

    left_document_id: str = Field(min_length=1, max_length=64)
    right_document_id: str = Field(min_length=1, max_length=64)


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


def create_comparison_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/comparison", tags=["comparison"])

    def _documents(request: Request):
        return request.app.state.corpus_data or []

    @router.get("/groups")
    async def groups(request: Request):
        documents = _documents(request)
        if not documents:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "CORPUS_NOT_CONFIGURED",
                    "message": "语料未配置：版本对比仅显示服务器当前已加载语料",
                    "request_id": request.state.request_id,
                },
            )
        from campus_assistant.comparison.service import group_versions

        return {
            "groups": group_versions(documents),
            "disclaimer": "文字差异对比：不判断版本适用性；日期较新不等于现行有效。",
            "request_id": request.state.request_id,
        }

    @router.post(
        "",
        responses={503: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    )
    async def compare(body: CompareRequest, request: Request):
        documents = _documents(request)
        if not documents:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "CORPUS_NOT_CONFIGURED",
                    "message": "语料未配置：版本对比仅显示服务器当前已加载语料",
                    "request_id": request.state.request_id,
                },
            )
        by_id = {d.get("document_id"): d for d in documents}
        left = by_id.get(body.left_document_id)
        right = by_id.get(body.right_document_id)
        if left is None or right is None:
            missing = body.left_document_id if left is None else body.right_document_id
            return JSONResponse(
                status_code=404,
                content={
                    "code": "DOCUMENT_NOT_FOUND",
                    "message": f"未找到文档：{missing}",
                    "request_id": request.state.request_id,
                },
            )

        from campus_assistant.comparison.service import compare_documents

        try:
            result = compare_documents(left, right)
        except ValueError as e:
            code = str(e)
            message = {
                "LEFT_RIGHT_SAME": "左右不能选择同一文档",
                "CROSS_POLICY_GROUP": "只能比较同一政策分组下的版本",
            }.get(code, "无法比较所选文档")
            return JSONResponse(
                status_code=400,
                content={"code": code, "message": message, "request_id": request.state.request_id},
            )
        result["request_id"] = request.state.request_id
        return result

    return router
