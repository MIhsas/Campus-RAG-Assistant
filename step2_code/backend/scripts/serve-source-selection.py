"""Serve the app with the real v1.1 pack + local BGE for T031 manual checks.

Usage (from step2_code/backend):
  .venv/Scripts/python.exe scripts/serve-source-selection.py --port 8010
Then open http://127.0.0.1:8010/search and /ask in a real browser.
No external calls; DeepSeek/Agent stay off unless separately enabled.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND / "src"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8010)
    ap.add_argument("--manifest", default=str(ROOT / "data/corpora/sicau-rag-pilot-v1.1/manifest.json"))
    ap.add_argument("--corpus-root", default=str(ROOT / "data/corpora/sicau-rag-pilot-v1.1"))
    ap.add_argument("--model-path", default=str(BACKEND / "models/bge-small-zh-v1.5"))
    args = ap.parse_args()

    import uvicorn

    from campus_assistant.main import create_app

    app = create_app(
        manifest_path=Path(args.manifest),
        corpus_root=Path(args.corpus_root),
        embedding_model_path=args.model_path if Path(args.model_path).exists() else None,
    )
    print(f"serving on http://{args.host}:{args.port}/search  (/ask, /preview, /procedures)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
