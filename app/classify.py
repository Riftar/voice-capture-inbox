"""Deterministic heuristic classifier — baseline that needs no network or API key.
Keyword and shape rules over the transcript text. Labels: idea / task / lead / noise.
"""

from __future__ import annotations

import re
from typing import Literal

CaptureType = Literal["idea", "task", "lead", "noise"]

TASK_PATTERNS = [
    r"\bbuy\b", r"\bcall\b", r"\bemail\b", r"\bremind\b", r"\bschedule\b",
    r"\bbook\b", r"\bpay\b", r"\bsend\b", r"\bfix\b", r"\bcheck\b",
    r"\btodo\b", r"\btomorrow\b", r"\btonight\b", r"\blater today\b",
    r"\bdon'?t forget\b", r"\bneed to\b", r"\bhave to\b", r"\bshould\b",
]
IDEA_PATTERNS = [
    r"\bwhat if\b", r"\bidea for\b", r"\bwe could\b", r"\bwe should build\b",
    r"\bimagine\b", r"\bconcept\b", r"\bfeature\b", r"\bproduct\b",
    r"\bstartup\b", r"\bapp that\b", r"\bwebsite that\b", r"\bservice that\b",
    r"\bmaybe (?:we|I) (?:could|can)\b",
]
LEAD_PATTERNS = [
    r"\bcontact\b", r"\breach out\b", r"\bprospective\b", r"\bclient\b",
    r"\bcustomer\b", r"\bintroduce\b", r"\bconnect(?:ion)?\b", r"\bfollow up\b",
    r"\bdemo\b", r"\bpartnership\b", r"\bcollab\b",
]
NOISE_PATTERNS = [
    r"^(?:uh+|um+|uhm+|erm+|hmm+)[\s,\.!?]*$",  # pure filler
    r"^(?:test|testing|hello|hi|mic check)"
    r"(?:\s+(?:one|two|three|check|testing?|two|three))*[\s,\.!?]*$",
    r"^\s*$",
]


def classify_heuristic(text: str) -> CaptureType:
    t = " ".join(text.lower().split())
    if len(t) < 3 or re.match(NOISE_PATTERNS[0], t) or re.match(NOISE_PATTERNS[1], t) or not t.strip():
        return "noise"
    for pat in IDEA_PATTERNS:
        if re.search(pat, t):
            return "idea"
    for pat in LEAD_PATTERNS:
        if re.search(pat, t):
            return "lead"
    for pat in TASK_PATTERNS:
        if re.search(pat, t):
            return "task"
    # Default for short action-ish statements without keywords: task if it reads
    # like an instruction, otherwise idea (a raw thought worth keeping).
    return "idea"
