# Voice Capture Inbox

**Hold a button, speak, done.**

Best ideas arrive while walking. Opening an app and typing kills the capture. This is the dead-simple front-door for turning spoken thoughts into filed, actionable items.

## The problem

- Insight is spontaneous — walking, coffee, between tasks. By the time you unlock your phone and open a notes app, the idea is half-gone.
- Whisper-based desktop dictation (e.g. Superwhisper on macOS) proves the demand — but nothing owns the **mobile → knowledge-base** path.
- Raw voice memos pile up in an unlistenable backlog. Capture without filing is hoarding.

## How it works

1. **Capture** — one dead-simple endpoint: hold button, speak, release. No screens, no typing, no folders to pick.
2. **Transcribe** — speech-to-text via Gemini (`gemini-2.5-flash`).
3. **Classify** — each capture is sorted into `idea` / `task` / `lead` / `noise` (LLM with a deterministic keyword fallback).
4. **Store** — SQLite + audio files under `data/` (disposable: delete the folder to reset).
5. **Confirm** — the page shows a card with the transcript and label seconds after you let go.

## Quickstart

Requirements: Python 3.11+ and a browser (Chrome/Edge/Firefox; Safari iOS 16.4+).

    git clone https://github.com/Riftar/voice-capture-inbox.git
    cd voice-capture-inbox
    python3 -m venv .venv && source .venv/bin/activate
    pip install fastapi uvicorn google-genai python-multipart pytest httpx
    uvicorn app.main:app --port 8777

Open http://localhost:8777, allow microphone access, hold the button, speak, release.

Optional: copy `.env.example` to `.env` and set `GEMINI_API_KEY` for real transcription + LLM classification. Without it, captures are stored as **unprocessed** (audio saved, inline notice shown) — the app still works end-to-end for the capture loop.

## Tests

    pytest tests/ -v          # unit tests, no network or API key needed
    pytest tests/e2e -v       # headless-browser end-to-end (needs: pip install pytest-playwright && playwright install chromium)

## Status

Working prototype. Roadmap and design decisions live in [execplan/001-voice-capture-inbox.md](execplan/001-voice-capture-inbox.md).

## Why voice capture scales

Capture is the universal front-door. Any knowledge workflow — notes, tasks, leads, journals — gets better with voice input. Same convergence: one capture surface, many destinations.

## License

[MIT](LICENSE) — use it, copy it, ship it.
