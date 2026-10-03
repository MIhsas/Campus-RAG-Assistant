"""Local /compare page demo entry (T017).

Serves the real app on 127.0.0.1 with the synthetic comparison corpus
explicitly injected. Default product startup does NOT inject synthetic data;
corpus changes require restarting this demo (no disk monitoring).

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-comparison-page.py [--port 8020]
Then open http://127.0.0.1:8020/compare
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="版本对比页面本地演示（显式注入合成比较语料）")
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--corpus", default="examples/comparison-corpus")
    args = parser.parse_args()

    from pathlib import Path

    import uvicorn

    from campus_assistant.main import create_app

    corpus = Path(args.corpus)
    app = create_app(
        manifest_path=corpus / "manifest.json",
        corpus_root=corpus,
    )
    print("本地演示服务（合成比较语料，虚构政策，不代表真实学校规定）")
    print(f"打开 http://127.0.0.1:{args.port}/compare")
    print("语料更新需重启本演示（不监控磁盘变化）。")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
