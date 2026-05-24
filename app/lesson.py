"""
Lesson engine.

Tracks per-session arithmetic practice: current question, attempt count,
streak, and which questions have been finished. The store is a plain
process-local dict — fine for the hackathon demo, swap for Redis later.

The engine deliberately knows nothing about voice, Gemini, or Silk.
It owns the deterministic part: pick a question, score an attempt,
decide whether to advance or retry.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from threading import Lock

# ---------- Questions ----------------------------------------------------

@dataclass(frozen=True)
class Question:
    id: str
    prompt: str          # Hinglish so the child reads it the same way the tutor speaks
    expected_answer: int


# Grade 1-3 add/sub deck. Keep it hand-authored — adaptive curriculum
# is explicitly out of scope for v1.
DECK: list[Question] = [
    Question("q01", "2 + 3 kitna hota hai?",   5),
    Question("q02", "4 + 1 kitna hota hai?",   5),
    Question("q03", "6 + 3 kitna hota hai?",   9),
    Question("q04", "7 + 5 kitna hota hai?",  12),
    Question("q05", "8 + 6 kitna hota hai?",  14),
    Question("q06", "9 + 4 kitna hota hai?",  13),
    Question("q07", "5 − 2 kitna hota hai?",   3),
    Question("q08", "7 − 3 kitna hota hai?",   4),
    Question("q09", "9 − 4 kitna hota hai?",   5),
    Question("q10", "10 − 6 kitna hota hai?",  4),
    Question("q11", "12 − 5 kitna hota hai?",  7),
    Question("q12", "14 − 8 kitna hota hai?",  6),
]

_BY_ID = {q.id: q for q in DECK}


def get_question(qid: str) -> Question | None:
    return _BY_ID.get(qid)


# ---------- Session ------------------------------------------------------

@dataclass
class Session:
    id: str
    current_question_id: str
    attempt_count: int = 0
    streak: int = 0
    completed_question_ids: list[str] = field(default_factory=list)


@dataclass
class TurnResult:
    """What `record_attempt` returns. The HTTP layer reshapes this into
    the public /api/turn response, so the engine stays transport-agnostic."""
    is_correct: bool
    expected_answer: int
    attempt_count: int
    streak: int
    next_question: Question | None      # None when the deck is done
    finished_question_id: str | None    # set when we advance off the current Q


# ---------- Store --------------------------------------------------------

class SessionStore:
    """Thread-safe in-memory session store. One per process.

    A child refreshing the page keeps the same session_id in localStorage,
    so as long as the server process stays up the lesson resumes naturally.
    Clearing localStorage starts a new lesson — good enough for a demo.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def get_or_create(self, session_id: str | None) -> Session:
        with self._lock:
            if session_id and session_id in self._sessions:
                return self._sessions[session_id]
            new_id = session_id or uuid.uuid4().hex
            session = Session(id=new_id, current_question_id=DECK[0].id)
            self._sessions[new_id] = session
            return session

    def record_attempt(self, session: Session, parsed_answer: int | None) -> TurnResult:
        """Score one attempt and mutate the session in place.

        Rules:
          - parsed_answer is None => ask again, same question, no streak change.
          - correct  => streak += 1, mark question complete, advance.
          - wrong    => streak = 0, attempt_count += 1, same question.
        """
        with self._lock:
            question = _BY_ID[session.current_question_id]

            if parsed_answer is None:
                return TurnResult(
                    is_correct=False,
                    expected_answer=question.expected_answer,
                    attempt_count=session.attempt_count,
                    streak=session.streak,
                    next_question=question,
                    finished_question_id=None,
                )

            session.attempt_count += 1
            is_correct = parsed_answer == question.expected_answer

            if is_correct:
                session.streak += 1
                session.completed_question_ids.append(question.id)
                next_q = _pick_next(session)
                if next_q is not None:
                    session.current_question_id = next_q.id
                    session.attempt_count = 0
                return TurnResult(
                    is_correct=True,
                    expected_answer=question.expected_answer,
                    attempt_count=0 if next_q else session.attempt_count,
                    streak=session.streak,
                    next_question=next_q,
                    finished_question_id=question.id,
                )

            session.streak = 0
            return TurnResult(
                is_correct=False,
                expected_answer=question.expected_answer,
                attempt_count=session.attempt_count,
                streak=session.streak,
                next_question=question,
                finished_question_id=None,
            )


def _pick_next(session: Session) -> Question | None:
    """Linear progression through the deck. Adaptive difficulty is v2."""
    for q in DECK:
        if q.id not in session.completed_question_ids:
            return q
    return None


# Module-level singleton — convenient for the FastAPI route.
store = SessionStore()
