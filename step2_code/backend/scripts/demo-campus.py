"""Unified offline campus demo entry (T018).

One local service for all five features: Q&A (/ask), evidence search
(/search), procedures & todos (/procedures), version comparison (/compare),
corpus preview (/preview), plus a unified home page (/).

- Combines examples/parse-corpus + examples/comparison-corpus into a
  combined demo corpus under .cache/ (clean rebuild each run): original
  document IDs, file contents and hashes are preserved byte-for-byte; the
  two source fixtures and gold are never modified. Document ID conflicts
  abort with an explicit error — never silently overwritten.
- Uses an explicit marked MOCK generator whose outputs carry
  【模拟输出，非真实 DeepSeek 回答】. The demo app is explicitly created
  with the mock provider and never sends requests to real generation
  services (this is about the demo app's requests; it is not a claim that
  the entire import chain ignores environment configuration).
- All simulated answers are mock results, not real-time DeepSeek answers.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-campus.py [--port 8030]        # serve
    .venv\\Scripts\\python.exe scripts\\demo-campus.py --record-api OUT.json # local API demo record
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SOURCES = [
    BACKEND / "examples" / "parse-corpus",
    BACKEND / "examples" / "comparison-corpus",
]
COMBINED_DIR = BACKEND / ".cache" / "demo-campus-corpus"


def _ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower().replace("-", "") == "utf8":
                continue
            wrapped = io.TextIOWrapper(stream.buffer, encoding="utf-8", line_buffering=True)
            if stream is sys.stdout:
                sys.stdout = wrapped
            else:
                sys.stderr = wrapped
        except (AttributeError, OSError):
            pass


def build_combined_corpus(out_dir: Path = COMBINED_DIR) -> Path:
    """Clean-rebuild the combined demo corpus. Sources are read-only."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    documents = []
    seen: dict[str, str] = {}
    for src in SOURCES:
        manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["documents"]:
            doc_id = entry["document_id"]
            if doc_id in seen:
                raise SystemExit(
                    f"文档 ID 冲突：{doc_id}（{seen[doc_id]} 与 {src}），不静默覆盖"
                )
            seen[doc_id] = str(src)
            src_file = src / entry["local_path"]
            dst_name = f"{src.name}__{entry['local_path']}"
            shutil.copyfile(src_file, out_dir / dst_name)
            sha = hashlib.sha256((out_dir / dst_name).read_bytes()).hexdigest()
            if sha != entry["sha256"]:
                raise SystemExit(f"组合语料哈希不一致：{doc_id}（{src_file}）")
            documents.append({**entry, "local_path": dst_name})
    (out_dir / "manifest.json").write_text(
        json.dumps({"schema_version": "1.0", "documents": documents}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_dir


class CampusMockProvider:
    """Explicitly-injected marked mock generator for the unified demo."""

    provider_id = "mock:campus-demo（模拟，非真实 DeepSeek）"

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
                "text": "【模拟输出，非真实 DeepSeek 回答】根据原文摘录整理的相关内容见引用（本段由本地模拟生成器产生，仅用于演示）。",
                "evidence_ids": [ev],
            }],
            "metadata": {
                "provider": "mock", "model": "mock-campus-demo", "request_id": None,
                "usage": None, "latency_ms": 0, "max_tokens": None, "finish_reason": None,
            },
        }


def _build_app(asr_model_dir: str | None = None):
    from campus_assistant.main import create_app

    corpus = build_combined_corpus()
    asr_adapter = None
    if asr_model_dir:
        # T020：真实本地 ASR 仅从显式指定的本地模型目录加载（不自动下载）
        from campus_assistant.asr.adapter import FunASRParaformerAdapter

        asr_adapter = FunASRParaformerAdapter(asr_model_dir)
    return create_app(
        manifest_path=corpus / "manifest.json",
        corpus_root=corpus,
        answer_provider=CampusMockProvider(),
        procedures_path=BACKEND / "examples" / "procedures" / "procedures.json",
        # T019：合成自查规则由统一演示显式注入（普通服务不自动启用）
        self_check_path=BACKEND / "examples" / "self-check" / "rule.json",
        asr_adapter=asr_adapter,
        # T022：演示入口使用带演示问题的首页；正常入口为中性首页
        demo_home=True,
        # T023：模拟规划器仅由演示入口显式注入（普通服务默认关闭 Agent 模式）；
        # 全程标注“模拟规划，非DeepSeek实时规划”。
        planner=_demo_planner(),
    )


def _demo_planner():
    """Scripted simulated planner for the demo — NOT a real model."""
    from campus_assistant.agent.planner import ScriptedPlanner

    return ScriptedPlanner([
        {"tool": "search_policy", "args": {}},
        {"tool": "build_checklist_draft", "args": {}},
        {"type": "finish", "summary": "模拟脚本完成：检索并整理草稿"},
    ])


def _record_api(out_path: Path, asr_model_dir: str | None = None) -> int:
    """Local API demo record over the unified app (zero external calls)."""
    from fastapi.testclient import TestClient

    app = _build_app(asr_model_dir)
    client = TestClient(app)
    calls = []

    def rec(name, method, url, body, resp):
        try:
            payload = resp.json()
        except Exception:
            payload = {"_non_json": True}
        calls.append({
            "name": name, "method": method, "url": url, "request": body,
            "status_code": resp.status_code, "response": payload,
        })

    rec("home", "GET", "/", None, client.get("/"))
    rec("ask-status", "GET", "/api/v1/ask/status", None, client.get("/api/v1/ask/status"))
    rec("search-status", "GET", "/api/v1/search/status", None, client.get("/api/v1/search/status"))
    rec("procedures-list", "GET", "/api/v1/procedures", None, client.get("/api/v1/procedures"))
    rec("comparison-groups", "GET", "/api/v1/comparison/groups", None, client.get("/api/v1/comparison/groups"))
    cmp_body = {"left_document_id": "cmp-defer-v1", "right_document_id": "cmp-defer-v2"}
    rec("comparison", "POST", "/api/v1/comparison", cmp_body,
        client.post("/api/v1/comparison", json=cmp_body))
    ask_extract = {"query": "缓考申请须由谁批准，之后还需要向哪个部门备案？", "top_k": 5,
                   "mode": "bm25", "answer_mode": "extractive", "filters": {"admission_year": 2023}}
    rec("ask-extractive", "POST", "/api/v1/ask", ask_extract,
        client.post("/api/v1/ask", json=ask_extract))
    ask_gen = {"query": "缓考申请须由谁批准，之后还需要向哪个部门备案？", "top_k": 5,
               "mode": "bm25", "answer_mode": "generated", "filters": {"admission_year": 2023}}
    rec("ask-generated-mock", "POST", "/api/v1/ask", ask_gen,
        client.post("/api/v1/ask", json=ask_gen))
    draft_body = {"filters": {"admission_year": 2023}}
    rec("procedures-draft", "POST", "/api/v1/procedures/proc-apply-defer/draft", draft_body,
        client.post("/api/v1/procedures/proc-apply-defer/draft", json=draft_body))
    rec("self-check-rule", "GET", "/api/v1/self-check/rule", None,
        client.get("/api/v1/self-check/rule"))
    sc_body = {
        "filters": {"admission_year": 2023},
        "answers": {
            "apply_at_first_year_end": "yes",
            "no_discipline_record": "yes",
            "rank_top_30": "yes",
            "passed_assessment": "unknown",
        },
    }
    rec("self-check-eval", "POST", "/api/v1/self-check", sc_body,
        client.post("/api/v1/self-check", json=sc_body))
    preview = client.get("/preview")
    calls.append({"name": "preview-page", "method": "GET", "url": "/preview", "request": None,
                  "status_code": preview.status_code, "response": {"_html": len(preview.text)}})

    out = {
        "demo": "T018 unified campus demo — local API record (combined corpus + marked mock generator)",
        "evidence_kind": "本地统一服务 API 记录；生成回答均为标记 mock（非真实 DeepSeek 实时回答）；零外部调用",
        "external_model_calls": 0,
        "combined_corpus": str(COMBINED_DIR.relative_to(BACKEND)),
        "sources_readonly": [str(s.relative_to(BACKEND)) for s in SOURCES],
        "calls": calls,
        "notes": [
            "组合语料保留原文档 ID/内容/哈希；两份原始夹具与 gold 未修改。",
            "ask-generated-mock 的回答带【模拟输出，非真实 DeepSeek 回答】标记。",
            "组合语料扩大检索候选：演示按需使用清晰筛选条件，不伪造检索结果。",
        ],
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = all(c["status_code"] in (200, 201) for c in calls)
    print(json.dumps({
        "record": str(out_path),
        "calls_recorded": len(calls),
        "all_routes_ok": ok,
        "statuses": {c["name"]: c["status_code"] for c in calls},
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    _ensure_utf8_streams()
    parser = argparse.ArgumentParser(description="统一离线演示入口（组合语料 + 标记 mock 生成器）")
    parser.add_argument("--port", type=int, default=8030)
    parser.add_argument("--record-api", default=None, help="输出本地 API 演示记录 JSON 后退出")
    parser.add_argument("--asr-model-dir", default=None, help="本地 FunASR 模型目录（显式指定才启用真实本地识别）")
    args = parser.parse_args()

    if args.record_api:
        return _record_api(Path(args.record_api), args.asr_model_dir)

    import uvicorn

    app = _build_app(args.asr_model_dir)
    print("统一离线演示服务（合成语料 + 标记 mock 生成器，非真实 DeepSeek 实时回答）")
    print(f"打开 http://127.0.0.1:{args.port}/ （统一首页）")
    print("组合语料每次启动重建自两份只读夹具；如夹具更新请重启本服务。")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
