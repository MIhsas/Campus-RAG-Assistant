"""Audio decoding and limits for local ASR (T020).

Decode browser-captured audio (WAV, WebM/Opus and other PyAV-readable
formats) to 16 kHz mono float32 in memory. Hard limits are enforced
server-side: 5 MB input, 30 seconds decoded audio. Nothing is written to
disk here and nothing is logged.
"""

from __future__ import annotations

import io

import numpy as np

MAX_AUDIO_BYTES = 5 * 1024 * 1024
MAX_AUDIO_SECONDS = 30.0
TARGET_SAMPLE_RATE = 16000
# 保守静音阈值：峰值低于约 -60 dBFS 判为静音/几乎无声。只拦截明显静音
# （含数字静音），不要求可靠噪声分类，也不解决模型全部幻觉问题。
SILENCE_PEAK_THRESHOLD = 1e-3


class AudioError(Exception):
    """Safe Chinese message for audio problems."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def decode_audio(data: bytes) -> tuple[np.ndarray, float]:
    """Decode compressed/wave audio bytes to (16k mono float32, duration_s)."""
    if not data:
        raise AudioError("音频为空，无法转写")
    if len(data) > MAX_AUDIO_BYTES:
        raise AudioError(f"音频超过 {MAX_AUDIO_BYTES // (1024 * 1024)} MB 限制")
    try:
        import av
    except ImportError as e:  # pragma: no cover
        raise AudioError("服务端缺少音频解码组件（PyAV）") from e

    try:
        with av.open(io.BytesIO(data), mode="r") as container:
            audio_stream = next((s for s in container.streams if s.type == "audio"), None)
            if audio_stream is None:
                raise AudioError("无法解码音频（未找到音频流）")
            resampler = av.AudioResampler(
                format="fltp", layout="mono", rate=TARGET_SAMPLE_RATE
            )
            chunks = []
            for frame in container.decode(audio_stream):
                for out_frame in resampler.resample(frame):
                    chunks.append(out_frame.to_ndarray().reshape(-1))
            tail = resampler.resample(None) if hasattr(resampler, "resample") else []
            for out_frame in (tail or []):
                chunks.append(out_frame.to_ndarray().reshape(-1))
    except AudioError:
        raise
    except Exception as e:
        raise AudioError("无法解码音频（格式不支持或文件损坏）") from e

    if not chunks:
        raise AudioError("无法解码音频（没有可解码的音频帧）")
    waveform = np.concatenate(chunks).astype(np.float32, copy=False)
    duration = float(len(waveform)) / TARGET_SAMPLE_RATE
    if duration <= 0:
        raise AudioError("音频时长为 0，无法转写")
    if duration > MAX_AUDIO_SECONDS:
        raise AudioError(f"音频时长 {duration:.1f} 秒，超过 {MAX_AUDIO_SECONDS:.0f} 秒限制")
    # 解码后、推理前拦截静音（含数字静音）——无有效语音不进入模型
    peak = float(np.max(np.abs(waveform))) if waveform.size else 0.0
    if peak < SILENCE_PEAK_THRESHOLD:
        raise AudioError("音频为静音，未识别到有效语音，请重录或重新选择音频")
    return waveform, duration
