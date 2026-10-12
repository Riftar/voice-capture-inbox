# ExecPlan: Voice Capture Inbox — Web App Prototype

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. When revising, write a note at the bottom describing the change and why.

## Purpose / Big Picture

After this plan is implemented, a person walking with their phone can open a web page, hold a big button, speak a thought, release, and within seconds see their capture transcribed, classified (idea / task / lead / noise), and stored — with a confirmation card on the same page. That closes the loop "best ideas arrive while walking; opening an app and typing kills the capture."

This is a prototype, not a product. It exists to answer one question: does the hold-button → transcribe → classify → file → confirm loop feel instant and reliable enough to be the universal front-door for capture? Once answered, we decide whether to build it for real.

The prototype runs locally on a single machine. It is not multi-user, not internet-exposed, and stores no secrets in the repo.

## Progress

- [x] (2026-10-13 00:06 UTC+8) ExecPlan v1 authored; committed as execplan/001-voice-capture-inbox.md.
- [ ] Milestone 1: local web UI with hold-button recording; upload endpoint stub; SQLite store.
- [ ] Milestone 2: ASR via Gemini; graceful degradation without API key.
- [ ] Milestone 3: classification (heuristic baseline + Gemini structured output).
- [ ] Milestone 4: end-to-end test with a real browser; README quickstart; CI for unit tests.
- [ ] Final: Outcomes & Retrospective entry; promote-or-discard decision recorded.

## Surprises & Discoveries

(None yet.)

## Decision Log

- Decision: Repository is public with an MIT license.
  Rationale: the owner asked for a license that permits public use and copying; MIT is the most permissive standard license.
  Date/Author: 2026-10-12 / Richard.

- Decision: Frontend is a single static HTML file with vanilla JavaScript; backend is FastAPI (Python 3.11+).
  Rationale: the prototype answers a UX question, not an architecture question. One HTML file means no build step and no node_modules; FastAPI gives file uploads, JSON routes, and auto-generated /docs for free. Smallest solution that actually works.
  Date/Author: 2026-10-12 / Richard.

- Decision: Classification ships a deterministic heuristic as the baseline, with Gemini structured output as the primary path and automatic fallback to the heuristic on API unavailability.
  Rationale: tests must pass with no network and no API key; the heuristic also guarantees the loop is demonstrable even when the key is missing. The Gemini path uses a fixed set of allowed labels so output is parseable without guesswork.
  Date/Author: 2026-10-12 / Richard.

- Decision: Audio is stored as files under data/audio/ with metadata in SQLite; the database file is disposable.
  Rationale: keeps blobs out of the database, makes "reset everything" a single rm of data/, and keeps the store module trivially testable.
  Date/Author: 2026-10-12 / Richard.

## Context and Orientation

The reader is assumed to know nothing about this repository. As of this writing the repo contains only two files: README.md (the product concept) and LICENSE (MIT). There is no code yet; everything below is created from scratch.

Terms of art, defined in plain language:

- ASR (Automatic Speech Recognition): turning an audio file into text. Here, the audio is sent to the Gemini API with an instruction to transcribe it.
- MediaRecorder API: a browser feature (Chrome, Edge, Firefox, Safari on iOS 16.4+ and Android) that lets JavaScript capture microphone audio into a webm/opus blob. The frontend uses it while the button is held.
- Hold button: a page element that starts recording on pointerdown and stops on pointerup or pointercancel. Pointer events cover both mouse and touch, which is why they are used instead of separate mouse/touch handlers.
- Classification: deciding whether a capture is an idea, a task, a lead, or noise (not worth filing). The LLM is asked to return exactly one of those four words.
- Gemini API key: a secret string authorizing API calls. It is read from the environment variable GEMINI_API_KEY (optionally via a local .env file that is gitignored). The repo ships .env.example listing the variable.
- SQLite: a single-file database. The whole database is one file, data/captures.db, created automatically on first run; deleting it resets all metadata.
- FastAPI: the Python web framework receiving the browser's audio upload at POST /api/captures, calling transcription and classification, storing the result, and returning JSON. Uvicorn is the server program that runs FastAPI: "uvicorn app.main:app" starts it.
- Playwright: a browser automation library used by the end-to-end test to open the real page and drive the real flow.

## Plan of Work

Four milestones. Each leaves the app runnable and is independently verifiable.

Milestone 1 — Hold-button capture UI (local only). Create app/main.py (FastAPI app serving static/index.html at / and a POST /api/captures stub returning placeholder JSON), static/index.html (the page with the hold button, pointer events plus MediaRecorder, fetch upload), and app/store.py (SQLite persistence, auto-creating data/captures.db). Acceptance: start the server, open the page, hold the button, speak, release; the network tab shows POST /api/captures returning the stub, and a row exists in the database.

Milestone 2 — ASR via Gemini. Add app/asr.py with an async transcribe function (see Interfaces). The frontend is unchanged. Acceptance: with GEMINI_API_KEY set, a real spoken capture returns text within a few seconds; without the key, the UI shows an inline notice ("transcription unavailable; saved as unprocessed capture") instead of an error page.

Milestone 3 — Classification. Add app/classify.py (deterministic heuristic: keyword and shape rules mapping text to one of the four labels) and app/classify_gemini.py (Gemini call constrained to the four labels, falling back to the heuristic on any API failure). Acceptance: heuristic labels "buy oat milk on the way home" as task, "what if we..." as idea, "contact X about Y" as lead, filler like "uhh test one two" as noise; tests cover all four labels and the fallback path.

Milestone 4 — E2E and polish. Add tests/e2e/test_flow.py (Playwright, headless): start the backend on a free port, open the page, simulate a hold, upload a fixture .webm via the page's own code path, assert the confirmation card shows label and transcript. Expand README quickstart; add .env.example and .gitignore; add a GitHub Actions workflow running the unit tests (mocked, no secrets). Acceptance: full pytest run green; README quickstart works from a clean clone.

File tree at completion:

    app/
      __init__.py
      main.py            # FastAPI routes
      store.py           # SQLite store
      asr.py             # Gemini transcription (M2)
      classify.py        # heuristic classifier (M3)
      classify_gemini.py # LLM classifier with fallback (M3)
    static/
      index.html         # the entire frontend
    data/                # gitignored: captures.db + audio/
    tests/
      test_capture.py
      test_store.py
      test_asr.py
      test_classify.py
      e2e/
        test_flow.py
        fixtures/short.webm
    execplan/
      001-voice-capture-inbox.md
    .env.example
    .gitignore
    README.md
    LICENSE

## Concrete Steps

All commands run from the repository root (any clone; the path is wherever you checked it out).

One-time setup:

    python3 -m venv .venv && source .venv/bin/activate
    pip install fastapi uvicorn google-genai python-multipart pytest httpx pytest-playwright
    playwright install chromium

Run the dev server:

    uvicorn app.main:app --reload --port 8777

Expected output includes "Uvicorn running on http://127.0.0.1:8777"; opening that URL renders the page with the hold button.

Run unit tests (no network, no API key):

    pytest tests/ -v

Run the end-to-end test (headless browser, no API key needed if the fixture transcript is produced by the heuristic path):

    pytest tests/e2e/test_flow.py -v

## Validation and Acceptance

Phrased as behavior a human can verify:

1. From a clean clone, following only the README quickstart gets the app running within five minutes.
2. Holding the button and speaking yields a confirmation card within a few seconds showing the transcript and one of the four labels.
3. With GEMINI_API_KEY unset, capture still stores the audio and shows the inline "unprocessed" notice; nothing crashes.
4. pytest unit suite and e2e test pass as described above.
5. No secrets in the repo: a search of git history for key-like strings returns nothing sensitive.

## Idempotence and Recovery

Every step is an additive file creation; rerunning is safe. data/ is disposable: deleting it resets all state without touching code. Rolling back a milestone is git revert of that milestone's commits. The prototype holds no long-running services beyond uvicorn; stopping it stops everything. The venv lives in .venv/ (gitignored).

## Artifacts and Notes

Confirmation card markup the frontend renders (illustrative):

    <div class="card" data-id="42">
      <span class="label label-task">task</span>
      <p>buy oat milk on the way home</p>
    </div>

API response shape (M2 onward):

    {
      "id": 42,
      "status": "processed",
      "transcript": "buy oat milk on the way home",
      "class": "task",
      "created_at": "2026-10-13T00:20:00Z"
    }

## Interfaces and Dependencies

Python 3.11+; fastapi, uvicorn, google-genai (official SDK), python-multipart (file uploads), pytest, httpx (async test transport), pytest-playwright. Frontend dependencies: none (vanilla JS and browser APIs only).

Contracts that must exist at the end (stable names):

    # app/asr.py
    async def transcribe(audio: bytes, mime: str) -> str

    # app/classify.py
    CaptureType = Literal["idea", "task", "lead", "noise"]
    def classify_heuristic(text: str) -> CaptureType

    # app/classify_gemini.py
    async def classify(text: str) -> CaptureType   # falls back to classify_heuristic on API failure

    # app/store.py
    class CaptureStore:
        def add(self, audio_path: str, mime: str, transcript: str | None, cls: str | None) -> int
        def get(self, id: int) -> CaptureRow | None
        def list(self, limit: int = 50) -> list[CaptureRow]

SQLite schema:

    CREATE TABLE captures (
        id INTEGER PRIMARY KEY,
        created_at TEXT NOT NULL,
        audio_path TEXT NOT NULL,
        mime TEXT NOT NULL,
        transcript TEXT,
        class TEXT CHECK(class IN ('idea','task','lead','noise'))
    );

## Outcomes & Retrospective

(To be written at completion.)
