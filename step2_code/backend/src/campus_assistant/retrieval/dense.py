"""Dense retrieval using normalized embeddings and dot product.

No FAISS dependency — uses NumPy for small-scale exact search.
Stores independent copies of chunks; modifying results doesn't affect the index.
"""

from __future__ import annotations

import copy
from typing import Any
from urllib.parse import quote

import numpy as np


class DenseIndex:
    """Dense retrieval index over T006 chunks using embedding vectors."""

    def __init__(self, chunks: list[dict[str, Any]], embeddings: np.ndarray):
        """
        Args:
            chunks: List of chunk dicts (deep-copied).
            embeddings: Normalized float32 array of shape (N, dim).
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"chunks ({len(chunks)}) 和 embeddings ({len(embeddings)}) 数量不匹配")

        self._chunks = [copy.deepcopy(c) for c in chunks]
        self._embeddings = np.array(embeddings, dtype=np.float32)
        self._count = len(chunks)

    @property
    def valid_chunk_count(self) -> int:
        return self._count

    def search(
        self,
        query_embedding: np.ndarray,
        *,
        top_k: int = 5,
        allowed_document_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search with a normalized query embedding.

        Returns hits sorted by score desc, chunk_id asc for ties.
        Only returns hits with score > 0.

        allowed_document_ids: document admission set applied before
        truncation (ranks restart at 1 within the admitted set).
        None = unrestricted; empty set = no candidates.
        """
        if self._count == 0:
            return []

        # Dot product (embeddings are already normalized)
        scores = self._embeddings @ query_embedding

        # Get indices sorted by score desc, then by chunk_id asc for ties
        chunk_ids = [c.get("chunk_id", "") for c in self._chunks]
        indexed = list(enumerate(scores))
        # Sort: score desc, chunk_id asc
        indexed.sort(key=lambda x: (-x[1], chunk_ids[x[0]]))

        # Admission before truncation: never drop high-ranked excluded docs
        # out of an already-truncated Top-K.
        if allowed_document_ids is None:
            candidates = indexed[:top_k]
        else:
            candidates = []
            for item in indexed:
                if self._chunks[item[0]].get("document_id") in allowed_document_ids:
                    candidates.append(item)
                    if len(candidates) >= top_k:
                        break

        hits = []
        for rank, (idx, score) in enumerate(candidates, start=1):
            if score <= 0:
                continue

            chunk = self._chunks[idx]
            doc_id = chunk.get("document_id", "")
            block_id = chunk.get("block_id", "")
            preview_url = f"/preview#{quote(doc_id, safe='')}/{quote(block_id, safe='')}"

            hits.append({
                "rank": rank,
                "score": float(score),
                "chunk": copy.deepcopy(chunk),
                "preview_url": preview_url,
                "matched_terms": [],  # Dense doesn't have term-level matches
            })

        return hits
