"""In-memory BM25 index over T006 chunks.

Fixed positive IDF variant per T007 contract.
No persistence, no external dependencies, pure Python standard library.
"""

from __future__ import annotations

import copy
import math
from typing import Any

from campus_assistant.retrieval.tokenize import tokenize


def _validate_params(k1: float, b: float, top_k: int) -> None:
    """Validate BM25 parameters. Raises ValueError."""
    if isinstance(k1, bool) or not isinstance(k1, (int, float)):
        raise ValueError("k1 必须是有限正实数")
    if math.isnan(k1) or math.isinf(k1) or k1 <= 0:
        raise ValueError("k1 必须是有限正实数")
    if isinstance(b, bool) or not isinstance(b, (int, float)):
        raise ValueError("b 必须是 0—1 之间的有限实数")
    if math.isnan(b) or math.isinf(b) or b < 0 or b > 1:
        raise ValueError("b 必须是 0—1 之间的有限实数")
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k 必须是 1—100 之间的整数")
    if top_k < 1 or top_k > 100:
        raise ValueError("top_k 必须是 1—100 之间的整数")


class BM25Index:
    """BM25 index over a list of T006 chunk dicts.

    Indexes only chunk['text']. Stores deep copies of input chunks.
    """

    def __init__(self, chunks: list[dict[str, Any]], *, k1: float = 1.5, b: float = 0.75):
        _validate_params(k1, b, 1)  # top_k not relevant here, use 1 as placeholder

        self._k1 = k1
        self._b = b

        # Validate and deep-copy chunks
        self._chunks: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for i, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                raise ValueError(f"chunk[{i}] 必须是字典")
            chunk_id = chunk.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError(f"chunk[{i}].chunk_id 必须是非空字符串")
            if chunk_id in seen_ids:
                raise ValueError(f"重复的 chunk_id: {chunk_id}")
            seen_ids.add(chunk_id)
            if "text" not in chunk:
                raise ValueError(f"chunk[{i}] 缺少 text 字段")
            self._chunks.append(copy.deepcopy(chunk))

        # Build index: for each chunk, compute token frequencies
        # Only chunks with at least one token contribute to N, df, avgdl
        self._tokenized: list[list[str]] = []
        self._tf: list[dict[str, int]] = []
        self._dl: list[int] = []  # token count per chunk (0 if no tokens)
        self._valid_indices: list[int] = []  # indices with at least one token

        for i, chunk in enumerate(self._chunks):
            tokens = tokenize(chunk.get("text", ""))
            freq: dict[str, int] = {}
            for t in tokens:
                freq[t] = freq.get(t, 0) + 1
            self._tokenized.append(tokens)
            self._tf.append(freq)
            self._dl.append(len(tokens))
            if len(tokens) > 0:
                self._valid_indices.append(i)

        self._N = len(self._valid_indices)  # chunks with >=1 token
        self._avgdl = (
            sum(self._dl[i] for i in self._valid_indices) / self._N
            if self._N > 0
            else 0.0
        )

        # Precompute df(t) for all terms in valid chunks
        self._df: dict[str, int] = {}
        for i in self._valid_indices:
            for t in self._tf[i]:
                self._df[t] = self._df.get(t, 0) + 1

    @property
    def valid_chunk_count(self) -> int:
        """Number of chunks with at least one token (actual N used in BM25)."""
        return self._N

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        allowed_document_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search the index with a query string.

        Args:
            query: Query text.
            top_k: Maximum number of results (1-100).
            allowed_document_ids: Document admission set applied before
                truncation. None = unrestricted; empty set = no candidates.
                IDF/df stay computed over the full corpus.

        Returns:
            Ordered list of hit dicts.
        """
        if isinstance(top_k, bool) or not isinstance(top_k, int):
            raise ValueError("top_k 必须是 1—100 之间的整数")
        if top_k < 1 or top_k > 100:
            raise ValueError("top_k 必须是 1—100 之间的整数")

        if not isinstance(query, str):
            raise ValueError("query 必须是字符串")

        # Tokenize query, deduplicate preserving first occurrence order
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        seen: set[str] = set()
        unique_terms: list[str] = []
        for t in query_tokens:
            if t not in seen:
                seen.add(t)
                unique_terms.append(t)

        if self._N == 0:
            return []

        # Score each valid chunk
        results: list[tuple[float, str, int]] = []  # (score, chunk_id, chunk_index)

        for i in self._valid_indices:
            if allowed_document_ids is not None:
                if self._chunks[i].get("document_id") not in allowed_document_ids:
                    continue
            score = 0.0
            for t in unique_terms:
                tf = self._tf[i].get(t, 0)
                if tf == 0:
                    continue
                df = self._df.get(t, 0)
                idf = math.log(1 + (self._N - df + 0.5) / (df + 0.5))
                dl = self._dl[i]
                contrib = idf * (tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * dl / self._avgdl))
                score += contrib
            if score > 0:
                results.append((score, self._chunks[i]["chunk_id"], i))

        # Sort: score desc, chunk_id asc for ties
        results.sort(key=lambda x: (-x[0], x[1]))
        results = results[:top_k]

        # Build hit objects
        hits: list[dict[str, Any]] = []
        for rank, (score, chunk_id, idx) in enumerate(results, start=1):
            chunk = self._chunks[idx]
            doc_id = chunk.get("document_id", "")
            block_id = chunk.get("block_id", "")
            from urllib.parse import quote
            preview_url = (
                "/preview#"
                + quote(doc_id, safe="")
                + "/"
                + quote(block_id, safe="")
            )

            # Build matched_terms
            matched_terms: list[dict[str, Any]] = []
            for t in unique_terms:
                tf = self._tf[idx].get(t, 0)
                if tf == 0:
                    continue
                df = self._df.get(t, 0)
                idf = math.log(1 + (self._N - df + 0.5) / (df + 0.5))
                dl = self._dl[idx]
                contrib = idf * (tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * dl / self._avgdl))
                matched_terms.append({
                    "term": t,
                    "tf": tf,
                    "df": df,
                    "idf": idf,
                    "contribution": contrib,
                })

            hits.append({
                "rank": rank,
                "score": score,
                "chunk": copy.deepcopy(chunk),
                "preview_url": preview_url,
                "matched_terms": matched_terms,
            })

        return hits
