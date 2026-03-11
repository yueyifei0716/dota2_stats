"""MMR-related API endpoints."""

from fastapi import APIRouter

from services.cache import read_mmr_history
import notion_db as nc
import notion_cache as cache

router = APIRouter()


@router.get("/mmr_history")
def get_mmr_history():
    return read_mmr_history()


@router.post("/update_mmr")
def update_mmr(data: dict):
    mmr = data.get("mmr")
    result = data.get("result", "")
    if mmr:
        try:
            mmr_int = int(mmr)
            nc.append_mmr_history(mmr_int, result)
            cache.invalidate("mmr_history")
            return {"success": True}
        except ValueError:
            return {"success": False, "message": "Invalid MMR value"}
    return {"success": False, "message": "Missing MMR"}


@router.post("/calibrate_mmr")
def calibrate_mmr(data: dict):
    mmr = data.get("mmr")
    if mmr:
        try:
            mmr_int = int(mmr)
            nc.update_profile({"current_mmr": mmr_int, "estimated_mmr": mmr_int})
            nc.append_mmr_history(mmr_int, "Calibrate")
            cache.invalidate("profile")
            cache.invalidate("mmr_history")
            return {"success": True}
        except ValueError:
            return {"success": False, "message": "Invalid MMR value"}
    return {"success": False, "message": "Missing MMR"}
