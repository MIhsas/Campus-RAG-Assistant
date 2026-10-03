"""Tests for the unified run entry assembly and status truthfulness (T022).

Covers: defaults-off assembly, explicit feature injection only, generator
degrade messaging, zero generator calls on startup/status/extractive,
neutral vs demo home, and T021-R1 registration fixes (strict is_synthetic,
quoted startup command). No heavy models, no network.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"
PROCEDURES = BACKEND / "examples" / "procedures" / "procedures.json"
RULE = BACKEND / "examples" / "self-check" / "rule.json"

_spec = importlib.util.spec_from_file_location(
    "serve_corpus", BACKEND / "scripts" / "serve-corpus.py"
)
serve_corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve_corpus)


class CountingProvider:
    provider_id = "counting-stub（测试桩）"

    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return {"type": "insufficient_evidence", "reason": "桩返回：材料不足"}


def _build(**kw):
    return serve_corpus.build_app(
        manifest=PARSE_CORPUS / "manifest.json",
        corpus_root=PARSE_CORPUS,
        **kw,
    )


class TestAssemblyDefaults:
    def test_minimal_defaults_off(self):
        app, report = _build()
        c = TestClient(app, raise_server_exceptions=False)
        s = c.get("/api/v1/search/status").json()
        assert s["available_modes"] == ["bm25"]
        a = c.get("/api/v1/ask/status").json()
        assert a["generator_configured"] is False
        v = c.get("/api/v1/asr/status").json()
        assert v["configured"] is False
        assert c.get("/api/v1/procedures").status_code == 503
        assert c.get("/api/v1/self-check/rule").status_code == 503
        # 未隐式加载任何合成配置
        text = "\n".join(line for line, _ in report)
        assert "办事模板：未配置" in text and "自查规则：未配置" in text
        assert "生成器：未启用" in text

    def test_explicit_injection_only(self, tmp_path):
        app, report = _build(procedures=PROCEDURES, self_check=RULE)
        c = TestClient(app, raise_server_exceptions=False)
        assert c.get("/api/v1/procedures").status_code == 200
        assert c.get("/api/v1/self-check/rule").status_code == 200
        text = "\n".join(line for line, _ in report)
        assert "办事模板：已配置" in text and "自查规则：已配置" in text

    def test_missing_feature_config_degrades_explicitly(self, tmp_path):
        app, report = _build(
            embedding_model_dir=str(tmp_path / "no-model"),
            asr_model_dir=str(tmp_path / "no-asr"),
            procedures=tmp_path / "no.json",
            self_check=tmp_path / "no-rule.json",
        )
        text = "\n".join(line for line, _ in report)
        assert "已降级，仅 BM25" in text
        assert "文字提问仍可用" in text
        assert "办事模板：请求启用但文件不存在" in text
        assert "自查规则：请求启用但文件不存在" in text
        s = TestClient(app, raise_server_exceptions=False).get("/api/v1/search/status").json()
        assert s["available_modes"] == ["bm25"]


class TestGenerator:
    def test_generator_off_by_default_and_degrades_with_message(self):
        app, report = _build(generator="deepseek", provider_factory=lambda: None)
        text = "\n".join(line for line, _ in report)
        assert "请求启用但配置不完整" in text and "已降级" in text
        a = TestClient(app, raise_server_exceptions=False).get("/api/v1/ask/status").json()
        assert a["generator_configured"] is False

    def test_generator_zero_calls_until_explicit_generate(self):
        stub = CountingProvider()
        app, report = _build(generator="deepseek", provider_factory=lambda: stub)
        text = "\n".join(line for line, _ in report)
        assert "生成器：已配置" in text and "未验证服务连接" in text
        c = TestClient(app, raise_server_exceptions=False)
        # 启动后状态与摘录零生成调用
        c.get("/api/v1/ask/status")
        c.get("/api/v1/search/status")
        r = c.post("/api/v1/ask", json={"query": "缓考申请", "top_k": 5, "mode": "bm25", "answer_mode": "extractive"})
        assert r.status_code == 200 and r.json()["status"] == "evidence_only"
        assert stub.calls == 0, "启动/状态/摘录不得调用生成器"
        # 显式生成才可达
        g = c.post("/api/v1/ask", json={"query": "缓考申请", "top_k": 5, "mode": "bm25", "answer_mode": "generated"})
        assert g.status_code == 200
        assert stub.calls == 1
        assert "桩返回" in g.json()["insufficient_reason"]


class TestHomes:
    def test_neutral_home_vs_demo_home(self):
        app, _ = _build()
        home = TestClient(app, raise_server_exceptions=False).get("/")
        assert home.status_code == 200
        body = home.text
        assert "校园助手" in body
        assert "演示问题" not in body, "正常首页不得出现演示问题"
        assert "capability-status" in body

        app2, _ = serve_corpus.build_app(
            manifest=PARSE_CORPUS / "manifest.json",
            corpus_root=PARSE_CORPUS,
            demo_home=True,
        )
        demo = TestClient(app2, raise_server_exceptions=False).get("/")
        assert "演示问题" in demo.text, "演示入口保留演示问题"


class TestT021R1Fixes:
    def _register(self, tmp_path, meta):
        src = tmp_path / "doc.txt"
        src.write_text("内容", encoding="utf-8")
        meta_path = tmp_path / "meta.json"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        out = tmp_path / "pkg"
        proc = subprocess.run(
            [sys.executable, str(BACKEND / "scripts" / "register-corpus.py"),
             "--input", str(src), "--meta", str(meta_path), "--out-dir", str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(BACKEND),
        )
        return proc, out

    def _meta(self):
        return {
            "document_id": "x", "policy_group_id": "g", "title": "t",
            "source_url": "https://example.org/p", "source_site": "s",
            "version_label": "v", "published_at": None, "effective_from": None,
            "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": True,
        }

    def test_startup_command_quotes_paths(self, tmp_path):
        proc, out = self._register(tmp_path, self._meta())
        assert proc.returncode == 0
        assert '"--manifest "' not in proc.stdout  # sanity
        # 路径以引号包裹（项目根目录含空格）
        for line in proc.stdout.splitlines():
            if "serve-corpus.py" in line:
                assert '"--manifest"' not in line  # 参数名不加引号
                assert '--manifest "' in line and '--corpus-root "' in line

    def test_is_synthetic_strict_bool(self, tmp_path):
        for bad in ("false", 0, None):
            meta = self._meta()
            meta["is_synthetic"] = bad
            proc, out = self._register(tmp_path / f"case-{str(bad)}", meta) if False else self._register(tmp_path, meta)
            assert proc.returncode == 2, f"is_synthetic={bad!r} 应被拒绝"
            assert "is_synthetic 必须是 JSON 布尔值" in proc.stdout
            assert not out.exists()

    def test_is_synthetic_true_preserved(self, tmp_path):
        meta = self._meta()
        proc, out = self._register(tmp_path, meta)
        assert proc.returncode == 0
        m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert m["documents"][0]["is_synthetic"] is True
