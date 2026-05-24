"""
Public /api/turn request + response contract.

Locked early so the frontend, the lesson engine, the Gemini path
(phase 4), and the Silk path (phase 5) all target the same shape.
Optional fields will be filled in by later phases. In Phase 3,
`transcript` is either the typed answer or the Deepgram transcript.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TurnRequest(BaseModel):
    session_id: str | None = None
    question_id: str
    typed_answer: str | None = None
    # Multipart requests carry the audio UploadFile outside this JSON schema.


class NextQuestion(BaseModel):
    id: str
    prompt: str


class TurnResponse(BaseModel):
    session_id: str
    transcript: str | None
    parsed_answer: int | None
    expected_answer: int
    is_correct: bool
    attempt_count: int
    streak: int
    tutor_text: str
    audio_url: str | None = None
    audio_base64: str | None = None
    next_question: NextQuestion | None
    error: str | None = Field(
        default=None,
        description="Set when a fallback path is taken (mic denied, STT failure, etc.)",
    )
