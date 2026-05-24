"""
Silk Mulberry text-to-speech synthesis.

Converts validated tutor text to 24 kHz mono WAV audio for playback.
The text should already pass validator.py rules before reaching this module.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any

import httpx


SILK_BASE_URL = "https://silk-api.rumik.ai/v1/tts"


@dataclass(frozen=True)
class TTSResult:
    audio_base64: str | None
    error: str | None = None


async def synthesize(text: str, speaker: str = "speaker_1") -> TTSResult:
    """Synthesize tutor text to WAV audio.

    Args:
        text: Validated tutor line (should pass validator.py)
        speaker: Silk speaker ID, one of speaker_1 through speaker_4

    Returns:
        TTSResult with base64-encoded WAV audio or error code.
        On timeout or network failure, returns error so caller can fall back to
        text-only response and keep the demo moving.
    """
    api_key = os.getenv("SILK_API_KEY", "").strip()
    if not api_key:
        return TTSResult(audio_base64=None, error="tts_unconfigured")

    timeout = _float_env("SILK_TIMEOUT", default=5.0)
    model = os.getenv("SILK_MODEL", "mulberry").strip()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                SILK_BASE_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "text": text,
                    "speaker": speaker,
                },
            )
            response.raise_for_status()

            # Response is binary WAV audio
            audio_bytes = response.content
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            return TTSResult(audio_base64=audio_base64, error=None)

    except httpx.TimeoutException:
        return TTSResult(audio_base64=None, error="tts_timeout")
    except httpx.HTTPError as e:
        # Try to extract Silk error code from response
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                code = error_data.get("code", "tts_failed")
                return TTSResult(audio_base64=None, error=f"tts_{code}")
            except Exception:
                pass
        return TTSResult(audio_base64=None, error="tts_failed")
    except Exception:
        return TTSResult(audio_base64=None, error="tts_failed")


def _float_env(name: str, *, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default
