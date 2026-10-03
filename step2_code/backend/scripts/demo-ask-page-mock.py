"""Local /ask page demo with a clearly-marked MOCK generator (T015).

Serves the real app on 127.0.0.1 with a fake in-process AnswerProvider whose
outputs are always marked 【模拟输出，非真实 DeepSeek 回答】. This entry point
exists ONLY for offline page demos — the fake is not in any product startup
path (main.py / demo.py), and no external request is ever made.

Mock behavior by query text (for exercising all page states):
- contains "模拟失败"  → raises  → 页面出现「生成失败 + 查看本次问题的原文依据」
- contains "模拟不足"  → insufficient_evidence（即使有证据；练习材料不足态）
  注意：查询须含可检索词（如“缓考申请模拟不足”）才会命中证据进入 mock；
  无检索命中的问题走本地短路，不进 mock 分支。
- no evidence (e.g. "宿舍门禁时间是几点？") → insufficient_evidence（本地短路，不进 mock）
- otherwise → simulated answer citing the first sent evidence id

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-ask-page-mock.py [--port 8010]
Then open http://127.0.0.1:8010/ask
"""

from __future__ import annotations

import argparse


class MockPageDemoProvider:
    """Fake provider for the local page demo only — clearly marked output."""

    provider_id = "mock:page-demo（模拟，非真实 DeepSeek）"

    def generate(self, *, query, evidence, filters):
        if "模拟失败" in query:
            raise RuntimeError("mock: simulated generator failure")
        if "模拟不足" in query:
            return {"type": "insufficient_evidence", "reason": "【模拟输出】材料不足（mock）。"}
        if not evidence:
            return {"type": "insufficient_evidence", "reason": "【模拟输出】材料不足（mock）。"}
        ev = evidence[0]["evidence_id"]
        return {
            "type": "answer",
            "paragraphs": [{
                "text": "【模拟输出，非真实 DeepSeek 回答】根据原文摘录，缓考申请须经所在学院批准，报教务处备案后方可生效。（本段由本地模拟生成器产生，仅用于页面演示）",
                "evidence_ids": [ev],
            }],
            "metadata": {
                "provider": "mock",
                "model": "mock-page-demo",
                "request_id": None,
                "usage": None,
                "latency_ms": 0,
                "max_tokens": None,
                "finish_reason": None,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="/ask 页面本地演示（模拟生成器，零外部请求）")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--corpus", default="examples/parse-corpus")
    args = parser.parse_args()

    from pathlib import Path

    import uvicorn

    from campus_assistant.main import create_app

    corpus = Path(args.corpus)
    # 合成办事模板仅在演示入口显式启用（T016），不进入默认产品运行。
    app = create_app(
        manifest_path=corpus / "manifest.json",
        corpus_root=corpus,
        answer_provider=MockPageDemoProvider(),
        procedures_path=Path("examples/procedures/procedures.json"),
    )
    print("本地演示服务（模拟生成器，输出带【模拟输出】标记，非真实 DeepSeek 回答）")
    print(f"打开 http://127.0.0.1:{args.port}/ask")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
