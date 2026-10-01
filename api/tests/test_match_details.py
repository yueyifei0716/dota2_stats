import unittest
from unittest.mock import patch

from fastapi import HTTPException
from routers.players import _aggregate_recent, _player_match_detail, player_match_details, _player_quick_payload, _player_dashboard_payload
from routers.hero_guides import hero_builds
from routers import players


class MatchDetailTests(unittest.TestCase):
    def test_saved_detail_fallback_keeps_its_original_capture_time(self):
        record = {"fetched_at": 2000, "data": {"recent_matches": [{
            "match_id": "9022234630", "detail_available": True,
            "detail_fetched_at": 1000, "gold_per_min": 356,
        }]}}
        with patch.object(players, "_cached_get", return_value=(None, "timeout")), \
             patch.object(players.public_player_cache, "load", return_value=record):
            _, detail, warning = players._player_match_detail(894447460, "9022234630")
        self.assertEqual(detail["detail_fetched_at"], 1000)
        self.assertEqual(detail["detail_status"], "ready")
        self.assertIn("保留此前已核验", warning)

    def test_scorecard_success_reuses_the_same_public_raw_cache_in_list_details(self):
        account, match_id, fetched = 894447460, "9022234630", 1790836000
        raw = {"duration": 2454, "radiant_win": True, "players": [{
            "account_id": account, "hero_id": 14, "player_slot": 3, "level": 21,
            "gold_per_min": 356, "xp_per_min": 605, "kills": 8, "deaths": 11, "assists": 16,
            "item_0": 1, "item_1": 0, "item_2": 36, "item_3": 116,
            "item_4": 214, "item_5": 267, "item_neutral": 680,
            "benchmarks": {"gold_per_min": {"raw": 356, "pct": .38}},
        }]}
        class Response:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return raw
        with patch.object(players, "_cache", {}), patch.object(players, "_upstream_failures", {}), \
             patch.object(players.time, "time", return_value=fetched), \
             patch.object(players, "_cached_item_catalog", return_value={}), \
             patch.object(players.requests, "get", side_effect=[Response(), AssertionError("duplicate upstream read")]) as get:
            card = players.player_match_scorecard(account, match_id)
            detail = players.player_match_details(account, match_id)["matches"][0]
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["params"], {"api_key": None})
        self.assertEqual(card["match_detail"]["items"], detail["items"])
        self.assertEqual([item["item_id"] for item in detail["items"]], [1, 0, 36, 116, 214, 267])
        self.assertEqual(detail["neutral_item"]["item_id"], 680)
        self.assertEqual(detail["detail_fetched_at"], fetched)
        self.assertEqual(detail["gold_per_min"], 356)
        self.assertEqual(detail["xp_per_min"], 605)
        self.assertTrue(detail["detail_available"])
        self.assertTrue(detail["equipment_available"])
        self.assertEqual(detail["detail_status"], "ready")
        self.assertFalse(detail["replay_parsed"])

    def test_normalizing_another_players_cached_raw_never_reuses_the_first_players_detail(self):
        raw = {"players": [{"account_id": 1, "gold_per_min": 356, "item_0": 1}]}
        _, detail, warning = players._match_detail_from_raw(2, "9022234630", raw)
        self.assertIsNone(detail)
        self.assertIn("missing player 2", warning)

    def test_unread_recent_match_is_deferred(self):
        matches = _aggregate_recent([{"match_id": 9022234630, "hero_id": 14}], 1)
        self.assertEqual(matches[0]["detail_status"], "deferred")
        self.assertFalse(matches[0]["detail_available"])

    def test_unparsed_replay_still_has_final_inventory_and_economy(self):
        raw = {"players": [{"account_id": 894447460, "level": 21,
                "gold_per_min": 356, "xp_per_min": 605, "last_hits": 68,
                "item_0": 1, "item_1": 36, "item_2": 116,
                "item_3": 214, "item_4": 267, "item_5": 0}]}
        with patch("routers.players._cached_get", return_value=(raw, None)) as get:
            _, detail, warning = _player_match_detail(894447460, "9022234630", {})
        self.assertIsNone(warning)
        self.assertTrue(detail["equipment_available"])
        self.assertFalse(detail["replay_parsed"])
        self.assertEqual(detail["gold_per_min"], 356)
        self.assertEqual([item["item_id"] for item in detail["items"]], [1, 36, 116, 214, 267, 0])
        self.assertIsNone(get.call_args.args[1]["api_key"])

    def test_explicit_ninth_match_is_not_truncated_and_partial_failure_is_retryable(self):
        def fetch(account, match_id, catalog):
            if match_id == "2": return match_id, None, "upstream HTTP 429"
            return match_id, {"detail_available": True, "detail_status": "ready", "gold_per_min": 356}, None
        with patch("routers.players._cached_item_catalog", return_value={}), patch("routers.players._player_match_detail", side_effect=fetch):
            rows = player_match_details(894447460, "9022234630,2,9022234630")["matches"]
        self.assertEqual([row["match_id"] for row in rows], ["9022234630", "2"])
        self.assertEqual(rows[0]["gold_per_min"], 356)
        self.assertEqual(rows[1]["detail_status"], "retryable")
        self.assertIn("429", rows[1]["detail_error"])

    def test_request_budget_and_invalid_ids_are_rejected_before_fetch(self):
        for value in ["", "0", "-1", "1/secret", "1,", ",".join(str(i) for i in range(1, 10))]:
            with self.subTest(value=value), patch("routers.players._cached_item_catalog") as get:
                with self.assertRaises(HTTPException) as error: player_match_details(1, value)
                self.assertEqual(error.exception.status_code, 422)
                get.assert_not_called()

    def test_expired_cache_is_usable_but_retains_warning(self):
        with patch("routers.players._cached_get", return_value=({"players": [{"account_id": 1, "item_0": 0}]}, "cached data")):
            _, detail, warning = _player_match_detail(1, "1", {})
        self.assertTrue(detail["detail_available"])
        self.assertEqual(warning, "cached data")

    def test_unavailable_match_list_is_not_reported_as_no_games(self):
        for payload in [_player_quick_payload, _player_dashboard_payload]:
            with self.subTest(payload=payload.__name__), patch("routers.players._fetch_player_sources", return_value=({"recent": None}, ["HTTP 429"])):
                with self.assertRaises(HTTPException) as error: payload(1, 50)
                self.assertEqual(error.exception.status_code, 503)

    def test_high_rank_budget_exhaustion_never_becomes_a_valid_empty_sample(self):
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.BUILD_BUDGET_SECONDS", 0), patch("routers.hero_guides._public_get") as get:
            result = hero_builds(7)
            get.assert_not_called()
        self.assertEqual(result["source"]["status"], "unavailable")
        self.assertTrue(result["source"]["budget_exhausted"])
        self.assertEqual(result["candidates"], [])


if __name__ == "__main__": unittest.main()
