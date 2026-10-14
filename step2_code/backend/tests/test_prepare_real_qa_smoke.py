"""Tests for prepare-real-qa-smoke.py (T040 A 阶段本地准备).

必要业务回归（不以条数为目标）：环境标志守卫、输出目录不覆盖、
messages 与 builder 一致且不塞 gold、零证据本地短路计划、
合成语料小闭环（extractive 证据包 + 未来 messages，零外部请求）。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare-real-qa-smoke.py"
_spec = importlib.util.spec_from_file_location("prepare_real_qa_smoke", _SCRIPT)
prep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prep)

from campus_assistant.qa.deepseek import build_messages  # noqa: E402


def test_guard_enable_flags_restores_env(monkeypatch):
    monkeypatch.setenv("CAMPUS_GENERATOR", "deepseek")
    monkeypatch.setenv("CAMPUS_PLANNER", "deepseek")
    monkeypatch.setenv("CAMPUS_ASR", "funasr")
    with prep.guard_enable_flags():
        assert "CAMPUS_GENERATOR" not in os.environ
        assert "CAMPUS_PLANNER" not in os.environ
        assert "CAMPUS_ASR" not in os.environ
    assert os.environ["CAMPUS_GENERATOR"] == "deepseek"
    assert os.environ["CAMPUS_PLANNER"] == "deepseek"
    assert os.environ["CAMPUS_ASR"] == "funasr"
    with pytest.raises(RuntimeError):
        with prep.guard_enable_flags():
            raise RuntimeError("boom")
    assert os.environ["CAMPUS_GENERATOR"] == "deepseek"


def test_write_outputs_refuses_nonempty_dir(tmp_path):
    out = tmp_path / "T040-A"
    out.mkdir()
    (out / "existing.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        prep.write_outputs(out, {"new.json": "{}"})
    assert (out / "existing.txt").read_text(encoding="utf-8") == "keep"


def test_messages_builder_consistent_and_no_gold_leak():
    question = {
        "question_id": "x1",
        "query": "考试纪律是什么？",
        "conditions": {"campus": None, "student_type": None, "admission_year": None, "as_of_date": None},
        "evidence": [
            {"fact_id": "f1", "document_id": "doc-a", "block_id": "b1", "char_start": 0, "char_end": 10,
             "quote": "作弊的定义原文"},
        ],
    }
    evidence = [
        {"evidence_id": "E1", "text": "带小抄属于作弊。", "document_id": "doc-a",
         "block_id": "b1", "char_start": 0, "char_end": 9},
    ]
    messages = build_messages(query=question["query"], evidence=evidence, filters=None)
    checks = prep.check_messages_clean(question, evidence, messages, build_messages, None)
    assert checks["builder_consistent"] and checks["gold_leaks"] == 0
    # gold quote（不在证据里）一旦出现在 messages 中必须判失败
    leaked = build_messages(
        query=question["query"],
        evidence=[{**evidence[0], "text": "作弊的定义原文"}],
        filters=None,
    )
    assert leaked[1]["content"].count("作弊的定义原文") == 1  # 在证据内——允许
    poisoned = [
        {"role": "system", "content": messages[0]["content"]},
        {"role": "user", "content": messages[1]["content"] + "\n补充：作弊的定义原文"},
    ]
    # 塞入 gold 会先被 builder 一致性守卫拒绝（与 build_messages 输出不一致）
    with pytest.raises(RuntimeError, match="不一致|gold"):
        prep.check_messages_clean(question, evidence, poisoned, build_messages, None)


def test_zero_evidence_plan_is_local_short_circuit():
    plan = prep.per_question_plan("u04", {"evidence": [], "evidence_state": "no_hits"})
    assert plan["planned_external_attempts"] == 0
    assert "本地短路" in plan["rule"]
    plan2 = prep.per_question_plan("q08", {"evidence": [{"evidence_id": "E1"}], "evidence_state": "ok"})
    assert plan2["planned_external_attempts"] == 1


def _write_corpus(tmp_path: Path) -> Path:
    content = "考试开始三十分钟后考生不得进入考场。\n携带小抄属于作弊行为。"
    fpath = tmp_path / "doc-a.txt"
    fpath.write_text(content, encoding="utf-8")
    sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "doc-a",
            "policy_group_id": "g1",
            "title": "考试纪律规定",
            "source_url": "https://example.org/a",
            "source_site": "测试站",
            "local_path": "doc-a.txt",
            "sha256": sha,
            "version_label": "v1",
            "published_at": "2019-11-07",
            "effective_from": "2019-11-07",
            "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": False,
        }],
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp


def test_mini_pipeline_extractive_and_messages(tmp_path):
    manifest_path = _write_corpus(tmp_path)
    create_app = prep.import_create_app()
    app = prep.build_app(create_app, manifest_path, tmp_path)
    from fastapi.testclient import TestClient

    client = TestClient(app)
    assert client.get("/api/v1/ask/status").json()["generator_configured"] is False
    question = {
        "question_id": "x2",
        "query": "迟到多久不得进入考场？",
        "conditions": {"campus": None, "student_type": None, "admission_year": None, "as_of_date": "2026-10-03"},
        "evidence": [],
    }
    got = prep.collect_extractive(client, question)
    api = got["response"]
    prep.check_frozen_consistency(question, api)
    blocks = prep.index_blocks(app)
    prep.check_evidence_slices(question, api["evidence"], blocks)
    # 合成资料混入守卫单独确认（真实包 dry-run 中 is_synthetic 必须为假）
    with pytest.raises(RuntimeError, match="合成"):
        prep.check_evidence_slices(
            question, [{**api["evidence"][0], "is_synthetic": True}], blocks
        )
    messages = build_messages(query=question["query"], evidence=api["evidence"], filters=dict(question["conditions"]))
    checks = prep.check_messages_clean(
        question, api["evidence"], messages, build_messages, dict(question["conditions"])
    )
    assert checks["builder_consistent"]
    assert api["status"] == "evidence_only" and api["evidence_state"] == "ok"
    assert api["evidence"], "合成语料应产生至少一条正式证据"
