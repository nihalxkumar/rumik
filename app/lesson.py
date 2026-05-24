"""
Lesson engine — Phase 2.

Tracks per-session state for the arithmetic loop: current question,
attempt count, streak, completed questions. Server-side only,
in-memory dict keyed by session_id. Good enough for a hackathon
demo; swap for Redis later if needed.
"""
from dataclasses import dataclass, field


@dataclass
class Question:
    id: str
    prompt: str          # e.g. "7 + 5 kitna hota hai?"
    expected_answer: int


@dataclass
class Session:
    id: str
    current_question_id: str
    attempt_count: int = 0
    streak: int = 0
    completed_question_ids: list[str] = field(default_factory=list)


# Hardcoded Grade 1–3 add/sub deck — Phase 2 fleshes this out.
QUESTIONS: list[Question] = [
    Question("q1", "7 + 5 kitna hota hai?",  12),
    Question("q2", "9 − 4 kitna hota hai?",  5),
    Question("q3", "6 + 8 kitna hota hai?",  14),
]


def next_question(session: Session) -> Question | None:
    """Naive linear progression. Phase 2 may add difficulty bumps."""
    for q in QUESTIONS:
        if q.id not in session.completed_question_ids:
            return q
    return None
