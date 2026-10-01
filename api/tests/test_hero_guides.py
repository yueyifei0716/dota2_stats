"""Candidate equipment must come from actual, same-patch inventory evidence."""

import unittest
from unittest.mock import patch
from fastapi import HTTPException
import requests
import time
import json
import tempfile
from copy import deepcopy
from pathlib import Path

from routers.hero_guides import BUILD_SNAPSHOT_DIR, _read_saved_build, _valid_saved_build, _write_saved_build, _public_feed, _select_matches, _abilities, _catalog, _description, _public_get, _verified_rank, aggregate_builds, hero_builds, hero_mechanics


CATALOG = _catalog({
    "blink": {"id": 1, "cost": 2250, "dname": "Blink Dagger", "created": False},
    "overwhelming_blink": {"id": 600, "cost": 6800, "dname": "Overwhelming Blink", "created": True},
    "blade_mail": {"id": 127, "cost": 2300, "dname": "Blade Mail", "created": True},
    "black_king_bar": {"id": 116, "cost": 4050, "dname": "Black King Bar", "created": True},
    "boots": {"id": 29, "cost": 500},
    "ultimate_orb": {"id": 24, "cost": 2800, "created": False},
    "neutral": {"id": 900, "cost": 0},
})


def match(match_id=1, patch_id=42, time=100, items=None):
    inventory = items or [1, 127, 116, 29, 0, 0]
    player = {"hero_id": 2, "player_slot": 0, "item_neutral": 900,
              **{f"item_{index}": value for index, value in enumerate(inventory)},
              "purchase_log": [{"key": "blink", "time": time}], "name": "Example"}
    return {"match_id": match_id, "start_time": 10000 + match_id, "duration": 3000, "patch": patch_id,
            "radiant_win": True, "players": [player]}


def profile(account_id, rank=80, leaderboard=100):
    return {"profile": {"account_id": account_id, "personaname": f"Player {account_id}"},
            "rank_tier": rank, "leaderboard_rank": leaderboard, "computed_mmr": 99999}


class HeroGuideTests(unittest.TestCase):
    def setUp(self):
        self.saved_directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch("routers.hero_guides.BUILD_CACHE_DIR", self.saved_directory))

    def saved_fixture(self, now=2_000_000):
        detail = match()
        detail.update(start_time=now - 1000, lobby_type=7, game_mode=22)
        detail["players"][0].update(account_id=1, lane_role=2)
        payload = aggregate_builds(2, [detail], CATALOG, {1: {**profile(1), "checked_at": now - 10}}, now)
        payload["source"] = {"scope": "ranked_immortal_players", "fetched_at": now,
                             "players": [{"account_id": 1, "rank_tier": 80, "leaderboard_rank": 100, "checked_at": now - 10}], "stale": False}
        return payload

    def test_cold_failed_refresh_returns_exact_bundled_public_arc_sample_and_original_dates(self):
        snapshot = json.loads((BUILD_SNAPSHOT_DIR / "113.json").read_text())["payload"]
        fetched = snapshot["source"]["fetched_at"]
        now = fetched + 600
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", return_value=(None, "HTTP 429")):
            result = hero_builds(113)
        self.assertEqual(result["sample"], snapshot["sample"])
        self.assertEqual(result["players_count"], 1)
        self.assertEqual(result["matches"], snapshot["matches"])
        self.assertEqual(result["groups"], snapshot["groups"])
        self.assertEqual(result["source"]["fetched_at"], fetched)
        self.assertEqual(result["source"]["status"], "stale")
        self.assertEqual(result["source"]["fallback_origin"], "bundled_public_snapshot")
        self.assertEqual(result["source"]["refresh_attempted_at"], now)
        self.assertFalse(result["source"]["rank_reverified_on_refresh"])
        self.assertEqual(list(self.saved_directory.iterdir()), [])

    def test_expired_rank_snapshot_cannot_rescue_a_failed_refresh(self):
        snapshot = json.loads((BUILD_SNAPSHOT_DIR / "113.json").read_text())["payload"]
        now = snapshot["matches"][0]["rank_checked_at"] + 86401
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", return_value=(None, "HTTP 429")):
            result = hero_builds(113)
        self.assertEqual(result["sample"], 0)
        self.assertEqual(result["source"]["status"], "unavailable")

    def test_stale_memory_ttl_cannot_extend_rank_evidence_past_twenty_four_hours(self):
        snapshot = json.loads((BUILD_SNAPSHOT_DIR / "113.json").read_text())["payload"]
        now = snapshot["matches"][0]["rank_checked_at"] + 86401
        cache = {"ranked_builds:113": {"data": snapshot, "time": now - 10, "ttl": 60}}
        with patch("routers.hero_guides._cache", cache), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", return_value=(None, "HTTP 429")) as request:
            result = hero_builds(113)
        self.assertGreater(request.call_count, 0)
        self.assertEqual(result["sample"], 0)

    def test_cold_snapshot_account_is_only_a_discovery_seed_and_requires_fresh_rank(self):
        snapshot = json.loads((BUILD_SNAPSHOT_DIR / "113.json").read_text())["payload"]
        account = snapshot["source"]["players"][0]["account_id"]
        now = snapshot["source"]["fetched_at"] + 600
        for tier, expected in [(75, 0), (80, 1)]:
            def get(path, params=None, **kwargs):
                if path == "/publicMatches": return [], None
                if path == "/rankings": return {"rankings": []}, None
                if path == "/constants/items": return {item["slug"]: item for item in CATALOG.values()}, None
                if path == "/constants/patch": return [], None
                if path == f"/players/{account}": return profile(account,rank=tier), None
                if path == f"/players/{account}/matches":
                    return [{"match_id":501,"hero_id":113,"start_time":now-10,"duration":3000,"lobby_type":7,"game_mode":22}], None
                detail=match(501);detail.update(start_time=now-10,lobby_type=7,game_mode=22)
                detail["players"][0].update(hero_id=113,account_id=account)
                return detail,None
            with self.subTest(tier=tier), patch("routers.hero_guides._cache",{}), patch("routers.hero_guides.time.time",return_value=now), patch("routers.hero_guides._cached_get",side_effect=get) as request:
                result=hero_builds(113)
            self.assertEqual(result["sample"],expected)
            self.assertIn(account,result["source"]["discovery_seed_accounts"])
            history_calls=[call for call in request.call_args_list if call.args[0]==f"/players/{account}/matches"]
            self.assertEqual(bool(history_calls),tier==80)
            if expected:
                self.assertEqual([row["match_id"] for row in result["matches"]],["501"])
                self.assertEqual(result["matches"][0]["rank_checked_at"],now)
                self.assertFalse(result["source"]["stale"])

    def test_new_valid_arc_sample_is_never_augmented_or_replaced_by_the_bundled_snapshot(self):
        snapshot = json.loads((BUILD_SNAPSHOT_DIR / "113.json").read_text())["payload"]
        now = snapshot["source"]["fetched_at"] + 600
        def get(path, params=None, **kwargs):
            if path == "/publicMatches":
                return [], None
            if path == "/rankings":
                return {"rankings": [{"account_id": 99}]}, None
            if path == "/constants/items":
                return {item["slug"]: item for item in CATALOG.values()}, None
            if path == "/constants/patch":
                return [], None
            if path == "/players/99":
                return profile(99), None
            if path == "/players/99/matches":
                return [{"match_id": 501, "hero_id": 113, "start_time": now - 10,
                         "duration": 3000, "lobby_type": 7, "game_mode": 22}], None
            detail = match(501)
            detail.update(start_time=now - 10, lobby_type=7, game_mode=22)
            detail["players"][0].update(hero_id=113, account_id=99)
            return detail, None
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", side_effect=get):
            result = hero_builds(113)
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["matches"][0]["account_id"], 99)
        self.assertFalse(result["source"]["stale"])
        self.assertTrue((self.saved_directory / "113.json").exists())

    def test_disk_evidence_survives_memory_reset_and_failed_refresh_without_extending_age(self):
        now = 2_000_000
        previous = self.saved_fixture(now)
        _write_saved_build(2, previous, now)
        original = (self.saved_directory / "2.json").read_text()
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now + 601), patch("routers.hero_guides._cached_get", return_value=(None, "HTTP 503")):
            result = hero_builds(2)
        self.assertEqual(result["matches"], previous["matches"])
        self.assertEqual(result["source"]["fetched_at"], now)
        self.assertEqual(result["source"]["fallback_origin"], "disk_cache")
        self.assertTrue(result["source"]["stale"])
        self.assertEqual((self.saved_directory / "2.json").read_text(), original)
        self.assertIsNone(_read_saved_build(self.saved_directory, 2, now + 86401))

    def test_saved_evidence_rejects_identity_lobby_expiry_inventory_and_group_corruption(self):
        now = 2_000_000
        valid = self.saved_fixture(now)
        self.assertTrue(_valid_saved_build(2, valid, now))
        mutations = [lambda p: p["matches"][0].update(hero_id=7),
                     lambda p: p["matches"][0].update(account_id=99),
                     lambda p: p["matches"][0].update(lobby_type=1),
                     lambda p: p["matches"][0].update(rank_checked_at=now - 86401),
                     lambda p: p["matches"][0].update(start_time=now - 15 * 86400),
                     lambda p: p["matches"][0].update(items=[]),
                     lambda p: p["groups"][0].update(sample=100),
                     lambda p: p["groups"][0].update(match_ids=["999"]),
                     lambda p: p["source"].update(fetched_at=now + 1)]
        for mutate in mutations:
            payload = deepcopy(valid)
            mutate(payload)
            with self.subTest(payload=payload):
                self.assertFalse(_valid_saved_build(2, payload, now))
        path = self.saved_directory / "2.json"
        path.write_text(json.dumps({"schema_version": 1, "hero_id": 7, "payload": valid}))
        self.assertIsNone(_read_saved_build(self.saved_directory, 2, now))
        path.write_text("{bad json")
        self.assertIsNone(_read_saved_build(self.saved_directory, 2, now))

    def test_public_feed_is_two_pages_shared_across_heroes_and_uses_official_cursor(self):
        calls = []
        def fetch(path, params=None, **kwargs):
            calls.append((path, params))
            start = 300 if len(calls) == 1 else 200
            return [{"match_id": match_id} for match_id in range(start, start - 100, -1)], None
        with patch("routers.hero_guides._cache", {}):
            data, warning = _public_feed(fetch, time.monotonic() + 10)
            self.assertEqual(_public_feed(fetch, time.monotonic() + 10), (data, warning))
        self.assertEqual(len(data), 200)
        self.assertEqual(calls, [("/publicMatches", {"min_rank": 75}), ("/publicMatches", {"min_rank": 75, "less_than_match_id": 201})])

    def test_public_feed_average_rank_never_verifies_a_player_and_seed_details_are_reused(self):
        now = 2_000_000
        def get(path, params=None, **kwargs):
            if path == "/publicMatches":
                return [{"match_id": account, "start_time": now - account, "duration": 3000,
                         "lobby_type": 7, "game_mode": 22, "avg_rank_tier": 75,
                         "radiant_team": [2, 7, 8, 9, 10]} for account in [10, 11, 12]], None
            if path == "/rankings":
                return {"rankings": []}, None
            if path == "/constants/items":
                return {item["slug"]: item for item in CATALOG.values()}, None
            if path == "/constants/patch":
                return [], None
            if path.startswith("/players/"):
                account = int(path.split("/")[2])
                if path.endswith("/matches"):
                    return [], None
                return profile(account, rank=75 if account == 12 else 80, leaderboard=None if account == 11 else 300), None
            account = int(path.split("/")[-1])
            detail = match(account)
            detail.update(start_time=now - account, lobby_type=7, game_mode=22)
            detail["players"][0]["account_id"] = account
            return detail, None
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides.time.sleep"), patch("routers.hero_guides._cached_get", side_effect=get) as request:
            result = hero_builds(2)
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["matches"][0]["account_id"], 10)
        self.assertEqual(result["source"]["players_verified"], 1)
        self.assertEqual(result["source"]["public_feed"]["accounts_discovered"], 3)
        self.assertFalse(result["source"]["public_feed"]["individual_rank_verified"])
        self.assertEqual(sum(call.args[0] == "/matches/10" for call in request.call_args_list), 1)
    def test_replay_lanes_and_patches_have_independent_item_denominators(self):
        details = [match(index) for index in range(1, 8)]
        for detail in details[:3]:
            detail["players"][0]["lane_role"] = 2
            detail["players"][0]["account_id"] = 1
        for detail in details[3:6]:
            detail["players"][0]["lane_role"] = 1
            detail["players"][0]["account_id"] = 2
        details[6]["players"][0]["lane_role"] = 99
        old = match(8, patch_id=41)
        old["players"][0]["lane_role"] = 2
        result = aggregate_builds(2, [*details, old], CATALOG)
        groups = {(group["patch_id"], group["lane_role"]): group for group in result["groups"]}
        self.assertEqual(groups[(42, 2)]["sample"], 3)
        self.assertEqual(groups[(42, 1)]["sample"], 3)
        self.assertEqual(groups[(42, None)]["sample"], 1)
        self.assertEqual(groups[(41, 2)]["sample"], 1)
        self.assertEqual(groups[(42, 1)]["candidates"][0]["sample"], 3)
        self.assertEqual(groups[(42, 1)]["players_count"], 1)
        self.assertTrue(all(group["position"] is None for group in result["groups"]))
        self.assertFalse(any(group["position_verified"] for group in result["groups"]))

    def test_purchase_branches_use_actual_order_even_for_sold_items_and_exclude_missing_logs(self):
        details = [match(index, items=[116, 0, 0, 0, 0, 0]) for index in range(1, 5)]
        for index, detail in enumerate(details):
            detail["players"][0]["account_id"] = index + 1
        # Input log order is not guaranteed; chronology comes from timestamps.
        details[0]["players"][0]["purchase_log"] = [{"key": "black_king_bar", "time": 1000}, {"key": "blink", "time": 100}, {"key": "blade_mail", "time": 500}, {"key": "blink", "time": 1200}]
        details[1]["players"][0]["purchase_log"] = [{"key": "blink", "time": 150}, {"key": "black_king_bar", "time": 700}, {"key": "blade_mail", "time": 1100}]
        details[2]["players"][0]["purchase_log"] = [{"key": "blink", "time": -100}, {"key": "blink", "time": True}, {"key": "blade_mail", "time": 4000}]
        del details[3]["players"][0]["purchase_log"]
        result = aggregate_builds(2, details, CATALOG)
        group = result["groups"][0]
        self.assertEqual(group["inventory_sample"], 4)
        self.assertEqual(group["purchase_log_sample"], 2)
        self.assertEqual(group["missing_purchase_log_sample"], 2)
        self.assertEqual({tuple(branch["slugs"]) for branch in group["purchase_branches"]}, {("blink", "blade_mail", "black_king_bar"), ("blink", "black_king_bar", "blade_mail")})
        self.assertTrue(all(branch["frequency"] == 50 and branch["sample"] == 2 and branch["players"] == 1 for branch in group["purchase_branches"]))
        self.assertTrue(all(item["purchase_minute"] is None and item["timing_sample"] == 2 for item in group["purchase_items"]))
        self.assertEqual(result["matches"][0]["purchase_sequence"], [])

    def test_unavailable_catalog_keeps_verified_match_without_inventing_purchase_items(self):
        detail = match()
        detail["players"][0]["purchase_log"] = [{"key": "overwhelming_blink", "time": 1000}]
        result = aggregate_builds(2, [detail], {})
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["matches"][0]["purchase_sequence"], [])
        self.assertEqual(result["groups"][0]["purchase_items"], [])

    def test_selection_balances_players_and_caps_at_twenty_four_details(self):
        eligible = {}
        for account in range(1, 13):
            for index in range(8):
                key = f"{account}-{index}"
                eligible[key] = {"match_id": key, "expected_account_id": account, "start_time": 100000 - account * 100 - index}
        selected = _select_matches(eligible)
        self.assertEqual(len(selected), 24)
        self.assertEqual(len({row["expected_account_id"] for row in selected[:12]}), 12)
        self.assertTrue(all(sum(row["expected_account_id"] == account for row in selected) == 2 for account in range(1, 13)))

    def test_endpoint_can_collect_twenty_four_verified_games_with_bounded_reads_and_cache(self):
        now = 2_000_000

        def get(path, params=None, **kwargs):
            if path == "/publicMatches":
                return [], None
            if path == "/rankings":
                return {"rankings": [{"account_id": account} for account in range(1, 31)]}, None
            if path == "/constants/items":
                return {item["slug"]: item for item in CATALOG.values()}, None
            if path == "/constants/patch":
                return [{"id": 42, "name": "test"}], None
            if path.startswith("/players/"):
                account = int(path.split("/")[2])
                if not path.endswith("/matches"):
                    return profile(account), None
                return [{"match_id": account * 100 + index, "hero_id": 2, "lobby_type": 7,
                         "game_mode": 22, "start_time": now - account * 100 - index, "duration": 3000}
                        for index in range(1, 9)], None
            match_id = int(path.split("/")[-1])
            detail = match(match_id)
            detail.update(start_time=now - match_id, lobby_type=7, game_mode=22)
            detail["players"][0].update(account_id=match_id // 100, lane_role=2)
            return detail, None

        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides.time.sleep"), patch("routers.hero_guides._cached_get", side_effect=get) as request:
            result = hero_builds(2)
            calls = request.call_count
            self.assertEqual(hero_builds(2), result)
            self.assertEqual(request.call_count, calls)
        self.assertEqual(result["sample"], 24)
        self.assertEqual(result["players_count"], 12)
        self.assertEqual(result["source"]["requests_used"], 52)
        self.assertEqual(calls, 52)
        self.assertEqual(result["source"]["request_limit"], 52)
        self.assertEqual(result["source"]["sample_status"], "observed")
        self.assertEqual(result["groups"][0]["purchase_log_sample"], 24)

    def test_rate_limited_refresh_preserves_recent_real_evidence_and_its_original_timestamps(self):
        now = 2_000_000
        detail = match()
        detail.update(start_time=now - 1000, lobby_type=7, game_mode=22)
        detail["players"][0]["account_id"] = 1
        previous = aggregate_builds(2, [detail], CATALOG, {1: {**profile(1), "checked_at": now - 700}}, now)
        previous["source"] = {"scope": "ranked_immortal_players", "fetched_at": now - 601, "status": "insufficient", "players": [{"account_id": 1, "rank_tier": 80, "leaderboard_rank": 100, "checked_at": now - 700}], "sample_status": "small_sample"}
        cache = {"ranked_builds:2": {"data": previous, "time": now - 601, "ttl": 600}}
        with patch("routers.hero_guides._cache", cache), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", return_value=(None, "/secret_path returned HTTP 429")):
            result = hero_builds(2)
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["source"]["status"], "stale")
        self.assertTrue(result["source"]["stale"])
        self.assertEqual(result["source"]["fetched_at"], now - 601)
        self.assertEqual(result["matches"][0]["rank_checked_at"], now - 700)
        self.assertTrue(all(failure["reason"] == "rate_limited" and failure["http_status"] == 429 for failure in result["source"]["warnings"]))
        self.assertNotIn("secret_path", str(result))
        self.assertEqual(cache["ranked_builds:2"]["ttl"], 60)

    def test_exhausted_budget_reports_stage_failures_without_any_upstream_read(self):
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.BUILD_BUDGET_SECONDS", 0), patch("routers.hero_guides._cached_get") as request:
            result = hero_builds(2)
        request.assert_not_called()
        self.assertEqual(result["sample"], 0)
        self.assertTrue(result["source"]["budget_exhausted"])
        self.assertEqual(result["source"]["requests_used"], 0)
        self.assertTrue(all(failure["reason"] == "budget_exhausted" for failure in result["source"]["warnings"]))


    def test_hero_read_does_not_send_a_configured_paid_api_key(self):
        with patch.dict("os.environ", {"OPENDOTA_API_KEY": "unused-test-credential"}), patch("routers.players._cache", {}), patch("routers.players.requests.get") as get:
            get.return_value.status_code = 200
            get.return_value.json.return_value = {"ok": True}
            self.assertEqual(_public_get("/rankings", {"hero_id": 7}, attempts=1), ({"ok": True}, None))
        prepared = requests.Request("GET", get.call_args.args[0], params=get.call_args.kwargs["params"]).prepare()
        self.assertEqual(prepared.url, "https://api.opendota.com/api/rankings?hero_id=7")

    def test_patch_isolation_does_not_blend_old_builds(self):
        result = aggregate_builds(2, [match(1, 41), match(2), match(3), match(4)], CATALOG)
        self.assertEqual(result["sample"], 3)
        self.assertEqual(result["patch_id"], 42)
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["candidates"][0]["example_matches"], ["4", "3", "2"])

    def test_inventory_is_six_slots_and_neutral_is_not_a_candidate(self):
        matches = [match(index) for index in range(1, 4)]
        for detail in matches:
            detail["players"][0]["backpack_0"] = 127
        result = aggregate_builds(2, matches, CATALOG)
        self.assertEqual(len(result["matches"][0]["items"]), 6)
        self.assertEqual(result["matches"][0]["neutral"]["item_id"], 900)
        self.assertEqual(result["candidates"][0]["matches"], 3)
        self.assertEqual(result["candidates"][0]["pick_rate"], 100)
        self.assertNotIn(900, [item["item_id"] for item in result["candidates"]])

    def test_duplicate_slots_and_upgraded_blink_count_once(self):
        matches = [match(index, items=[600, 1, 127, 127, 0, 0]) for index in range(1, 4)]
        result = aggregate_builds(2, matches, CATALOG)
        self.assertEqual([item["matches"] for item in result["candidates"]], [3, 3])
        self.assertEqual(result["candidates"][0]["slug"], "blink")

    def test_missing_equipment_is_not_an_empty_inventory(self):
        detail = match()
        del detail["players"][0]["item_5"]
        self.assertEqual(aggregate_builds(2, [detail], CATALOG)["sample"], 0)
        self.assertEqual(aggregate_builds(2, [match()], CATALOG)["candidates"], [])

    def test_purchase_time_needs_three_observed_logs(self):
        matches = [match(1, time=600), match(2, time=1200), match(3, time=1800)]
        result = aggregate_builds(2, matches, CATALOG)
        blink = result["candidates"][0]
        self.assertEqual(blink["purchase_minute"], 20)
        self.assertEqual(blink["timing_sample"], 3)
        del matches[0]["players"][0]["purchase_log"]
        self.assertIsNone(aggregate_builds(2, matches, CATALOG)["candidates"][0]["purchase_minute"])

    def test_upgraded_blink_time_does_not_become_basic_blink_time(self):
        matches = [match(index, items=[600, 127, 0, 0, 0, 0]) for index in range(1, 4)]
        for detail in matches:
            detail["players"][0]["purchase_log"] = [{"key": "overwhelming_blink", "time": 1800}]
        candidate = aggregate_builds(2, matches, CATALOG)["candidates"][0]
        self.assertIsNone(candidate["purchase_minute"])
        self.assertEqual(candidate["timing_sample"], 0)

    def test_unknown_result_does_not_become_a_loss(self):
        matches = [match(index) for index in range(1, 4)]
        for detail in matches:
            detail["radiant_win"] = None
        result = aggregate_builds(2, matches, CATALOG)
        self.assertIsNone(result["matches"][0]["win"])
        self.assertIsNone(result["candidates"][0]["win_rate"])

    def test_missing_team_slot_is_not_assumed_dire(self):
        detail = match()
        del detail["players"][0]["player_slot"]
        self.assertIsNone(aggregate_builds(2, [detail], CATALOG)["matches"][0]["win"])

    def test_repeated_match_cannot_inflate_sample(self):
        detail = match()
        result = aggregate_builds(2, [detail, detail, detail], CATALOG)
        self.assertEqual(result["sample"], 1)
        self.assertEqual(result["candidates"], [])

    def test_unknown_patch_is_not_blended_with_known_patch(self):
        detail = match(4)
        del detail["patch"]
        result = aggregate_builds(2, [match(1), match(2), match(3), detail], CATALOG)
        self.assertIsNone(result["patch_id"])
        self.assertEqual(result["sample"], 1)

    def test_missing_neutral_remains_unknown(self):
        detail = match()
        del detail["players"][0]["item_neutral"]
        self.assertIsNone(aggregate_builds(2, [detail], CATALOG)["matches"][0]["neutral"]["item_id"])

    def test_valve_description_resolves_numbers_and_escapes_markup(self):
        ability = {"special_values": [{"name": "range", "values_float": [100, 200], "values_scepter": [500]}]}
        self.assertEqual(_description("<b>范围</b> %range%", ability), "范围 100/200")
        self.assertEqual(_description("范围 %range%", ability, "scepter"), "范围 500")
        self.assertEqual(_description("概率 20%%", ability), "概率 20%")

    def test_new_hero_source_failure_is_not_reported_as_nonexistent(self):
        with patch("routers.hero_guides._valve", return_value=({}, None, True)):
            with self.assertRaises(HTTPException) as raised:
                hero_mechanics(146)
        self.assertEqual(raised.exception.status_code, 503)

    def test_rank_evidence_requires_identity_immortal_and_a_real_leaderboard_place(self):
        self.assertTrue(_verified_rank(profile(1), 1))
        for record in [profile(2), profile(1, 75), profile(1, None), profile(1, "80"),
                       profile(1, leaderboard=None), profile(1, leaderboard=0), profile(1, leaderboard=True)]:
            with self.subTest(record=record):
                self.assertFalse(_verified_rank(record, 1))

    def test_ordinary_players_and_nonranked_details_cannot_enter_high_rank_inventory(self):
        details, ranks = [], {}
        for index in range(1, 6):
            detail = match(index)
            detail.update(lobby_type=7, game_mode=22)
            detail["players"][0]["account_id"] = index
            ranks[index] = profile(index, rank=75 if index == 1 else 80)
            details.append(detail)
        details[-1]["lobby_type"] = 1
        result = aggregate_builds(2, details, CATALOG, ranks, now=20000)
        self.assertEqual(result["sample"], 3)
        self.assertEqual([row["account_id"] for row in result["matches"]], [4, 3, 2])
        self.assertTrue(all(row["rank_tier"] == 80 for row in result["matches"]))
        self.assertNotIn("computed_mmr", result["matches"][0])

    def test_build_endpoint_rechecks_ranked_hero_time_and_account_instead_of_trusting_query_filters(self):
        now = 2_000_000
        recent = [{"match_id": index, "account_id": index, "start_time": now - index, "leagueid": 100} for index in range(1, 11)]

        def get(path, params=None, **kwargs):
            if path == "/publicMatches":
                return [], None
            if path == "/rankings":
                return {"rankings": recent}, None
            if path == "/constants/items":
                return {item["slug"]: item for item in CATALOG.values()}, None
            if path == "/constants/patch":
                return [{"id": 42, "name": "test"}], None
            if path.startswith("/players/"):
                account_id = int(path.split("/")[2])
                if not path.endswith("/matches"):
                    return profile(account_id), None
                row = {"match_id": account_id, "hero_id": 2, "lobby_type": 7, "game_mode": 22,
                       "start_time": now - account_id, "duration": 3000}
                invalid = [{**row, "match_id": 20, "start_time": now + 10},
                           {**row, "match_id": 21, "start_time": now - 15 * 86400},
                           {**row, "match_id": 22, "lobby_type": 1},
                           {**row, "match_id": 23, "hero_id": 7},
                           {**row, "match_id": 24, "game_mode": 23}]
                return [row, row, *invalid], None
            detail = match(int(path.split("/")[-1]))
            detail["start_time"] = now - detail["match_id"]
            detail.update(lobby_type=7, game_mode=22)
            detail["players"][0]["account_id"] = detail["match_id"]
            return detail, "显示的是缓存数据" if detail["match_id"] == 1 else None

        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", side_effect=get) as request:
            result = hero_builds(2)
        self.assertEqual(result["sample"], 10)
        self.assertEqual(result["source"]["attempted"], 10)
        self.assertEqual(result["source"]["status"], "partial")
        self.assertEqual(result["source"]["scope"], "ranked_immortal_players")
        self.assertEqual(result["source"]["players_verified"], 10)
        self.assertEqual(len(result["source"]["players"]), 10)
        self.assertEqual(result["matches"][0]["match_type"], "天梯排位")
        paths = {call.args[0] for call in request.call_args_list}
        self.assertNotIn("/matches/20", paths)
        self.assertNotIn("/matches/21", paths)
        self.assertNotIn("/matches/22", paths)
        self.assertNotIn("/matches/23", paths)
        self.assertNotIn("/matches/24", paths)
        self.assertIn("/matches/9", paths)
        for call in request.call_args_list:
            if call.args[0].startswith("/players/") and call.args[0].endswith("/matches"):
                self.assertEqual(call.args[1], {"hero_id": 2, "lobby_type": 7, "date": 14, "limit": 8, "api_key": None})
            self.assertIsNone(call.args[1]["api_key"])

    def test_stale_or_missing_rank_cannot_be_promoted_by_hero_ranking(self):
        now = 2_000_000

        def get(path, params=None, **kwargs):
            if path == "/publicMatches":
                return [], None
            if path == "/rankings":
                return {"rankings": [{"account_id": account} for account in [1, 2, 3]]}, None
            if path.startswith("/players/"):
                account = int(path.split("/")[-1])
                return profile(account, rank=75 if account == 1 else None if account == 2 else 80), "缓存数据" if account == 3 else None
            return {}, None

        with patch("routers.hero_guides._cache", {}) as cache, patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", side_effect=get) as request:
            result = hero_builds(2)
            calls = request.call_count
            self.assertEqual(hero_builds(2), result)
            self.assertEqual(request.call_count, calls)
            self.assertEqual(cache["ranked_builds:2"]["ttl"], 60)
        self.assertEqual(result["sample"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["source"]["players_verified"], 0)
        self.assertEqual(result["source"]["status"], "unavailable")
        self.assertFalse(any(call.args[0].endswith("/matches") and call.args[0].startswith("/players/") for call in request.call_args_list))

    def test_match_detail_identity_mismatch_cannot_supply_equipment(self):
        now = 2_000_000

        def get(path, params=None, **kwargs):
            if path == "/publicMatches":
                return [], None
            if path == "/rankings":
                return {"rankings": [{"account_id": 1}]}, None
            if path == "/players/1":
                return profile(1), None
            if path == "/players/1/matches":
                return [{"match_id": 1, "hero_id": 2, "lobby_type": 7, "game_mode": 22, "start_time": now - 1, "duration": 3000}], None
            if path == "/matches/1":
                detail = match()
                detail.update(start_time=now - 1, lobby_type=7, game_mode=22)
                detail["players"][0]["account_id"] = 99
                return detail, None
            return {}, None

        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides.time.time", return_value=now), patch("routers.hero_guides._cached_get", side_effect=get):
            result = hero_builds(2)
        self.assertEqual(result["sample"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["source"]["players"], [])
        self.assertEqual(result["source"]["status"], "insufficient")

    def test_build_endpoint_unavailable_source_does_not_fabricate_candidates(self):
        with patch("routers.hero_guides._cache", {}), patch("routers.hero_guides._cached_get", return_value=(None, "请求超时")):
            result = hero_builds(2)
        self.assertEqual(result["sample"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["source"]["status"], "unavailable")

    def test_combo_is_withheld_when_current_skills_change(self):
        hero = {"id": 7, "name": "npc_dota_hero_earthshaker", "name_loc": "撼地者", "abilities": []}
        with patch("routers.hero_guides._valve", return_value=({"heroes": [hero]}, 100, False)):
            self.assertIsNone(hero_mechanics(7)["practice"])
        self.assertEqual(_abilities({"abilities": [{"name": "test", "name_loc": "测试", "behavior": "2"}]})[0]["kind"], "被动")


if __name__ == "__main__":
    unittest.main()
