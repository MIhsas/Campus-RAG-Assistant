"""Local ASR API endpoints (T020).

GET  /api/v1/asr/status      — provider/model/limits availability
POST /api/v1/asr/transcribe  — raw audio body (WAV / browser WebM-Opus)

Server-side hard limits: 5 MB input, 30 s decoded audio. Single
concurrency (busy → clear error). Inference runs in the thread pool so
the event loop is never blocked. Audio bytes and transcripts are used only
within the request — never persisted or logged. No cloud ASR, no paid
calls, no automatic model download: unconfigured → explicit 503.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from campus_assistant.asr.audio import MAX_AUDIO_BYTES, MAX_AUDIO_SECONDS
from campus_assistant.asr.adapter import ASRError
from campus_assistant.asr.audio import AudioError


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


NO_SPEECH_MESSAGE = "未识别到有效语音，请重录或重新选择音频"


def create_asr_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/asr", tags=["asr"])
    busy_lock = asyncio.Lock()

    def _adapter(request: Request):
        return getattr(request.app.state, "asr_adapter", None)

    @router.get("/status")
    async def asr_status(request: Request):
        adapter = _adapter(request)
        configured = adapter is not None
        return {
            "configured": configured,
            "provider": getattr(adapter, "provider", None) if configured else None,
            "model": getattr(adapter, "model_id", None) if configured else None,
            "limits": {
                "max_bytes": MAX_AUDIO_BYTES,
                "max_seconds": int(MAX_AUDIO_SECONDS),
            },
            "formats": ["wav", "webm/opus（浏览器 MediaRecorder 实际支持的格式）"],
            "note": "本地识别：仅从已配置本地模型目录加载，不自动下载，不调用云端 ASR。",
            "request_id": request.state.request_id,
        }

    @router.post(
        "/transcribe",
        responses={503: {"model": ErrorResponse}, 400: {"model": ErrorResponse},
                   409: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    )
    async def transcribe(request: Request):
        adapter = _adapter(request)
        if adapter is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "ASR_NOT_CONFIGURED",
                    "message": "本地语音识别未配置（可继续使用文字提问）",
                    "request_id": request.state.request_id,
                },
            )
        data = await request.body()
        if not data:
            return JSONResponse(
                status_code=400,
                content={"code": "AUDIO_EMPTY", "message": "未收到音频数据", "request_id": request.state.request_id},
            )
        if len(data) > MAX_AUDIO_BYTES:
            return JSONResponse(
                status_code=400,
                content={
                    "code": "AUDIO_TOO_LARGE",
                    "message": f"音频超过 {MAX_AUDIO_BYTES // (1024 * 1024)} MB 限制",
                    "request_id": request.state.request_id,
                },
            )

        if busy_lock.locked():
            return JSONResponse(
                status_code=409,
                content={"code": "ASR_BUSY", "message": "转写服务繁忙（单并发），请稍后再试",
                         "request_id": request.state.request_id},
            )

        from starlette.concurrency import run_in_threadpool

        async with busy_lock:
            try:
                result = await run_in_threadpool(adapter.transcribe, data)
            except AudioError as e:
                return JSONResponse(
                    status_code=400,
                    content={"code": "AUDIO_INVALID", "message": e.user_message,
                             "request_id": request.state.request_id},
                )
            except ASRError as e:
                return JSONResponse(
                    status_code=502,
                    content={"code": "ASR_EXECUTION_ERROR", "message": e.user_message,
                             "request_id": request.state.request_id},
                )
            except Exception as e:  # pragma: no cover - defensive
                return JSONResponse(
                    status_code=502,
                    content={
                        "code": "ASR_EXECUTION_ERROR",
                        "message": f"本地转写执行失败（{type(e).__name__}）",
                        "request_id": request.state.request_id,
                    },
                )

        text = result.get("text", "") or ""
        if not text.strip():
            # 空/空白转写结果：明确“未识别到有效语音”状态，页面不显示成功编辑器
            return {
                "status": "no_speech",
                "text": "",
                "message": "未识别到有效语音，请重录或重新选择音频",
                "provider": result.get("provider"),
                "model": result.get("model"),
                "duration_seconds": result.get("duration_seconds"),
                "elapsed_ms": result.get("elapsed_ms"),
                "confidence": result.get("confidence"),
                "request_id": request.state.request_id,
            }

        return {
            "status": "ok",
            "text": text,
            "provider": result.get("provider"),
            "model": result.get("model"),
            "duration_seconds": result.get("duration_seconds"),
            "elapsed_ms": result.get("elapsed_ms"),
            "confidence": result.get("confidence"),
            "request_id": request.state.request_id,
        }

    return router
