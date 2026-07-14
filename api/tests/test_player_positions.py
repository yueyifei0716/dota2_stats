import unittest
from concurrent.futures import ThreadPoolExecutor
import os
import time
from unittest.mock import patch

from routers.players import (
    _apply_stratz_match_data,
    _cache,
    _cached_stratz_player_matches,
    _position_meta_fit,
    _role_matrix,
    _stratz_graphql,
    _stratz_meta_snapshot,
    meta_overview,
)


class PlayerPositionTests(unittest.TestCase):
    def test_snapshot_runtime_skips_ip_locked_stratz_requests(self):
        with patch.dict(os.environ, {"STRATZ_RUNTIME_MODE": "snapshot", "STRATZ_API_TOKEN": "configured"}):
            data, status, warning = _stratz_graphql("query { constants { gameVersions { id } } }")

        self.assertIsNone(data)
        self.assertEqual(status, "unavailable")
        self.assertIsNone(warning)

    def test_verified_weekly_meta_snapshot_is_complete(self):
        snapshot = _stratz_meta_snapshot()

        self.assertTrue(snapshot["available"])
        self.assertEqual(set(snapshot["hero_meta"]["by_scope"]), {"pos1", "pos2", "pos3", "pos4", "pos5"})
        self.assertTrue(all(snapshot["hero_meta"]["by_scope"][f"pos{position}"] for position in range(1, 6)))

    @patch("routers.players._cached_stratz_hero_stats", return_value=(None, "unavailable", "IP restricted", 1783296000))
    def test_meta_endpoint_uses_snapshot_when_live_stratz_is_unavailable(self, _hero_stats):
        overview = meta_overview()

        self.assertTrue(overview["available"])
        self.assertEqual(overview["status"], "ready")
        self.assertEqual(overview["data_freshness"], "weekly_snapshot")
        self.assertEqual(overview["warnings"], [])

    @patch("routers.players._stratz_graphql", return_value=({"player": None}, "ready", None))
    def test_missing_stratz_player_degrades_without_crashing(self, _graphql):
        _cache.clear()

        matches, warning = _cached_stratz_player_matches(123, 20)

        self.assertIsNone(matches)
        self.assertIn("no public Ranked Roles data", warning)

    def test_only_explicit_stratz_positions_are_applied(self):
        matches = [
            {"match_id": "100", "position": 0, "position_key": "", "position_name": ""},
            {"match_id": "101", "position": 0, "position_key": "", "position_name": ""},
        ]
        raw = [
            {"id": 100, "players": [{"position": "POSITION_5", "imp": 29, "award": "MVP", "kills": 2, "deaths": 3, "assists": 19}]},
            {"id": 101, "players": [{"position": None, "imp": None, "award": None}]},
        ]

        verified = _apply_stratz_match_data(matches, raw)

        self.assertEqual(verified, 1)
        self.assertEqual(matches[0]["position"], 5)
        self.assertEqual(matches[0]["position_key"], "pos5")
        self.assertEqual(matches[0]["position_name"], "5号位 硬辅")
        self.assertEqual(matches[0]["stratz_imp"], 29)
        self.assertEqual(matches[1]["position"], 0)
        self.assertEqual(matches[1]["position_source"], "unavailable")

    @patch("routers.players._cached_item_catalog", return_value={
        1: {"name": "Blink Dagger", "icon": "https://cdn.example/blink.png"},
        287: {"name": "Keen Optic", "icon": "https://cdn.example/neutral.png"},
    })
    def test_stratz_equipment_includes_six_inventory_slots_and_neutral(self, _catalog):
        matches = [{"match_id": "200"}]
        raw = [{
            "id": 200,
            "players": [{
                "item0Id": 1,
                "item1Id": 0,
                "item2Id": 0,
                "item3Id": 0,
                "item4Id": 0,
                "item5Id": 0,
                "neutral0Id": 287,
            }],
        }]

        _apply_stratz_match_data(matches, raw)

        self.assertTrue(matches[0]["equipment_available"])
        self.assertEqual(matches[0]["equipment_source"], "stratz")
        self.assertEqual(len(matches[0]["items"]), 6)
        self.assertEqual(matches[0]["items"][0]["name"], "Blink Dagger")
        self.assertEqual(matches[0]["items"][1]["item_id"], 0)
        self.assertEqual(matches[0]["neutral_item"]["item_id"], 287)

    @patch("routers.players._stratz_graphql", return_value=(None, "unavailable", "temporary failure"))
    def test_stale_stratz_matches_are_used_during_temporary_failure(self, _graphql):
        cache_key = "stratz:player-matches:456:20"
        cached_matches = [{"id": 900, "players": []}]
        _cache.clear()
        _cache[cache_key] = {"time": 0, "data": cached_matches}

        matches, warning = _cached_stratz_player_matches(456, 20)

        self.assertEqual(matches, cached_matches)
        self.assertIn("using cached player matches", warning)

    def test_concurrent_stratz_requests_are_coalesced(self):
        _cache.clear()

        def delayed_response(_query, timeout=30):
            time.sleep(0.05)
            return {"player": {"matches": [{"id": 901, "players": []}]}}, "ready", None

        with patch("routers.players._stratz_graphql", side_effect=delayed_response) as graphql:
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: _cached_stratz_player_matches(789, 20), range(2)))

        self.assertEqual(graphql.call_count, 1)
        self.assertEqual(results[0][0], results[1][0])

    def test_role_matrix_keeps_carry_and_support_separate(self):
        matches = [
            self._match(position=1, win=True, imp=12, hero_name="卓尔游侠"),
            self._match(position=5, win=False, imp=-4, hero_name="卓尔游侠"),
        ]

        matrix = _role_matrix(matches)

        self.assertEqual([row["position"] for row in matrix], [1, 5])
        self.assertEqual(matrix[0]["win_rate"], 100.0)
        self.assertEqual(matrix[1]["win_rate"], 0.0)
        self.assertEqual(matrix[0]["avg_imp"], 12.0)
        self.assertEqual(matrix[1]["avg_imp"], -4.0)

    def test_meta_fit_compares_same_hero_in_same_position(self):
        matches = [
            self._match(position=1, win=True, hero_id=6),
            self._match(position=1, win=True, hero_id=6),
            self._match(position=5, win=False, hero_id=6),
            self._match(position=5, win=False, hero_id=6),
        ]
        hero_meta = {
            "by_scope": {
                "pos1": [{"hero_id": 6, "matches": 1000, "win_rate": 55.0, "meta_score": 54.5}],
                "pos5": [{"hero_id": 6, "matches": 200, "win_rate": 45.0, "meta_score": 46.0}],
            }
        }

        fit = _position_meta_fit(matches, hero_meta)
        by_position = {row["position"]: row for row in fit}

        self.assertEqual(by_position[1]["meta_win_rate"], 55.0)
        self.assertEqual(by_position[1]["gap"], 45.0)
        self.assertEqual(by_position[5]["meta_win_rate"], 45.0)
        self.assertEqual(by_position[5]["gap"], -45.0)

    @staticmethod
    def _match(position, win, imp=0, hero_name="测试英雄", hero_id=1):
        return {
            "hero_id": hero_id,
            "hero_name": hero_name,
            "position": position,
            "position_key": f"pos{position}",
            "position_name": f"{position}号位",
            "win": win,
            "kills": 5,
            "deaths": 5,
            "assists": 10,
            "gold_per_min": 500,
            "xp_per_min": 600,
            "last_hits": 200,
            "hero_damage": 20000,
            "stratz_imp": imp,
            "stratz_award": "NONE",
        }


if __name__ == "__main__":
    unittest.main()
