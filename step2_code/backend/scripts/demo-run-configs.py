"""Config-combination capability check for the unified run entry (T022).

Exercises the declared configuration combinations against the EXISTING
synthetic corpora/models and records expected vs actual capabilities.
Uses the existing local embedding model (loads once, ONE query — no old
evaluations), the existing local ASR directory (status only), and a
counting stub for the generator (zero external calls, no real key).

Output: config-combos.json + config-combos.md (配置组合→预期/实测能力表).

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-run-configs.py --out-dir <submissions/T022>
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"
PROCEDURES = BACKEND / "examples" / "procedures" / "procedures.json"
RULE = BACKEND / "examples" / "self-check" / "rule.json"
EMBED_DIR = BACKEND / "models" / "bge-small-zh-v1.5"
ASR_DIR = BACKEND / ".cache" / "asr-models" / "paraformer-zh"


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


class CountingStub:
    provider_id = "counting-stub（测试桩，非真实生成）"

    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return {"type": "insufficient_evidence", "reason": "桩返回：材料不足（模拟）"}


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_streams()
    parser = argparse.ArgumentParser(description="统一运行入口配置组合验证（零外部调用）")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    from fastapi.testclient import TestClient

    spec = importlib.util.spec_from_file_location("serve_corpus", BACKEND / "scripts" / "serve-corpus.py")
    serve_corpus = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serve_corpus)

    rows = []
    raw = []

    def check(name, expected, actual, ok):
        rows.append({"combo": name, "expected": expected, "actual": actual, "match": bool(ok)})

    def build(**kw):
        return serve_corpus.build_app(
            manifest=PARSE_CORPUS / "manifest.json", corpus_root=PARSE_CORPUS, **kw
        )

    # C1 最小配置
    app, report = build()
    c = TestClient(app, raise_server_exceptions=False)
    s = c.get("/api/v1/search/status").json()
    a = c.get("/api/v1/ask/status").json()
    v = c.get("/api/v1/asr/status").json()
    actual = (f"检索模式={'、'.join(s['available_modes'])}；生成器={'已配置' if a['generator_configured'] else '未配置'}；"
              f"ASR={'已配置' if v['configured'] else '未配置'}；办事/自查=未配置")
    ok1 = (s["available_modes"] == ["bm25"] and not a["generator_configured"] and not v["configured"])
    check("C1 最小（仅语料）", "BM25、摘录可用；生成器/ASR/模板/规则未配置", actual, ok1)
    raw.append({"combo": "C1", "report": report})

    # C2 + 本地向量模型（现有模型加载一次，单条查询）
    app2, report2 = build(embedding_model_dir=str(EMBED_DIR))
    c2 = TestClient(app2, raise_server_exceptions=False)
    s2 = c2.get("/api/v1/search/status").json()
    one = c2.post("/api/v1/search", json={"query": "缓考", "top_k": 3, "mode": "dense"})
    modes = "、".join(s2["available_modes"])
    ok2 = (set(s2["available_modes"]) == {"bm25", "dense", "hybrid"} and one.status_code == 200 and len(one.json().get("hits", [])) > 0)
    check("C2 + embedding-model-dir", "三模式可用（bm25、dense、hybrid）；dense 单查询可返回",
          f"检索模式={modes}；dense 查询 HTTP {one.status_code} 命中 {len(one.json().get('hits', []))} 条", ok2)
    raw.append({"combo": "C2", "report": report2})

    # C3 + 本地 ASR 目录（仅状态，不转写）
    app3, report3 = build(asr_model_dir=str(ASR_DIR))
    c3 = TestClient(app3, raise_server_exceptions=False)
    v3 = c3.get("/api/v1/asr/status").json()
    check("C3 + asr-model-dir", "ASR 状态为已配置（模型按需加载）",
          f"ASR={'已配置（' + (v3.get('provider') or '') + ' / ' + (v3.get('model') or '') + '）' if v3['configured'] else '未配置'}", v3["configured"] is True)
    raw.append({"combo": "C3", "report": report3})

    # C4 + 显式模板/规则
    app4, report4 = build(procedures=PROCEDURES, self_check=RULE)
    c4 = TestClient(app4, raise_server_exceptions=False)
    st_p, st_s = c4.get('/api/v1/procedures').status_code, c4.get('/api/v1/self-check/rule').status_code
    check("C4 + procedures + self-check", "办事模板与自查规则接口可用",
          f"procedures={st_p}；self-check={st_s}", st_p == 200 and st_s == 200)
    raw.append({"combo": "C4", "report": report4})

    # C5 生成器计数桩：启动/状态/摘录零调用，显式生成一次
    stub = CountingStub()
    app5, report5 = build(generator="deepseek", provider_factory=lambda: stub)
    c5 = TestClient(app5, raise_server_exceptions=False)
    c5.get("/api/v1/ask/status")
    c5.get("/api/v1/search/status")
    ex = c5.post("/api/v1/ask", json={"query": "缓考申请", "top_k": 5, "mode": "bm25", "answer_mode": "extractive"})
    zero_calls = stub.calls
    gen = c5.post("/api/v1/ask", json={"query": "缓考申请", "top_k": 5, "mode": "bm25", "answer_mode": "generated"})
    ok5 = (zero_calls == 0 and gen.status_code == 200 and stub.calls == 1)
    check("C5 生成器（计数桩）", "启动/状态/摘录零生成调用；显式生成可达（桩）",
          f"摘录后调用数={zero_calls}；显式生成 HTTP {gen.status_code}，调用数={stub.calls}", ok5)
    raw.append({"combo": "C5", "report": report5})

    # C6 生成器缺配置 → 明确降级
    app6, report6 = build(generator="deepseek", provider_factory=lambda: None)
    a6 = TestClient(app6, raise_server_exceptions=False).get("/api/v1/ask/status").json()
    text6 = "\n".join(line for line, _ in report6)
    ok6 = ("请求启用但配置不完整" in text6 and not a6["generator_configured"])
    check("C6 生成器缺配置", "明确提示降级，摘录仍可用，不静默当成功启用",
          f"报告含「请求启用但配置不完整」={'请求启用但配置不完整' in text6}；generator_configured={a6['generator_configured']}", ok6)
    raw.append({"combo": "C6", "report": report6})

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config-combos.json").write_text(
        json.dumps({"evidence_kind": "本地装配验证（合成语料/现有本地模型/测试桩），零外部调用",
                    "rows": rows, "reports": raw}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# T022 配置组合 → 预期/实测能力表",
        "",
        "实测对象：现有合成语料（examples/parse-corpus）与现有本地模型/配置；测试资料为合成性质，不代表真实校园效果。零外部调用。",
        "",
        "| 配置组合 | 预期能力 | 实测结果 | 一致 |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['combo']} | {r['expected']} | {r['actual']} | {'✓' if r['match'] else '✗'} |")
    ok_all = all(r["match"] for r in rows)
    lines += [
        "",
        f"总体：{'全部一致' if ok_all else '存在不一致（见上表）'}。",
        "",
        "## 可复制 Windows 命令（路径含空格已加引号）",
        "",
        "```powershell",
        "Set-Location 'F:\\Collage Paper\\step2_code\\backend'",
        "& .\\.venv\\Scripts\\python.exe scripts\\serve-corpus.py `",
        "  --manifest 'F:\\Collage Paper\\step2_code\\backend\\examples\\parse-corpus\\manifest.json' `",
        "  --corpus-root 'F:\\Collage Paper\\step2_code\\backend\\examples\\parse-corpus'",
        "# 可选功能（均默认关闭，显式指定才启用；模型仅本地目录、不自动下载）：",
        "#   --embedding-model-dir 'F:\\Collage Paper\\step2_code\\backend\\models\\bge-small-zh-v1.5'",
        "#   --asr-model-dir 'F:\\Collage Paper\\step2_code\\backend\\.cache\\asr-models\\paraformer-zh'",
        "#   --procedures 'F:\\Collage Paper\\step2_code\\backend\\examples\\procedures\\procedures.json'",
        "#   --self-check 'F:\\Collage Paper\\step2_code\\backend\\examples\\self-check\\rule.json'",
        "#   --generator deepseek   # 密钥仅放本地环境变量 CAMPUS_GENERATOR/DEEPSEEK_API_KEY，不进命令行",
        "```",
    ]
    (out_dir / "config-combos.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"config_combos": str(out_dir / "config-combos.md"),
                      "rows_ok": [r["match"] for r in rows]}, ensure_ascii=False))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
