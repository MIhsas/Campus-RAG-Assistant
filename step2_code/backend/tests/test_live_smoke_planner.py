"""T025 stage A smoke-CLI focused tests — three local verification classes.

1. normal dry-run: exit 0, zero network, checklist rows not pre-filled;
2. loopback full chain: real execution layer + mock, HTTP attempts counted at
   the send point equal the server-received count;
3. early finish / technical failure: non-zero exit, partial evidence kept.

Plus one pre-flight class (config/corpus mismatch → non-zero with ZERO
requests). No matrix expansion; zero external calls; no downloads.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


smoke = _load("live_smoke_planner", BACKEND / "scripts" / "live-smoke-planner.py")
helpers = _load("t025_mock_helpers", BACKEND / "tests" / "test_deepseek_planner.py")


class TestDryRun:
    def test_dry_run_zero_network_and_unfilled_checklist(self, tmp_path):
        out = tmp_path / "dry.json"
        code = smoke.main(["--mode", "dry-run", "--out", str(out)])
        assert code == 0, "默认 dry-run 成功为 0"
        d = json.loads(out.read_text(encoding="utf-8"))
        assert d["mode"] == "dry-run" and d["run"] is None
        assert "零网络" in d["marking"]
        # 前置校验覆盖配置/资料/模板/固定题
        checks = {r["check"] for r in d["preflight"]}
        assert any("is_synthetic" in c for c in checks)
        assert any("固定事项" in c for c in checks)
        assert all(r["pass"] is not False for r in d["preflight"])
        # 资料身份含哈希与合成标记
        assert d["corpus_identity"]["all_synthetic"] is True
        assert d["corpus_identity"]["manifest_sha256"]
        assert all(x["is_synthetic"] is True for x in d["corpus_identity"]["documents"])
        assert d["corpus_identity"]["template"]["sha256"]
        # 核对表不预写通过结论
        rows = {c["item"]: c for c in d["checklist"]}
        assert rows["是否实际搜索"]["pass"] is None and "待实际运行核对" in rows["是否实际搜索"]["observed"]
        assert rows["草稿是否存在且事项/条件正确"]["pass"] is None
        assert rows["是否有失败/提前 finish"]["pass"] is None
        # 预算与配置（不含密钥）
        assert d["config"]["max_tokens"] == 300
        assert d["budget"]["auto_retries"] == 0
        assert "DEEPSEEK_API_KEY" not in json.dumps(d, ensure_ascii=False)

    def test_dry_run_requires_no_key(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        assert smoke.main(["--mode", "dry-run"]) == 0


class TestLoopbackFullChain:
    def test_full_chain_attempts_equal_server_received(self, tmp_path):
        mock = helpers.MockChatServer([
            helpers.act_call("search_policy", {"query": "缓考"}),
            helpers.act_call("build_checklist_draft", {}),
            helpers.act_finish("【模拟】全部办理工作已完成"),
        ])
        try:
            out = tmp_path / "mock.json"
            code = smoke.main(["--mode", "mock", "--mock-base-url", mock.url(), "--out", str(out)])
            assert code == 0, "完整链 + 核对表全过 → 0"
            d = json.loads(out.read_text(encoding="utf-8"))
            run = d["run"]
            # 发送处计数 == 服务端接收数 == 循环计数（不按 plan_rounds 推算）
            assert run["http_observed_at_send"] == len(mock.requests) == run["planner_http_attempts"]
            assert run["status"] == "completed" and run["tool_calls_used"] == 2
            # 完整审计：逐轮 audit（缺失写 null）、结束语仅记录
            audits = [e.get("audit") for e in run["events"] if e.get("kind") == "plan_decision"]
            assert len(audits) == 3 and all(a is not None for a in audits)
            assert run.get("planner_summary") == "【模拟】全部办理工作已完成"
            # 核对表按实际动作给出结论
            rows = {c["item"]: c for c in d["checklist"]}
            assert rows["是否实际搜索"]["pass"] is True and "命中" in rows["是否实际搜索"]["observed"]
            assert rows["草稿是否存在且事项/条件正确"]["pass"] is True
            assert rows["引用是否与直接 service 相同"]["pass"] is True
            assert rows["是否有失败/提前 finish"]["pass"] is True
            # mock 标注 + 无密钥
            assert "mock 联调" in d["marking"] and "非真实冒烟" in d["marking"]
            assert "sk-smoke-mock-not-real" not in json.dumps(d, ensure_ascii=False)
        finally:
            mock.close()


class TestFailureNonZero:
    def test_early_finish_non_zero_keeps_evidence(self, tmp_path):
        mock = helpers.MockChatServer([
            helpers.act_call("search_policy", {"query": "缓考"}),
            helpers.act_finish("【模拟】全部办理工作已完成"),
        ])
        try:
            out = tmp_path / "early.json"
            code = smoke.main(["--mode", "mock", "--mock-base-url", mock.url(), "--out", str(out)])
            assert code == 1, "提前 finish 缺产物 → 非零退出"
            d = json.loads(out.read_text(encoding="utf-8"))
            run = d["run"]
            assert run["status"] == "partial" and run["results"]["draft"] is None
            assert run["results"]["search"] is not None, "保留已有检索证据"
            rows = {c["item"]: c for c in d["checklist"]}
            assert rows["草稿是否存在且事项/条件正确"]["pass"] is False
            assert rows["是否有失败/提前 finish"]["pass"] is False
            assert run["http_observed_at_send"] == len(mock.requests) == 2
        finally:
            mock.close()

    def test_technical_failure_non_zero_zero_retry(self, tmp_path):
        mock = helpers.MockChatServer([
            helpers.act_call("search_policy", {"query": "缓考"}),
            {"http_status": 500},
        ])
        try:
            out = tmp_path / "fail.json"
            code = smoke.main(["--mode", "mock", "--mock-base-url", mock.url(), "--out", str(out)])
            assert code == 1
            d = json.loads(out.read_text(encoding="utf-8"))
            run = d["run"]
            assert run["stop_reason"] == "planner_error"
            assert run["results"]["search"] is not None, "失败前证据保留"
            assert run["http_observed_at_send"] == 2 == run["planner_http_attempts"], "零重试"
            assert len(mock.requests) == 2
            assert d["exit_ok"] is False
        finally:
            mock.close()

    def test_truncated_response_keeps_audit_single_request(self, tmp_path):
        # T025-R1：带审计信封的 length 响应——失败轮 id/model/usage/finish_reason 保留
        mock = helpers.MockChatServer([
            {"content": '{"type": "finish", "summary": "x', "finish_reason": "length"},
        ])
        try:
            out = tmp_path / "trunc.json"
            code = smoke.main(["--mode", "mock", "--mock-base-url", mock.url(), "--out", str(out)])
            assert code == 1
            d = json.loads(out.read_text(encoding="utf-8"))
            run = d["run"]
            assert run["stop_reason"] == "planner_error"
            assert run["http_observed_at_send"] == 1 == run["planner_http_attempts"], "一次请求、无重试"
            assert len(mock.requests) == 1
            err_events = [e for e in run["events"] if e.get("kind") == "plan_error"]
            assert len(err_events) == 1
            audit = err_events[0].get("audit")
            assert audit is not None, "失败轮审计不得丢失"
            assert audit["request_id"] == "mock-1"
            assert audit["model"] == "mock-planner（模拟，非真实 DeepSeek）"
            assert audit["usage"] == {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
            assert audit["finish_reason"] == "length"
            assert audit["max_tokens"] == 300 and audit["latency_ms"] is not None
            # 不传播 headers/密钥/原始正文
            dumped = json.dumps(d, ensure_ascii=False)
            assert "Authorization" not in dumped and "sk-" not in dumped
        finally:
            mock.close()


class TestPreflightFailsWithoutRequests:
    def test_non_loopback_mock_url_rejected_zero_requests(self, tmp_path):
        out = tmp_path / "bad.json"
        code = smoke.main(["--mode", "mock", "--mock-base-url", "https://api.deepseek.com", "--out", str(out)])
        assert code == 1, "任意环境地址不得当成已授权目标"
        d = json.loads(out.read_text(encoding="utf-8"))
        assert d["run"] is None, "前置失败 → 零请求"
        assert any(r["pass"] is False and "loopback" in r["check"] for r in d["preflight"])

    def test_prefix_bypass_urls_rejected_zero_requests(self, tmp_path):
        # T025-R1：前缀绕过（完整主机名并非本地）必须拒绝，零请求非零退出
        for bad in ("http://127.0.0.1.example.invalid", "http://localhost@example.invalid"):
            out = tmp_path / "bypass.json"
            code = smoke.main(["--mode", "mock", "--mock-base-url", bad, "--out", str(out)])
            assert code == 1, f"应拒绝 {bad}"
            d = json.loads(out.read_text(encoding="utf-8"))
            assert d["run"] is None, f"{bad} 必须零请求"
            assert any(r["pass"] is False and "loopback" in r["check"] for r in d["preflight"])
        # 正常 loopback 仍接受（完整主机名解析）
        assert smoke._is_loopback_url("http://127.0.0.1:18080") is True
        assert smoke._is_loopback_url("http://localhost:18080") is True

    def test_live_without_key_fails_before_any_request(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
        monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
        out = tmp_path / "live.json"
        code = smoke.main(["--mode", "live", "--out", str(out)])
        assert code == 1
        d = json.loads(out.read_text(encoding="utf-8"))
        assert d["run"] is None, "零请求"
        assert any(r["pass"] is False and "密钥" in r["check"] for r in d["preflight"])
        # 环境变量名可出现在说明中；密钥值绝不可出现（本例无值）
        assert "key_present" in d["config"] and d["config"]["key_present"] is False
        assert "sk-" not in json.dumps(d, ensure_ascii=False)

    def test_live_with_nonofficial_base_url_rejected(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-not-real-for-test")
        monkeypatch.setenv("DEEPSEEK_BASE_URL", "http://127.0.0.1:9")
        try:
            out = tmp_path / "live2.json"
            code = smoke.main(["--mode", "live", "--out", str(out)])
            assert code == 1
            d = json.loads(out.read_text(encoding="utf-8"))
            assert d["run"] is None, "非官方地址零请求"
            assert any(r["pass"] is False and "官方端点" in r["check"] for r in d["preflight"])
        finally:
            monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)


class TestUsage:
    def test_argparse_errors_exit_2(self):
        with pytest.raises(SystemExit) as ei:
            smoke.main(["--mode", "mock"])  # 缺 --mock-base-url
        assert ei.value.code == 2
        with pytest.raises(SystemExit) as ei:
            smoke.main(["--mode", "dry-run", "--mock-base-url", "http://127.0.0.1:1"])
        assert ei.value.code == 2
