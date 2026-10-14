"""Tests for live-smoke-real-qa.py (T040 B 单次执行入口).

少量本地 mock 业务回归（不以条数为目标）：发送位置计数与预算、
首次技术失败即停、业务不足可继续、前置不符零请求、完整记录。
全部 mock 注入（FakeClient），零网络；mock 不冒充真实生成质量。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "live-smoke-real-qa.py"
_spec = importlib.util.spec_from_file_location("live_smoke_real_qa", _SCRIPT)
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)

from campus_assistant.qa.deepseek import DeepSeekAnswerProvider  # noqa: E402


def _answer_content(text="回答段落", ids=("E1",)):
    return json.dumps({"type": "answer", "paragraphs": [{"text": text, "evidence_ids": list(ids)}]}, ensure_ascii=False)


def _insufficient_content():
    return json.dumps({"type": "insufficient_evidence", "reason": "材料不足"}, ensure_ascii=False)


class _FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    """DeepSeekAnswerProvider 的注入式 client；按脚本返回响应或抛连接错误。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(url)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _deepseek_ok(status="answer"):
    content = _answer_content() if status == "answer" else _insufficient_content()
    return _FakeResp(200, {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "model": "deepseek-flash", "id": "req-mock", "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    })


QUESTIONS = {
    qid: {"question_id": qid, "query": "考试纪律", "conditions": {"campus": None, "student_type": None, "admission_year": None, "as_of_date": None}}
    for qid in smoke.QUESTION_ORDER
}


def _make_app(client_script):
    """合成语料 + 注入 mock provider 的 app（零网络）。"""
    import tempfile, os
    from fastapi.testclient import TestClient

    tmp = Path(tempfile.mkdtemp())
    content = "考试纪律说明与成绩评定办法。"
    fpath = tmp / "doc.txt"
    fpath.write_text(content, encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "doc-mock", "policy_group_id": "g", "title": "测试资料",
            "source_url": "https://example.org/m", "source_site": "测试", "local_path": "doc.txt",
            "sha256": hashlib.sha256(fpath.read_bytes()).hexdigest(), "version_label": "v1",
            "published_at": None, "effective_from": None, "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []}, "is_synthetic": False,
        }],
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    fake = _FakeClient(client_script)
    inner, counting = smoke.build_counting_provider(
        api_key="sk-test-placeholder", inner_client=fake,
    )
    recording = smoke.AttemptRecordingProvider(inner, counting)
    create_app = smoke.import_create_app()
    app = create_app(
        manifest_path=tmp / "manifest.json", corpus_root=tmp,
        embedding_model_path=None, answer_provider=recording,
        procedures_path=None, self_check_path=None, asr_adapter=None, planner=None,
    )
    return TestClient(app), recording, fake, tmp


def test_attempt_counting_and_fail_stop():
    import httpx

    client, recording, fake, _ = _make_app([
        _FakeResp(500, {}),  # 第一次：HTTP 技术失败
    ])
    out = smoke.execute_live_loop(client=client, recording=recording, questions=QUESTIONS)
    assert recording.external_http_attempts == 1  # 发送位置计数；连接/HTTP 失败同样占用
    assert out["questions"]["q08"]["outcome"] == "technical_failure"
    assert out["questions"]["q10"]["outcome"] == "not_attempted"
    assert out["questions"]["u03"]["outcome"] == "not_attempted"
    assert out["questions"]["u04"]["outcome"] == "not_attempted"
    assert out["exit_ok"] is False
    assert out["stop"]["reason"].startswith("技术失败即停（q08）")
    assert out["attempt_log"][0]["supplier_http_status"] == 500

    # 连接错误同样消耗一次尝试
    client2, recording2, _, _ = _make_app([httpx.ConnectError("mock-refused")])
    out2 = smoke.execute_live_loop(client=client2, recording=recording2, questions=QUESTIONS)
    assert recording2.external_http_attempts == 1
    assert out2["questions"]["q08"]["outcome"] == "technical_failure"
    assert out2["attempt_log"][0]["supplier_http_status"] is None  # 未观察到供应商状态 → null
    assert out2["questions"]["q10"]["outcome"] == "not_attempted"


def test_business_insufficient_continues_and_answers_recorded():
    client, recording, fake, _ = _make_app([
        _deepseek_ok("insufficient"),
        _deepseek_ok("answer"),
        _deepseek_ok("insufficient"),
        _deepseek_ok("answer"),
    ])
    out = smoke.execute_live_loop(client=client, recording=recording, questions=QUESTIONS)
    assert out["questions"]["q08"]["outcome"] == "business_insufficient"  # 业务不足可继续
    assert out["questions"]["q10"]["outcome"] == "answered"
    assert out["questions"]["u03"]["outcome"] == "business_insufficient"
    assert out["questions"]["u04"]["outcome"] == "answered"
    assert recording.external_http_attempts == 4
    assert out["exit_ok"] is True and out["stop"]["reason"] == "completed_all"
    # 完整记录：paragraph→E 映射、generation_meta、本地/供应商状态分开
    answered = out["questions"]["q10"]
    assert answered["paragraphs"][0]["evidence_ids"] == ["E1"]
    assert answered["paragraphs"][0]["citations"][0]["evidence_id"] == "E1"
    assert answered["generation_meta"]["model"] == "deepseek-flash"
    assert answered["local_http_status"] == 200 and answered["supplier_http_status"] == 200
    assert answered["attempts"] == 1


def test_preflight_rejects_without_requests(tmp_path):
    # 最小语料与题集；A 材料故意缺失 → 前置失败必须零外部请求
    content = "考试纪律说明与成绩评定办法。"
    fpath = tmp_path / "doc.txt"
    fpath.write_text(content, encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "doc-mock", "policy_group_id": "g", "title": "测试资料",
            "source_url": "https://example.org/m", "source_site": "测试", "local_path": "doc.txt",
            "sha256": hashlib.sha256(fpath.read_bytes()).hexdigest(), "version_label": "v1",
            "published_at": None, "effective_from": None, "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []}, "is_synthetic": False,
        }],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    qpath = tmp_path / "questions.json"
    qpath.write_text(json.dumps({
        "questions": [
            {"question_id": qid, "query": f"问题{qid}", "conditions": v["conditions"]}
            for qid, v in QUESTIONS.items()
        ]
    }, ensure_ascii=False), encoding="utf-8")

    fake = _FakeClient([])  # 若被调用会立即耗尽脚本；断言零请求
    inner, counting = smoke.build_counting_provider(api_key="sk-test-placeholder", inner_client=fake)
    recording = smoke.AttemptRecordingProvider(inner, counting)
    result, ok = smoke.run_b(
        live=True, a_dir=tmp_path / "no-a-dir", out_dir=None,
        questions_path=qpath, corpus_root=tmp_path,
        provider_factory=lambda: inner,
        require_official_config=False,
        a_rev1_dir=tmp_path / "no-rev1", cache_a_dir=tmp_path / "no-cache",
        emit=lambda *_: None,
    )
    assert ok is False
    assert recording.external_http_attempts == 0 and fake.calls == []  # 前置失败零请求
    assert result["preflight"]["a_identity_ok"] is False

    # 非官方目标：官方门拒绝
    evil = DeepSeekAnswerProvider("sk-test-placeholder", base_url="http://evil.example", client=fake)
    cfg = smoke.check_official_config(smoke.resolve_config(evil))
    assert cfg["ok"] is False and "endpoint" in cfg["reason"]


def test_zero_evidence_short_circuit_costs_no_attempt():
    # conditions 使准入集合为空 → 零证据本地短路
    q_empty = {
        "q08": {"query": "问题", "conditions": {"campus": None, "student_type": "不存在类型", "admission_year": None, "as_of_date": None}},
        "q10": {"query": "问题", "conditions": {"campus": None, "student_type": "不存在类型", "admission_year": None, "as_of_date": None}},
        "u03": {"query": "问题", "conditions": {"campus": None, "student_type": "不存在类型", "admission_year": None, "as_of_date": None}},
        "u04": {"query": "问题", "conditions": {"campus": None, "student_type": "不存在类型", "admission_year": None, "as_of_date": None}},
    }
    client, recording, fake, _ = _make_app([])
    out = smoke.execute_live_loop(client=client, recording=recording, questions=q_empty)
    assert recording.external_http_attempts == 0  # 零证据不计外部尝试
    assert out["questions"]["q08"]["outcome"] == "local_short_circuit"
    assert out["exit_ok"] is True


def test_output_gate_refuses_before_any_send(tmp_path):
    """必修1 业务链：非空输出目录 + 可用 mock → 调用前拒绝、实际 post=0、旧文件不变。"""
    content = "考试纪律说明与成绩评定办法。"
    fpath = tmp_path / "doc.txt"
    fpath.write_text(content, encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "doc-mock", "policy_group_id": "g", "title": "测试资料",
            "source_url": "https://example.org/m", "source_site": "测试", "local_path": "doc.txt",
            "sha256": hashlib.sha256(fpath.read_bytes()).hexdigest(), "version_label": "v1",
            "published_at": None, "effective_from": None, "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []}, "is_synthetic": False,
        }],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    qpath = tmp_path / "questions.json"
    qpath.write_text(json.dumps({
        "questions": [
            {"question_id": qid, "query": f"问题{qid}", "conditions": v["conditions"]}
            for qid, v in QUESTIONS.items()
        ]
    }, ensure_ascii=False), encoding="utf-8")

    out_dir = tmp_path / "existing"
    out_dir.mkdir()
    sentinel = out_dir / "previous.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    fake = _FakeClient([_deepseek_ok() for _ in range(4)])
    inner, counting = smoke.build_counting_provider(api_key="sk-test-placeholder", inner_client=fake)

    with pytest.raises(RuntimeError, match="拒绝覆盖"):
        smoke.run_b(
            live=True, a_dir=tmp_path / "a", out_dir=out_dir,
            questions_path=qpath, corpus_root=tmp_path,
            provider_factory=lambda: inner, emit=lambda *_: None,
        )
    assert fake.calls == [] and counting.posts == 0          # 调用前拒绝，实际 post=0
    assert sentinel.read_text(encoding="utf-8") == "preserve"  # 旧文件不变
    assert not (out_dir / "live-results.json").exists()        # 未写新审计


def test_presend_failure_zero_post_zero_count():
    """必修2 业务链：发送前消息构造失败 → 实际 post=0、外部计数=0。"""
    from unittest.mock import patch

    client, recording, fake, _ = _make_app([])
    with patch("campus_assistant.qa.deepseek.build_messages", side_effect=RuntimeError("mock pre-send failure")):
        out = smoke.execute_live_loop(client=client, recording=recording, questions=QUESTIONS)
    assert fake.calls == []                        # 实际 post=0
    assert recording.external_http_attempts == 0   # 发送前本地异常计 0
    assert recording.provider_calls == 1           # provider 调用另列
    assert out["questions"]["q08"]["outcome"] == "technical_failure"
    assert out["questions"]["q08"]["attempts"] == 0
    assert out["questions"]["q10"]["outcome"] == "not_attempted"  # 失败即停
    assert out["exit_ok"] is False
