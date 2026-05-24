"""
Deterministic answer parser.

The design doc is explicit: do not ask Gemini to decide correctness.
We parse the child's transcript (or typed input) into an int here,
before any AI sees it. Accept digits, English words, and Hinglish
Roman-script number words. Tolerate noise like "I think 12" or
"mera answer 12 hai".
"""
from __future__ import annotations

import re

# English number words up to 30 covers Grade 1-3 add/sub answers
# comfortably (max sum ~ 9 + 9 doubled is well under 30, and our deck
# stays in single + small-double-digit territory).
_EN_WORDS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
    "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
    "twenty-nine": 29, "thirty": 30,
}

# Hinglish (Roman-script Hindi) number words. Multiple spellings per
# number because Deepgram and children both vary. Keep this list
# tight — false positives are worse than missed numbers (we'd rather
# ask the child to repeat than score the wrong number).
_HI_WORDS: dict[str, int] = {
    "shunya": 0, "zero": 0,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4,
    "panch": 5, "paanch": 5, "che": 6, "cheh": 6, "chhe": 6,
    "saat": 7, "aath": 8, "nau": 9, "das": 10, "dus": 10,
    "gyarah": 11, "gyaarah": 11, "barah": 12, "baarah": 12,
    "terah": 13, "teraah": 13, "chaudah": 14, "chodah": 14,
    "pandrah": 15, "pandra": 15, "solah": 16, "sola": 16,
    "satrah": 17, "satra": 17, "atharah": 18, "athara": 18,
    "unnees": 19, "unees": 19, "bees": 20, "bis": 20,
    "ikkis": 21, "baais": 22, "bais": 22, "teis": 23, "tees": 30,
    "chaubis": 24, "pachees": 25, "pacchis": 25, "chhabbis": 26,
    "sattais": 27, "atthais": 28, "untees": 29,
}

_WORD_LOOKUP = {**_EN_WORDS, **_HI_WORDS}

# Words that signal "what follows is the actual answer". When the
# transcript has multiple numbers, prefer the one closest to one of
# these markers; otherwise take the last number.
_ANSWER_CUES = {
    "answer", "ans", "jawab", "jawaab", "hota", "hai", "equals", "is",
    "matlab", "barabar", "result",
}

_TOKEN_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)?|\d+")


def parse(text: str) -> int | None:
    """Return the parsed numeric answer, or None if we should ask again.

    Heuristic:
      1. Tokenize and convert each token to int if possible (digits or word).
      2. If exactly one number is found, return it.
      3. If multiple are found and a cue word ("answer", "jawab", ...)
         appears, return the number nearest (after) the last cue.
      4. Otherwise return the last number.
    """
    if not text:
        return None

    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    numbers: list[tuple[int, int]] = []   # (token_index, value)
    cue_indices: list[int] = []

    for i, tok in enumerate(tokens):
        if tok.isdigit():
            numbers.append((i, int(tok)))
        elif tok in _WORD_LOOKUP:
            numbers.append((i, _WORD_LOOKUP[tok]))
        elif tok in _ANSWER_CUES:
            cue_indices.append(i)

    if not numbers:
        return None
    if len(numbers) == 1:
        return numbers[0][1]

    if cue_indices:
        last_cue = cue_indices[-1]
        after = [(i, v) for (i, v) in numbers if i > last_cue]
        if after:
            return after[0][1]

    return numbers[-1][1]
