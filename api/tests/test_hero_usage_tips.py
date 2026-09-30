"""Actual play advice must be distinct from definitions and upgrade-only skills."""

import unittest
from unittest.mock import patch

from routers.hero_guides import hero_mechanics


def skill(slug, description, notes=None, **fields):
    return {"name": slug, "name_loc": slug, "desc_loc": description,
            "notes_loc": notes or [], "behavior": "4", **fields}


def guide(hero_id, abilities, stale=False):
    hero = {"id": hero_id, "name": "npc_dota_hero_test", "name_loc": "测试英雄", "abilities": abilities}
    with patch("routers.hero_guides._valve", return_value=({"heroes": [hero]}, 100, stale)):
        return hero_mechanics(hero_id)


class HeroUsageTests(unittest.TestCase):
    def test_uncovered_juggernaut_has_movable_ward_advice_and_current_evidence(self):
        result = guide(8, [skill("juggernaut_healing_ward", "召唤一个治疗守卫，治疗友军。治疗守卫可以移动。", ["可以控制治疗守卫。"]),
                           skill("juggernaut_omni_slash", "主宰攻击目标和附近的其它敌方单位。")])
        self.assertIsNone(result["practice"])
        self.assertEqual(len(result["usage_tips"]), 2)
        ward = result["usage_tips"][0]
        self.assertIn("单独控制", ward["action"])
        self.assertIn("后方", ward["action"])
        self.assertIn("可以移动", ward["evidence"][0]["text"])
        self.assertNotEqual(ward["action"], result["abilities"][0]["description"])

    def test_lifestealer_wounds_advice_uses_fading_slow_and_attack_based_heal(self):
        result = guide(54, [skill("life_stealer_open_wounds", "减缓受害者的移动速度，友军攻击该单位时根据造成的伤害回复生命。受害者逐渐恢复移动速度。", ["减速效果不断降低。"]),
                            skill("life_stealer_infest", "噬魂鬼在体内时每秒恢复生命，可以现身。无法对敌方英雄生效。")])
        self.assertIsNone(result["practice"])
        wounds, infest = result["usage_tips"]
        self.assertIn("前段减速", wounds["action"])
        self.assertIn("实际攻击这个目标", wounds["action"])
        self.assertIn("不是给全队直接加血", wounds["action"])
        self.assertIn("不能对敌方英雄", infest["action"])
        self.assertIn("逐渐恢复移动速度", wounds["evidence"][0]["text"])

    def test_lina_soul_advice_requires_a_hit_not_just_a_cast(self):
        result = guide(25, [skill("lina_fiery_soul", "每次技能击中一个敌人都会获得攻击和移动速度加成。", ["每次技能击中敌人都会刷新持续时间。", "使用物品不会触发。"], behavior="2")])
        self.assertIn("命中敌人", result["usage_tips"][0]["action"])
        self.assertIn("落空或只用物品", result["usage_tips"][0]["action"])

    def test_changed_mechanism_withholds_specific_ward_advice(self):
        result = guide(8, [skill("juggernaut_healing_ward", "召唤一个治疗守卫。")])
        self.assertEqual(result["usage_tips"], [])

    def test_upgrade_only_and_hidden_abilities_never_become_base_advice(self):
        for fields in [{"ability_is_granted_by_scepter": True}, {"ability_is_granted_by_shard": True}, {"behavior": "5"}]:
            with self.subTest(fields=fields):
                result = guide(8, [skill("juggernaut_omni_slash", "攻击附近的其它敌方单位。", **fields)])
                self.assertEqual(result["usage_tips"], [])

    def test_interrupting_another_units_channel_does_not_become_self_channel_advice(self):
        result = guide(20, [skill("vengefulspirit_nether_swap", "瞬间交换位置，移形换位会打断目标的持续施法。", behavior="8", target_team=3)])
        self.assertEqual(result["usage_tips"], [])

    def test_channel_exception_does_not_invent_a_movement_restriction(self):
        result = guide(6, [skill("drow_ranger_multishot", "持续施法 - 射出箭矢。", ["可以缓慢移动和使用物品。"], behavior="132")])
        self.assertEqual(result["usage_tips"], [])

    def test_passive_next_attack_is_not_presented_as_an_active_button(self):
        result = guide(9, [skill("mirana_selemenes_faith", "下次攻击会造成额外伤害。", behavior="2")])
        self.assertEqual(result["usage_tips"], [])

    def test_healing_denial_and_healing_amplification_are_not_direct_heals(self):
        for description in ["敌人无法获得任何治疗效果。", "对友军的治疗效果根据生命值增强。"]:
            with self.subTest(description=description):
                self.assertEqual(guide(69, [skill("test", description, target_team=3)])["usage_tips"], [])

    def test_stale_or_unrecognized_mechanics_stay_a_gap(self):
        ability = skill("juggernaut_healing_ward", "治疗守卫可以移动并治疗友军。")
        self.assertTrue(guide(8, [ability])["usage_tips"])
        cached = guide(8, [ability], stale=True)
        self.assertEqual(cached["usage_tips"], [])
        self.assertTrue(cached["source"]["stale"])
        self.assertEqual(guide(146, [skill("new_mechanism", "未识别的新机制。")])["usage_tips"], [])

    def test_unparseable_skill_flags_do_not_produce_advice_or_crash(self):
        for behavior in [None, "unknown", -1, True]:
            with self.subTest(behavior=behavior):
                self.assertEqual(guide(8, [skill("juggernaut_healing_ward", "治疗守卫可以移动并治疗友军。", behavior=behavior)])["usage_tips"], [])


if __name__ == "__main__":
    unittest.main()
