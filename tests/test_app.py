"""Unit tests for the capture API, store, and classifiers. No network, no API key:
Gemini paths are either skipped (no key) or exercised via monkeypatching."""

from __future__ import annotations

import asyncio
import threading

import pytest
from fastapi.testclient import TestClient

from app.asr import TranscriptionUnavailable, transcribe
from app.classify import classify_heuristic
from app.classify_gemini import classify
from app.main import app
from app.store import CaptureStore


def run_coro(coro):
    """Run a coroutine to completion regardless of pytest's loop regime.

    pytest-playwright installs anyio's plugin, which runs tests inside a live
    event loop where asyncio.run() is forbidden. A worker thread with its own
    loop sidesteps both regimes (plain sync and anyio) with no extra deps.
    """
    out: dict = {}

    def _run() -> None:
        try:
            out["result"] = asyncio.run(coro)
        except BaseException as exc:  # re-raised in the main thread below
            out["exc"] = exc

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=10)
    if "exc" in out:
        raise out["exc"]
    if "result" not in out:
        raise RuntimeError("coroutine did not finish in 10s")
    return out["result"]


@pytest.fixture()
def client(tmp_path):
    from app import main

    main.store = CaptureStore(tmp_path / "captures.db", tmp_path / "audio")
    with TestClient(app) as c:
        yield c


FAKE_AUDIO = b"WEBM_FAKE_AUDIO_BYTES_FOR_TESTS"


def test_index_serves_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "HOLD TO TALK" in res.text


def test_upload_without_key_degrades_gracefully(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = client.post(
        "/api/captures",
        files={"file": ("capture.webm", FAKE_AUDIO, "audio/webm")},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "unprocessed"
    assert data["transcript"] is None
    assert "GEMINI_API_KEY" in data["note"]


def test_upload_empty_rejected(client):
    res = client.post("/api/captures", files={"file": ("e.webm", b"", "audio/webm")})
    assert res.status_code == 400


def test_full_pipeline_with_mock_transcription(client, monkeypatch):
    async def fake_transcribe(audio, mime):
        return "buy oat milk on the way home"

    async def fake_classify(text):
        return "task"

    monkeypatch.setattr("app.main.transcribe", fake_transcribe)
    monkeypatch.setattr("app.main.classify", fake_classify)
    res = client.post(
        "/api/captures",
        files={"file": ("c.webm", FAKE_AUDIO, "audio/webm")},
    )
    data = res.json()
    assert data["status"] == "processed"
    assert data["transcript"] == "buy oat milk on the way home"
    assert data["class"] == "task"
    # stored and retrievable
    got = client.get(f"/api/captures/{data['id']}").json()
    assert got["class"] == "task"
    listed = client.get("/api/captures").json()
    assert any(r["id"] == data["id"] for r in listed)


def test_asr_raises_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(TranscriptionUnavailable):
        run_coro(transcribe(b"x", "audio/webm"))


def test_asr_wraps_api_errors(monkeypatch):
    import app.asr as asr_mod

    class Boom:
        def generate_content(self, *a, **k):
            raise RuntimeError("quota exceeded")

    class FakeClient:
        models = Boom()

    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setattr(asr_mod.genai, "Client", lambda api_key: FakeClient())
    with pytest.raises(TranscriptionUnavailable):
        run_coro(asr_mod.transcribe(b"x", "audio/webm"))


def test_classify_gemini_falls_back_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert run_coro(classify("buy oat milk")) == "task"


def test_classify_gemini_falls_back_on_api_error(monkeypatch):
    import app.classify_gemini as cg

    class Boom:
        def generate_content(self, *a, **k):
            raise RuntimeError("api down")

    class FakeClient:
        models = Boom()

    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setattr(cg.genai, "Client", lambda api_key: FakeClient())
    assert run_coro(cg.classify("what if we built a ladder app")) == "idea"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("buy oat milk on the way home", "task"),
        ("remind me to call the dentist tomorrow", "task"),
        ("what if the inbox could sort itself by energy level", "idea"),
        ("idea for a weekend newsletter about urban design", "idea"),
        ("reach out to Dita about the warehouse partnership", "lead"),
        ("follow up with the client from Tuesday", "lead"),
        ("uhh", "noise"),
        ("test one two", "noise"),
        ("", "noise"),
    ],
)
def test_heuristic_all_four_labels(text, expected):
    assert classify_heuristic(text) == expected


def test_store_roundtrip(tmp_path):
    s = CaptureStore(tmp_path / "db", tmp_path / "a")
    s.init()
    path = s.save_audio(b"abc", "audio/webm")
    cid = s.add(audio_path=path, mime="audio/webm", transcript="hi", cls="idea")
    row = s.get(cid)
    assert row.transcript == "hi" and row.cls == "idea"
    assert (tmp_path / "a" / path.split("/")[-1]).read_bytes() == b"abc"
    assert len(s.list()) == 1
