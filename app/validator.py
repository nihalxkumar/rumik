"""
Silk-safe text validator — Phase 4.

Enforces the rules from the design doc:
  - exactly one leading tone tag from the allowed set
  - 1–3 sentences, max 180 chars
  - Roman script only (no Devanagari)
  - no second tone tag, no unsupported bracketed events
"""
import re

ALLOWED_TAGS = {"[neutral]", "[happy]", "[whisper]", "[excited]", "[sad]", "[angry]"}

_TAG_RE      = re.compile(r"^\[(neutral|happy|whisper|excited|sad|angry)\]\s*")
_OTHER_BRACK = re.compile(r"\[[^\]]+\]")
_DEVANAGARI  = re.compile(r"[\u0900-\u097F]")
_SENTENCE    = re.compile(r"[.!?]+")


class ValidationError(ValueError):
    pass


def validate(text: str) -> str:
    """Return the text unchanged if it passes, else raise."""
    if not _TAG_RE.match(text):
        raise ValidationError("missing or unsupported leading tone tag")
    body = _TAG_RE.sub("", text, count=1)

    if len(text) > 180:
        raise ValidationError("text exceeds 180 characters")
    if _OTHER_BRACK.search(body):
        raise ValidationError("unexpected bracketed token in body")
    if _DEVANAGARI.search(text):
        raise ValidationError("Devanagari script not allowed")

    sentences = [s for s in _SENTENCE.split(body) if s.strip()]
    if not 1 <= len(sentences) <= 3:
        raise ValidationError("must be 1–3 sentences")

    return text
