"""Real local ASR transcription evidence run (T020).

Loads the FunASR Paraformer adapter from an explicit local model directory
and transcribes one local audio file in-process. Records audio provenance
(hash/size), reference text, the RAW recognition output (typos kept —
never edited into "correct" text), model identity and timings.

Local CPU inference only — no cloud ASR, no paid calls, no audio upload.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-asr-transcribe.py \
        --model-dir .cache/asr-models/paraformer-zh \
        --audio .cache/t020-audio/tts-sample.wav \
        --reference "缓考申请须经所在学院批准，并报教务处备案。" \
        --audio-origin "本地 Windows TTS 合成（Microsoft Huihui Desktop, zh-CN），非真人录音"
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path


def _ensure_utf8_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") == "utf8":
        return
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="真实本地 ASR 转写取证（零外部调用）")
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--reference", default=None, help="参考文本（人工对照，不参与识别）")
    parser.add_argument("--audio-origin", default="未标注")
    parser.add_argument("--out", default=None, help="输出 JSON 路径（默认打印到 stdout）")
    args = parser.parse_args(argv)

    from campus_assistant.asr.adapter import FunASRParaformerAdapter

    audio_path = Path(args.audio)
    audio_bytes = audio_path.read_bytes()
    adapter = FunASRParaformerAdapter(args.model_dir)
    result = adapter.transcribe(audio_bytes)

    provenance_file = Path(args.model_dir) / "PROVENANCE.json"
    model_files = []
    if provenance_file.is_file():
        try:
            model_files = json.loads(provenance_file.read_text(encoding="utf-8")).get("files", [])
        except Exception:
            model_files = []

    out = {
        "evidence_kind": "真实本地 ASR 转写（FunASR Paraformer，Windows CPU）；零外部推理调用",
        "external_model_calls": 0,
        "audio": {
            "path": str(audio_path),
            "origin": args.audio_origin,
            "sha256": hashlib.sha256(audio_bytes).hexdigest(),
            "size_bytes": len(audio_bytes),
        },
        "reference_text": args.reference,
        "raw_recognition": {
            "text": result["text"],
            "note": "识别原始输出，保留实际错字；未做任何人工改正。",
        },
        "model": {
            "provider": result["provider"],
            "model_id": result["model"],
            "model_dir": args.model_dir,
            "provenance_files": model_files[:3],
        },
        "timing": {
            "audio_duration_seconds": result["duration_seconds"],
            "transcribe_elapsed_ms": result["elapsed_ms"],
        },
        "confidence": result["confidence"],
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
