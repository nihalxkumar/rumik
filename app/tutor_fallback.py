"""
Local tutor lines used until Gemini lands in phase 4.

Every line is hand-validated against `validator.py` (one leading
tone tag, 1–3 sentences, Roman script). When Gemini is wired up,
these become the fallback for when the AI call fails or its output
fails validation twice — so we never let the demo go silent.
"""
from __future__ import annotations

import random

_CORRECT = [
    "[happy] Sahi jawab! Bahut badhiya.",
    "[excited] Wah! Bilkul sahi.",
    "[happy] Shabaash! Sahi answer.",
]

_WRONG = [
    "[neutral] Almost! Ek baar phir try karo.",
    "[neutral] Itna paas the. Phir se sochkar bolo.",
    "[sad] Galat ho gaya. Koi baat nahi, ek aur try.",
]

_NO_PARSE = [
    "[neutral] Mujhe number nahi mila. Sirf jawab bolo.",
    "[neutral] Saaf se ek number bolo.",
]


def pick(is_correct: bool, parsed_was_none: bool) -> str:
    if parsed_was_none:
        return random.choice(_NO_PARSE)
    return random.choice(_CORRECT if is_correct else _WRONG)
