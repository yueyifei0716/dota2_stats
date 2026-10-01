"""Regression checks against captured Valve mechanics and unsafe drift cases."""

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.hero_playbooks import operating_guide

FIXTURES = Path(__file__).with_name("fixtures")


def fixture(name):
    value = json.loads((FIXTURES / f"{name}.json").read_text())
    return value["hero"], value["abilities"]


class OperatingGuideTests(unittest.TestCase):
    def test_current_valve_mechanics_have_six_distinct_learning_guides(self):
        for name, expected in [("arc_warden", 4), ("juggernaut", 3), ("sniper", 3),
                               ("puck", 3), ("lina", 3), ("life_stealer", 3)]:
            with self.subTest(hero=name):
                hero, abilities = fixture(name)
                guide = operating_guide(hero, abilities)
                self.assertEqual(guide["kind"], "editorial_practice")
                self.assertEqual(len(guide["sequences"]), expected)
                self.assertTrue(guide["source_urls"])
                descriptions = {ability["description"] for ability in abilities}
                raw_slugs = {ability["name"] for ability in hero["abilities"]}
                for sequence in guide["sequences"]:
                    self.assertGreaterEqual(len(sequence["steps"]), 4)
                    self.assertTrue(sequence["when"])
                    self.assertGreaterEqual(len(sequence["cautions"]), 2)
                    self.assertNotIn("_rules", sequence)
                    for step in sequence["steps"]:
                        self.assertNotIn(step["detail"], descriptions)
                        if "skill" in step:
                            self.assertIn(step["skill"], raw_slugs)

    def test_missing_or_changed_arc_flux_keeps_only_independent_cards(self):
        for change in ("missing", "description"):
            hero, abilities = fixture("arc_warden")
            if change == "missing":
                hero["abilities"] = [a for a in hero["abilities"] if a["name"] != "arc_warden_flux"]
            else:
                next(a for a in abilities if a["slug"] == "arc_warden_flux")["description"] = "造成伤害并眩晕，不再使用旧机制。"
            result = operating_guide(hero, abilities)
            self.assertIsNone(result["build_plan"])
            self.assertEqual(len(result["sequences"]), 2)
            self.assertTrue(all("乱流" not in sequence["title"] for sequence in result["sequences"]))

    def test_changed_arc_double_never_reuses_old_distance_or_current_item_combo(self):
        hero, abilities = fixture("arc_warden")
        next(a for a in abilities if a["slug"] == "arc_warden_tempest_double")["description"] = "复制体远离本体时造成伤害降低。"
        self.assertIsNone(operating_guide(hero, abilities))

    def test_changed_field_and_spark_mechanisms_withhold_dependent_sequences(self):
        for slug, description in [("arc_warden_magnetic_field", "友军抵挡所有攻击和法术。"),
                                  ("arc_warden_spark_wraith", "立即对指定英雄造成伤害。")]:
            hero, abilities = fixture("arc_warden")
            next(a for a in abilities if a["slug"] == slug)["description"] = description
            result = operating_guide(hero, abilities)
            if result:
                self.assertIsNone(result["build_plan"])
                self.assertTrue(all(slug not in [step.get("skill") for step in s["steps"]] for s in result["sequences"]))

    def test_hidden_upgrade_item_and_invalid_flags_fail_closed(self):
        variations = [{"behavior": 17}, {"ability_is_granted_by_scepter": True},
                      {"ability_is_granted_by_shard": True}, {"is_item": True},
                      {"behavior": None}, {"behavior": "unknown"},
                      {"behavior": -1}, {"behavior": True}]
        for fields in variations:
            with self.subTest(fields=fields):
                hero, abilities = fixture("arc_warden")
                next(a for a in hero["abilities"] if a["name"] == "arc_warden_tempest_double").update(fields)
                self.assertIsNone(operating_guide(hero, abilities))

    def test_prepared_names_without_raw_basics_do_not_create_combo(self):
        hero, abilities = fixture("arc_warden")
        hero["abilities"] = []
        self.assertIsNone(operating_guide(hero, abilities))

    def test_changed_secondary_mechanisms_only_remove_relevant_practice(self):
        cases = [("juggernaut", "juggernaut_healing_ward", "召唤固定守卫。", [], 2),
                 ("sniper", "sniper_take_aim", "主动提升攻击距离。", [], 1),
                 ("puck", "puck_phase_shift", "立即闪避一次伤害。", [], 0),
                 ("lina", "lina_fiery_soul", "每次施放技能就获得攻速。", [], 0),
                 ("life_stealer", "life_stealer_infest", "感染敌方英雄。", [], 1)]
        for name, slug, description, notes, expected in cases:
            with self.subTest(hero=name):
                hero, abilities = fixture(name)
                next(a for a in abilities if a["slug"] == slug).update(description=description, notes=notes)
                result = operating_guide(hero, abilities)
                self.assertEqual(len(result["sequences"]) if result else 0, expected)

    def test_arc_build_is_explicit_editorial_order_without_invented_statistics(self):
        result = operating_guide(*fixture("arc_warden"))
        self.assertEqual([step["item"] for step in result["build_plan"]["steps"]],
                         ["bottle", "hand_of_midas", "maelstrom", "mjollnir"])
        self.assertIn("编辑学习", result["build_plan"]["label"])
        self.assertIn("不是样本统计", result["build_plan"]["note"])
        self.assertEqual(set(result["build_plan"]), {"label", "steps", "branches", "note", "source_url"})
        self.assertNotIn("win_rate", json.dumps(result))
        self.assertNotIn("sample", json.dumps(result))

    def test_item_sequences_explicitly_require_purchase_and_returns_are_isolated(self):
        hero, abilities = fixture("arc_warden")
        first = operating_guide(hero, abilities)
        self.assertIn("已购买紫苑", first["sequences"][1]["when"])
        self.assertIn("已购买邪恶镰刀", first["sequences"][3]["when"])
        first["sequences"][0]["steps"][0]["detail"] = "mutated"
        first["build_plan"]["steps"].clear()
        second = operating_guide(hero, abilities)
        self.assertNotEqual(second["sequences"][0]["steps"][0]["detail"], "mutated")
        self.assertEqual(len(second["build_plan"]["steps"]), 4)

    def test_arc_numeric_cautions_come_from_current_raw_mechanics(self):
        hero, abilities = fixture("arc_warden")
        result = operating_guide(hero, abilities)
        cautions = " ".join(result["sequences"][0]["cautions"])
        self.assertIn("1.5 秒", cautions)
        self.assertIn("移动减速最高 35%", cautions)
        self.assertIn("攻击失准最高 35%", cautions)
        spark = next(a for a in hero["abilities"] if a["name"] == "arc_warden_spark_wraith")
        next(s for s in spark["special_values"] if s["name"] == "base_activation_delay")["values_float"] = [2.5]
        cautions = " ".join(operating_guide(hero, abilities)["sequences"][0]["cautions"])
        self.assertIn("2.5 秒", cautions)
        self.assertNotIn("1.5 秒", cautions)

    def test_unknown_heroes_and_empty_input_stay_an_explicit_gap(self):
        self.assertIsNone(operating_guide({"id": 146, "abilities": []}, []))
        self.assertIsNone(operating_guide({}, []))
        self.assertIsNone(operating_guide(None, []))
        hero, _ = fixture("arc_warden")
        self.assertIsNone(operating_guide(hero, []))


if __name__ == "__main__":
    unittest.main()
