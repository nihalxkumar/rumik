"""
Rumik FastAPI entrypoint.

Owns wiring only: static files, templates, routes. Real logic lives
in lesson.py / answer_parser.py / validator.py / stt.py / brain.py
and (later) tts.py.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile

from app import answer_parser, brain, lesson, stt, tts, tutor_fallback, validator
from app.schemas import NextQuestion, TurnRequest, TurnResponse

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Rumik")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ---------- Pages ---------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "stars": 12, "streak": 3},
    )


@app.get("/practice", response_class=HTMLResponse)
async def practice(request: Request) -> HTMLResponse:
    """Render the practice screen seeded with the first question of a
    fresh session. The browser will swap in subsequent questions via
    /api/turn so we don't reload the page mid-lesson."""
    first = lesson.DECK[0]
    return templates.TemplateResponse(
        "practice.html",
        {
            "request": request,
            "question_id": first.id,
            "question_prompt": first.prompt,
            "progress_percent": 0,
            "deck_total": len(lesson.DECK),
        },
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


# ---------- API ----------------------------------------------------

@app.post("/api/turn", response_model=TurnResponse)
async def api_turn(request: Request) -> TurnResponse:
    """One full lesson turn: score the answer, pick the next question,
    return the tutor line.

    Accepts both the Phase 2 JSON typed-answer path and the Phase 3
    multipart audio path. Both converge into a transcript string before
    deterministic parsing and scoring.
    """
    payload, audio, audio_content_type = await _read_turn_request(request)

    transcript = payload.typed_answer
    stt_error: str | None = None
    if audio is not None:
        stt_result = await stt.transcribe(audio, content_type=audio_content_type)
        transcript = stt_result.transcript or payload.typed_answer
        stt_error = stt_result.error

    session = lesson.store.get_or_create(payload.session_id)
    # Reject question_id mismatches loudly — they signal a stale tab,
    # which is better surfaced than silently re-scoring the wrong question.
    if payload.question_id != session.current_question_id:
        raise HTTPException(
            status_code=409,
            detail=f"stale question_id {payload.question_id}; expected {session.current_question_id}",
        )

    parsed = answer_parser.parse(transcript or "")
    result = lesson.store.record_attempt(session, parsed)

    question = lesson.get_question(payload.question_id)
    if question is None:
        raise HTTPException(status_code=409, detail=f"unknown question_id {payload.question_id}")

    tutor_text = await _tutor_line(
        brain.TutorContext(
            question=question,
            transcript=transcript,
            parsed_answer=parsed,
            expected_answer=result.expected_answer,
            is_correct=result.is_correct,
            streak=result.streak,
            attempt_count=result.attempt_count,
        ),
        parsed_was_none=parsed is None,
    )

    # Synthesize tutor text to audio via Silk.
    audio_base64 = None
    tts_error = None
    tts_result = await tts.synthesize(tutor_text)
    if tts_result.error:
        tts_error = tts_result.error
    else:
        audio_base64 = tts_result.audio_base64

    return TurnResponse(
        session_id=session.id,
        transcript=transcript,
        parsed_answer=parsed,
        expected_answer=result.expected_answer,
        is_correct=result.is_correct,
        attempt_count=result.attempt_count,
        streak=result.streak,
        tutor_text=tutor_text,
        audio_url=None,
        audio_base64=audio_base64,
        next_question=(
            NextQuestion(id=result.next_question.id, prompt=result.next_question.prompt)
            if result.next_question
            else None
        ),
        error=_turn_error(parsed=parsed, stt_error=stt_error, tts_error=tts_error),
    )


async def _read_turn_request(request: Request) -> tuple[TurnRequest, bytes | None, str | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("audio")
        audio: bytes | None = None
        audio_content_type: str | None = None
        if isinstance(upload, UploadFile):
            audio = await upload.read()
            audio_content_type = upload.content_type
        payload = TurnRequest(
            session_id=_form_str(form.get("session_id")),
            question_id=_required_form_str(form.get("question_id"), "question_id"),
            typed_answer=_form_str(form.get("typed_answer")),
        )
        return payload, audio, audio_content_type

    body = await request.json()
    return TurnRequest.model_validate(body), None, None


def _form_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _required_form_str(value: object, field_name: str) -> str:
    text = _form_str(value)
    if not text:
        raise HTTPException(status_code=422, detail=f"missing {field_name}")
    return text


def _turn_error(*, parsed: int | None, stt_error: str | None, tts_error: str | None = None) -> str | None:
    if parsed is not None:
        return stt_error or tts_error
    return stt_error or tts_error or "no_number_parsed"


async def _tutor_line(context: brain.TutorContext, *, parsed_was_none: bool) -> str:
    """Get a Gemini tutor line, falling back to local validated strings.

    The response must always pass the Silk validator before returning.
    """
    generated = await brain.generate_tutor_line(context)
    line = generated.text or tutor_fallback.pick(context.is_correct, parsed_was_none)
    return validator.validate(line)
