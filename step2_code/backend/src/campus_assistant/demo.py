"""Demo application entry point.

Loads the example parse-corpus for preview. Usage:
    uvicorn campus_assistant.demo:app --host 127.0.0.1 --port 8001

To enable dense/hybrid search, set CAMPUS_EMBEDDING_MODEL_DIR environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

from campus_assistant.main import create_app

_EXAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "examples" / "parse-corpus"
_MANIFEST = _EXAMPLE_DIR / "manifest.json"
_MODEL_DIR = os.environ.get("CAMPUS_EMBEDDING_MODEL_DIR", "")
# 合成办事模板仅在演示入口显式启用（T016），不进入默认产品运行。
_PROCEDURES = Path(__file__).resolve().parent.parent.parent / "examples" / "procedures" / "procedures.json"


def _answer_provider_from_env() -> object | None:
    from campus_assistant.qa.deepseek import provider_from_env

    return provider_from_env()


app = create_app(
    manifest_path=_MANIFEST,
    corpus_root=_EXAMPLE_DIR,
    embedding_model_path=_MODEL_DIR if _MODEL_DIR else None,
    answer_provider=_answer_provider_from_env(),
    procedures_path=_PROCEDURES,
)
