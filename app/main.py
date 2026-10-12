"""Voice Capture Inbox — FastAPI application.

Serves the single-page frontend and the capture API.
Pipeline: audio upload -> transcribe (ASR) -> classify -> store -> respond.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from .asr import TranscriptionUnavailable, transcribe
from .classify_gemini import classify
from .store import CaptureStore

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "captures.db"

store = CaptureStore(DB_PATH, AUDIO_DIR)

app = FastAPI(title="Voice Capture Inbox", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    store.init()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.post("/api/captures")
async def create_capture(file: UploadFile) -> JSONResponse:
    audio = await file.read()
    mime = file.content_type or "audio/webm"
    if not audio:
        return JSONResponse({"error": "empty upload"}, status_code=400)

    audio_path = store.save_audio(audio, mime)
    transcript: str | None = None
    cls: str | None = None
    note: str | None = None

    # ASR first; classification needs text. Each stage degrades gracefully.
    try:
        transcript = await transcribe(audio, mime)
    except TranscriptionUnavailable as exc:
        note = f"transcription unavailable: {exc}"
    else:
        try:
            cls = await classify(transcript)
        except Exception as exc:  # classifier must never 5xx the capture
            note = f"classification failed: {exc}"

    cap_id = store.add(audio_path=audio_path, mime=mime, transcript=transcript, cls=cls)
    status = "processed" if cls else "unprocessed"
    return JSONResponse(
        {
            "id": cap_id,
            "status": status,
            "transcript": transcript,
            "class": cls,
            "note": note,
            "created_at": store.get(cap_id).created_at if store.get(cap_id) else None,
        },
        status_code=201,
    )


@app.get("/api/captures")
def list_captures(limit: int = 50) -> list[dict]:
    return [row_to_dict(r) for r in store.list(limit=limit)]


@app.get("/api/captures/{cap_id}")
def get_capture(cap_id: int) -> JSONResponse:
    row = store.get(cap_id)
    if row is None:
        endpoint = f"/api/captures/{cap_id}"
        return JSONResponse({"error": f"not found: {endpoint}"}, status_code=404)
    return JSONResponse(row_to_dict(row))


def row_to_dict(row) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at,
        "audio_path": row.audio_path,
        "mime": row.mime,
            "transcript": row.transcript,
        "class": row.cls,
    }
