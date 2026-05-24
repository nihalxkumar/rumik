"""Tests for Silk TTS synthesis."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app import tts


@pytest.mark.asyncio
async def test_synthesize_returns_base64_audio_on_success():
    """Valid Silk response returns base64-encoded audio."""
    mock_audio = b"RIFF\x24\x00\x00\x00WAVEfmt "  # Minimal WAV header

    with patch("app.tts.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = mock_audio
        mock_response.raise_for_status = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"SILK_API_KEY": "rk_test_123"}):
            result = await tts.synthesize("[neutral] Test")

    assert result.error is None
    assert result.audio_base64 is not None
    assert len(result.audio_base64) > 0
    # Verify it's valid base64 by decoding
    import base64
    decoded = base64.b64decode(result.audio_base64)
    assert decoded == mock_audio


@pytest.mark.asyncio
async def test_synthesize_without_key_is_unconfigured():
    """Missing API key returns unconfigured error."""
    with patch.dict("os.environ", {"SILK_API_KEY": ""}):
        result = await tts.synthesize("[neutral] Test")

    assert result.error == "tts_unconfigured"
    assert result.audio_base64 is None


@pytest.mark.asyncio
async def test_synthesize_timeout_returns_error():
    """Silk timeout falls back gracefully."""
    import httpx

    with patch("app.tts.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"SILK_API_KEY": "rk_test_123"}):
            result = await tts.synthesize("[neutral] Test")

    assert result.error == "tts_timeout"
    assert result.audio_base64 is None


@pytest.mark.asyncio
async def test_synthesize_includes_speaker_in_request():
    """Speaker parameter is sent to Silk API."""
    mock_audio = b"RIFF"

    with patch("app.tts.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = mock_audio
        mock_response.raise_for_status = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        with patch.dict("os.environ", {"SILK_API_KEY": "rk_test_123"}):
            await tts.synthesize("[neutral] Test", speaker="speaker_2")

    # Verify the request body
    call_kwargs = mock_client.post.call_args[1]
    assert call_kwargs["json"]["speaker"] == "speaker_2"
    assert call_kwargs["json"]["text"] == "[neutral] Test"
    assert call_kwargs["json"]["model"] == "mulberry"
