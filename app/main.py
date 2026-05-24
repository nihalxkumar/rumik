"""
Rumik FastAPI entrypoint.

Owns wiring only: static files, templates, routes. Real logic lives
in lesson.py / answer_parser.py / validator.py and (later) stt.py,
brain.py, tts.py.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import answer_parser, lesson, tutor_fallback, validator
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
async def api_turn(payload: TurnRequest) -> TurnResponse:
    """One full lesson turn: score the answer, pick the next question,
    return the tutor line.

    Phase 2 supports the typed-answer path only. Phase 3 will accept
    multipart audio uploads on the same endpoint and run them through
    Deepgram before calling into the lesson engine.
    """
    session = lesson.store.get_or_create(payload.session_id)

    # Reject question_id mismatches loudly — they signal a stale tab,
    # which is better surfaced than silently re-scoring the wrong question.
    if payload.question_id != session.current_question_id:
        raise HTTPException(
            status_code=409,
            detail=f"stale question_id {payload.question_id}; expected {session.current_question_id}",
        )

    parsed = answer_parser.parse(payload.typed_answer or "")
    result = lesson.store.record_attempt(session, parsed)

    tutor_text = _tutor_line(result.is_correct, parsed_was_none=parsed is None)

    return TurnResponse(
        session_id=session.id,
        transcript=payload.typed_answer,
        parsed_answer=parsed,
        expected_answer=result.expected_answer,
        is_correct=result.is_correct,
        attempt_count=result.attempt_count,
        streak=result.streak,
        tutor_text=tutor_text,
        audio_url=None,
        audio_base64=None,
        next_question=(
            NextQuestion(id=result.next_question.id, prompt=result.next_question.prompt)
            if result.next_question
            else None
        ),
        error=None if parsed is not None else "no_number_parsed",
    )


def _tutor_line(is_correct: bool, *, parsed_was_none: bool) -> str:
    """Pick a local tutor line and confirm it passes the Silk validator.

    Doing this here — even with hand-authored strings — means phase 4's
    Gemini wiring inherits a code path that already validates before
    returning. The strings are also guaranteed Silk-safe by tests.
    """
    line = tutor_fallback.pick(is_correct, parsed_was_none)
    return validator.validate(line)
