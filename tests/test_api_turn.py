"""End-to-end tests for /api/turn."""
import httpx
import pytest

from app import lesson
from app import brain as brain_module
from app import stt as stt_module
from app.main import app


def reset_store():
    # Each test gets its own session store so streaks don't leak.
    lesson.store = lesson.SessionStore()


def fresh_client():
    reset_store()
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


def first_question_id() -> str:
    return lesson.DECK[0].id


@pytest.mark.asyncio
async def test_correct_typed_answer_advances():
    qid = first_question_id()
    expected = lesson.DECK[0].expected_answer

    async with fresh_client() as c:
        r = await c.post("/api/turn", json={
            "session_id": None,
            "question_id": qid,
            "typed_answer": str(expected),
        })

    assert r.status_code == 200
    data = r.json()
    assert data["is_correct"] is True
    assert data["parsed_answer"] == expected
    assert data["streak"] == 1
    assert data["next_question"]["id"] == lesson.DECK[1].id
    assert data["tutor_text"].startswith("[")
    assert data["session_id"]


@pytest.mark.asyncio
async def test_gemini_tutor_line_is_used(monkeypatch):
    qid = first_question_id()

    async def fake_generate(context: brain_module.TutorContext):
        assert context.question.id == qid
        assert context.parsed_answer == 5
        assert context.is_correct is True
        return brain_module.BrainResult(text="[happy] Gemini says sahi jawab!")

    monkeypatch.setattr("app.main.brain.generate_tutor_line", fake_generate)

    async with fresh_client() as c:
        r = await c.post("/api/turn", json={
            "session_id": None,
            "question_id": qid,
            "typed_answer": "5",
        })

    data = r.json()
    assert data["tutor_text"] == "[happy] Gemini says sahi jawab!"


@pytest.mark.asyncio
async def test_invalid_gemini_tutor_line_falls_back(monkeypatch):
    qid = first_question_id()

    async def fake_generate(context: brain_module.TutorContext):
        return brain_module.BrainResult(text=None, error="brain_invalid")

    monkeypatch.setattr("app.main.brain.generate_tutor_line", fake_generate)

    async with fresh_client() as c:
        r = await c.post("/api/turn", json={
            "session_id": None,
            "question_id": qid,
            "typed_answer": "5",
        })

    data = r.json()
    assert data["tutor_text"].startswith("[")
    assert data["tutor_text"] != "[happy] Gemini says sahi jawab!"
    assert data["error"] is None


@pytest.mark.asyncio
async def test_wrong_typed_answer_keeps_question():
    qid = first_question_id()
    wrong = lesson.DECK[0].expected_answer + 7

    async with fresh_client() as c:
        r = await c.post("/api/turn", json={
            "session_id": None,
            "question_id": qid,
            "typed_answer": str(wrong),
        })

    data = r.json()
    assert data["is_correct"] is False
    assert data["streak"] == 0
    assert data["next_question"]["id"] == qid


@pytest.mark.asyncio
async def test_unparseable_answer_returns_error_field():
    qid = first_question_id()

    async with fresh_client() as c:
        r = await c.post("/api/turn", json={
            "session_id": None,
            "question_id": qid,
            "typed_answer": "I dunno",
        })

    data = r.json()
    assert data["error"] == "no_number_parsed"
    assert data["parsed_answer"] is None
    assert data["is_correct"] is False
    assert data["next_question"]["id"] == qid


@pytest.mark.asyncio
async def test_stale_question_id_returns_409():
    qid = first_question_id()

    # First turn: get back the assigned session_id and advance past q1.
    async with fresh_client() as c:
        r = await c.post("/api/turn", json={
            "session_id": None,
            "question_id": qid,
            "typed_answer": str(lesson.DECK[0].expected_answer),
        })
        assert r.status_code == 200
        sid = r.json()["session_id"]

        # Posting the now-completed question_id should 409 — that means a
        # stale browser tab, which we'd rather surface than silently re-score.
        stale = await c.post("/api/turn", json={
            "session_id": sid,
            "question_id": qid,
            "typed_answer": "1",
        })

    assert r.status_code == 200
    assert stale.status_code == 409


@pytest.mark.asyncio
async def test_multipart_audio_answer_advances(monkeypatch):
    qid = first_question_id()

    async def fake_transcribe(audio: bytes, *, content_type: str | None):
        assert audio == b"fake-webm"
        assert content_type == "audio/webm"
        return stt_module.STTResult(transcript="panch")

    monkeypatch.setattr("app.main.stt.transcribe", fake_transcribe)

    async with fresh_client() as c:
        r = await c.post(
            "/api/turn",
            data={"question_id": qid},
            files={"audio": ("answer.webm", b"fake-webm", "audio/webm")},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["transcript"] == "panch"
    assert data["parsed_answer"] == 5
    assert data["is_correct"] is True
    assert data["next_question"]["id"] == lesson.DECK[1].id
    assert data["error"] is None


@pytest.mark.asyncio
async def test_multipart_stt_failure_falls_back_to_typed_answer(monkeypatch):
    qid = first_question_id()

    async def fake_transcribe(audio: bytes, *, content_type: str | None):
        return stt_module.STTResult(transcript=None, error="stt_timeout")

    monkeypatch.setattr("app.main.stt.transcribe", fake_transcribe)

    async with fresh_client() as c:
        r = await c.post(
            "/api/turn",
            data={"question_id": qid, "typed_answer": "5"},
            files={"audio": ("answer.webm", b"fake-webm", "audio/webm")},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["transcript"] == "5"
    assert data["parsed_answer"] == 5
    assert data["is_correct"] is True
    assert data["error"] == "stt_timeout"


@pytest.mark.asyncio
async def test_multipart_audio_without_transcript_keeps_question(monkeypatch):
    qid = first_question_id()

    async def fake_transcribe(audio: bytes, *, content_type: str | None):
        return stt_module.STTResult(transcript=None, error="empty_transcript")

    monkeypatch.setattr("app.main.stt.transcribe", fake_transcribe)

    async with fresh_client() as c:
        r = await c.post(
            "/api/turn",
            data={"question_id": qid},
            files={"audio": ("answer.webm", b"fake-webm", "audio/webm")},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["transcript"] is None
    assert data["parsed_answer"] is None
    assert data["attempt_count"] == 0
    assert data["next_question"]["id"] == qid
    assert data["error"] == "empty_transcript"
