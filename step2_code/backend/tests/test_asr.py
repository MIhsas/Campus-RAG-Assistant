"""Tests for the local ASR module and API (T020).

Covers: server-side limits (5MB / 30s), undecodable/empty audio, explicit
unconfigured behavior, marked-mock transcription response fields, busy
(409) and execution-error (502) mapping. Mock is explicitly injected and
marked — never the normal service path. No model downloads here.
"""

from __future__ import annotations

import asyncio
import io
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient

from campus_assistant.asr.adapter import ASRError, MockASRAdapter, asr_from_env
from campus_assistant.asr.audio import AudioError, decode_audio
from campus_assistant.main import create_app


def _wav_bytes(seconds: float = 1.0, freq: int = 440) -> bytes:
    rate = 16000
    t = np.arange(int(rate * seconds)) / rate
    pcm = (np.sin(2 * np.pi * freq * t) * 0.3 * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _silent_wav_bytes(seconds: float = 1.0) -> bytes:
    rate = 16000
    pcm = np.zeros(int(rate * seconds), dtype="<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class TestAudioDecode:
    def test_wav_decodes_with_duration(self):
        waveform, duration = decode_audio(_wav_bytes(1.5))
        assert abs(duration - 1.5) < 0.05
        assert waveform.dtype == np.float32

    def test_empty_and_undecodable(self):
        with pytest.raises(AudioError, match="音频为空"):
            decode_audio(b"")
        with pytest.raises(AudioError, match="无法解码"):
            decode_audio(b"not audio data at all")

    def test_size_limit(self):
        big = b"\x00" * (5 * 1024 * 1024 + 1)
        with pytest.raises(AudioError, match="MB"):
            decode_audio(big)

    def test_duration_limit(self):
        with pytest.raises(AudioError, match="秒限制"):
            decode_audio(_wav_bytes(31.0))

    def test_digital_silence_rejected_before_model(self):
        # T020-R1：解码后、推理前拦截静音——不进入识别路径
        adapter = MockASRAdapter()
        with pytest.raises(AudioError, match="静音"):
            adapter.transcribe(_silent_wav_bytes(1.0))
        assert adapter.calls == 0, "静音不得进入识别逻辑"
        with pytest.raises(AudioError, match="未识别到有效语音"):
            decode_audio(_silent_wav_bytes(1.0))


class TestAsrApi:
    def _client(self, adapter) -> TestClient:
        return TestClient(create_app(asr_adapter=adapter), raise_server_exceptions=False)

    def test_not_configured_503(self):
        c = self._client(None)
        st = c.get("/api/v1/asr/status").json()
        assert st["configured"] is False
        r = c.post("/api/v1/asr/transcribe", content=_wav_bytes())
        assert r.status_code == 503
        assert r.json()["code"] == "ASR_NOT_CONFIGURED"
        assert "可继续使用文字提问" in r.json()["message"]

    def test_marked_mock_transcribe_fields(self):
        adapter = MockASRAdapter(text="【模拟转写】测试。")
        c = self._client(adapter)
        st = c.get("/api/v1/asr/status").json()
        assert st["configured"] is True
        assert "mock" in st["provider"]
        assert st["limits"]["max_bytes"] == 5 * 1024 * 1024
        assert st["limits"]["max_seconds"] == 30
        r = c.post("/api/v1/asr/transcribe", content=_wav_bytes(2.0))
        assert r.status_code == 200
        d = r.json()
        assert d["text"] == "【模拟转写】测试。"
        assert "mock" in d["provider"]
        assert abs(d["duration_seconds"] - 2.0) < 0.05
        assert d["elapsed_ms"] >= 0
        assert d["confidence"] is None  # 不伪造置信度

    def test_audio_errors_400(self):
        c = self._client(MockASRAdapter())
        assert c.post("/api/v1/asr/transcribe", content=b"").status_code == 400
        r = c.post("/api/v1/asr/transcribe", content=b"garbage bytes")
        assert r.status_code == 400
        assert "解码" in r.json()["message"]
        r2 = c.post("/api/v1/asr/transcribe", content=_wav_bytes(31.0))
        assert r2.status_code == 400
        assert "秒限制" in r2.json()["message"]

    def test_execution_error_502(self):
        c = self._client(MockASRAdapter(fail=True))
        r = c.post("/api/v1/asr/transcribe", content=_wav_bytes())
        assert r.status_code == 502
        assert r.json()["code"] == "ASR_EXECUTION_ERROR"

    def test_silent_audio_rejected_400(self):
        c = self._client(MockASRAdapter())
        r = c.post("/api/v1/asr/transcribe", content=_silent_wav_bytes())
        assert r.status_code == 400
        assert "未识别到有效语音" in r.json()["message"]

    def test_empty_transcription_is_no_speech(self):
        # T020-R1：空/空白转写结果 → 明确 no_speech 状态，不是成功
        for blank in ("", "   ", "\n\t"):
            c = self._client(MockASRAdapter(text=blank))
            r = c.post("/api/v1/asr/transcribe", content=_wav_bytes())
            assert r.status_code == 200
            d = r.json()
            assert d["status"] == "no_speech"
            assert d["text"] == ""
            assert "未识别到有效语音" in d["message"]

    def test_busy_409_single_concurrency(self):
        adapter = MockASRAdapter(delay_s=0.5)
        c = self._client(adapter)
        import threading

        statuses = []
        def call():
            r = c.post("/api/v1/asr/transcribe", content=_wav_bytes())
            statuses.append(r.status_code)
        threads = [threading.Thread(target=call) for _ in range(2)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert 200 in statuses and 409 in statuses


class TestConfig:
    def test_asr_from_env_gating(self, tmp_path):
        assert asr_from_env({}) is None
        assert asr_from_env({"CAMPUS_ASR": "funasr"}) is None
        assert asr_from_env({"CAMPUS_ASR": "funasr", "CAMPUS_ASR_MODEL_DIR": str(tmp_path / "nope")}) is None
        tmp_path.mkdir(exist_ok=True)
        adapter = asr_from_env({"CAMPUS_ASR": "funasr", "CAMPUS_ASR_MODEL_DIR": str(tmp_path)})
        assert adapter is not None
        assert adapter.provider == "funasr-paraformer"
