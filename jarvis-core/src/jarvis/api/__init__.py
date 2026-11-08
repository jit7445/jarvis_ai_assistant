"""Core's HTTP surface (Phase 10). Only the gateway calls it, with the shared secret."""
import hmac
import io
from collections.abc import Callable

import numpy as np
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from scipy.io.wavfile import read

from jarvis import config
from jarvis.core.proposal import to_intent
from jarvis.planner.prompt import ABOUT, system_prompt
from jarvis.speech import stt
from jarvis.tools.executor import execute
from jarvis.tools.registry import TOOLS, InvalidIntent

MAX_COMMAND_AUDIO_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARS = 2000


def create_app(token: str, port: int, run_command: Callable[[str], str]) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    @app.middleware("http")
    async def guard(request: Request, call_next):
        # Host check: a web page that rebinds its own name to 127.0.0.1 still sends its own Host.
        if request.headers.get("host") not in hosts:
            return JSONResponse({"error": "host"}, status_code=403)
        given = request.headers.get(config.TOKEN_HEADER, "")
        if not token or not hmac.compare_digest(given.encode(), token.encode()):
            return JSONResponse({"error": "token"}, status_code=401)
        length = int(request.headers.get("content-length") or 0)
        if length > MAX_COMMAND_AUDIO_BYTES:
            return JSONResponse({"error": "too large"}, status_code=413)
        return await call_next(request)

    @app.get("/health")
    def health():
        ready = stt.server is not None and stt.server.ready
        return {"ok": True, "whisper": "loaded" if ready else "on demand"}

    @app.get("/tools")
    def tools():
        return {"tools": {name: {"args": sorted(schema), "about": ABOUT.get(name, "")}
                          for name, schema in TOOLS.items()},
                "apps": sorted(config.ALLOWED_APPS), "prompt": system_prompt()}

    @app.post("/transcribe")
    async def transcribe(request: Request):
        body = await request.body()
        try:
            rate, audio = read(io.BytesIO(body))
        except (ValueError, EOFError):
            return JSONResponse({"error": "not a WAV file"}, status_code=415)
        audio = np.asarray(audio)
        if rate != config.SAMPLE_RATE or audio.dtype != np.int16:
            return JSONResponse({"error": "expected 16 kHz 16-bit WAV"}, status_code=415)
        if audio.ndim > 1:
            audio = audio[:, 0]
        text = await run_in_threadpool(stt.transcribe, audio)
        return {"text": text}

    @app.post("/execute")
    async def run(request: Request):
        try:
            proposal = await request.json()
            intent = to_intent(proposal)
        except (ValueError, InvalidIntent, PermissionError):
            return JSONResponse({"ok": False, "message": "Refused: not a valid tool call."},
                                status_code=422)
        if intent is None:
            return JSONResponse({"ok": False, "message": "No tool given."}, status_code=422)
        result = await run_in_threadpool(execute, intent)
        return {"ok": result.ok, "message": result.message,
                "needs_confirmation": result.needs_confirmation}

    @app.post("/command")
    async def command(request: Request):
        try:
            text = (await request.json()).get("text")
        except (ValueError, AttributeError):
            text = None
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS:
            return JSONResponse({"error": "text required"}, status_code=422)
        return {"reply": await run_in_threadpool(run_command, text.strip())}

    return app


def serve(app: FastAPI, port: int) -> None:
    """In a background thread, beside the AppKit run loop."""
    import threading

    import uvicorn
    server = uvicorn.Server(uvicorn.Config(app, host=config.LOCALHOST, port=port,
                                           log_level="warning", access_log=False))
    threading.Thread(target=server.run, daemon=True).start()
