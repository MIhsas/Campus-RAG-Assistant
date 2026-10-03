"""Tests for the unified campus demo entry (T018).

Covers: combined corpus preserves original document IDs/contents/hashes and
stays parseable; ID conflicts abort explicitly; the unified app serves all
routes with the marked mock generator (never the real generator config);
procedures template citations validate against the combined corpus.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app

BACKEND = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "demo_campus", BACKEND / "scripts" / "demo-campus.py"
)
demo_campus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo_campus)


@pytest.fixture()
def combined(tmp_path):
    return demo_campus.build_combined_corpus(tmp_path / "combined")


class TestCombinedCorpus:
    def test_ids_and_hashes_preserved(self, combined):
        sources = {}
        for src in demo_campus.SOURCES:
            manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
            for e in manifest["documents"]:
                sources[e["document_id"]] = e
        out_manifest = json.loads((combined / "manifest.json").read_text(encoding="utf-8"))
        out_ids = {e["document_id"] for e in out_manifest["documents"]}
        assert out_ids == set(sources)
        for e in out_manifest["documents"]:
            assert e["sha256"] == sources[e["document_id"]]["sha256"]
            # 文件内容逐字节一致
            data = (combined / e["local_path"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == e["sha256"]

    def test_parseable_and_sources_untouched(self, combined):
        from campus_assistant.corpus.parse import parse_manifest

        r = parse_manifest(combined / "manifest.json", combined)
        assert r["valid"]
        assert len(r["documents"]) == 5  # 2 parse + 3 comparison
        # 源夹具未被修改（manifest 仍在原处且可解析）
        for src in demo_campus.SOURCES:
            assert (src / "manifest.json").is_file()

    def test_id_conflict_aborts_explicitly(self, tmp_path):
        a = tmp_path / "src-a"
        b = tmp_path / "src-b"
        for d in (a, b):
            d.mkdir()
            (d / "x.txt").write_text("内容", encoding="utf-8")
        entry = {
            "document_id": "dup-id", "policy_group_id": "g", "title": "t",
            "source_url": "https://example.org/p", "source_site": "s",
            "local_path": "x.txt",
            "sha256": hashlib.sha256((d / "x.txt").read_bytes()).hexdigest(),
            "version_label": "v", "published_at": None, "effective_from": None,
            "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": True,
        }
        for d in (a, b):
            (d / "manifest.json").write_text(
                json.dumps({"schema_version": "1.0", "documents": [entry]}), encoding="utf-8"
            )
        old = demo_campus.SOURCES
        demo_campus.SOURCES = [a, b]
        try:
            with pytest.raises(SystemExit, match="ID 冲突"):
                demo_campus.build_combined_corpus(tmp_path / "out")
        finally:
            demo_campus.SOURCES = old


class TestUnifiedApp:
    def test_all_routes_and_marked_mock(self, tmp_path, combined):
        app = create_app(
            manifest_path=combined / "manifest.json",
            corpus_root=combined,
            answer_provider=demo_campus.CampusMockProvider(),
            procedures_path=BACKEND / "examples" / "procedures" / "procedures.json",
        )
        c = TestClient(app, raise_server_exceptions=False)
        for path in ["/", "/ask", "/search", "/procedures", "/compare", "/preview"]:
            assert c.get(path).status_code == 200, path
        st = c.get("/api/v1/ask/status").json()
        assert st["generator_configured"] is True
        assert "mock" in (st["generator_identity"] or "")
        # 模板引用在组合语料上通过校验（2024 缓考草稿可保存）
        draft = c.post("/api/v1/procedures/proc-apply-defer/draft",
                       json={"filters": {"admission_year": 2024}}).json()
        assert draft["saveable"] is True
        # 版本对比在组合语料上可用
        groups = c.get("/api/v1/comparison/groups").json()["groups"]
        assert {g["policy_group_id"] for g in groups} >= {"syn-cmp-defer", "syn-cmp-grades"}
        # mock 生成带标记
        ask = c.post("/api/v1/ask", json={
            "query": "缓考申请须由谁批准？", "top_k": 5, "mode": "bm25",
            "answer_mode": "generated", "filters": {"admission_year": 2023},
        }).json()
        assert ask["status"] == "generated"
        assert "【模拟输出，非真实 DeepSeek 回答】" in ask["answer"]["paragraphs"][0]["text"]

    def test_demo_entry_source_uses_mock_only(self):
        """文档性检查：演示脚本源码不含真实生成器配置读取。

        这是源码字符串检查，不是运行时隔离证明；运行时隔离以演示 app
        显式注入 mock 且不向真实服务发请求为准（见 demo-campus.py）。
        """
        src = (BACKEND / "scripts" / "demo-campus.py").read_text(encoding="utf-8")
        assert "provider_from_env" not in src
        assert "CAMPUS_GENERATOR" not in src
        assert "DEEPSEEK_API_KEY" not in src
