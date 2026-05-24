import httpx
import pytest

from app import brain
from app.lesson import DECK


def context() -> brain.TutorContext:
    return brain.TutorContext(
        question=DECK[0],
        transcript="panch",
        parsed_answer=5,
        expected_answer=5,
        is_correct=True,
        streak=1,
        attempt_count=0,
    )


def test_extract_text_from_gemini_payload():
    payload = {
        "candidates": [
            {"content": {"parts": [{"text": "[happy] Sahi jawab!"}]}},
        ],
    }

    assert brain._extract_text(payload) == "[happy] Sahi jawab!"


def test_extract_text_returns_none_for_empty_payload():
    assert brain._extract_text({"candidates": []}) is None


@pytest.mark.asyncio
async def test_generate_tutor_line_without_key_is_unconfigured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = await brain.generate_tutor_line(context())

    assert result.text is None
    assert result.error == "brain_unconfigured"


@pytest.mark.asyncio
async def test_generate_tutor_line_posts_to_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/models/gemini-2.5-flash:generateContent")
        assert request.headers["x-goog-api-key"] == "key"
        body = request.read().decode()
        assert "Expected answer: 5" in body
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": "[happy] Sahi jawab! Bahut badhiya."}]}},
                ],
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

    monkeypatch.setattr(brain.httpx, "AsyncClient", FakeAsyncClient)

    result = await brain.generate_tutor_line(context())

    assert result.text == "[happy] Sahi jawab! Bahut badhiya."
    assert result.error is None


@pytest.mark.asyncio
async def test_generate_tutor_line_retries_invalid_output(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        text = "missing tag" if calls == 1 else "[happy] Ab valid hai!"
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
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

    monkeypatch.setattr(brain.httpx, "AsyncClient", FakeAsyncClient)

    result = await brain.generate_tutor_line(context())

    assert calls == 2
    assert result.text == "[happy] Ab valid hai!"
