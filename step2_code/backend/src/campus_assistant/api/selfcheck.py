"""Self-check API endpoints (T019).

GET  /api/v1/self-check/rule — rule info (items, three-state options, citations)
POST /api/v1/self-check      — deterministic evaluation (filters like /search)

Rule config is explicitly injected at app creation; ordinary services
return 503. User answers are processed only within the request — never
persisted to reports, logs or storage. Citation links are server-bound;
client-provided citations are not accepted.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from campus_assistant.api.search import SearchFilters


class SelfCheckRequest(BaseModel):
    model_config = {"extra": "forbid"}

    filters: SearchFilters | None = None
    answers: dict[str, Any] = Field(default_factory=dict)

    @field_validator("answers", mode="before")
    @classmethod
    def validate_answers(cls, v: Any) -> dict:
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("answers 必须是对象")
        for key, val in v.items():
            if val is not None and val not in ("yes", "no", "unknown"):
                raise ValueError(f"answers.{key} 必须是 yes/no/unknown 或 null")
        return v


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


def create_selfcheck_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/self-check", tags=["self-check"])

    def _rule(request: Request):
        return getattr(request.app.state, "self_check_rule", None)

    @router.get("/rule")
    async def rule_info(request: Request):
        rule = _rule(request)
        if rule is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "SELF_CHECK_NOT_CONFIGURED",
                    "message": "自查规则未配置（合成规则仅由演示/测试显式注入）",
                    "request_id": request.state.request_id,
                },
            )
        return {
            "configured": True,
            "rule_id": rule["rule_id"],
            "rule_version": rule["rule_version"],
            "title": rule.get("title"),
            "summary": rule.get("summary"),
            "is_synthetic": bool(rule.get("is_synthetic", True)),
            "answer_options": rule.get("answer_options", []),
            "not_collected": rule.get("not_collected", []),
            "items": [
                {
                    "item_id": it["item_id"],
                    "title": it["title"],
                    "question": it["question"],
                    "answer_field": it["answer_field"],
                    "explanation": it["explanation"],
                    "citation": rule["citations"][it["citation_index"]],
                }
                for it in rule.get("items", [])
            ],
            "disclaimer": "个人自查演示：不代表学校审核结果；不收集姓名、学号或违纪详情。",
            "request_id": request.state.request_id,
        }

    @router.post(
        "",
        responses={503: {"model": ErrorResponse}},
    )
    async def evaluate(body: SelfCheckRequest, request: Request):
        rule = _rule(request)
        if rule is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "SELF_CHECK_NOT_CONFIGURED",
                    "message": "自查规则未配置（合成规则仅由演示/测试显式注入）",
                    "request_id": request.state.request_id,
                },
            )
        from campus_assistant.selfcheck.service import evaluate_self_check

        result = evaluate_self_check(
            rule,
            body.answers,
            body.filters.normalized() if body.filters else None,
            request.app.state.corpus_data or [],
        )
        result["request_id"] = request.state.request_id
        return result

    return router
