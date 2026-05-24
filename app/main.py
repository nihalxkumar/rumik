"""
Rumik FastAPI entrypoint.

Owns nothing but wiring: static files, templates, routes. Real logic
lives in lesson.py / stt.py / brain.py / validator.py / tts.py (added
in later phases).
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Rumik")

# Static assets served at /static — referenced via url_for in templates.
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Landing screen — pick a lesson block."""
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "stars": 12, "streak": 3},
    )


@app.get("/practice", response_class=HTMLResponse)
async def practice(request: Request) -> HTMLResponse:
    """Active practice voice loop. Wires to /api/turn (Phase 3+)."""
    return templates.TemplateResponse(
        "practice.html",
        {
            "request": request,
            "question": "7 + 5 kitna hota hai?",
            "progress_percent": 45,
        },
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
