"""Refresh the verified five-position STRATZ snapshot from a fixed-egress worker."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


API_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = API_DIR.parent
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from routers.players import (  # noqa: E402
    POSITION_META_SCOPES,
    STRATZ_META_SNAPSHOT,
    _cached_stratz_hero_stats,
    _global_meta_overview,
)


def main() -> int:
    if not os.getenv("STRATZ_API_TOKEN", "").strip():
        print("FAILED: STRATZ_API_TOKEN is not configured")
        return 1

    os.environ["STRATZ_RUNTIME_MODE"] = "live"
    stats, status, warning, week = _cached_stratz_hero_stats()
    if status != "ready" or not isinstance(stats, list):
        print(f"FAILED: {warning or status}")
        return 1

    snapshot = _global_meta_overview(stats, status, week)
    scopes = snapshot.get("hero_meta", {}).get("by_scope", {})
    missing = [scope["key"] for scope in POSITION_META_SCOPES if not scopes.get(scope["key"])]
    if not snapshot.get("available") or missing:
        print(f"FAILED: incomplete position scopes: {','.join(missing) or 'unknown'}")
        return 1

    snapshot.update({
        "warnings": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    STRATZ_META_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    temporary = STRATZ_META_SNAPSHOT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.replace(STRATZ_META_SNAPSHOT)
    print(
        "READY: "
        f"{snapshot['period_start']}..{snapshot['period_end']} "
        f"{len(stats)} rows {snapshot['snapshot']['heroes']} heroes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
