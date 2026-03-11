"""FastAPI entry point for Dota 2 Stats API."""

import sys
from pathlib import Path

# Add project root so we can import notion_db, notion_cache, fetch_dota_stats
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import dashboard, matches, heroes, mmr, actions, opendota

app = FastAPI(title="Dota 2 Stats API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
