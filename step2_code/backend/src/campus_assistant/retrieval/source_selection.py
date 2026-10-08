"""Optional single-document source selection (T031).

User-explicit choice of ONE successfully-parsed document to restrict
retrieval to. Intersects with (never replaces) the T011 applicability
filters: admission happens before Top-K truncation. The selected source
comes from the user only — never inferred from query wording, gold labels
or retrieval rankings. Not selecting = previous behaviour (all documents).

Catalog entries expose identity/metadata fields only: no disk paths, no
full text, no credentials. Unknown metadata stays null — we do not guess
document numbers or dates.
"""

from __future__ import annotations

from typing import Any

SOURCE_SELECTION_VERSION = "1.0"

# Whitelisted catalog fields — anything else in document metadata stays out.
CATALOG_FIELDS = (
    "title",
    "version_label",
    "policy_group_id",
    "published_at",
    "effective_from",
    "effective_to",
)


class SourceSelectionError(ValueError):
    """Raised for invalid document_id input (empty/whitespace/unknown)."""

    def __init__(self, message: str, code: str = "SOURCE_DOCUMENT_INVALID"):
        super().__init__(message)
        self.code = code


def normalize_document_id(value: Any) -> str | None:
    """Validate raw request input for document_id.

    None = no selection. Everything else must be a non-empty string.
    Raises SourceSelectionError on empty/whitespace/wrong-type/over-long.
    Unknown IDs are checked separately against the parsed catalog.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise SourceSelectionError(
            "document_id 必须是字符串或 null", "SOURCE_DOCUMENT_INVALID"
        )
    v = value.strip()
    if not v:
        raise SourceSelectionError(
            "document_id 不能为空字符串；不选择请用 null 或不传",
            "SOURCE_DOCUMENT_INVALID",
        )
    if len(v) > 128:
        raise SourceSelectionError(
            "document_id 长度不能超过 128", "SOURCE_DOCUMENT_INVALID"
        )
    return v


def build_document_catalog(documents: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Selection catalog for successfully parsed documents.

    Stable ordering by document_id. Only identity/metadata fields are
    exposed; missing metadata values stay None (never guessed).
    """
    entries: list[dict[str, Any]] = []
    for doc in documents or []:
        meta = doc.get("metadata") or {}
        doc_id = doc.get("document_id") or meta.get("document_id")
        if not doc_id:
            continue
        entry: dict[str, Any] = {"document_id": doc_id}
        for field in CATALOG_FIELDS:
            value = meta.get(field)
            entry[field] = value if value is not None else None
        entry["is_synthetic"] = bool(meta.get("is_synthetic", False))
        entries.append(entry)
    entries.sort(key=lambda e: e["document_id"])
    return entries


def resolve_document_id(
    document_id: str | None, documents: list[dict[str, Any]] | None
) -> str | None:
    """Confirm a normalized document_id exists in the parsed catalog.

    Raises SourceSelectionError for unknown IDs — callers map this to a
    clear 422; the request must NOT silently degrade to "all documents".
    """
    if document_id is None:
        return None
    known = {
        (d.get("document_id") or (d.get("metadata") or {}).get("document_id"))
        for d in documents or []
    }
    if document_id not in known:
        raise SourceSelectionError(
            f"document_id 不在当前成功解析的文档目录中: {document_id}",
            "SOURCE_DOCUMENT_NOT_FOUND",
        )
    return document_id


def build_source_selection(
    *,
    document_id: str | None,
    documents: list[dict[str, Any]] | None,
    allowed_document_ids: set[str] | None,
) -> dict[str, Any]:
    """Summary of the source-selection condition and its intersection.

    Counts keep the two stages distinct (never interchangeable):
    - allowed_before_selection: documents admitted by the four applicability
      conditions alone (document_total when no conditions are active).
    - allowed_after_selection: documents admitted after intersecting with the
      selected file (0 or 1 when selected; same as before when not).
    """
    docs = documents or []
    total = len(docs)
    before = total if allowed_document_ids is None else len(allowed_document_ids)

    if document_id is None:
        return {
            "selected": False,
            "document_id": None,
            "title": None,
            "version_label": None,
            "policy_group_id": None,
            "is_admitted": None,
            "allowed_before_selection": before,
            "allowed_after_selection": before,
            "notes": ["未选择指定文件；检索范围为全部通过适用条件的资料"],
        }

    meta: dict[str, Any] = {}
    for doc in docs:
        if doc.get("document_id") == document_id:
            meta = doc.get("metadata") or {}
            break

    admitted = (
        True if allowed_document_ids is None else document_id in allowed_document_ids
    )
    after = 1 if admitted else 0
    notes = [
        "仅在所选文件内检索；不代表该版本现行有效",
        "所选来源来自用户明确选择，未从查询或答案自动推断版本",
    ]
    if not admitted:
        notes.insert(
            0,
            "所选文件未通过现有适用条件筛选，最终可准入 0 份；未取消筛选、未回退其他文件",
        )

    return {
        "selected": True,
        "document_id": document_id,
        "title": meta.get("title"),
        "version_label": meta.get("version_label"),
        "policy_group_id": meta.get("policy_group_id"),
        "is_admitted": admitted,
        "allowed_before_selection": before,
        "allowed_after_selection": after,
        "notes": notes,
    }


def intersect_allowed(
    allowed_document_ids: set[str] | None, document_id: str | None
) -> set[str] | None:
    """Intersect the condition-admitted set with the selected file.

    None (unrestricted) becomes {document_id}; an empty intersection stays
    empty so retrievers return no hits instead of falling back to other
    documents. Applied BEFORE Top-K truncation by the shared pipeline.
    """
    if document_id is None:
        return allowed_document_ids
    if allowed_document_ids is None:
        return {document_id}
    return allowed_document_ids & {document_id}
