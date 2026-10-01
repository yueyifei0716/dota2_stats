"""All catalog heroes must retain useful authored teaching against Valve data."""

from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest

from routers.hero_guides import _abilities
from services.hero_playbooks import _eligible, operating_guide

ROOT = Path(__file__).resolve().parents[1]


class FullHeroTeachingTests(unittest.TestCase):
    def test_every_actual_catalog_hero_has_a_gated_route_and_actionable_flow(self):
        source = json.loads(gzip.decompress((ROOT / "snapshots/valve_public.json.gz").read_bytes()))
        items = json.loads((ROOT / "snapshots/opendota_items.json").read_text())
        # The snapshot is a receipt around the actual public catalog.
        catalog = items.get("items", items.get("data", items))
        self.assertEqual(len(source["heroes"]), 127)
        for hero in source["heroes"]:
            with self.subTest(hero=hero["id"]):
                abilities = _abilities(hero)
                result = operating_guide(hero, abilities)
                self.assertIsNotNone(result)
                self.assertGreaterEqual(len(result["build_plan"]["steps"]), 3)
                self.assertGreaterEqual(len(result["build_plan"]["branches"]), 2)
                self.assertGreaterEqual(len(result["sequences"]), 1)
                self.assertIn("编辑", result["build_plan"]["label"])
                raw_slugs = {a["name"] for a in hero["abilities"]}
                for decision in [*result["build_plan"]["steps"], *result["build_plan"]["branches"]]:
                    self.assertIn(decision["item"], catalog)
                for sequence in result["sequences"]:
                    self.assertTrue(sequence["when"])
                    self.assertGreaterEqual(len(sequence["steps"]), 4)
                    self.assertGreaterEqual(len(sequence["cautions"]), 2)
                    for step in sequence["steps"]:
                        self.assertTrue(step["detail"])
                        if step.get("skill"):
                            self.assertIn(step["skill"], raw_slugs)
                        if step.get("item"):
                            self.assertIn(step["item"], catalog)

    def test_invoked_spells_require_current_base_orbs_and_invoke(self):
        fixture = json.loads((ROOT / "tests/fixtures/invoker.json").read_text())
        hero, abilities = fixture["hero"], fixture["abilities"]
        self.assertIn("invoker_tornado", _eligible(hero, abilities))
        self.assertEqual(len(operating_guide(hero, abilities)["sequences"]), 2)
        for slug in ["invoker_invoke", "invoker_wex"]:
            modified = deepcopy(hero)
            modified["abilities"] = [a for a in modified["abilities"] if a["name"] != slug]
            self.assertNotIn("invoker_tornado", _eligible(modified, abilities))
        modified = deepcopy(abilities)
        next(a for a in modified if a["slug"] == "invoker_invoke")["description"] = "该技能已改变，无法再祈唤法术。"
        self.assertNotIn("invoker_tornado", _eligible(hero, modified))

    def test_invoked_exception_never_accepts_items_or_upgrade_only_skills(self):
        fixture = json.loads((ROOT / "tests/fixtures/invoker.json").read_text())
        for field in ["is_item", "ability_is_granted_by_scepter", "ability_is_granted_by_shard"]:
            hero = deepcopy(fixture["hero"])
            next(a for a in hero["abilities"] if a["name"] == "invoker_tornado")[field] = True
            self.assertNotIn("invoker_tornado", _eligible(hero, fixture["abilities"]))


if __name__ == "__main__":
    unittest.main()
