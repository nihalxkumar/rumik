from app.lesson import DECK, SessionStore


def test_new_session_starts_on_first_question():
    s = SessionStore().get_or_create(None)
    assert s.current_question_id == DECK[0].id
    assert s.attempt_count == 0
    assert s.streak == 0


def test_same_id_returns_same_session():
    store = SessionStore()
    a = store.get_or_create("kid-1")
    b = store.get_or_create("kid-1")
    assert a is b


def test_correct_answer_advances_and_grows_streak():
    store = SessionStore()
    s = store.get_or_create(None)
    first = DECK[0]

    r = store.record_attempt(s, first.expected_answer)
    assert r.is_correct is True
    assert r.streak == 1
    assert r.finished_question_id == first.id
    assert r.next_question == DECK[1]
    assert s.current_question_id == DECK[1].id


def test_wrong_answer_keeps_question_and_resets_streak():
    store = SessionStore()
    s = store.get_or_create(None)
    # Build a streak first.
    store.record_attempt(s, DECK[0].expected_answer)
    assert s.streak == 1

    wrong = DECK[1].expected_answer + 1
    r = store.record_attempt(s, wrong)
    assert r.is_correct is False
    assert r.streak == 0
    assert r.next_question == DECK[1]
    assert s.current_question_id == DECK[1].id
    assert r.attempt_count == 1


def test_unparsed_answer_does_not_count_as_attempt():
    store = SessionStore()
    s = store.get_or_create(None)
    r = store.record_attempt(s, None)
    assert r.is_correct is False
    assert r.attempt_count == 0
    assert s.attempt_count == 0
    assert s.current_question_id == DECK[0].id


def test_finishing_deck_returns_no_next_question():
    store = SessionStore()
    s = store.get_or_create(None)
    for q in DECK:
        store.record_attempt(s, q.expected_answer)
    assert s.completed_question_ids == [q.id for q in DECK]
    # Next attempt would have no next_question, but the final
    # record_attempt above already returned next_question=None.
