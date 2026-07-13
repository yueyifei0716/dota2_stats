"""Commercial conversion endpoints for DotaSense."""

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()

ACCESS_TOKEN_TTL = 60 * 60 * 24 * 30

PLAN_CONFIG = {
    "founder": {
        "name": "Founder Pro",
        "price": "¥19/月",
        "checkout_env": "DOTASENSE_CHECKOUT_FOUNDER_URL",
    },
    "review": {
        "name": "单次复盘",
        "price": "¥49/次",
        "checkout_env": "DOTASENSE_CHECKOUT_REVIEW_URL",
    },
    "team": {
        "name": "战队空间",
        "price": "¥199/月",
        "checkout_env": "DOTASENSE_CHECKOUT_TEAM_URL",
    },
}


class LeadPayload(BaseModel):
    account_id: Optional[int] = None
    plan: str = Field(default="founder", max_length=32)
    contact: str = Field(..., min_length=2, max_length=120)
    role: str = Field(default="", max_length=60)
    goal: str = Field(default="", max_length=500)
    source: str = Field(default="web", max_length=80)


class AccessPayload(BaseModel):
    code: str = Field(..., min_length=2, max_length=120)
    account_id: Optional[int] = None
    plan: str = Field(default="founder", max_length=32)


def _checkout_url(plan: str) -> str:
    config = PLAN_CONFIG.get(plan)
    if not config:
        return ""
    return os.getenv(config["checkout_env"], "")


def _lead_store_path() -> Path:
    configured = os.getenv("DOTASENSE_LEADS_PATH")
    if configured:
        return Path(configured)
    return Path("/tmp/dotasense_leads.jsonl")


def _append_lead(record: Dict[str, Any]) -> None:
    path = _lead_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _send_webhook(record: Dict[str, Any]) -> bool:
    webhook_url = os.getenv("DOTASENSE_LEADS_WEBHOOK_URL")
    if not webhook_url:
        return False
    try:
        response = requests.post(webhook_url, json=record, timeout=8)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def _access_secret() -> str:
    return os.getenv("DOTASENSE_ACCESS_SECRET") or os.getenv("DOTASENSE_PRO_ACCESS_CODE", "")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def _sign_access_body(body: str) -> str:
    secret = _access_secret()
    return hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_access_token(account_id: Optional[int], plan: str = "founder") -> Dict[str, Any]:
    selected_plan = plan if plan in PLAN_CONFIG else "founder"
    expires_at = int(time.time()) + ACCESS_TOKEN_TTL
    token_payload = {
        "account_id": int(account_id or 0),
        "expires_at": expires_at,
        "plan": selected_plan,
    }
    body = json.dumps(token_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    signature = _sign_access_body(body)
    return {
        "access_token": f"{_b64encode(body.encode('utf-8'))}.{signature}",
        "expires_at": expires_at,
        "plan": selected_plan,
        "ttl_seconds": ACCESS_TOKEN_TTL,
    }


def verify_access_token(token: Optional[str], account_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    secret = _access_secret()
    if not secret or not token or "." not in token:
        return None

    encoded_body, provided_signature = token.split(".", 1)
    try:
        body = _b64decode(encoded_body).decode("utf-8")
        payload = json.loads(body)
    except (ValueError, json.JSONDecodeError):
        return None

    expected_signature = _sign_access_body(body)
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    expires_at = int(payload.get("expires_at") or 0)
    if expires_at < int(time.time()):
        return None

    token_account = int(payload.get("account_id") or 0)
    if account_id is not None and token_account and token_account != int(account_id):
        return None

    return payload


def _bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        return ""
    prefix = "Bearer "
    if authorization.startswith(prefix):
        return authorization[len(prefix):].strip()
    return authorization.strip()


@router.get("/commercial/config")
def commercial_config():
    plans = []
    for key, config in PLAN_CONFIG.items():
        checkout = _checkout_url(key)
        plans.append({
            "key": key,
            "name": config["name"],
            "price": config["price"],
            "checkout_configured": bool(checkout),
        })

    return {
        "plans": plans,
        "sales_contact": os.getenv("DOTASENSE_SALES_CONTACT", ""),
        "sales_url": os.getenv("DOTASENSE_SALES_URL", ""),
        "discord_url": os.getenv("DOTASENSE_DISCORD_URL", ""),
        "webhook_configured": bool(os.getenv("DOTASENSE_LEADS_WEBHOOK_URL")),
        "access_code_configured": bool(os.getenv("DOTASENSE_PRO_ACCESS_CODE")),
    }


@router.post("/commercial/leads")
def create_lead(payload: LeadPayload):
    plan = payload.plan if payload.plan in PLAN_CONFIG else "founder"
    record = {
        "created_at": int(time.time()),
        "account_id": payload.account_id,
        "plan": plan,
        "plan_name": PLAN_CONFIG[plan]["name"],
        "contact": payload.contact.strip(),
        "role": payload.role.strip(),
        "goal": payload.goal.strip(),
        "source": payload.source.strip(),
    }
    _append_lead(record)
    print("DOTASENSE_LEAD " + json.dumps(record, ensure_ascii=False))
    delivered = _send_webhook(record)
    checkout_url = _checkout_url(plan)

    return {
        "ok": True,
        "plan": plan,
        "lead_delivered": delivered,
        "checkout_url": checkout_url,
        "next_step": "checkout" if checkout_url else "manual_contact",
    }


@router.post("/commercial/access")
def create_access(payload: AccessPayload):
    expected_code = os.getenv("DOTASENSE_PRO_ACCESS_CODE", "").strip()
    if not expected_code:
        raise HTTPException(status_code=503, detail="Pro access code is not configured")

    provided_code = payload.code.strip()
    if not hmac.compare_digest(provided_code, expected_code):
        raise HTTPException(status_code=401, detail="Invalid Pro access code")

    issued = issue_access_token(payload.account_id, payload.plan)
    return {
        "ok": True,
        "account_id": payload.account_id,
        **issued,
    }


@router.get("/commercial/access/verify")
def verify_access(
    account_id: Optional[int] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
):
    payload = verify_access_token(_bearer_token(authorization), account_id)
    return {
        "ok": bool(payload),
        "account_id": payload.get("account_id") if payload else account_id,
        "plan": payload.get("plan") if payload else "",
        "expires_at": payload.get("expires_at") if payload else 0,
    }
