import pytest

from app.answer_parser import parse


@pytest.mark.parametrize("text,expected", [
    ("12",                            12),
    ("twelve",                        12),
    ("barah",                         12),
    ("I think 12",                    12),
    ("mera answer 12 hai",            12),
    ("jawab barah hai",               12),
    ("the answer is twenty",          20),
    ("umm pandrah",                   15),
    ("",                              None),
    ("I don't know",                  None),
    # When multiple numbers appear, prefer the one after the cue word.
    ("first I said 5 but the answer is 12", 12),
    # No cue word — fall back to the last number.
    ("5 and 12",                      12),
])
def test_parse(text, expected):
    assert parse(text) == expected
