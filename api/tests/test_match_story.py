import unittest
from unittest.mock import patch

from routers.players import _scorecard_story


class MatchStoryTests(unittest.TestCase):
    @patch(
        "routers.players._cached_item_catalog",
        return_value={
            1: {"name": "Blink Dagger", "icon": "https://cdn.example/blink.png", "slug": "blink"},
        },
    )
    def test_story_uses_only_parsed_replay_events(self, _catalog):
        match = {
            "version": 22,
            "duration": 1800,
            "radiant_win": True,
            "radiant_gold_adv": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2500],
            "objectives": [{"time": 1200, "type": "CHAT_MESSAGE_AEGIS", "player_slot": 2}],
        }
        player = {
            "player_slot": 2,
            "kills": 5,
            "deaths": 2,
            "assists": 8,
            "gold_per_min": 560,
            "gold_t": [minute * 500 for minute in range(12)],
            "xp_t": [minute * 600 for minute in range(12)],
            "lh_t": [minute * 7 for minute in range(12)],
            "purchase_log": [{"time": 780, "key": "blink"}],
            "kills_log": [{"time": 320, "key": "npc_dota_hero_axe"}],
            "obs_log": [{"time": 410, "type": "obs_log"}],
            "sen_log": [],
            "teamfight_participation": 0.65,
        }

        story = _scorecard_story(match, player, [1], 2)

        self.assertTrue(story["available"])
        self.assertEqual(story["economy"][10]["last_hits"], 70)
        self.assertEqual(story["summary"]["teamfight_participation"], 65.0)
        titles = [chapter["title"] for chapter in story["chapters"]]
        self.assertIn("对线阶段结算", titles)
        self.assertIn("Blink Dagger", titles)
        self.assertIn("取得不朽之守护", titles)
        self.assertIn("全队最大单分钟经济变化", titles)
        self.assertIn("首次放置侦查守卫", titles)

    def test_unparsed_match_has_no_story_claims(self):
        story = _scorecard_story({"duration": 1800}, {"kills": 5}, [], 0)

        self.assertFalse(story["available"])
        self.assertEqual(story["chapters"], [])
        self.assertEqual(story["economy"], [])

    def test_sparse_replay_does_not_turn_missing_fields_into_zero(self):
        story = _scorecard_story(
            {"version": 22, "radiant_win": True, "radiant_gold_adv": [None, None, 2500]},
            {"player_slot": 0, "gold_t": [100, 200], "kills": 1, "deaths": 1, "assists": 1},
            [],
            0,
        )

        self.assertTrue(story["available"])
        self.assertIsNone(story["economy"][0]["team_advantage"])
        self.assertNotIn("hero_kills", story["summary"])
        self.assertNotIn("observer_wards", story["summary"])
        self.assertNotIn("对线阶段结算", [chapter["title"] for chapter in story["chapters"]])
        self.assertNotIn("全队最大单分钟经济变化", [chapter["title"] for chapter in story["chapters"]])
        self.assertNotIn("比赛结束", [chapter["title"] for chapter in story["chapters"]])


if __name__ == "__main__":
    unittest.main()
