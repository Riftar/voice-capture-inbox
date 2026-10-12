"""End-to-end test: real backend + real browser (headless Chromium via Playwright).

The microphone cannot be driven headlessly, so this exercises the page's own
upload path the way a real capture would: page.evaluate() calls the page's
upload() with a synthetic blob, which goes through the identical fetch pipeline.
Requires the heuristic path (no GEMINI_API_KEY) so it runs keyless in CI.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

from fastapi.testclient import TestClient  # noqa: E402
from playwright.sync_api import expect  # noqa: E402

from app.main import app  # noqa: E402
from app.store import CaptureStore  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture()
def server(tmp_path):
    from app import main

    main.store = CaptureStore(tmp_path / "captures.db", tmp_path / "audio")
    port = free_port()
    thread = threading.Thread(
        target=lambda: uvicorn_run(app, port), daemon=True
    )
    thread.start()
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                yield f"http://127.0.0.1:{port}"
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("backend did not start")


def uvicorn_run(app, port):
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def test_hold_button_and_capture_flow(page, server):
    page.goto(server)
    expect(page.locator("#btn")).to_be_visible()
    expect(page.locator("#btn")).to_have_text("HOLD TO TALK")

    # Drive the page's own upload path with a synthetic blob (same code path
    # a real recording takes after MediaRecorder stops).
    page.evaluate(
        """
        async () => {
          const blob = new Blob(['fake-webm-bytes'], { type: 'audio/webm' });
          await window.__upload(blob);
        }
        """
    )

    # Without a key the capture is stored unprocessed — the card must render.
    card = page.locator(".card").first
    expect(card).to_be_visible(timeout=10_000)
    expect(card.locator(".label")).to_contain_text("unprocessed")
    expect(card.locator(".text")).to_contain_text("(no transcript)")
