"""ASR adapters (T020): FunASR Paraformer local, plus a marked mock.

FunASRParaformerAdapter loads exclusively from a configured local model
directory — no automatic download, no network calls, no cloud ASR. An
unconfigured service reports itself unavailable (ASR_NOT_CONFIGURED).

The MockASRAdapter is for tests only: it must be explicitly injected,
always identifies itself as mock, and never enters the normal service
default path.

Transcription results report text, actual provider/model, audio duration
and elapsed time. Confidence is not invented when the backend provides
none.
"""

from __future__ import annotations

import tempfile
import time
import wave
from pathlib import Path
from typing import Any

from campus_assistant.asr.audio import TARGET_SAMPLE_RATE, decode_audio


class ASRError(Exception):
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def _wav_bytes(waveform, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    """Wrap a float32 mono waveform as 16-bit PCM WAV bytes (in memory)."""
    import io

    import numpy as np

    pcm = np.clip(waveform, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class FunASRParaformerAdapter:
    """Local FunASR + Paraformer zh adapter (Windows CPU)."""

    provider = "funasr-paraformer"

    def __init__(self, model_dir: str | Path):
        model_path = Path(model_dir)
        if not model_path.is_dir():
            raise ValueError(f"ASR 模型目录不存在：{model_path.name}")
        self._model_dir = model_path
        self._model_id = None
        self._model = None

    @property
    def model_id(self) -> str:
        if self._model_id is None:
            # 来源标识：目录内 PROVENANCE.json（逐文件哈希清单）摘要；无清单
            # 时退回目录名并标注来源未核实。不猜 revision。
            provenance = self._model_dir / "PROVENANCE.json"
            if provenance.is_file():
                import hashlib

                digest = hashlib.sha256(provenance.read_bytes()).hexdigest()[:12]
                self._model_id = f"paraformer-zh@provenance-{digest}"
            else:
                self._model_id = f"paraformer-zh@{self._model_dir.name}(来源未核实)"
        return self._model_id

    @property
    def model_dir(self) -> Path:
        return self._model_dir

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from funasr import AutoModel
        except Exception as e:
            raise ASRError(f"本地识别组件加载失败（{type(e).__name__}）") from e
        try:
            # 仅从本地目录加载；不触发任何自动下载
            self._model = AutoModel(
                model=str(self._model_dir), device="cpu", disable_update=True
            )
        except Exception as e:
            raise ASRError(f"本地模型加载失败（{type(e).__name__}）") from e

    def transcribe(self, audio_bytes: bytes) -> dict[str, Any]:
        waveform, duration = decode_audio(audio_bytes)
        self._ensure_loaded()
        started = time.monotonic()
        # Windows 上 libsndfile 打不开被进程持有的临时文件：写完关闭再交给
        # 后端，结束/失败均删除，不保留音频。
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        try:
            tmp.write(_wav_bytes(waveform))
            tmp.close()
            results = self._model.generate(input=str(tmp_path), batch_size_s=0)
        except Exception as e:
            raise ASRError(f"本地转写执行失败（{type(e).__name__}）") from e
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        elapsed_ms = int((time.monotonic() - started) * 1000)
        text = ""
        if results:
            text = (results[0] or {}).get("text", "") or ""
        return {
            "text": text,
            "provider": self.provider,
            "model": self.model_id,
            "duration_seconds": round(duration, 3),
            "elapsed_ms": elapsed_ms,
            "confidence": None,  # 后端未提供可靠置信度，不伪造
        }


class MockASRAdapter:
    """Explicitly-injected marked mock for tests — never a normal service path."""

    provider = "mock-asr（模拟，非真实识别）"

    def __init__(self, text: str = "【模拟转写】测试文本。", fail: bool = False, delay_s: float = 0.0):
        self._text = text
        self._fail = fail
        self._delay_s = delay_s
        self.calls = 0

    @property
    def model_id(self) -> str:
        return "mock-asr-model"

    def transcribe(self, audio_bytes: bytes) -> dict[str, Any]:
        # 解码/静音门先于任何“识别”动作——静音不进入模型路径
        waveform, duration = decode_audio(audio_bytes)
        self.calls += 1
        if self._delay_s:
            time.sleep(self._delay_s)
        if self._fail:
            raise ASRError("本地转写执行失败（模拟失败）")
        return {
            "text": self._text,
            "provider": self.provider,
            "model": self.model_id,
            "duration_seconds": round(duration, 3),
            "elapsed_ms": 0,
            "confidence": None,
        }


def asr_from_env(environ=None) -> FunASRParaformerAdapter | None:
    """Explicit enable + local model dir → adapter. Never downloads.

    CAMPUS_ASR=funasr 且 CAMPUS_ASR_MODEL_DIR 指向存在的本地目录时启用。
    """
    import os

    env = os.environ if environ is None else environ
    if env.get("CAMPUS_ASR", "").strip().lower() != "funasr":
        return None
    model_dir = env.get("CAMPUS_ASR_MODEL_DIR", "").strip()
    if not model_dir:
        return None
    if not Path(model_dir).is_dir():
        return None
    return FunASRParaformerAdapter(model_dir)
