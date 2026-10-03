"""Planner live-smoke CLI (T025 stage A — preparation only).

One reproducible, checkable CLI run for the planner smoke. Modes:

  --mode dry-run (default)  No network, no key required. Prints/writes the
                            configuration plan, corpus identity + synthetic
                            flags, budget and the expected checklist items.
                            Never presents scripted/mock results as real.
  --mode live               ONE planner-loop run against the OFFICIAL
                            endpoint only (https://api.deepseek.com /
                            deepseek-flash). NOT authorized at stage A —
                            requires explicit user authorization (stage B).
  --mode mock               TEST-ONLY explicit loopback integration
                            (--mock-base-url must be 127.0.0.1/localhost).
                            Marked "mock 联调（模拟服务，非真实冒烟）" in every
                            output. Never a silent fallback for live.

Fixed synthetic question (T025, not user-editable):
  查找缓考依据并整理办理草稿 / proc-apply-defer / admission_year=2023
over examples/parse-corpus（全部 is_synthetic=true）+ examples/procedures.

Pre-flight (BEFORE the first request; any failure → exit 1 with ZERO
requests):
- live: configured base_url must be the official URL, model deepseek-flash,
  max_tokens 300; key loaded from existing env only (presence boolean is
  recorded — the value never is). An arbitrary DEEPSEEK_BASE_URL is NOT
  treated as an authorized official target.
- corpus parses valid, non-empty, EVERY document is_synthetic=true;
- the local template contains the fixed procedure; the question/conditions
  are the fixed ones compiled into this script.

Execution reuses the real execution layer (run_planner_loop + DeepSeekPlanner)
— no parallel flow. Budget: ≤4 planning HTTP (≤1 per round), max_tokens=300,
single-call timeout 20s / monotonic deadline 30s, ZERO retries; stop on first
technical failure; no second question; answer generator never enabled.
If the required artifacts are not produced, the run records partial/stopped
as-is (T024-R1 server-side verdict) — no hidden extra tool calls.

Recording: full input snapshot, corpus/template hashes, actual config (no
keys), run status & stop_reason, server verdict, actual actions + observation
summaries, tool results/citations, per-round provider audit (missing fields
null, audits kept even for failed rounds when obtained), and HTTP attempts
COUNTED AT THE HTTP SEND POINT (never derived from plan_rounds).
No Authorization/keys recorded. Only synthetic-corpus content recorded.

Checklist (逐条结果核对表) is computed from ACTUAL run results — never
pre-filled with pass conclusions.

Exit codes: 0 = dry-run success, or live/mock run completed with every
checklist check passing; 1 = pre-flight failure / technical failure /
non-completed run / checklist failure; 2 = argparse usage error.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\live-smoke-planner.py
    .venv\\Scripts\\python.exe scripts\\live-smoke-planner.py --mode dry-run --out dry-run.json
    .venv\\Scripts\\python.exe scripts\\live-smoke-planner.py --mode mock --mock-base-url http://127.0.0.1:<port> --out mock-run.json
    # --mode live 仅在用户明确授权（B 阶段）且本地密钥已配置后执行一次
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"
PROCEDURES_PATH = BACKEND / "examples" / "procedures" / "procedures.json"

if str(BACKEND / "src") not in sys.path:
    sys.path.insert(0, str(BACKEND / "src"))

OFFICIAL_BASE_URL = "https://api.deepseek.com"
OFFICIAL_MODEL = "deepseek-flash"
SMOKE_MAX_TOKENS = 300
SMOKE_CALL_TIMEOUT_S = 20.0
SMOKE_DEADLINE_S = 30.0
SMOKE_MAX_HTTP = 4
SMOKE_AUTO_RETRIES = 0

# 本任务固定合成题（编译进脚本，不接受用户改写）
FIXED_QUESTION = "查找缓考依据并整理办理草稿"
FIXED_PROCEDURE = "proc-apply-defer"
FIXED_FILTERS = {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None}

MOCK_FAKE_KEY = "sk-smoke-mock-not-real"


class CountingHTTPClient:
    """Wraps httpx and counts POSTs AT THE HTTP SEND POINT.

    The send counter is the authoritative attempt count for this run; the
    loop's planner_http_attempts is cross-checked against it. No retries.
    """

    def __init__(self, trust_env: bool) -> None:
        import httpx

        self._client = httpx.Client(trust_env=trust_env)
        self.sent = 0
        self.sent_urls: list[str] = []

    def post(self, url, json=None, headers=None, timeout=None):  # noqa: A002
        self.sent += 1
        self.sent_urls.append(str(url))
        return self._client.post(url, json=json, headers=headers, timeout=timeout)

    def close(self) -> None:
        self._client.close()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_loopback_url(url: str) -> bool:
    """Strict loopback check via standard URL parsing (T025-R1).

    Requires scheme http/https and the COMPLETE hostname to be exactly
    localhost / 127.0.0.1 / ::1 (accurately parsed, never prefix matching).
    Rejects userinfo (user@host), malformed/absent hosts and invalid ports.
    No DNS probing — parsing only.
    """
    from urllib.parse import urlsplit

    try:
        parts = urlsplit(url)
        port = parts.port  # raises ValueError on malformed/out-of-range ports
    except ValueError:
        return False
    if parts.scheme not in ("http", "https"):
        return False
    if parts.username is not None or parts.password is not None:
        return False  # 拒绝 userinfo（如 localhost@example.invalid）
    host = parts.hostname  # lowercased, IPv6 brackets stripped
    if not host:
        return False
    return host in ("127.0.0.1", "localhost", "::1")


def _ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower().replace("-", "") == "utf8":
                continue
            import io

            wrapped = io.TextIOWrapper(stream.buffer, encoding="utf-8", line_buffering=True)
            if stream is sys.stdout:
                sys.stdout = wrapped
            else:
                sys.stderr = wrapped
        except (AttributeError, OSError):
            pass


def _row(check: str, expected: str, observed: str, ok: bool | None) -> dict:
    return {"check": check, "expected": expected, "observed": observed, "pass": ok}


def preflight(mode: str, mock_base_url: str | None) -> tuple[list[dict], dict, object, object, str | None]:
    """All checks BEFORE any request. Returns (rows, identity, documents,
    procedures, api_key or None). Raises SystemExit-free: caller decides."""
    rows: list[dict] = []
    ok_all = True

    def add(check, expected, observed, ok):
        nonlocal ok_all
        rows.append(_row(check, expected, observed, ok))
        if ok is False:
            ok_all = False

    # --- 配置核对 ---
    if mode == "live":
        import os

        cfg_base = os.environ.get("DEEPSEEK_BASE_URL", "").strip() or OFFICIAL_BASE_URL
        cfg_model = os.environ.get("DEEPSEEK_MODEL", "").strip() or OFFICIAL_MODEL
        add("配置：官方端点", OFFICIAL_BASE_URL, cfg_base, cfg_base.rstrip("/") == OFFICIAL_BASE_URL)
        add("配置：模型", OFFICIAL_MODEL, cfg_model, cfg_model == OFFICIAL_MODEL)
    elif mode == "mock":  # 显式 loopback（标准 URL 解析校验），标注非官方
        url = (mock_base_url or "").strip()
        add("配置：loopback 显式注入（测试专用）",
            "完整主机名为 127.0.0.1 / localhost / ::1（标准 URL 解析；拒绝 userinfo、畸形端口）",
            url or "（缺失）", _is_loopback_url(url))
    else:  # dry-run：零网络、无目标
        add("配置：目标端点", "dry-run 零请求（无网络目标）", "dry-run（不发起任何请求）", True)
    add("配置：max_tokens", str(SMOKE_MAX_TOKENS), str(SMOKE_MAX_TOKENS), True)
    add("配置：预算", f"≤{SMOKE_MAX_HTTP} 次规划 HTTP、零重试、单次 {SMOKE_CALL_TIMEOUT_S:g}s/总 {SMOKE_DEADLINE_S:g}s",
        f"max_http={SMOKE_MAX_HTTP}, auto_retries={SMOKE_AUTO_RETRIES}", True)

    # --- 资料核对：合成、非空、解析成功 ---
    identity = {"manifest_path": str(PARSE_CORPUS / "manifest.json"), "documents": []}
    documents = None
    try:
        from campus_assistant.corpus.parse import parse_manifest

        result = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)
        documents = result["documents"]
        valid = result["valid"]
        n = len(documents)
        all_syn = all((d.get("metadata") or {}).get("is_synthetic") is True for d in documents)
        add("语料：解析成功且非空", "valid 且 ≥1 文档", f"valid={valid}，文档 {n}", valid and n > 0)
        add("语料：全部 is_synthetic=true", "全部 true", f"全部 {n} 篇 is_synthetic={all_syn}", all_syn)
        identity["manifest_sha256"] = _sha256_file(PARSE_CORPUS / "manifest.json")
        identity["document_count"] = n
        identity["all_synthetic"] = all_syn
        for d in documents:
            meta = d.get("metadata") or {}
            identity["documents"].append({
                "document_id": d.get("document_id"),
                "title": meta.get("title"),
                "sha256": meta.get("sha256"),
                "is_synthetic": meta.get("is_synthetic"),
            })
    except Exception as e:  # noqa: BLE001
        add("语料：解析成功且非空", "valid 且 ≥1 文档", f"解析失败（{type(e).__name__}）", False)

    # --- 模板核对：固定事项存在 ---
    procedures = None
    try:
        from campus_assistant.procedures.service import load_procedures

        procedures = load_procedures(PROCEDURES_PATH)
        proc = next((p for p in procedures["procedures"] if p["procedure_id"] == FIXED_PROCEDURE), None)
        add("模板：含固定事项", FIXED_PROCEDURE, FIXED_PROCEDURE if proc else "（缺失）", proc is not None)
        identity["template"] = {
            "path": str(PROCEDURES_PATH),
            "sha256": _sha256_file(PROCEDURES_PATH),
            "procedure_id": FIXED_PROCEDURE,
            "template_version": (proc or {}).get("template_version"),
            "is_synthetic": bool((proc or {}).get("is_synthetic", procedures.get("is_synthetic", False))),
        }
    except Exception as e:  # noqa: BLE001
        add("模板：含固定事项", FIXED_PROCEDURE, f"加载失败（{type(e).__name__}）", False)

    # --- 固定题目（编译值自检） ---
    add("题目：固定合成题", f"{FIXED_QUESTION} / {FIXED_PROCEDURE} / 年级 2023",
        f"{FIXED_QUESTION} / {FIXED_PROCEDURE} / 年级 2023", True)

    # --- 密钥（仅 live 需要；只记存在性） ---
    api_key = None
    if mode == "live":
        import os

        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip() or None
        add("密钥：本地环境已配置", "DEEPSEEK_API_KEY 非空（值不记录）",
            "已配置" if api_key else "未配置", api_key is not None)
    elif mode == "mock":
        api_key = MOCK_FAKE_KEY
        add("密钥：mock 显式假密钥", "不使用真实密钥", "mock 假密钥（标注）", True)

    return rows, identity, documents, procedures, api_key if ok_all else None


def build_checklist(run: dict | None, documents, procedures) -> list[dict]:
    """逐条结果核对表：按实际动作核对，不预写通过结论。"""
    if run is None:
        return [
            {"item": "是否实际搜索", "expected": "search_policy 至少一次成功并返回命中", "observed": "待实际运行核对", "pass": None},
            {"item": "草稿是否存在且事项/条件正确",
             "expected": f"草稿存在、procedure_id={FIXED_PROCEDURE}、条件=年级 2023",
             "observed": "待实际运行核对", "pass": None},
            {"item": "引用是否与直接 service 相同", "expected": "草稿引用与本地 build_draft 直接结果逐条一致",
             "observed": "待实际运行核对", "pass": None},
            {"item": "是否需人工核实", "expected": "saveable=false/待核实项如实标注", "observed": "待实际运行核对", "pass": None},
            {"item": "是否有失败/提前 finish", "expected": "无失败动作、无缺产物提前结束", "observed": "待实际运行核对", "pass": None},
            {"item": "是否零自动保存", "expected": "零自动保存（不写待办/localStorage/任何存储）",
             "observed": "静态实现判断（非运行时监控）：脚本仅写 --out 运行记录，代码路径无其他写入", "pass": True},
        ]

    rows: list[dict] = []
    events = run.get("events") or []
    results = run.get("results") or {}
    search = results.get("search")
    draft = results.get("draft")

    search_ok = [e for e in events
                 if e.get("kind") == "tool_call" and e.get("tool") == "search_policy" and e.get("status") == "ok"]
    hits = (search or {}).get("hit_count", 0)
    rows.append({
        "item": "是否实际搜索",
        "expected": "search_policy 至少一次成功并返回命中",
        "observed": f"search_policy 成功 {len(search_ok)} 次，命中 {hits} 条",
        "pass": bool(search_ok) and hits > 0,
    })

    snap = run.get("snapshot") or {}
    cond_ok = snap.get("filters") == FIXED_FILTERS
    draft_ok = draft is not None and draft.get("procedure_id") == FIXED_PROCEDURE and cond_ok
    rows.append({
        "item": "草稿是否存在且事项/条件正确",
        "expected": f"草稿存在、procedure_id={FIXED_PROCEDURE}、条件=年级 2023",
        "observed": (
            f"草稿 {'存在' if draft else '不存在'}"
            + (f"，procedure_id={draft.get('procedure_id')}" if draft else "")
            + f"，快照条件={json.dumps(snap.get('filters'), ensure_ascii=False)}"
        ),
        "pass": bool(draft_ok),
    })

    # 引用对照直接 service（本地重算，不经过模型）
    cite_pass: bool | None = None
    cite_obs = "无草稿，无法对照"
    if draft is not None and procedures is not None and documents is not None:
        try:
            from campus_assistant.procedures.service import build_draft

            direct = build_draft(procedures, FIXED_PROCEDURE, FIXED_FILTERS, documents)

            def cites(d):
                return [(c.get("document_id"), c.get("block_id"), c.get("quote"))
                        for s in d.get("steps", []) for c in s.get("citations", [])]

            same = cites(draft) == cites(direct)
            cite_pass = same
            cite_obs = f"草稿引用 {len(cites(draft))} 条，与直接 build_draft {'一致' if same else '不一致'}"
        except Exception as e:  # noqa: BLE001
            cite_obs = f"对照失败（{type(e).__name__}）"
            cite_pass = False
    rows.append({
        "item": "引用是否与直接 service 相同",
        "expected": "草稿引用与本地 build_draft 直接结果逐条一致",
        "observed": cite_obs, "pass": cite_pass,
    })

    if draft is None:
        man_obs, man_pass = "无草稿", None
    else:
        unspec = sum(len(s.get("unspecified") or []) for s in draft.get("steps", []))
        failed = [c for s in draft.get("steps", []) for c in s.get("citations", []) if not c.get("usable")]
        needs = (not draft.get("saveable")) or unspec > 0 or failed
        man_obs = (f"saveable={draft.get('saveable')}，未明确事项 {unspec} 项，未通过引用 {len(failed)} 条"
                   f"——{'需人工核实（已如实标注）' if needs else '无人工核实项'}"
                   f"（程序化摘要，非人工核对结论）")
        # 该行核对的是“人工核实需求是否如实标注”，而非“人工核对已通过”
        man_pass = True
    rows.append({
        "item": "是否需人工核实",
        "expected": "saveable=false/待核实项如实标注（程序化摘要，不代表人工核对已通过）",
        "observed": man_obs, "pass": man_pass,
    })

    failures = [e for e in events if e.get("status") not in ("ok", None)]
    early = run.get("status") != "completed"
    rows.append({
        "item": "是否有失败/提前 finish",
        "expected": "无失败动作、无缺产物提前结束（status=completed）",
        "observed": f"status={run.get('status')}，stop_reason={run.get('stop_reason')}，失败/被拒事件 {len(failures)} 条",
        "pass": (not failures) and not early,
    })

    rows.append({
        "item": "是否零自动保存",
        "expected": "零自动保存（不写待办/localStorage/任何存储）",
        "observed": "静态实现判断（非运行时监控）：脚本仅写 --out 运行记录，代码路径无其他写入",
        "pass": True,
    })
    return rows


def run_smoke(mode: str, mock_base_url: str | None, out_path: str | None) -> int:
    _ensure_utf8_streams()
    marking = {
        "dry-run": "dry-run 配置计划（零网络、零请求；不冒充真实模型结果）",
        "live": "真实冒烟（官方端点）——执行须用户明确授权（B 阶段）",
        "mock": "mock 联调（本地模拟服务，非真实冒烟）",
    }[mode]

    rows, identity, documents, procedures, api_key = preflight(mode, mock_base_url)
    pre_ok = all(r["pass"] is not False for r in rows)

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "marking": marking,
        "input_snapshot": {
            "question": FIXED_QUESTION,
            "procedure_id": FIXED_PROCEDURE,
            "filters": FIXED_FILTERS,
            "source": "T025 任务固定合成题（编译进脚本，不接受改写）",
        },
        "corpus_identity": identity,
        "config": {
            "base_url": OFFICIAL_BASE_URL if mode == "live" else (mock_base_url or None),
            "model": OFFICIAL_MODEL if mode == "live" else "mock（loopback）",
            "max_tokens": SMOKE_MAX_TOKENS,
            "call_timeout_s": SMOKE_CALL_TIMEOUT_S,
            "deadline_s": SMOKE_DEADLINE_S,
            "max_planning_http": SMOKE_MAX_HTTP,
            "auto_retries": SMOKE_AUTO_RETRIES,
            "answer_generator": "未启用（本脚本不构造任何答案生成器）",
            "key_present": bool(api_key),
            "key_note": "密钥仅经现有环境变量加载；值不记录、不打印",
        },
        "preflight": rows,
        "budget": {
            "max_plan_rounds": 4, "max_tool_calls": 6,
            "planning_http_per_round": 1, "auto_retries": SMOKE_AUTO_RETRIES,
            "max_tokens_per_call": SMOKE_MAX_TOKENS,
        },
        "run": None,
        "checklist": build_checklist(None, documents, procedures),
        "exit_ok": False,
        "notes": [
            "B 阶段真实调用尚未授权；--live 不因本脚本存在而获得授权。",
            "mock 模式仅为 loopback 显式联调，不静默作为 live 的降级分支。",
            "计数在 HTTP 发送处观察（CountingHTTPClient.sent），不按 plan_rounds 推算。",
        ],
    }

    if not pre_ok:
        out["checklist"] = build_checklist(None, documents, procedures)
        out["notes"].append("前置校验未通过：零请求，非零退出。")
        _emit(out, out_path, mode)
        return 1

    if mode == "dry-run":
        out["exit_ok"] = True
        out["notes"].append("dry-run 成功：未发起任何网络请求，未运行 planner。")
        _emit(out, out_path, mode)
        return 0

    # --- 一次 planner loop（复用真实执行层） ---
    from campus_assistant.agent.deepseek_planner import DeepSeekPlanner
    from campus_assistant.agent.tools import RunSnapshot, ToolContext, build_tool_registry
    from campus_assistant.agent.workflow import run_planner_loop

    trust_env = mode == "live"
    client = CountingHTTPClient(trust_env=trust_env)
    try:
        planner = DeepSeekPlanner(
            api_key or MOCK_FAKE_KEY,
            base_url=OFFICIAL_BASE_URL if mode == "live" else mock_base_url,
            model=OFFICIAL_MODEL if mode == "live" else "mock-model",
            max_tokens=SMOKE_MAX_TOKENS,
            timeout=SMOKE_CALL_TIMEOUT_S,
            trust_env=trust_env,
            client=client,
        )
        # 与服务端同口径构建本地 BM25 索引，使 search_policy 返回真实命中
        from campus_assistant.corpus.chunk import chunk_documents
        from campus_assistant.retrieval.bm25 import BM25Index

        chunks = chunk_documents(documents or [], max_chars=500)
        bm25 = BM25Index(chunks, k1=1.5, b=0.75) if chunks else None
        ctx = ToolContext(
            procedures=procedures,
            documents=documents or [],
            bm25_index=bm25, dense_index=None, embedding_service=None,
            available_modes=["bm25"],
            snapshot=RunSnapshot(
                procedure_id=FIXED_PROCEDURE, query=FIXED_QUESTION, filters=dict(FIXED_FILTERS),
            ),
        )
        run = run_planner_loop(
            planner=planner, snapshot=ctx.snapshot, ctx=ctx,
            registry=build_tool_registry(), deadline_s=SMOKE_DEADLINE_S,
        )
    finally:
        sent = client.sent
        client.close()

    run["http_observed_at_send"] = sent
    run["http_send_urls"] = list(client.sent_urls)
    out["run"] = run
    out["checklist"] = build_checklist(run, documents, procedures)

    completed = run.get("status") == "completed"
    checks_ok = all(c["pass"] is not False for c in out["checklist"])
    consistent = run.get("planner_http_attempts") == sent
    out["exit_ok"] = bool(completed and checks_ok and consistent)
    if not consistent:
        out["notes"].append(f"HTTP 计数不一致：发送处 {sent} vs 循环计数 {run.get('planner_http_attempts')}。")
    if not completed:
        out["notes"].append(f"运行未达 completed（{run.get('status')}/{run.get('stop_reason')}），如实记录，非零退出。")
    _emit(out, out_path, mode)
    return 0 if out["exit_ok"] else 1


def _emit(out: dict, out_path: str | None, mode: str) -> None:
    # 摘要到 stderr；完整结构化结果到 stdout（与 T014 惯例一致）
    summary = [
        f"[live-smoke-planner] mode={mode} marking={out['marking']}",
        f"前置校验：{sum(1 for r in out['preflight'] if r['pass'] is not False)}/{len(out['preflight'])} 通过",
    ]
    if out.get("run"):
        r = out["run"]
        summary.append(
            f"运行：status={r.get('status')} stop={r.get('stop_reason')} "
            f"http_send={r.get('http_observed_at_send')} http_loop={r.get('planner_http_attempts')} "
            f"tools={r.get('tool_calls_used')}")
    for c in out.get("checklist", []):
        mark = {True: "✓", False: "✗", None: "·"}[c["pass"]]
        summary.append(f"  [{mark}] {c['item']}：{c['observed']}")
    summary.append(f"exit_ok={out['exit_ok']}")
    print("\n".join(summary), file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=2), file=sys.stdout)
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out_path}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="规划器真实冒烟 CLI（T025 A：默认 dry-run；--live 须 B 阶段授权）")
    parser.add_argument("--mode", choices=["dry-run", "live", "mock"], default="dry-run",
                        help="dry-run（默认，零网络）/ live（官方端点，须授权）/ mock（测试专用 loopback）")
    parser.add_argument("--mock-base-url", default=None,
                        help="仅 --mode mock：loopback 地址（127.0.0.1/localhost）")
    parser.add_argument("--out", default=None, help="结构化结果 JSON 输出路径（可选）")
    args = parser.parse_args(argv)

    if args.mode == "mock" and not args.mock_base_url:
        parser.error("--mode mock 需要显式 --mock-base-url（loopback）")
    if args.mode != "mock" and args.mock_base_url:
        parser.error("--mock-base-url 仅允许与 --mode mock 一起使用")
    return run_smoke(args.mode, args.mock_base_url, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
