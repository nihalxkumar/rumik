import httpx
import pytest

from app import stt


def test_extract_transcript_from_deepgram_payload():
    payload = {
        "results": {
            "channels": [
                {"alternatives": [{"transcript": "panch"}]},
            ],
        },
    }

    assert stt._extract_transcript(payload) == "panch"


def test_extract_transcript_returns_none_for_empty_payload():
    assert stt._extract_transcript({"results": {"channels": []}}) is None


@pytest.mark.asyncio
async def test_transcribe_without_key_is_unconfigured(monkeypatch):
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)

    result = await stt.transcribe(b"audio", content_type="audio/webm")

    assert result.transcript is None
    assert result.error == "stt_unconfigured"


@pytest.mark.asyncio
async def test_transcribe_empty_audio_is_error(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "key")

    result = await stt.transcribe(b"", content_type="audio/webm")

    assert result.transcript is None
    assert result.error == "empty_audio"


@pytest.mark.asyncio
async def test_transcribe_posts_audio_to_deepgram(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/listen"
        assert request.headers["authorization"] == "Token key"
        assert request.headers["content-type"] == "audio/webm"
        assert request.content == b"audio"
        return httpx.Response(
            200,
            json={
                "results": {
                    "channels": [
                        {"alternatives": [{"transcript": "barah"}]},
                    ],
                },
            },
        )

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    class FakeAsyncClient:
        def __init__(self, timeout: float):
            self.client = real_async_client(transport=transport, timeout=timeout)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setattr(stt.httpx, "AsyncClient", FakeAsyncClient)

    result = await stt.transcribe(b"audio", content_type="audio/webm")

    assert result.transcript == "barah"
    assert result.error is None
