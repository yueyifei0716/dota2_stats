import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from routers.players import _apply_confirmed_positions
from services.training import (
    evaluate_mission,
    get_active_mission,
    list_recent_missions,
    load_position_labels,
    recommend_mission,
    save_position_label,
    start_mission,
    storage_status,
)


CLIENT_ID = "test-client-identity-0001"


class TrainingMissionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {"DOTASENSE_DB_PATH": str(Path(self.temp_dir.name) / "training.sqlite3")},
            clear=False,
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def test_mission_completes_only_after_three_measurable_matches(self):
        baseline = [self._match(index, 900 - index, deaths=7) for index in range(10)]
        recommendation = recommend_mission(baseline, [])
        self.assertEqual(recommendation["focus_key"], "deaths")
        self.assertEqual(recommendation["baseline_value"], 7)
        self.assertEqual(recommendation["target_value"], 6)

        mission = start_mission(42, CLIENT_ID, recommendation, now=1000)
        first_two = [self._match(20, 1100, deaths=5), self._match(21, 1200, deaths=6)]
        active = evaluate_mission(mission, first_two)
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["progress"]["completed_games"], 2)
        self.assertIsNone(active["progress"]["achieved"])

        completed = evaluate_mission(mission, [*first_two, self._match(22, 1300, deaths=4)])
        self.assertEqual(completed["status"], "completed")
        self.assertTrue(completed["progress"]["achieved"])
        self.assertEqual(completed["progress"]["current_value"], 5)
        self.assertIsNone(get_active_mission(42, CLIENT_ID))
        self.assertEqual(list_recent_missions(42, CLIENT_ID)[0]["status"], "completed")

    def test_player_position_label_never_overrides_stratz(self):
        save_position_label(42, CLIENT_ID, "100", 5)
        save_position_label(42, CLIENT_ID, "101", 1)
        matches = [
            {
                "match_id": "100",
                "position": 0,
                "position_source": "unavailable",
                "role_name": "",
                "role_source": "unknown",
            },
            {
                "match_id": "101",
                "position": 2,
                "position_key": "pos2",
                "position_name": "2号位 中单",
                "position_source": "stratz",
                "role_name": "2号位 中单",
                "role_source": "stratz",
            },
        ]

        count = _apply_confirmed_positions(42, CLIENT_ID, matches)

        self.assertEqual(count, 1)
        self.assertEqual(matches[0]["position"], 5)
        self.assertEqual(matches[0]["position_source"], "user_confirmed")
        self.assertEqual(matches[1]["position"], 2)
        self.assertEqual(matches[1]["position_source"], "stratz")
        labels = load_position_labels(42, CLIENT_ID, ["100", "101"])
        self.assertEqual(labels["101"]["position"], 1)

    def test_serverless_storage_requires_postgres_for_persistence(self):
        with patch.dict(
            os.environ,
            {
                "VERCEL": "1",
                "DOTASENSE_DB_PATH": "",
                "POSTGRES_URL": "",
                "DATABASE_URL": "",
            },
            clear=False,
        ):
            status = storage_status()

        self.assertEqual(status["backend"], "sqlite")
        self.assertFalse(status["persistent"])
        self.assertFalse(status["production_ready"])

    def test_postgres_marks_training_storage_as_production_ready(self):
        with patch.dict(
            os.environ,
            {
                "VERCEL": "1",
                "DOTASENSE_DB_PATH": "",
                "POSTGRES_URL": "postgresql://configured-without-connecting",
            },
            clear=False,
        ):
            status = storage_status()

        self.assertEqual(status["backend"], "postgresql")
        self.assertTrue(status["persistent"])
        self.assertTrue(status["production_ready"])

    def test_recommendation_keeps_missing_metrics_missing(self):
        recommendation = recommend_mission([{"match_id": "100"}], [])

        self.assertFalse(recommendation["available"])
        self.assertIsNone(recommendation["baseline_value"])
        self.assertIsNone(recommendation["target_value"])
        with self.assertRaises(ValueError):
            start_mission(42, CLIENT_ID, recommendation, now=1000)

    @staticmethod
    def _match(index, start_time, deaths):
        return {
            "match_id": str(1000 + index),
            "hero_id": 1,
            "hero_name": "测试英雄",
            "hero_icon": "",
            "win": deaths < 6,
            "kills": 5,
            "deaths": deaths,
            "assists": 10,
            "kda": round(15 / max(deaths, 1), 2),
            "gold_per_min": 500,
            "played_at": "2026-08-12 12:00",
            "start_time": start_time,
        }


if __name__ == "__main__":
    unittest.main()
