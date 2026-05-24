"""
Gemini tutor text generation.

The lesson engine decides correctness. Gemini only turns that deterministic
state into a short, child-friendly Hinglish tutor line that must pass the
Silk-safe validator before it reaches the browser.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from app import validator
from app.lesson import Question


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass(frozen=True)
class TutorContext:
    question: Question
    transcript: str | None
    parsed_answer: int | None
    expected_answer: int
    is_correct: bool
    streak: int
    attempt_count: int


@dataclass(frozen=True)
class BrainResult:
    text: str | None
    error: str | None = None


async def generate_tutor_line(context: TutorContext) -> BrainResult:
    """Ask Gemini for one validated tutor line.

    Invalid model output is retried once with a stricter repair prompt. Any
    network/API/validation failure returns an error so the caller can use local
    fallback lines and keep the demo moving.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return BrainResult(text=None, error="brain_unconfigured")

    timeout = _float_env("GEMINI_TIMEOUT", default=3.0)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    url = f"{GEMINI_BASE_URL}/{model}:generateContent"
    headers = {"x-goog-api-key": api_key}

    last_error = "brain_failed"
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(2):
            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json=_request_body(context, repair=attempt == 1),
                )
                response.raise_for_status()
                candidate = _extract_text(response.json())
                if candidate is None:
                    last_error = "brain_empty"
                    continue
                return BrainResult(text=validator.validate(candidate), error=None)
            except validator.ValidationError:
                last_error = "brain_invalid"
            except httpx.TimeoutException:
                return BrainResult(text=None, error="brain_timeout")
            except httpx.HTTPError:
                return BrainResult(text=None, error="brain_failed")

    return BrainResult(text=None, error=last_error)


def _request_body(context: TutorContext, *, repair: bool) -> dict[str, Any]:
    prompt = _prompt(context)
    if repair:
        prompt += "\nYour previous answer broke the output rules. Return only one valid line."
    return {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 64,
        },
    }


def _prompt(context: TutorContext) -> str:
    parsed = "none" if context.parsed_answer is None else str(context.parsed_answer)
    transcript = context.transcript or ""
    return f"""You are Rumik, a warm arithmetic tutor for a Grade 1-3 Indian child.

Return exactly one tutor line.
Rules:
- Start with exactly one tone tag: [neutral], [happy], [whisper], [excited], or [sad].
- Use Roman-script Hinglish only. No Devanagari.
- Keep it under 180 characters.
- Use 1 to 3 short sentences.
- Do not include the expected answer unless the child is already correct.
- Do not add JSON, markdown, labels, quotes, or extra brackets.

Question: {context.question.prompt}
Expected answer: {context.expected_answer}
Child transcript: {transcript}
Parsed answer: {parsed}
Correct: {context.is_correct}
Streak: {context.streak}
Attempt count on this question: {context.attempt_count}
"""


def _extract_text(payload: dict[str, Any]) -> str | None:
    candidates = payload.get("candidates", [])
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [part.get("text", "") for part in parts if isinstance(part.get("text"), str)]
    text = "".join(texts).strip()
    return text or None


def _float_env(name: str, *, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default
