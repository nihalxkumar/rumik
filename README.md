# Rumik — Arithmetic Voice Tutor

Mobile-first AI tutor for Indian primary-school children. The child taps to speak
an answer to a simple arithmetic question, hears short Hinglish feedback, and
moves to the next question. Built for a 60-second judge demo.

See [`PLAN.md`](./PLAN.md) for the phase-by-phase build, and
[`../neo-main-design-20260524-150819.md`](../neo-main-design-20260524-150819.md)
for the original design.

## Stack

- **FastAPI** + Jinja2 — server-rendered, tiny payload
- **Vibrant Wonder Blocks** design system — single `tokens.css` +
  `components.css`, no Tailwind CDN
- **Deepgram → Gemini → Silk** voice pipeline (added in phases 3–5)

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in keys before phase 3
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000>. Mic access needs HTTPS on a real phone —
use Cloudflare Tunnel / ngrok for device testing.

## Layout

```
rumik/
├── app/
│   ├── main.py              # FastAPI wiring
│   ├── lesson.py            # Lesson engine (Phase 2)
│   ├── validator.py         # Silk-safe text validation (Phase 4)
│   ├── static/
│   │   ├── css/
│   │   │   ├── tokens.css       # Design tokens (single source of truth)
│   │   │   ├── base.css         # Resets + type scale + layout utilities
│   │   │   └── components.css   # .btn .card .pill .bubble .mic .progress ...
│   │   └── js/voice-loop.js     # MediaRecorder + /api/turn wiring
│   └── templates/
│       ├── base.html             # Loads fonts + tokens ONCE
│       ├── home.html
│       ├── practice.html
│       └── partials/
│           ├── _icon.html        # Material Symbols icon macro
│           └── _components.html  # button / card / pill / bubble / mic ...
└── tests/
```

## Design-system rules

1. **Never re-declare design tokens inline.** Use CSS variables from `tokens.css`.
2. **Never import Tailwind, fonts, or Material Symbols in a screen template.**
   `base.html` owns that.
3. **Compose with Jinja macros**, not copy-pasted markup.
4. **Subset everything you can.** Material Symbols is loaded with
   `icon_names=` so only the glyphs we actually use ship.
