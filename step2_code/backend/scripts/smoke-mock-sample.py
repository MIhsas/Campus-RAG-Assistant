"""Generate the T025 本地 mock 示例 (mock-run.json) — TEST-ONLY helper.

Spawns the loopback chat-completions mock (MockChatServer from
tests/test_deepseek_planner.py, outputs marked simulated), then runs
live-smoke-planner.py in --mode mock against it and saves the structured
result. This is a loopback integration sample, NOT a real smoke run and NOT
a live fallback. Zero external calls.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 T025 本地 mock 示例（loopback，非真实冒烟）")
    parser.add_argument("--out", required=True, help="mock-run.json 输出路径")
    parser.add_argument(
        "--scenario", choices=["full-chain", "early-finish"], default="full-chain",
        help="full-chain=search→draft→finish（默认）；early-finish=search→finish（缺草稿）")
    args = parser.parse_args()

    tests = _load("t025_mock_helpers", BACKEND / "tests" / "test_deepseek_planner.py")
    smoke = _load("live_smoke_planner", BACKEND / "scripts" / "live-smoke-planner.py")

    if args.scenario == "full-chain":
        script = [
            tests.act_call("search_policy", {"query": "缓考"}),
            tests.act_call("build_checklist_draft", {}),
            tests.act_finish("【模拟】全部办理工作已完成"),
        ]
    else:
        script = [
            tests.act_call("search_policy", {"query": "缓考"}),
            tests.act_finish("【模拟】全部办理工作已完成"),
        ]

    mock = tests.MockChatServer(script)
    try:
        code = smoke.main([
            "--mode", "mock",
            "--mock-base-url", mock.url(),
            "--out", args.out,
        ])
        print(f"mock 服务端实际接收请求数：{len(mock.requests)}", file=sys.stderr)
        return code
    finally:
        mock.close()


if __name__ == "__main__":
    raise SystemExit(main())
