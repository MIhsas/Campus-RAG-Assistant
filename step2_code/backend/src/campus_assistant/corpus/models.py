"""Pydantic models for corpus manifest validation.

schema_version: "1.0"
Each document must pass structural validation before file-level checks.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Scope(BaseModel):
    """Applicability scope for a policy document.

    All three fields are REQUIRED. Unknown values use empty arrays,
    which CANNOT be interpreted as "applies to everyone".
    """

    model_config = ConfigDict(extra="forbid")

    campus: list[str]
    student_type: list[str]
    admission_years: list[int]

    @field_validator("campus", "student_type", mode="before")
    @classmethod
    def validate_string_list(cls, v: object) -> list[str]:
        if not isinstance(v, list):
            raise ValueError("必须是数组")
        result: list[str] = []
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"第 {i + 1} 项必须是字符串")
            if not item.strip():
                raise ValueError(f"第 {i + 1} 项去除首尾空白后不能为空")
            result.append(item.strip())
        return list(dict.fromkeys(result))

    @field_validator("admission_years", mode="before")
    @classmethod
    def validate_int_list(cls, v: object) -> list[int]:
        if not isinstance(v, list):
            raise ValueError("必须是数组")
        result: list[int] = []
        for i, item in enumerate(v):
            if not isinstance(item, int) or isinstance(item, bool):
                raise ValueError(f"第 {i + 1} 项必须是整数")
            if item < 1900 or item > 2100:
                raise ValueError(f"第 {i + 1} 项 {item} 超出 1900—2100 范围")
            result.append(item)
        return list(dict.fromkeys(result))


class Document(BaseModel):
    """Single document entry in a corpus manifest."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    policy_group_id: str
    title: str
    source_url: str
    source_site: str
    local_path: str
    sha256: str
    version_label: str
    published_at: Optional[str]
    effective_from: Optional[str]
    effective_to: Optional[str]
    scope: Scope
    is_synthetic: bool = Field(strict=True)

    @field_validator("document_id", "policy_group_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not isinstance(v, str) or not _ID_PATTERN.match(v):
            raise ValueError("必须匹配 [A-Za-z0-9][A-Za-z0-9_-]{0,63}")
        return v

    @field_validator("title", "source_site", "version_label")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("去除首尾空白后不能为空")
        return v

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not isinstance(v, str) or not v.startswith(("http://", "https://")):
            raise ValueError("必须是 http 或 https 绝对 URL")
        parsed = urlparse(v)
        if not parsed.hostname:
            raise ValueError("URL 必须包含主机名")
        if parsed.username or parsed.password:
            raise ValueError("URL 不得包含用户名/密码")
        return v

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("必须是字符串")
        v = v.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", v):
            raise ValueError("必须是 64 位十六进制字符串")
        return v

    @field_validator("published_at", "effective_from", "effective_to")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("必须是 YYYY-MM-DD 格式或 null")
        # Strict ASCII YYYY-MM-DD shape check
        if not _DATE_PATTERN.match(v):
            raise ValueError("必须是 YYYY-MM-DD 格式")
        # Real calendar date validation
        try:
            date.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError(f"不是有效日历日期: {v}")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "Document":
        if self.effective_from is not None and self.effective_to is not None:
            # Both are already validated as YYYY-MM-DD, safe to compare as strings
            if self.effective_to < self.effective_from:
                raise ValueError("effective_to 不得早于 effective_from")
        return self


class Manifest(BaseModel):
    """Top-level corpus manifest."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    documents: list[Document]

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"不支持的 schema_version: {v}，当前仅支持 1.0")
        return v

    @field_validator("documents")
    @classmethod
    def validate_documents_not_empty(cls, v: list[Document]) -> list[Document]:
        if len(v) == 0:
            raise ValueError("documents 至少需要一项")
        return v
