"""FastAPI entry point for Dota 2 Stats API."""

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent

# Vercel imports api/main.py from the repository root, while local uvicorn is
# commonly launched from api/. Keep both import styles working.
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(API_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import dashboard, matches, heroes, mmr, actions, opendota, players, commercial

app = FastAPI(title="Dota 2 Stats API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(heroes.router, prefix="/api")
app.include_router(mmr.router, prefix="/api")
app.include_router(actions.router, prefix="/api")
app.include_router(opendota.router, prefix="/api")
app.include_router(players.router, prefix="/api")
app.include_router(commercial.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
