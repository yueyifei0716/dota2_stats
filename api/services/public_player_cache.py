"""Bounded public-evidence snapshots; never stores training or client labels."""

from copy import deepcopy
import json
import os
from pathlib import Path
import time

MAX_AGE = 86400
SNAPSHOTS = Path(__file__).resolve().parents[1] / "snapshots" / "public_players"


def _directory():
    return Path(os.getenv("DOTASENSE_PUBLIC_CACHE_DIR", "/tmp/dotasense-public-players"))


def _valid(record, account_id, now):
    if not isinstance(record, dict) or record.get("account_id") != account_id:
        return False
    fetched = record.get("fetched_at")
    if type(fetched) not in (int, float) or not 0 <= now - fetched <= MAX_AGE:
        return False
    data = record.get("data")
    if not isinstance(data, dict) or data.get("profile", {}).get("account_id") != account_id:
        return False
    matches = data.get("recent_matches")
    return isinstance(matches, list) and all(isinstance(row, dict) and str(row.get("match_id", "")).isdigit() for row in matches)


def _public_fields(payload):
    data = deepcopy({key: payload[key] for key in (
        "profile", "recent_matches", "lifetime_heroes", "hero_meta", "counts", "rank_history"
    ) if key in payload})
    # A snapshot is public player evidence, not a user's private position labels.
    for row in data.get("recent_matches", []):
        if row.get("position_source") == "user_confirmed":
            row.update(position=0, position_key="", position_name="", position_source="unavailable", role_name="", role_source="unknown")
    return data


def load(account_id, now=None):
    now = time.time() if now is None else now
    candidates = []
    for path in (_directory() / f"{int(account_id)}.json", SNAPSHOTS / f"{int(account_id)}.json"):
        try:
            record = json.loads(path.read_text())
            if _valid(record, int(account_id), now):
                candidates.append(record)
        except (OSError, ValueError, TypeError):
            pass
    return deepcopy(max(candidates, key=lambda row: row["fetched_at"])) if candidates else None


def save(payload, now=None):
    account = payload.get("profile", {}).get("account_id")
    if type(account) is not int or account <= 0:
        return
    now = time.time() if now is None else now
    record = {"account_id": account, "fetched_at": now, "source": "OpenDota public player API", "data": _public_fields(payload)}
    if not _valid(record, account, now):
        return
    previous = load(account, now)
    if payload.get("data_stage") == "quick" and previous and len(previous["data"]["recent_matches"]) > len(record["data"]["recent_matches"]):
        return
    try:
        directory = _directory()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{account}.json"
        # A single process/thread replaces one complete JSON atomically.
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, suffix=".tmp", delete=False) as stream:
            json.dump(record, stream, ensure_ascii=False)
            temporary = Path(stream.name)
        temporary.replace(path)
        # Bound optional disk storage; bundled snapshots are never modified.
        records = sorted(directory.glob("*.json"), key=lambda file: file.stat().st_mtime, reverse=True)
        for old in records[100:]:
            old.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError):
        # Cache persistence must never prevent reading live public data.
        pass
