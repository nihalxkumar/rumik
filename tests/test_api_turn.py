"""End-to-end tests for /api/turn (typed-answer path, phase 2)."""
from fastapi.testclient import TestClient

from app import lesson
from app.main import app


def fresh_client():
    # Each test gets its own session store so streaks don't leak.
    lesson.store = lesson.SessionStore()
    return TestClient(app)


def first_question_id() -> str:
    return lesson.DECK[0].id


def test_correct_typed_answer_advances():
    c = fresh_client()
    qid = first_question_id()
    expected = lesson.DECK[0].expected_answer

    r = c.post("/api/turn", json={
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


def test_wrong_typed_answer_keeps_question():
    c = fresh_client()
    qid = first_question_id()
    wrong = lesson.DECK[0].expected_answer + 7

    r = c.post("/api/turn", json={
        "session_id": None,
        "question_id": qid,
        "typed_answer": str(wrong),
    })

    data = r.json()
    assert data["is_correct"] is False
    assert data["streak"] == 0
    assert data["next_question"]["id"] == qid


def test_unparseable_answer_returns_error_field():
    c = fresh_client()
    qid = first_question_id()

    r = c.post("/api/turn", json={
        "session_id": None,
        "question_id": qid,
        "typed_answer": "I dunno",
    })

    data = r.json()
    assert data["error"] == "no_number_parsed"
    assert data["parsed_answer"] is None
    assert data["is_correct"] is False
    assert data["next_question"]["id"] == qid


def test_stale_question_id_returns_409():
    c = fresh_client()
    qid = first_question_id()

    # First turn: get back the assigned session_id and advance past q1.
    r = c.post("/api/turn", json={
        "session_id": None,
        "question_id": qid,
        "typed_answer": str(lesson.DECK[0].expected_answer),
    })
    assert r.status_code == 200
    sid = r.json()["session_id"]

    # Posting the now-completed question_id should 409 — that means a
    # stale browser tab, which we'd rather surface than silently re-score.
    stale = c.post("/api/turn", json={
        "session_id": sid,
        "question_id": qid,
        "typed_answer": "1",
    })
    assert stale.status_code == 409
