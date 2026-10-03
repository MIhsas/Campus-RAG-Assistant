"""Question dataset contract models with strict validation.

Pydantic models for the evaluation question dataset. All fields use strict
types; unknown fields are rejected; booleans are not coerced from strings.
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator, model_validator

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class Evidence(BaseModel):
    """A single evidence unit pointing to a character span in a parsed block.

    ``fact_id`` (T027-R1, optional): sources sharing the same fact_id are
    ALTERNATIVE sources of one necessary fact (OR within the group);
    distinct fact_ids are different necessary facts (AND across groups).
    Omitted (old datasets) → every evidence unit is its own fact, i.e. the
    original per-evidence semantics.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    document_id: str
    document_sha256: str
    parser_version: str
    block_id: str
    char_start: StrictInt
    char_end: StrictInt
    quote: str
    fact_id: Optional[str] = None

    @field_validator("evidence_id", "document_id", "block_id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not isinstance(v, str) or not _ID_RE.match(v):
            raise ValueError("必须匹配 [A-Za-z0-9][A-Za-z0-9_-]{0,63}")
        return v

    @field_validator("fact_id")
    @classmethod
    def _validate_fact_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str) or not _ID_RE.match(v):
            raise ValueError("fact_id 必须匹配 [A-Za-z0-9][A-Za-z0-9_-]{0,63} 或为 null")
        return v

    @field_validator("document_sha256")
    @classmethod
    def _validate_sha256(cls, v: str) -> str:
        if not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v):
            raise ValueError("必须是 64 位十六进制字符串")
        return v.lower()

    @field_validator("parser_version")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("必须是非空字符串")
        return v

    @field_validator("char_start", "char_end")
    @classmethod
    def _validate_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("不能为负数")
        return v

    @field_validator("quote")
    @classmethod
    def _validate_quote(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("必须是字符串")
        return v

    @model_validator(mode="after")
    def _validate_range(self) -> "Evidence":
        if self.char_start >= self.char_end:
            raise ValueError("char_start 必须小于 char_end")
        return self


class Question(BaseModel):
    """A single evaluation question with optional evidence.

    T027 optional annotation fields (old datasets without them remain
    valid): question_type / group_id / conditions / rationale / missing.
    ``conditions`` carries the SAME applicability filters as the product
    search (campus/student_type/admission_year/as_of_date) — the evaluation
    pipeline applies the product filter rules with them.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str
    query: str
    answerable: StrictBool
    evidence: list[Evidence]
    question_type: Optional[str] = None
    group_id: Optional[str] = None
    conditions: Optional[dict] = None
    rationale: Optional[str] = None
    missing: Optional[str] = None
    # T027-R1：标注/题目修订留痕（修改理由；无修订则为 null）
    revision_note: Optional[str] = None

    @field_validator("question_id")
    @classmethod
    def _validate_qid(cls, v: str) -> str:
        if not isinstance(v, str) or not _ID_RE.match(v):
            raise ValueError("必须匹配 [A-Za-z0-9][A-Za-z0-9_-]{0,63}")
        return v

    @field_validator("query")
    @classmethod
    def _validate_query(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("必须是字符串")
        if len(v) < 1 or len(v) > 500:
            raise ValueError("长度必须在 1-500 之间")
        if not v.strip():
            raise ValueError("不能全为空白")
        return v

    @field_validator("question_type", "group_id", "rationale", "missing", "revision_note")
    @classmethod
    def _validate_optional_str(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str) or not v.strip():
            raise ValueError("必须是非空字符串或 null")
        return v

    @field_validator("conditions")
    @classmethod
    def _validate_conditions(cls, v: Optional[dict]) -> Optional[dict]:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("必须是对象或 null")
        allowed_keys = {"campus", "student_type", "admission_year", "as_of_date"}
        extra = set(v) - allowed_keys
        if extra:
            raise ValueError(f"conditions 含未知字段: {sorted(extra)}")
        campus = v.get("campus")
        student_type = v.get("student_type")
        for name, val in (("campus", campus), ("student_type", student_type)):
            if val is not None and (not isinstance(val, str) or not val.strip() or len(val) > 64):
                raise ValueError(f"conditions.{name} 必须是非空字符串（≤64）或 null")
        year = v.get("admission_year")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not (1900 <= year <= 2100)):
            raise ValueError("conditions.admission_year 必须是 1900—2100 整数或 null")
        as_of = v.get("as_of_date")
        if as_of is not None:
            if not isinstance(as_of, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):
                raise ValueError("conditions.as_of_date 必须是 YYYY-MM-DD 或 null")
        return {
            "campus": campus,
            "student_type": student_type,
            "admission_year": year,
            "as_of_date": as_of,
        }

    @model_validator(mode="after")
    def _validate_evidence_consistency(self) -> "Question":
        if self.answerable and len(self.evidence) == 0:
            raise ValueError("answerable=true 时 evidence 不能为空")
        if not self.answerable and len(self.evidence) > 0:
            raise ValueError("answerable=false 时 evidence 必须为空")
        # R3: Duplicate evidence_id within question
        seen_ids: set[str] = set()
        for ev in self.evidence:
            if ev.evidence_id in seen_ids:
                raise ValueError(f"题内重复 evidence_id: {ev.evidence_id}")
            seen_ids.add(ev.evidence_id)
        # R3: Duplicate source span (document_id, block_id, char_start, char_end)
        seen_spans: set[tuple] = set()
        for ev in self.evidence:
            span = (ev.document_id, ev.block_id, ev.char_start, ev.char_end)
            if span in seen_spans:
                raise ValueError(f"题内重复来源区间: {ev.document_id}/{ev.block_id}[{ev.char_start},{ev.char_end})")
            seen_spans.add(span)
        return self


class QuestionDataset(BaseModel):
    """Top-level question dataset container.

    ``authoring_note`` (T027, optional) must honestly describe who wrote
    the questions/annotations — synthetic model-assisted sets say so and
    are never presented as teacher/student independent annotation.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    dataset_id: str
    dataset_version: str
    split: str
    is_synthetic: StrictBool
    questions: list[Question]
    authoring_note: Optional[str] = None
    # T027-R1：v2 明确指标语义与分母（缺省=旧口径 unit_evidence_v1.0）
    metric_semantics: Optional[str] = None

    @field_validator("schema_version")
    @classmethod
    def _validate_schema(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"不支持的 schema_version: {v}")
        return v

    @field_validator("dataset_id")
    @classmethod
    def _validate_did(cls, v: str) -> str:
        if not isinstance(v, str) or not _ID_RE.match(v):
            raise ValueError("必须匹配 [A-Za-z0-9][A-Za-z0-9_-]{0,63}")
        return v

    @field_validator("dataset_version")
    @classmethod
    def _validate_nonempty_str(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("必须是非空字符串")
        return v

    @field_validator("split")
    @classmethod
    def _validate_split(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("必须是非空字符串")
        if v != "dev":
            raise ValueError(f"当前仅支持 split='dev'，收到: {v!r}")
        return v

    @field_validator("questions")
    @classmethod
    def _validate_nonempty(cls, v: list) -> list:
        if len(v) == 0:
            raise ValueError("questions 不能为空")
        return v

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> "QuestionDataset":
        seen: set[str] = set()
        for q in self.questions:
            if q.question_id in seen:
                raise ValueError(f"重复的 question_id: {q.question_id}")
            seen.add(q.question_id)
        return self
