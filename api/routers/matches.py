"""Match-related API endpoints."""

from fastapi import APIRouter, Query
from typing import Optional

from services.cache import read_matches
from services.stats import enrich_match
import notion_db as nc
import notion_cache as cache

router = APIRouter()


@router.get("/matches")
def get_matches(hero: Optional[str] = None, role: Optional[int] = None, limit: int = Query(100, le=200)):
    matches = read_matches()
    for m in matches:
        enrich_match(m)

    if hero:
        matches = [m for m in matches if m.get("hero_cn") == hero]
    if role:
        matches = [m for m in matches if (m.get("role") or m.get("lane_role", 0)) == role]

    return matches[:limit]


@router.get("/match_notes")
def get_match_notes(match_id: Optional[str] = None):
    matches = read_matches()
    if match_id:
        for m in matches:
            if m.get("match_id") == match_id:
                return {"note": m.get("note", "")}
        return {"note": ""}
    return {m["match_id"]: m.get("note", "") for m in matches if "match_id" in m}


@router.post("/match_notes")
def save_match_note(data: dict):
    match_id = data.get("match_id")
    if not match_id:
        return {"success": False, "message": "缺少match_id"}
    note = data.get("note", "")
    nc.update_match_note(str(match_id), note)
    cache.invalidate("matches")
    return {"success": True, "message": "笔记已保存"}
