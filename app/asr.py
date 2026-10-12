"""ASR via the Gemini API. If no GEMINI_API_KEY is set (or the call fails),
raises TranscriptionUnavailable so the caller can degrade gracefully —
the capture is still stored, just unprocessed.
"""

from __future__ import annotations

import asyncio
import os

from google import genai
from google.genai import types


class TranscriptionUnavailable(RuntimeError):
    """Raised when transcription cannot run (no API key, API error, empty result)."""


async def transcribe(audio: bytes, mime: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise TranscriptionUnavailable("GEMINI_API_KEY not set")

    try:
        client = genai.Client(api_key=api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[
                "Transcribe this audio recording verbatim. Reply with the transcript only.",
                types.Part.from_bytes(data=audio, mime_type=mime),
            ],
        )
    except Exception as exc:
        raise TranscriptionUnavailable(f"gemini api error: {exc}") from exc

    text = (response.text or "").strip()
    if not text:
        raise TranscriptionUnavailable("empty transcription result")
    return text
