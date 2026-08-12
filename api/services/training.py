"""Persistent, evidence-bound training missions and player-confirmed labels."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
from threading import RLock
import time
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MISSION_SIZE = 3
_DB_LOCK = RLock()

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS training_missions (
        id TEXT PRIMARY KEY,
        account_id BIGINT NOT NULL,
        client_id TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at BIGINT NOT NULL,
        completed_at BIGINT,
        recommendation_json TEXT NOT NULL,
        result_json TEXT,
        created_at BIGINT NOT NULL,
        updated_at BIGINT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_training_missions_owner
        ON training_missions(account_id, client_id, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_training_missions_active
        ON training_missions(account_id, client_id, status)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_training_missions_one_active
        ON training_missions(account_id, client_id) WHERE status = 'active'
    """,
    """
    CREATE TABLE IF NOT EXISTS player_match_labels (
        account_id BIGINT NOT NULL,
        client_id TEXT NOT NULL,
        match_id TEXT NOT NULL,
        position INTEGER NOT NULL,
        source TEXT NOT NULL,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (account_id, client_id, match_id)
    )
    """,
)

POSITION_NAMES = {
    1: "1号位 核心",
    2: "2号位 中单",
    3: "3号位 劣势路",
    4: "4号位 游走",
    5: "5号位 硬辅",
}

METRICS = {
    "deaths": {"label": "场均死亡", "unit": "次", "direction": "lower", "digits": 1},
    "gold_per_min": {"label": "场均 GPM", "unit": "GPM", "direction": "higher", "digits": 0},
    "kda": {"label": "场均 KDA", "unit": "", "direction": "higher", "digits": 2},
}


def normalize_client_id(value: str) -> str:
    client_id = str(value or "").strip()
    if len(client_id) < 16 or len(client_id) > 128:
        raise ValueError("A valid DotaSense client identity is required")
    if not all(character.isalnum() or character in "-_" for character in client_id):
        raise ValueError("DotaSense client identity contains invalid characters")
    return client_id


def _database_path() -> Path:
    configured = os.getenv("DOTASENSE_DB_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    if os.getenv("VERCEL"):
        return Path("/tmp/dotasense/dotasense.sqlite3")
    return PROJECT_ROOT / ".data" / "dotasense.sqlite3"


def _postgres_url() -> str:
    if os.getenv("DOTASENSE_DB_PATH", "").strip():
        return ""
    return os.getenv("POSTGRES_URL", "").strip() or os.getenv("DATABASE_URL", "").strip()


def storage_status() -> Dict[str, Any]:
    postgres_configured = bool(_postgres_url())
    path_configured = bool(os.getenv("DOTASENSE_DB_PATH", "").strip())
    serverless = bool(os.getenv("VERCEL"))
    return {
        "backend": "postgresql" if postgres_configured else "sqlite",
        "persistent": postgres_configured or not serverless,
        "production_ready": postgres_configured or (path_configured and not serverless),
    }


def _execute(connection: Any, statement: str, params: Iterable[Any] = ()):
    query = statement.replace("?", "%s") if _postgres_url() else statement
    return connection.execute(query, tuple(params))


def _initialize_schema(connection: Any) -> None:
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)


def _connect() -> Any:
    postgres_url = _postgres_url()
    if postgres_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("PostgreSQL persistence requires psycopg") from exc
        connection = psycopg.connect(postgres_url, row_factory=dict_row, connect_timeout=5)
        _initialize_schema(connection)
        return connection

    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    _initialize_schema(connection)
    return connection


@contextmanager
def _database():
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _loads(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def save_position_label(account_id: int, client_id: str, match_id: str, position: int) -> Dict[str, Any]:
    owner = normalize_client_id(client_id)
    match_key = str(match_id).strip()
    if not match_key.isdigit() or len(match_key) > 32:
        raise ValueError("A valid match id is required")
    if position not in POSITION_NAMES:
        raise ValueError("Position must be between 1 and 5")

    now = int(time.time())
    with _DB_LOCK, _database() as connection:
        _execute(connection,
            """
            INSERT INTO player_match_labels(account_id, client_id, match_id, position, source, updated_at)
            VALUES (?, ?, ?, ?, 'user_confirmed', ?)
            ON CONFLICT(account_id, client_id, match_id) DO UPDATE SET
                position = excluded.position,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (int(account_id), owner, match_key, position, now),
        )
    return {
        "match_id": match_key,
        "position": position,
        "position_key": f"pos{position}",
        "position_name": POSITION_NAMES[position],
        "position_source": "user_confirmed",
        "updated_at": now,
    }


def delete_position_label(account_id: int, client_id: str, match_id: str) -> bool:
    owner = normalize_client_id(client_id)
    with _DB_LOCK, _database() as connection:
        cursor = _execute(connection,
            "DELETE FROM player_match_labels WHERE account_id = ? AND client_id = ? AND match_id = ?",
            (int(account_id), owner, str(match_id)),
        )
    return cursor.rowcount > 0


def load_position_labels(account_id: int, client_id: str, match_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    if not client_id:
        return {}
    owner = normalize_client_id(client_id)
    keys = [str(match_id) for match_id in match_ids if str(match_id)]
    if not keys:
        return {}
    placeholders = ",".join("?" for _ in keys)
    with _DB_LOCK, _database() as connection:
        rows = _execute(connection,
            f"""
            SELECT match_id, position, source, updated_at
            FROM player_match_labels
            WHERE account_id = ? AND client_id = ? AND match_id IN ({placeholders})
            """,
            [int(account_id), owner, *keys],
        ).fetchall()
    return {
        row["match_id"]: {
            "match_id": row["match_id"],
            "position": int(row["position"]),
            "position_key": f"pos{int(row['position'])}",
            "position_name": POSITION_NAMES.get(int(row["position"]), ""),
            "position_source": row["source"],
            "updated_at": int(row["updated_at"]),
        }
        for row in rows
    }


def _metric_values(matches: List[Dict[str, Any]], metric_key: str, limit: int = 10) -> List[float]:
    values: List[float] = []
    for match in matches[:limit]:
        raw_value = match.get(metric_key)
        if raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if value != value or value < 0:
            continue
        if metric_key == "gold_per_min" and value <= 0:
            continue
        values.append(value)
    return values


def _average(values: List[float], digits: int) -> float:
    return round(sum(values) / len(values), digits) if values else 0


def recommend_mission(
    matches: List[Dict[str, Any]],
    hero_pool: List[Dict[str, Any]],
    requested_focus: str = "",
) -> Dict[str, Any]:
    death_values = _metric_values(matches, "deaths")
    gpm_values = _metric_values(matches, "gold_per_min")
    kda_values = _metric_values(matches, "kda")

    metric_values = {
        "deaths": death_values,
        "gold_per_min": gpm_values,
        "kda": kda_values,
    }
    if requested_focus in METRICS and metric_values[requested_focus]:
        focus_key = requested_focus
    elif death_values and _average(death_values, 1) >= 6:
        focus_key = "deaths"
    elif len(gpm_values) >= 3:
        focus_key = "gold_per_min"
    elif kda_values:
        focus_key = "kda"
    elif death_values:
        focus_key = "deaths"
    elif gpm_values:
        focus_key = "gold_per_min"
    else:
        return {
            "available": False,
            "focus_key": "deaths",
            "title": "暂无可用训练基线",
            "reason": "最近没有可用于比较的公开比赛结算数据。",
            "drill": "产生新的公开比赛后刷新，即可创建三局训练。",
            "metric_label": METRICS["deaths"]["label"],
            "unit": METRICS["deaths"]["unit"],
            "direction": METRICS["deaths"]["direction"],
            "baseline_value": None,
            "target_value": None,
            "baseline_games": 0,
            "target_games": MISSION_SIZE,
            "recommended_hero": {"hero_id": 0, "hero_name": "", "hero_icon": ""},
            "evidence": "未获取公开比赛结算",
        }

    values = metric_values[focus_key]
    metric = METRICS[focus_key]
    baseline = _average(values, int(metric["digits"]))
    if focus_key == "deaths":
        target = round(max(1.0, baseline - 1.0), 1)
        title = "减少无收益死亡"
        reason = f"最近 {len(values)} 场场均死亡 {baseline} 次，下一组三局先减少 1 次。"
        drill = "每局结束只记录最高代价的一次死亡，并检查当时视野、队友距离和关键装备是否可用。"
    elif focus_key == "gold_per_min":
        target = round(baseline + 25)
        title = "修复经济断档"
        reason = f"最近 {len(values)} 场有完整结算的比赛场均 {baseline:.0f} GPM。"
        drill = "下一组三局减少无收益移动；每局结算时记录 GPM，并复查死亡后的第一条刷钱路线。"
    else:
        target = round(baseline + 0.25, 2)
        title = "提高有效参战"
        reason = f"最近 {len(values)} 场场均 KDA 为 {baseline}。"
        drill = "下一组三局只参加能交换击杀、塔或 Roshan 的行动，结算后记录 KDA。"

    hero = hero_pool[0] if hero_pool else {}
    return {
        "available": True,
        "focus_key": focus_key,
        "title": title,
        "reason": reason,
        "drill": drill,
        "metric_label": metric["label"],
        "unit": metric["unit"],
        "direction": metric["direction"],
        "baseline_value": baseline,
        "target_value": target,
        "baseline_games": len(values),
        "target_games": MISSION_SIZE,
        "recommended_hero": {
            "hero_id": int(hero.get("hero_id") or 0),
            "hero_name": str(hero.get("hero_name") or ""),
            "hero_icon": str(hero.get("hero_icon") or ""),
        },
        "evidence": "OpenDota 公开比赛结算",
    }


def start_mission(
    account_id: int,
    client_id: str,
    recommendation: Dict[str, Any],
    now: Optional[int] = None,
) -> Dict[str, Any]:
    owner = normalize_client_id(client_id)
    focus_key = str(recommendation.get("focus_key") or "")
    if focus_key not in METRICS or not recommendation.get("available", True):
        raise ValueError("Unsupported training focus")
    if recommendation.get("baseline_value") is None or recommendation.get("target_value") is None:
        raise ValueError("Training baseline is unavailable")
    timestamp = int(now or time.time())
    mission_id = uuid4().hex
    payload = json.dumps(recommendation, ensure_ascii=False, separators=(",", ":"))

    with _DB_LOCK, _database() as connection:
        _execute(connection,
            """
            UPDATE training_missions
            SET status = 'cancelled', updated_at = ?
            WHERE account_id = ? AND client_id = ? AND status = 'active'
            """,
            (timestamp, int(account_id), owner),
        )
        _execute(connection,
            """
            INSERT INTO training_missions(
                id, account_id, client_id, status, started_at, completed_at,
                recommendation_json, result_json, created_at, updated_at
            ) VALUES (?, ?, ?, 'active', ?, NULL, ?, NULL, ?, ?)
            """,
            (mission_id, int(account_id), owner, timestamp, payload, timestamp, timestamp),
        )
    return {
        "id": mission_id,
        "account_id": int(account_id),
        "client_id": owner,
        "status": "active",
        "started_at": timestamp,
        "completed_at": None,
        "recommendation": recommendation,
        "result": None,
    }


def _row_to_mission(row: Any) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "account_id": int(row["account_id"]),
        "client_id": row["client_id"],
        "status": row["status"],
        "started_at": int(row["started_at"]),
        "completed_at": int(row["completed_at"]) if row["completed_at"] else None,
        "recommendation": _loads(row["recommendation_json"], {}),
        "result": _loads(row["result_json"], None),
    }


def get_active_mission(account_id: int, client_id: str) -> Optional[Dict[str, Any]]:
    if not client_id:
        return None
    owner = normalize_client_id(client_id)
    with _DB_LOCK, _database() as connection:
        row = _execute(connection,
            """
            SELECT * FROM training_missions
            WHERE account_id = ? AND client_id = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
            """,
            (int(account_id), owner),
        ).fetchone()
    return _row_to_mission(row) if row else None


def cancel_mission(account_id: int, client_id: str, mission_id: str) -> bool:
    owner = normalize_client_id(client_id)
    now = int(time.time())
    with _DB_LOCK, _database() as connection:
        cursor = _execute(connection,
            """
            UPDATE training_missions SET status = 'cancelled', updated_at = ?
            WHERE id = ? AND account_id = ? AND client_id = ? AND status = 'active'
            """,
            (now, str(mission_id), int(account_id), owner),
        )
    return cursor.rowcount > 0


def _mission_match_payload(match: Dict[str, Any], metric_key: str) -> Optional[Dict[str, Any]]:
    values = _metric_values([match], metric_key, limit=1)
    if not values:
        return None
    return {
        "match_id": str(match.get("match_id") or ""),
        "hero_id": int(match.get("hero_id") or 0),
        "hero_name": str(match.get("hero_name") or ""),
        "hero_icon": str(match.get("hero_icon") or ""),
        "win": bool(match.get("win")),
        "kills": int(match.get("kills") or 0),
        "deaths": int(match.get("deaths") or 0),
        "assists": int(match.get("assists") or 0),
        "played_at": str(match.get("played_at") or ""),
        "start_time": int(match.get("start_time") or 0),
        "metric_value": values[0],
    }


def _persist_completed_mission(mission: Dict[str, Any], result: Dict[str, Any], completed_at: int) -> None:
    with _DB_LOCK, _database() as connection:
        _execute(connection,
            """
            UPDATE training_missions
            SET status = 'completed', completed_at = ?, result_json = ?, updated_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (
                completed_at,
                json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                completed_at,
                mission["id"],
            ),
        )


def evaluate_mission(mission: Dict[str, Any], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    if mission.get("status") == "completed" and isinstance(mission.get("result"), dict):
        return {**mission, "progress": mission["result"]}

    recommendation = mission.get("recommendation") or {}
    focus_key = str(recommendation.get("focus_key") or "")
    metric = METRICS.get(focus_key, METRICS["deaths"])
    candidates = sorted(
        (match for match in matches if int(match.get("start_time") or 0) > int(mission.get("started_at") or 0)),
        key=lambda match: int(match.get("start_time") or 0),
    )
    mission_matches = []
    for match in candidates:
        payload = _mission_match_payload(match, focus_key)
        if payload:
            mission_matches.append(payload)
        if len(mission_matches) == MISSION_SIZE:
            break

    values = [float(match["metric_value"]) for match in mission_matches]
    current_value = _average(values, int(metric["digits"])) if values else None
    target_value = float(recommendation.get("target_value") or 0)
    complete = len(mission_matches) >= MISSION_SIZE
    achieved = None
    if complete and current_value is not None:
        achieved = current_value <= target_value if metric["direction"] == "lower" else current_value >= target_value

    baseline = float(recommendation.get("baseline_value") or 0)
    delta = round(current_value - baseline, int(metric["digits"])) if current_value is not None else None
    result = {
        "completed_games": len(mission_matches),
        "target_games": MISSION_SIZE,
        "current_value": current_value,
        "target_value": target_value,
        "baseline_value": baseline,
        "delta": delta,
        "achieved": achieved,
        "matches": mission_matches,
    }

    if complete:
        completed_at = max(match["start_time"] for match in mission_matches)
        _persist_completed_mission(mission, result, completed_at)
        return {
            **mission,
            "status": "completed",
            "completed_at": completed_at,
            "result": result,
            "progress": result,
        }
    return {**mission, "progress": result}


def list_recent_missions(account_id: int, client_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    if not client_id:
        return []
    owner = normalize_client_id(client_id)
    with _DB_LOCK, _database() as connection:
        rows = _execute(connection,
            """
            SELECT * FROM training_missions
            WHERE account_id = ? AND client_id = ? AND status != 'active'
            ORDER BY created_at DESC LIMIT ?
            """,
            (int(account_id), owner, max(1, min(limit, 20))),
        ).fetchall()
    return [_row_to_mission(row) for row in rows]


def training_state(
    account_id: int,
    client_id: str,
    matches: List[Dict[str, Any]],
    hero_pool: List[Dict[str, Any]],
) -> Dict[str, Any]:
    recommendation = recommend_mission(matches, hero_pool)
    active = get_active_mission(account_id, client_id) if client_id else None
    evaluated = evaluate_mission(active, matches) if active else None
    history = list_recent_missions(account_id, client_id, limit=4) if client_id else []
    if evaluated and evaluated.get("status") == "completed":
        history = [evaluated, *[mission for mission in history if mission["id"] != evaluated["id"]]][:4]
        evaluated = None
    return {
        "recommendation": recommendation,
        "active_mission": evaluated,
        "history": history,
        "storage": storage_status(),
    }
