"""Training mission and player-confirmed match context endpoints."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from routers.players import _cached_get, _player_dashboard_payload
from services.training import (
    cancel_mission,
    delete_position_label,
    normalize_client_id,
    recommend_mission,
    save_position_label,
    start_mission,
    training_state,
)


router = APIRouter()


class MissionStartPayload(BaseModel):
    focus_key: str = Field(default="", max_length=40)


class PositionLabelPayload(BaseModel):
    position: int = Field(..., ge=1, le=5)


def _required_client_id(value: Optional[str]) -> str:
    try:
        return normalize_client_id(value or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _recent_match_belongs_to_player(account_id: int, match_id: str) -> bool:
    matches, warning = _cached_get(f"/players/{account_id}/matches", {"limit": 100}, timeout=15)
    if warning or not isinstance(matches, list):
        raise HTTPException(status_code=502, detail=warning or "Unable to verify the player match")
    return any(str(match.get("match_id") or "") == str(match_id) for match in matches if isinstance(match, dict))


@router.post("/players/{account_id}/training/missions")
def create_training_mission(
    account_id: int,
    payload: MissionStartPayload,
    x_dotasense_client: Optional[str] = Header(default=None, alias="X-DotaSense-Client"),
):
    client_id = _required_client_id(x_dotasense_client)
    dashboard = _player_dashboard_payload(account_id, 50, client_id)
    recommendation = recommend_mission(
        dashboard.get("recent_matches", []),
        dashboard.get("hero_pool", []),
        requested_focus=payload.focus_key,
    )
    try:
        start_mission(account_id, client_id, recommendation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return training_state(account_id, client_id, dashboard.get("recent_matches", []), dashboard.get("hero_pool", []))


@router.delete("/players/{account_id}/training/missions/{mission_id}")
def remove_training_mission(
    account_id: int,
    mission_id: str,
    x_dotasense_client: Optional[str] = Header(default=None, alias="X-DotaSense-Client"),
):
    client_id = _required_client_id(x_dotasense_client)
    if not cancel_mission(account_id, client_id, mission_id):
        raise HTTPException(status_code=404, detail="Active mission was not found")
    dashboard = _player_dashboard_payload(account_id, 50, client_id)
    return training_state(account_id, client_id, dashboard.get("recent_matches", []), dashboard.get("hero_pool", []))


@router.put("/players/{account_id}/matches/{match_id}/position")
def confirm_match_position(
    account_id: int,
    match_id: str,
    payload: PositionLabelPayload,
    x_dotasense_client: Optional[str] = Header(default=None, alias="X-DotaSense-Client"),
):
    client_id = _required_client_id(x_dotasense_client)
    if not _recent_match_belongs_to_player(account_id, match_id):
        raise HTTPException(status_code=404, detail="Match was not found in this player's recent public history")
    try:
        return save_position_label(account_id, client_id, match_id, payload.position)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/players/{account_id}/matches/{match_id}/position")
def clear_match_position(
    account_id: int,
    match_id: str,
    x_dotasense_client: Optional[str] = Header(default=None, alias="X-DotaSense-Client"),
):
    client_id = _required_client_id(x_dotasense_client)
    return {"ok": delete_position_label(account_id, client_id, match_id)}
