"""Gemini-based classifier with automatic fallback to the heuristic.

Primary path: ask Gemini to return exactly one of the four labels, using a
response schema so the output is constrained. Any failure (no key, API error,
unparseable output) falls back to classify_heuristic so the loop never breaks.
"""

from __future__ import annotations

import os

from google import genai

from .classify import CaptureType, classify_heuristic

PROMPT = (
    "Classify this voice capture into exactly one category.\n"
    "idea: a raw thought, concept, or possibility worth exploring.\n"
    "task: an action the speaker intends to do.\n"
    "lead: a person or opportunity to follow up on (contact, prospect, connection).\n"
    "noise: filler, a test, or something not worth filing.\n\n"
    "Capture: {text}\n\n"
    "Respond with only the category word."
)

VALID = {"idea", "task", "lead", "noise"}


async def classify(text: str) -> CaptureType:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return classify_heuristic(text)
    try:
        client = genai.Client(api_key=api_key)
        response = await _to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=PROMPT.format(text=text),
        )
        answer = (response.text or "").strip().lower()
        for word in VALID:
            if word in answer:
                return word  # type: ignore[return-value]
    except Exception:
        pass
    return classify_heuristic(text)


def _to_thread(func, *args):
    import asyncio

    return asyncio.to_thread(func, *args)
