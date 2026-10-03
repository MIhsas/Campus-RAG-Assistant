"""T026 offline replay — loopback mock only, clearly marked simulated.

Reproduces the T025 first-round bad action (model passing self-made
``filters``) against the REPLAYED model (a loopback mock returning scripted
actions — NOT a real model) and checks, offline:

1. the outbound tool declaration contains NO model-writable filters /
   procedure_id (server-fixed params are injected from the user snapshot);
2. the bad action is still rejected (the scope lock is not loosened);
3. the run's snapshot conditions stay the user's (2023) and the draft still
   matches the direct service;
4. the next independent run on the same service completes normally;
5. bounded observation transparency: 4 pending items with 3 listed →
   total=4 / listed=3 / truncated=true, while the full draft keeps 4.

Zero external calls; the "model" is the loopback mock and every output is
marked accordingly. Writes offline-replay.json.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

if str(BACKEND / "src") not in sys.path:
    sys.path.insert(0, str(BACKEND / "src"))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="T026 离线回放（loopback mock，非真实模型）")
    parser.add_argument("--out", required=True, help="offline-replay.json 输出路径")
    args = parser.parse_args()

    helpers = _load("t026_mock_helpers", BACKEND / "tests" / "test_deepseek_planner.py")

    from campus_assistant.agent.deepseek_planner import DeepSeekPlanner
    from campus_assistant.agent.tools import RunSnapshot, ToolContext, build_tool_registry, tool_catalog
    from campus_assistant.agent.workflow import run_planner_loop
    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.procedures.service import build_draft, load_procedures

    documents = parse_manifest(BACKEND / "examples" / "parse-corpus" / "manifest.json",
                               BACKEND / "examples" / "parse-corpus")["documents"]
    procedures = load_procedures(BACKEND / "examples" / "procedures" / "procedures.json")
    registry = build_tool_registry()
    fixed_filters = {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None}

    def ctx():
        return ToolContext(
            procedures=procedures, documents=documents,
            bm25_index=None, dense_index=None, embedding_service=None,
            available_modes=["bm25"],
            snapshot=RunSnapshot(procedure_id="proc-apply-defer",
                                 query="查找缓考依据并整理办理草稿", filters=dict(fixed_filters)),
        )

    bad_action = {"type": "call", "tool": "search_policy",
                  "args": {"query": "缓考", "filters": {"年级": "2023"}}}  # T025 第1轮原样坏动作

    # 同一 mock 服务承载两次独立运行（回放坏动作 + 干净链），同一适配器实例
    mock = helpers.MockChatServer([
        {"content": json.dumps(bad_action, ensure_ascii=False)},                       # run1 轮1：坏动作
        helpers.act_call("search_policy", {"query": "缓考申请的条件"}),                  # run1 轮2
        helpers.act_call("build_checklist_draft", {}),                                  # run1 轮3
        helpers.act_finish("【模拟】已检索并整理草稿"),                                   # run1 轮4
        helpers.act_call("search_policy", {"query": "缓考申请的条件"}),                  # run2 轮1
        helpers.act_call("build_checklist_draft", {}),                                  # run2 轮2
        helpers.act_finish("【模拟】完成"),                                             # run2 轮3
    ])
    planner = DeepSeekPlanner("sk-replay-not-real", base_url=mock.url(), model="mock-model",
                              trust_env=False)

    try:
        c1 = ctx()
        run1 = run_planner_loop(planner=planner, snapshot=c1.snapshot, ctx=c1, registry=registry)
        c2 = ctx()
        run2 = run_planner_loop(planner=planner, snapshot=c2.snapshot, ctx=c2, registry=registry)

        # --- 出站声明检查（真实捕获的请求 payload，非代码推断） ---
        sys_msg = mock.requests[0]["messages"][0]["content"]
        decl = {
            "source": "mock 捕获的实际出站请求 payload（第 1 次请求 system 消息）",
            "param_bullet_filters_absent": "    - filters" not in sys_msg,
            "param_bullet_procedure_id_absent": "    - procedure_id" not in sys_msg,
            "draft_declares_no_params": "（无参数；范围条件与已选事项由服务端固定注入）" in sys_msg,
            "examples_present": '"tool": "search_policy", "args": {"query"' in sys_msg and '"tool": "build_checklist_draft", "args": {}}' in sys_msg,
            "mode_availability_present": "本次可用检索模式" in sys_msg,
            "no_write_note_present": "不要**在 args 中传入 filters 或 procedure_id" in sys_msg,
        }
        decl["all_ok"] = all(v for k, v in decl.items() if k != "source")

        # --- 坏动作仍被拒、快照未被放宽 ---
        r1_rejects = [e for e in run1["events"] if e["kind"] == "tool_rejected"]
        bad_rejected = bool(r1_rejects) and "不得放宽或改写" in (r1_rejects[0].get("error") or "")

        # --- 观察完整性：4 项待核实只列 3 项 ---
        draft_obs = next((e.get("observation") for e in run1["events"]
                          if e["kind"] == "tool_call" and e["tool"] == "build_checklist_draft"), None)
        full_draft = run1["results"]["draft"]
        pending_full = sum(len(s.get("unspecified") or []) for s in (full_draft or {}).get("steps", []))
        obs_check = {
            "pending_items_listed_in_observation": (draft_obs or {}).get("pending_items_listed"),
            "pending_items_total_in_observation": (draft_obs or {}).get("pending_items_total"),
            "pending_items_truncated": (draft_obs or {}).get("pending_items_truncated"),
            "full_draft_unspecified_count": pending_full,
            "consistent": (
                (draft_obs or {}).get("pending_items_total") == pending_full
                and (draft_obs or {}).get("pending_items_listed") < pending_full
                and (draft_obs or {}).get("pending_items_truncated") is True
                and pending_full == 4
            ),
        }

        # --- 草稿对照直接 service ---
        direct = build_draft(procedures, "proc-apply-defer", fixed_filters, documents)
        draft_same = json.dumps(full_draft, sort_keys=True, ensure_ascii=False) == \
            json.dumps(direct, sort_keys=True, ensure_ascii=False)

        out = {
            "note": "T026 离线回放：loopback mock 模拟模型动作（含 T025 第1轮原样坏动作），"
                    "非真实模型输出；零外部调用。mock 不进入正常启动路径。",
            "marking": "offline replay（loopback mock 模拟模型动作，非真实模型）",
            "declaration_check": decl,
            "run1_bad_action_replay": {
                "status": run1["status"], "stop_reason": run1["stop_reason"],
                "message": run1["message"],
                "bad_action": bad_action,
                "bad_action_rejected_before_business": bad_rejected,
                "rejection_error": (r1_rejects[0].get("error") if r1_rejects else None),
                "snapshot_filters_kept": run1["snapshot"]["filters"] == fixed_filters,
                "draft_matches_direct_service": draft_same,
                "events": [{"round": e["round"], "kind": e["kind"], "tool": e.get("tool"),
                            "status": e["status"], "error": e.get("error")} for e in run1["events"]],
            },
            "run2_clean_chain": {
                "status": run2["status"], "stop_reason": run2["stop_reason"],
                "tool_calls_used": run2["tool_calls_used"],
                "draft_matches_direct_service": json.dumps(run2["results"]["draft"], sort_keys=True, ensure_ascii=False)
                == json.dumps(direct, sort_keys=True, ensure_ascii=False),
            },
            "observation_completeness": obs_check,
            "declared_tools": [{"name": t["name"], "parameters": [p["name"] for p in t["parameters"]]}
                               for t in tool_catalog()],
        }
        ok = (decl["all_ok"] and bad_rejected
              and out["run1_bad_action_replay"]["snapshot_filters_kept"]
              and out["run1_bad_action_replay"]["draft_matches_direct_service"]
              and run2["status"] == "completed" and obs_check["consistent"])
        out["exit_ok"] = bool(ok)

        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"run1: {run1['status']}/{run1['stop_reason']} (bad_rejected={bad_rejected})")
        print(f"run2: {run2['status']}/{run2['stop_reason']} tools={run2['tool_calls_used']}")
        print(f"decl_ok={decl['all_ok']} obs_consistent={obs_check['consistent']} exit_ok={out['exit_ok']}")
        print(f"wrote {p}")
        return 0 if out["exit_ok"] else 1
    finally:
        mock.close()


if __name__ == "__main__":
    raise SystemExit(main())
