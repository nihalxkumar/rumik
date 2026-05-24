# Rumik — Phase-by-Phase Build Plan

This plan turns the design doc and the four Stitch mockups into a working
hackathon demo. Every phase is small enough to ship in one sitting and ends
with something visibly working. The order is chosen so the demo stays
runnable from Phase 1 onward — at no point is the app broken between phases.

The guiding principles: **mobile-first, real APIs, fast on cheap Android**,
and **shared design tokens instead of per-screen Tailwind configs**.

---

## Phase 0 — Confirm Silk API contract  *(blocking, design-doc step zero)*

Before any TTS code is written we need Silk's supported tags, request shape,
audio response format, timeout behavior, and failure codes. Without this,
`validator.py` and `tts.py` are guessing.

**Done when:** `docs/silk-contract.md` exists with sample request + response
captured from a real call.

---

## Phase 1 — Foundations  *(this PR — done)*

The scaffold lays down everything every later phase depends on, so we never
have to refactor design tokens or template structure later.

- FastAPI app with `/`, `/practice`, `/healthz`
- Shared design system:
  - `tokens.css` — colors, spacing, radii, shadows, type, motion (CSS vars)
  - `base.css` — reset, type scale, layout primitives
  - `components.css` — `.btn .card .pill .bubble .mic .progress .chip .toast`
- `base.html` template: fonts + tokens loaded **once**, with Material Symbols
  subsetted to the 13 icons used across all four mockups
- Jinja macros for `button`, `card`, `pill`, `tutor_bubble`, `mic_button`,
  `progress`, `chip`, `icon`
- Home screen and Practice screen rendered from those macros (proves the
  system works end-to-end)
- `validator.py` + tests for the Silk-safe text rules (cheap to do early)
- `.env.example` with the three keys + per-API timeouts

**Done when:** `uvicorn app.main:app` shows the home screen and the practice
screen, both styled correctly, with zero Tailwind CDN, zero duplicate font
imports, and `pytest` green.

---

## Phase 2 — Lesson engine + typed-answer fallback

Builds the boring brain of the app before any AI is wired in. This keeps
correctness deterministic and decoupled from Gemini.

- `lesson.py`: in-memory `Session` store keyed by `session_id` (cookie or
  localStorage); `next_question`, `record_attempt` (correctness, streak,
  attempt_count); JSON deck of ~15 Grade 1–3 add/sub questions
- `answer_parser.py`: digits, English words, Hindi/Hinglish number words
  (`barah`, `pandrah`, …), tolerant of `"I think 12"` / `"mera answer 12 hai"`
- `/api/turn` endpoint accepting **`typed_answer`** only (no audio yet),
  returning the full response shape from the design doc
- Hook the practice screen to `/api/turn` via the typed-answer path so the
  whole correctness loop is dogfoodable before any voice work

**Done when:** I can play a full lesson on desktop using typed answers,
streak/attempts update, and `next_question` rotates through the deck.

---

## Phase 3 — Voice input (Deepgram)

Adds the speech half of the loop. Still no Gemini — tutor lines fall back to
local strings — so we can confirm STT latency in isolation.

- Browser `MediaRecorder` in `voice-loop.js`: tap-to-start / tap-to-stop,
  webm/opus upload to `/api/turn`
- Mic state machine wired to `.mic[data-state]`: idle → recording → uploading
  → thinking → speaking → complete
- `stt.py`: Deepgram client with the 4-second timeout from the doc; on
  timeout the turn falls back to typed answer flow
- "Mic denied" path that reveals the typed-answer input
- "No number parsed" path that keeps the same question with a clear chip

**Done when:** On real phone over HTTPS I can speak a number and see it
transcribed + scored in under 5 s.

---

## Phase 4 — Tutor brain (Gemini → validator → fallback)

This is where the demo starts to feel alive. The validator from Phase 1 is
the safety net keeping Silk happy.

- `brain.py`: Gemini prompt + 3 s timeout; structured input (question,
  expected, parsed, is_correct, streak, attempt_count)
- One retry if `validator.validate()` rejects the response
- Hardcoded fallback lines per correctness state for when Gemini fails or
  the validator rejects twice
- Render the tutor line in the existing `.bubble` macro on the practice screen

**Done when:** Both correct and wrong answers produce on-brand Hinglish
text that always passes validation.

---

## Phase 5 — Voice output (Silk)

The loop closes. Latency budgets become visible.

- `tts.py`: Silk client with 5 s timeout; returns base64 audio or URL per
  Phase 0 contract
- Audio playback from `voice-loop.js` with autoplay fallback ("Play tutor
  voice" button when the browser blocks autoplay)
- "Silk failure" path: show the validated text and a Retry-audio button
- Hard 15 s total turn budget — if any leg exceeds, fall back to text

**Done when:** A judge can complete one full turn on a phone in <20 s,
hearing the tutor speak.

---

## Phase 6 — Remaining screens

The four Stitch mockups become real, all reusing the same macros.

- Session summary screen (`/summary`) — `card` + `progress` + `pill`
- Parent view (`/parent`) — read-only stats, reusing `pill` and `card`
- Polish: floating mascot art, pop-in animations on result, toast on streak
  milestones (Mint Green Success block per DESIGN.md)

**Done when:** All four screens render from shared components — no screen
re-declares colors, fonts, or shadow values.

---

## Phase 7 — Hackathon hardening

Everything that keeps a live demo alive.

- Manual deploy script for chosen host (Render / Fly / Railway — TBD)
- HTTPS verified on a real phone
- All eight failure cases from the design doc smoke-tested with a checklist
- Lighthouse pass on mid-tier Android emulation: ≥ 90 perf, < 200 KB JS,
  < 100 KB CSS, < 50 KB initial fonts (with `icon_names=` subset)
- One-page judge crib sheet: opening flow, two backup questions, recovery
  steps for each known failure

**Done when:** The demo survives at least one full "unplug the wifi /
plug back in" rehearsal without breaking.

---

## What's deliberately not in this plan

The design doc's Out-of-Scope list is honored: no grade switching, no
multilingual switching, no DB-backed accounts, no app-store packaging,
no judge-theater mode as primary surface. Adaptive difficulty stays
simple (linear progression through a hand-authored deck).
