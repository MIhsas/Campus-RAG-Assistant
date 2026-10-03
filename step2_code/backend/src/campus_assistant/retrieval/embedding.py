"""Embedding service for document and query encoding.

Loads a SentenceTransformer model once from an actual local directory
(explicit local_files_only=True — never rely on global offline settings),
provides batch document encoding and single query encoding with CPU float32
inference. Exposes a concise model identity without local filesystem paths.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_MAX_SEQ_LENGTH = 512
_REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")


def read_local_revision(model_dir: Path) -> str:
    """Read the model revision (commit hash) from existing download metadata.

    huggingface_hub snapshot downloads keep
    `.cache/huggingface/download/<file>.metadata` with the commit hash on the
    first line. Returns 'unknown' when metadata is missing, inconsistent or
    unverifiable — never guess a revision.
    """
    meta_dir = model_dir / ".cache" / "huggingface" / "download"
    commits: set[str] = set()
    try:
        for meta in sorted(meta_dir.glob("*.metadata")):
            first_line = meta.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
            if first_line and _REVISION_PATTERN.fullmatch(first_line[0]):
                commits.add(first_line[0])
    except OSError:
        return "unknown"
    if len(commits) == 1:
        return commits.pop()
    return "unknown"


class EmbeddingService:
    """Manages embedding model lifecycle and encoding.

    Only accepts an existing local model directory; hub IDs and remote
    fetches are rejected. Load failures raise ValueError with a concise
    Chinese reason (no absolute paths).
    """

    def __init__(self, model_path: str):
        from sentence_transformers import SentenceTransformer

        model_dir = Path(model_path)
        if not model_dir.is_dir():
            raise ValueError(f"模型目录不存在：{model_dir.name}")

        try:
            self._model = SentenceTransformer(
                str(model_dir), device="cpu", local_files_only=True
            )
        except Exception as e:
            raise ValueError(f"本地模型加载失败：{type(e).__name__}") from e

        self._model_name = model_dir.name
        self._revision = read_local_revision(model_dir)
        get_dim = getattr(self._model, "get_embedding_dimension", None) or getattr(
            self._model, "get_sentence_embedding_dimension"
        )
        self._dimension = get_dim()
        self._max_seq_length = (
            getattr(self._model, "max_seq_length", None) or DEFAULT_MAX_SEQ_LENGTH
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        """Concise model identity (directory name), not a local path."""
        return self._model_name

    @property
    def model_revision(self) -> str:
        """Verified revision from download metadata, or 'unknown'."""
        return self._revision

    @property
    def max_seq_length(self) -> int:
        return self._max_seq_length

    def _tokenizer(self) -> Any:
        tok = getattr(self._model, "tokenizer", None)
        if tok is not None:
            return tok
        return self._model._first_module().tokenizer  # type: ignore[union-attr]

    def count_truncated(self, texts: list[str]) -> int:
        """Count texts whose tokenized length exceeds the model token limit.

        Long chunks are only partially involved in vector computation at
        encode time; stored original/chunk text is never truncated here.
        """
        tokenizer = self._tokenizer()
        count = 0
        for text in texts:
            ids = tokenizer(text, add_special_tokens=True)["input_ids"]
            if len(ids) > self._max_seq_length:
                count += 1
        return count

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        """Encode documents (no query prefix). Returns normalized float32 array.

        Uses the model's token limit (long inputs are truncated inside the
        encoder only; count_truncated reports how many).
        """
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return np.array(embeddings, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """Encode query with retrieval prefix. Returns normalized float32 vector."""
        prefixed = f"为这个句子生成表示以用于检索相关文章：{query}"
        embedding = self._model.encode(
            [prefixed],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.array(embedding[0], dtype=np.float32)
