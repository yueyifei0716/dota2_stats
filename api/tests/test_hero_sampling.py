"""Sampling must reach verified recent replays before slow discovery finishes."""

from copy import deepcopy
from pathlib import Path
from threading import Event
import tempfile
import time
import unittest
from unittest.mock import patch

from routers import hero_guides as guides


NOW = 2_000_000
ITEMS = {"blink": {"id": 1, "cost": 2250, "dname": "Blink Dagger", "created": False}}


def profile(account, tier=80, leaderboard=100):
    return {"profile": {"account_id": account, "personaname": f"Player {account}"},
            "rank_tier": tier, "leaderboard_rank": leaderboard}


def replay(match_id, account=1, logged=True):
    player = {"hero_id": 2, "account_id": account, "player_slot": 0, "lane_role": 2,
              **{f"item_{index}": 1 if index == 0 else 0 for index in range(6)}}
    if logged:
        player["purchase_log"] = [{"key": "blink", "time": 600}]
    return {"match_id": match_id, "start_time": NOW - 100, "duration": 1800,
            "lobby_type": 7, "game_mode": 22, "patch": 42, "radiant_win": True,
            "players": [player]}


def seed_payload():
    payload = guides.aggregate_builds(2, [replay(800)], guides._catalog(ITEMS),
                                     {1: {**profile(1), "checked_at": NOW - 700}}, NOW)
    payload["source"] = {"scope": "ranked_immortal_players", "fetched_at": NOW - 700,
                         "players": [{"account_id": 1, "rank_tier": 80,
                                      "leaderboard_rank": 100, "checked_at": NOW - 700}],
                         "stale": False}
    return payload


class HeroSamplingTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(guides, "BUILD_CACHE_DIR", self.directory))
        self.enterContext(patch.object(guides, "BUILD_SNAPSHOT_DIR", self.directory))
        self.enterContext(patch.object(guides.time, "time", return_value=NOW))

    def cache_with_seed(self):
        return {"ranked_builds:2": {"data": seed_payload(), "time": NOW - 700, "ttl": 600}}

    def response(self, path, params=None, **options):
        if path == "/rankings":
            return {"rankings": [{"account_id": 1}, {"account_id": 1}]}, None
        if path == "/constants/items":
            return ITEMS, None
        if path == "/constants/patch":
            return [{"id": 42, "name": "7.41"}], None
        if path == "/players/1":
            return profile(1), None
        if path == "/players/1/matches":
            return [{key: value for key, value in replay(901).items() if key != "players"} | {"hero_id": 2}], None
        if path == "/matches/901":
            return replay(901), None
        self.fail(f"Unexpected read: {path}")

    def test_seed_profile_history_and_replay_start_before_slow_public_discovery_finishes(self):
        replay_reached = Event()
        discovery_finished = Event()
        reads_before_discovery = []

        def public_feed(fetch, deadline):
            replay_reached.wait(0.35)
            discovery_finished.set()
            return [], None

        def get(path, params=None, **options):
            if path in {"/players/1", "/players/1/matches", "/matches/901"}:
                reads_before_discovery.append((path, not discovery_finished.is_set()))
            if path == "/matches/901":
                replay_reached.set()
            return self.response(path, params, **options)

        with patch.object(guides, "_cache", self.cache_with_seed()), \
                patch.object(guides, "_public_feed", side_effect=public_feed), \
                patch.object(guides, "_cached_get", side_effect=get):
            result = guides.hero_builds(2)
        self.assertEqual(reads_before_discovery,
                         [("/players/1", True), ("/players/1/matches", True), ("/matches/901", True)])
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["purchase_log_sample"], 1)
        self.assertEqual(result["matches"][0]["match_id"], "901")
        self.assertEqual(result["matches"][0]["rank_checked_at"], NOW)

    def test_seed_ranking_and_public_participant_share_one_profile_history_and_replay_read(self):
        public = {key: value for key, value in replay(901).items() if key != "players"}
        public["radiant_team"] = [2, 7, 8, 9, 10]
        with patch.object(guides, "_cache", self.cache_with_seed()), \
                patch.object(guides, "_public_feed", return_value=([public, deepcopy(public)], None)), \
                patch.object(guides, "_cached_get", side_effect=self.response) as read:
            result = guides.hero_builds(2)
        paths = [call.args[0] for call in read.call_args_list]
        for path in ["/players/1", "/players/1/matches", "/matches/901"]:
            self.assertEqual(paths.count(path), 1, path)
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["source"]["players_checked"], 1)
        self.assertTrue(all(call.args[1]["api_key"] is None for call in read.call_args_list))

    def test_stored_rank_never_qualifies_rejected_or_stale_profiles_for_history_reads(self):
        for record, warning in [(profile(1, tier=75), None),
                                (profile(1, leaderboard=0), None),
                                (profile(1), "显示的是缓存数据"),
                                (None, "HTTP 403")]:
            def get(path, params=None, **options):
                if path == "/players/1":
                    return record, warning
                return self.response(path, params, **options)

            with self.subTest(record=record, warning=warning), \
                    patch.object(guides, "_cache", self.cache_with_seed()), \
                    patch.object(guides, "_public_feed", return_value=([], None)), \
                    patch.object(guides, "_cached_get", side_effect=get) as read:
                result = guides.hero_builds(2)
            paths = [call.args[0] for call in read.call_args_list]
            self.assertEqual(paths.count("/players/1"), 1)
            self.assertNotIn("/players/1/matches", paths)
            self.assertNotIn("/matches/901", paths)
            self.assertNotIn("901", [row["match_id"] for row in result["matches"]])

    def test_complete_final_inventory_does_not_invent_missing_purchase_logs(self):
        def get(path, params=None, **options):
            if path == "/matches/901":
                return replay(901, logged=False), None
            return self.response(path, params, **options)

        with patch.object(guides, "_cache", {}), \
                patch.object(guides, "_public_feed", return_value=([], None)), \
                patch.object(guides, "_cached_get", side_effect=get):
            result = guides.hero_builds(2)
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["purchase_log_sample"], 0)
        self.assertEqual(result["groups"][0]["purchase_branches"], [])
        self.assertEqual(result["matches"][0]["purchase_sequence"], [])

    def test_patch_summary_uses_only_verified_display_mapping(self):
        for name, expected in [("60", None), ("test", None), ("7.41", "7.41"), ("7.41b", "7.41b")]:
            def get(path, params=None, **options):
                if path == "/constants/patch":
                    return [{"id": 42, "name": name}], None
                return self.response(path, params, **options)

            with self.subTest(name=name), patch.object(guides, "_cache", {}), \
                    patch.object(guides, "_public_feed", return_value=([], None)), \
                    patch.object(guides, "_cached_get", side_effect=get):
                result = guides.hero_builds(2)
            self.assertEqual(result["patch_name"], expected)

    def test_prefer_cached_returns_isolated_evidence_immediately_without_extending_timestamps(self):
        cache = self.cache_with_seed()
        original = deepcopy(cache["ranked_builds:2"]["data"])
        with patch.object(guides, "_cache", cache), \
                patch.object(guides, "_cached_get") as read:
            result = guides.hero_builds(2, prefer_cached=True)
        read.assert_not_called()
        self.assertEqual(result["matches"], original["matches"])
        self.assertEqual(result["groups"], original["groups"])
        self.assertEqual(result["source"]["fetched_at"], NOW - 700)
        self.assertEqual(result["matches"][0]["rank_checked_at"], NOW - 700)
        self.assertEqual(result["source"]["cache_read_at"], NOW)
        self.assertEqual(result["source"]["fallback_origin"], "memory_cache")
        self.assertEqual(result["source"]["status"], "stale")
        self.assertTrue(result["source"]["stale"])
        self.assertFalse(result["source"]["rank_reverified_on_refresh"])
        self.assertIn("没有刷新", result["source"]["freshness_note"])
        result["matches"][0]["items"][0]["name"] = "Mutated"
        self.assertEqual(cache["ranked_builds:2"]["data"], original)

    def test_prefer_cached_expired_evidence_still_requires_a_fresh_pipeline(self):
        cache = self.cache_with_seed()
        previous = cache["ranked_builds:2"]["data"]
        previous["source"]["fetched_at"] = NOW - 86401
        previous["source"]["players"][0]["checked_at"] = NOW - 86401
        previous["matches"][0]["rank_checked_at"] = NOW - 86401
        with patch.object(guides, "_cache", cache), \
                patch.object(guides, "_public_feed", return_value=([], None)), \
                patch.object(guides, "_cached_get", side_effect=self.response) as read:
            result = guides.hero_builds(2, prefer_cached=True)
        self.assertGreater(read.call_count, 0)
        self.assertEqual(result["matches"][0]["match_id"], "901")
        self.assertEqual(result["matches"][0]["rank_checked_at"], NOW)
        self.assertFalse(result["source"]["stale"])

    def test_overlapping_early_replays_keep_half_second_spacing_and_bounded_reads(self):
        starts = []

        def get(path, params=None, **options):
            if path == "/players/1/matches":
                return [{key: value for key, value in replay(match_id).items() if key != "players"} | {"hero_id": 2}
                        for match_id in [901, 902, 903, 904]], None
            if path.startswith("/matches/"):
                starts.append(time.monotonic())
                return replay(int(path.split("/")[-1])), None
            return self.response(path, params, **options)

        started = time.monotonic()
        with patch.object(guides, "_cache", self.cache_with_seed()), \
                patch.object(guides, "BUILD_BUDGET_SECONDS", 2.2), \
                patch.object(guides, "_public_feed", return_value=([], None)), \
                patch.object(guides, "_cached_get", side_effect=get) as read:
            result = guides.hero_builds(2)
        self.assertEqual(result["sample"], 4)
        self.assertEqual(result["purchase_log_sample"], 4)
        self.assertLessEqual(read.call_count, 52)
        self.assertLess(time.monotonic() - started, 3)
        self.assertTrue(all(later - earlier >= 0.45 for earlier, later in zip(starts, starts[1:])), starts)


if __name__ == "__main__":
    unittest.main()
