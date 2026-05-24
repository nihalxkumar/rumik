"""
Speech-to-text integration.

Deepgram is deliberately isolated from the lesson engine. The HTTP layer
passes audio bytes in, gets a transcript out, then uses the same deterministic
answer parser and scoring path as typed answers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


@dataclass(frozen=True)
class STTResult:
    transcript: str | None
    error: str | None = None


async def transcribe(audio: bytes, *, content_type: str | None) -> STTResult:
    """Return the best transcript for an uploaded audio blob.

    Fail closed and fast: demo UX should fall back to typed input instead of
    hanging the turn when the key is missing, Deepgram times out, or the API
    returns an unexpected shape.
    """
    if not audio:
        return STTResult(transcript=None, error="empty_audio")

    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if not api_key:
        return STTResult(transcript=None, error="stt_unconfigured")

    timeout = _float_env("DEEPGRAM_TIMEOUT", default=4.0)
    params = {
        "model": os.getenv("DEEPGRAM_MODEL", "nova-2"),
        "language": os.getenv("DEEPGRAM_LANGUAGE", "hi"),
        "smart_format": "true",
        "numerals": "true",
    }
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": content_type or "application/octet-stream",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                DEEPGRAM_URL,
                params=params,
                headers=headers,
                content=audio,
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        return STTResult(transcript=None, error="stt_timeout")
    except httpx.HTTPError:
        return STTResult(transcript=None, error="stt_failed")

    transcript = _extract_transcript(response.json())
    return STTResult(
        transcript=transcript,
        error=None if transcript else "empty_transcript",
    )


def _extract_transcript(payload: dict[str, Any]) -> str | None:
    channels = payload.get("results", {}).get("channels", [])
    if not channels:
        return None
    alternatives = channels[0].get("alternatives", [])
    if not alternatives:
        return None
    transcript = alternatives[0].get("transcript")
    if not isinstance(transcript, str):
        return None
    transcript = transcript.strip()
    return transcript or None


def _float_env(name: str, *, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default
