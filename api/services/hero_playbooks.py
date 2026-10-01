"""Editorial, mechanism-gated instructions for a few explicitly reviewed heroes.

This module does not infer a combo from arbitrary skill descriptions or claim
that these learning plans were measured in matches. Call only with fresh Valve
mechanics. Unknown heroes and changed/upgrade-only mechanisms remain a gap.
"""

from copy import deepcopy
import re


def _bits(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    try:
        number = int(value)
        return number if number >= 0 else None
    except ValueError:
        return None


def _eligible(hero, abilities):
    raw = {}
    for skill in hero.get("abilities", []) or []:
        if not isinstance(skill, dict):
            continue
        behavior = _bits(skill.get("behavior"))
        if (behavior is None or behavior & 1 or skill.get("is_item") or
                skill.get("ability_is_granted_by_scepter") or skill.get("ability_is_granted_by_shard")):
            continue
        raw[skill.get("name")] = skill
    result = {}
    for ability in abilities or []:
        if not isinstance(ability, dict) or ability.get("slug") not in raw:
            continue
        description = ability.get("description")
        if not isinstance(description, str) or not description.strip():
            continue
        notes = ability.get("notes", [])
        if not isinstance(notes, list):
            notes = []
        result[ability["slug"]] = " ".join([description, *[n for n in notes if isinstance(n, str)]])
    return result


def _matches(current, rules):
    return all(slug in current and all(re.search(pattern, current[slug]) for pattern in patterns)
               for slug, patterns in rules.items())


def _number(hero, slug, field):
    """Use current raw numeric facts only; never hard-code a patch's timings."""
    for ability in hero.get("abilities", []) or []:
        if not isinstance(ability, dict) or ability.get("name") != slug:
            continue
        for value in ability.get("special_values", []) or []:
            if not isinstance(value, dict) or value.get("name") != field:
                continue
            numbers = value.get("values_float")
            if (isinstance(numbers, list) and len(numbers) == 1 and
                    type(numbers[0]) in (int, float) and numbers[0] > 0):
                return numbers[0]
    return None


def _step(label, detail, *, skill=None, item=None):
    return {**({"skill": skill} if skill else {}), **({"item": item} if item else {}),
            "label": label, "detail": detail}


def _sequence(title, when, steps, cautions, rules):
    return {"title": title, "when": when, "steps": steps, "cautions": cautions, "_rules": rules}


ARC = {
    "arc_warden_flux": [r"持续伤害", r"减缓.*移动速度", r"周围有其他敌方单位.*不会造成伤害"],
    "arc_warden_magnetic_field": [r"攻击速度", r"友方单位.*闪避来自磁场外的攻击"],
    "arc_warden_spark_wraith": [r"缓慢实体化", r"目标区域", r"敌方单位进入范围", r"减速"],
    "arc_warden_tempest_double": [r"复制体.*当前所有物品和基础技能", r"冷却时间.*独立", r"逐渐.*移动速度变慢.*攻击准确度下降"],
}

ARC_BUILD = {
    "label": "中单入门出装顺序（编辑学习建议）",
    "steps": [
        {"item": "bottle", "label": "先补对线补给与基础小件", "reason": "中单可用魔瓶配合控符；鞋、补给和小件按对线压力补齐，先保证能补刀和施法。"},
        {"item": "hand_of_midas", "label": "能稳定发育时做点金手", "reason": "为双体经济练习建立明确节奏；记得分别选本体和分身使用，危险局面先补生存。"},
        {"item": "maelstrom", "label": "接小电锤，开始处理兵线", "reason": "把练习重点转到清线、分控和安全转线；不要为攒装备放弃能守住的塔。"},
        {"item": "mjollnir", "label": "升级大电锤，形成普攻输出", "reason": "有稳定输出位置时完善清线与普攻能力；双体各自的物品操作需要分别完成。"},
    ],
    "branches": [
        {"when": "已有清线能力，需要抓缺少驱散、依赖施法逃生的落单英雄", "item": "orchid", "label": "紫苑抓人", "reason": "先由分身限制施法再接乱流、幽魂和普攻；沉默不能阻止物品驱散。"},
        {"when": "需要跨地图转线、守塔和处理危险兵线", "item": "travel_boots", "label": "飞鞋转线", "reason": "让分身承担危险线路，本体留在能撤退的位置；传送前看敌方位置和落点。"},
        {"when": "控制或法术使本体无法完成输出", "item": "black_king_bar", "label": "提前补黑皇杖", "reason": "按这局威胁提前安排生存装备，不必等输出路线全部买齐。"},
        {"when": "可驱散的沉默等减益经常打断行动", "item": "manta", "label": "按需分身斧", "reason": "用于应对能驱散的限制；先核对敌方控制是否能用弱驱散解除。"},
        {"when": "近战英雄持续贴脸，缺少拉开距离的手段", "item": "hurricane_pike", "label": "飓风长戟保站位", "reason": "先争取普攻空间，别把磁场当成对贴脸敌人的无条件保护。"},
        {"when": "需要限制关键目标，且已有足够生存与输出", "item": "sheepstick", "label": "邪恶镰刀补控制", "reason": "双体错开控制；先确认林肯、免疫和队友能否跟上。"},
    ],
    "note": "这是围绕中单补给→点金→小电锤→大电锤的编辑学习路线，可按威胁插入生存装备；不是样本统计、共同购买顺序或实测最优出装。不规定通用购买分钟。",
    "source_url": "https://dota2protracker.com/m/hero/Arc%20Warden",
}

ARC_SEQUENCES = [
    _sequence("六级抓落单：双乱流接退路幽魂", "风暴双雄已学、目标离开兵线和队友，自己有足够魔法且队友能跟进。", [
        _step("先确认目标落单", "看目标附近有没有它的队友或小兵；同时给本体选好不被反包的站位。"),
        _step("本体乱流起手", "对落单英雄施放乱流，利用减速争取后续布置时间。", skill="arc_warden_flux"),
        _step("本体幽魂放到退路", "把幽魂放在目标向塔或队友撤退会经过的位置，别只点它当前脚下。", skill="arc_warden_spark_wraith"),
        _step("开大并切到分身", "召出风暴双雄后立即单独选中分身；本体维持安全位置。", skill="arc_warden_tempest_double"),
        _step("分身补乱流", "让分身在施法距离内给同一目标接乱流，确认它仍没有走进友军或兵线。", skill="arc_warden_flux"),
        _step("分身幽魂继续封路", "第二个幽魂覆盖下一段退路，让对手绕路或走进触发区域。", skill="arc_warden_spark_wraith"),
        _step("在安全位置开磁场接普攻", "让双体在能持续攻击的位置输出；需续保护时错开两次磁场。", skill="arc_warden_magnetic_field"),
    ], ["乱流附近有目标一方的其他单位时停伤害，减速仍在；不要把进入兵线的目标当成完整乱流伤害。", "幽魂先实体化再触发，不能当成立即命中的指向技能。", "磁场只闪避圈外攻击，不能阻挡法术或贴脸攻击；两次磁场错开，不按叠加攻速计算。", "分身会随时间变慢且攻击失准；不要把它越走越远解释为离本体远就减伤。"], ARC),
    _sequence("已有紫苑：分身抓人，本体安全跟进", "已购买紫苑，目标缺少可立即使用的驱散或防护，分身能接近且本体位置安全。", [
        _step("召分身接近目标", "让风暴双雄先承担接近风险，保留本体退路并观察敌方支援。", skill="arc_warden_tempest_double"),
        _step("分身紫苑先限制施法", "在目标准备靠技能逃生前使用紫苑；如果已有法术抵挡或免疫，先处理或放弃这轮。", item="orchid"),
        _step("分身乱流跟上", "沉默生效后接乱流，检查目标是否仍远离自己的小兵和队友。", skill="arc_warden_flux"),
        _step("幽魂放到退路", "预判它朝塔、树林出口或队友退去的路径，提前放幽魂封路。", skill="arc_warden_spark_wraith"),
        _step("磁场内普攻", "分身找到能持续攻击的位置再开磁场；对手贴进来时优先拉开。", skill="arc_warden_magnetic_field"),
        _step("本体安全时才接第二轮", "本体不用为多交一个技能走进包围。第二个紫苑留到首个结束或目标驱散后再判断能否接上。", item="orchid"),
    ], ["沉默不是眩晕，目标仍可移动、普攻和使用物品；不要把两次紫苑一开始重叠。", "本体被切时先处理本体安全，不要只盯分身追击。"], ARC),
    _sequence("推塔与分控：分身走危险线，本体留退路", "有可推进兵线、队友位置或敌方露头信息支持；不确定敌方位置时以分身试探。", [
        _step("先安置本体", "把本体停在有视野、队友保护或能撤走的位置，再分配控制组。"),
        _step("分身去危险线", "让风暴双雄跟兵线推进；观察它剩余持续时间，避免本体无意识跟到塔前。", skill="arc_warden_tempest_double"),
        _step("磁场覆盖己方攻击单位", "推塔时把磁场落在己方英雄和兵线输出的位置；保护只针对圈外攻击。", skill="arc_warden_magnetic_field"),
        _step("幽魂布置切入口", "在敌方常用的树林出口、坡口或绕后入口提前放幽魂，争取发现和减速接近者的机会。", skill="arc_warden_spark_wraith"),
        _step("双磁场错开，本体受威胁就退", "若本体也安全参与，把第二次磁场留给续保护；敌人绕后时先切回本体撤退，再决定分身继续或回防。", skill="arc_warden_magnetic_field"),
    ], ["磁场不能让塔下单位免疫法术，也不能可靠阻止圈内贴身敌人。", "幽魂会被进入区域的其他敌方单位触发，不保证一定打到想抓的英雄。", "双体物品冷却独立；分别检查冷却，不要以为操作过本体就已操作分身。"], {s: ARC[s] for s in ("arc_warden_magnetic_field", "arc_warden_spark_wraith", "arc_warden_tempest_double")}),
    _sequence("已有羊刀：两次控制错开接", "已购买邪恶镰刀，目标无未处理的林肯或免疫，双体都能在安全距离施放且队友能跟输出。", [
        _step("先核对防护与跟进", "检查目标的法术抵挡、免疫和救人手段；没有处理把握就不强行交双羊。"),
        _step("召分身，先交一把羊刀", "让更安全的一体施放邪恶镰刀，并立即跟普通攻击。", skill="arc_warden_tempest_double", item="sheepstick"),
        _step("幽魂提前铺退路", "控制窗口里把幽魂放到结束后目标可能逃走的位置。", skill="arc_warden_spark_wraith"),
        _step("将结束时再接第二把", "切到另一体观察目标控制状态，接第二把羊刀；不要两体同时施放浪费控制时间。", item="sheepstick"),
    ], ["只有已购买羊刀才练这套；分身必须能使用该物品，不能把刷新球也当成可复制使用。", "敌人出现免疫、抵挡或救援后重新判断，不宣称双羊能保证击杀。"], {s: ARC[s] for s in ("arc_warden_spark_wraith", "arc_warden_tempest_double")}),
]


JUGG = {
    "juggernaut_blade_fury": [r"减益免疫", r"周围的敌方单位造成伤害", r"期间可以使用物品", r"只有不受剑刃风暴伤害的单位.*物理伤害"],
    "juggernaut_healing_ward": [r"治疗", r"可以移动", r"可以控制治疗守卫"],
    "juggernaut_omni_slash": [r"附近的其它敌方单位", r"无敌斩期间无敌"],
}
JUGG_SEQUENCES = [
    _sequence("对线击杀：队友控制后贴着转", "队友能先限制目标、退路已有视野，能在剑刃风暴范围内持续跟住。", [
        _step("先站到能跟住的位置", "等目标走离它的塔和支援，靠队友方向接近；别从很远处先开转再慢慢走。"),
        _step("队友控制生效后开转", "让队友先减速或控制，再开启剑刃风暴贴近目标。", skill="juggernaut_blade_fury"),
        _step("用移动跟住目标", "持续调整位置让目标留在周围伤害范围；不要以为对受剑刃风暴伤害的英雄下普攻指令还能额外打出常规物理伤害。", skill="juggernaut_blade_fury"),
        _step("结束后再接普攻或撤退", "转结束时看双方血量与支援：有安全攻击空间就接普攻，目标进塔或敌方支援到了就退。"),
    ], ["减益免疫不等于无敌；免疫穿透控制和物理攻击仍可能威胁你。", "先给自己留撤退路线，不把低血量当成必追理由。"], {"juggernaut_blade_fury": JUGG["juggernaut_blade_fury"]}),
    _sequence("无敌斩：先隔离目标，落地继续判断", "无敌斩可用，关键英雄与兵线、召唤物和其他敌人分开，落点不会被包围。", [
        _step("先把周围单位看清", "等兵线被处理或英雄离开其他单位，确认队友能接后续伤害；目标有躲避或防护时先等它交掉。"),
        _step("对隔离目标开无敌斩", "把无敌斩给需要击杀的英雄，观察它是否靠近其他单位导致斩击转移。", skill="juggernaut_omni_slash"),
        _step("大招结束再接近输出", "落地立刻看目标位置与敌方支援；仍能安全命中就接普攻，需要避免限制时再考虑剑刃风暴。", skill="juggernaut_blade_fury"),
        _step("不具备击杀条件就回队伍", "目标受救援、转移或多名敌人出现时，先沿已确认的路线撤出。"),
    ], ["无敌斩会在附近敌方单位间转移，不保证所有斩击都给最初英雄。", "无敌只在大招期间；落地后需要重新处理站位。"], {s: JUGG[s] for s in ("juggernaut_omni_slash", "juggernaut_blade_fury")}),
    _sequence("推塔续航：本体打塔，守卫单独跟后方", "队伍已经打赢一轮或正在安全推进，有受伤队友且治疗守卫可用。", [
        _step("先放在能照顾队伍的位置", "把治疗守卫放到受伤队友附近的安全一侧，避免直接放在敌人攻击范围最前端。", skill="juggernaut_healing_ward"),
        _step("单独选守卫跟队伍移动", "让守卫随队伍向前移动，但跟在受伤队友后方；不要与本体一起冲入塔前。", skill="juggernaut_healing_ward"),
        _step("本体继续打塔，间隔检查守卫", "本体攻击建筑时轮流检查小地图、守卫位置和队友血量，敌人来切守卫就先把它往后拉。"),
        _step("守卫跟着撤退，不留给对手", "队伍决定后撤时先带守卫走，给撤退队友保持治疗范围。", skill="juggernaut_healing_ward"),
    ], ["不要为了继续治疗让本体和守卫一起暴露。", "守卫需要单独控制，治疗不是放出后就自动跟随你的保证。"], {"juggernaut_healing_ward": JUGG["juggernaut_healing_ward"]}),
]

SNIPER = {
    "sniper_shrapnel": [r"减速", r"目标区域的视野", r"能量.*恢复"],
    "sniper_take_aim": [r"主动开启", r"自身.*减速", r"前方的锥形"],
    "sniper_assassinate": [r"短时间瞄准", r"从远距离", r"眩晕"],
}
SNIPER_SEQUENCES = [
    _sequence("正面输出：先用榴霰弹找区域，再站稳瞄准", "队友在前方承接，侧翼有视野，敌人必须经过一个通道或进入队伍攻击范围。", [
        _step("榴霰弹覆盖入口", "先把榴霰弹放在对手走来的通道，等区域视野确认位置，再决定站在哪里输出。", skill="sniper_shrapnel"),
        _step("在队友后方选普攻目标", "保持与前排的距离，选一个能持续攻击的目标；不要为了换目标走进侧翼黑区。"),
        _step("站位稳定后开瞄准", "朝向准备攻击的敌人再开启瞄准，集中这一段窗口打普通攻击。", skill="sniper_take_aim"),
        _step("被绕侧就先换位置", "敌人从侧后方接近或前排后退时，优先向队友和安全路线移动，等重新站稳再输出。"),
    ], ["瞄准会让自身减速并限制前方锥形视野，不能开着盲目追人。", "榴霰弹能量逐次恢复，保留后续通道覆盖，别把所有次数交在同一处。"], {s: SNIPER[s] for s in ("sniper_shrapnel", "sniper_take_aim")}),
    _sequence("收残血：有安全瞄准空间再用暗杀", "目标已离开普攻范围，队友或已有信息能确认目标，自己暂时不受贴身威胁。", [
        _step("先检查身边威胁", "看侧翼和小地图，确认没有敌人已经向你突进；被贴脸时先移动脱离。"),
        _step("确认目标再开始暗杀", "对需要补伤害的目标使用暗杀，给短时间瞄准留出施法空间。", skill="sniper_assassinate"),
        _step("等弹道结果，不先冲进黑区", "观察是否实际造成击杀，队友能继续追就由他们接；不要因为按下暗杀就走向未确认区域。"),
        _step("继续输出前重新站位", "目标存活时回到队友保护下选择普攻或下一轮技能，击杀后也先检查周围再继续。"),
    ], ["暗杀有瞄准过程，正在被切时不是立刻生效的救命控制。", "不把按下技能当作已经击杀；敌方防护和救援仍可能改变结果。"], {"sniper_assassinate": SNIPER["sniper_assassinate"]}),
    _sequence("守塔清线：用区域视野守住输出位置", "敌方兵线接近塔，自己能在塔后或队友后方处理兵线。", [
        _step("榴霰弹放兵线和入口", "把区域落在进塔兵线及敌人可能站住的位置，先确认有没有英雄跟进。", skill="sniper_shrapnel"),
        _step("安全位置普攻清线", "利用塔后或队友后方的位置打能打到的小兵，不追出保护范围。"),
        _step("把下一次留给敌人的路线", "敌人换位置时再补下一片区域覆盖，保留一个能量应对新的入口或撤退路线。", skill="sniper_shrapnel"),
        _step("敌人绕后时及时换侧", "看到侧翼突破就向队友移动；只在新的安全位置稳定后使用瞄准。", skill="sniper_take_aim"),
    ], ["榴霰弹不会对建筑造成伤害，不能当作隔空磨塔技能。", "本套不依赖魔晶震荡手雷；没有购买升级时不要预设有额外逃生技能。"], {"sniper_shrapnel": [*SNIPER["sniper_shrapnel"], r"不会对建筑造成伤害"], "sniper_take_aim": SNIPER["sniper_take_aim"]}),
]

PUCK = {
    "puck_illusory_orb": [r"路线方向", r"飞行过程中", r"灵动之翼.*传送到法球"],
    "puck_waning_rift": [r"传送至目标地点", r"沉默"],
    "puck_phase_shift": [r"持续施法", r"任何动作.*中止", r"无敌"],
    "puck_dream_coil": [r"束缚", r"走出梦境.*眩晕.*额外伤害"],
}
PUCK_SEQUENCES = [
    _sequence("撤退：先发安全法球，相位等位置再转移", "幻象法球和相位转移可用，能提前确定一个没有敌人包围的退路方向。", [
        _step("先定安全终点和路线", "看队友位置与地形，把法球路线朝安全侧规划；当前法球支持路线施法，别只盯最初发射方向。"),
        _step("向退路发幻象法球", "先把法球发出去，让它飞向已选退路；确认它仍在飞行。", skill="puck_illusory_orb"),
        _step("危险伤害到来时用相位", "攻击或技能将到达时施放相位转移，暂时停止其他动作，观察法球位置。", skill="puck_phase_shift"),
        _step("法球到安全位置时用灵动之翼", "在法球尚未消失且落点安全时转移到它的位置，然后继续向队友撤退；这次转移会结束相位。", skill="puck_illusory_orb"),
    ], ["相位期间任何动作都会中止保护；不要先乱点移动再期待完整无敌时间。", "法球结束后不能再转移，不能机械地等满相位时间。", "法球落点不安全时重新判断，不把传送本身当成脱离包围的保证。"], {s: PUCK[s] for s in ("puck_illusory_orb", "puck_phase_shift")}),
    _sequence("消耗：法球打路线，沉默后按退路决定追退", "目标在法球路径上，附近敌人和自己的撤退路线可见，队友能接应。", [
        _step("法球穿过目标的移动路线", "根据它的走位规划法球路径，让路径经过目标；先用命中和视野信息判断局面。", skill="puck_illusory_orb"),
        _step("确认安全才转移过去", "只有落点有队友支援或有可走的退路时才用灵动之翼接近；否则留在原处消耗。", skill="puck_illusory_orb"),
        _step("新月之痕接近并沉默", "目标在可作用范围时用新月之痕接伤害和沉默，把落点选在能返回队友的一侧。", skill="puck_waning_rift"),
        _step("接普攻后按信息撤出", "沉默窗口里有安全距离就接普攻；敌方支援出现则走回队伍，必要时用相位等下一次移动窗口。", skill="puck_phase_shift"),
    ], ["已经转移到法球后，不要预设同一个法球还可再用一次作为回程。", "沉默不能限制普通攻击和物品，贴身换血仍有风险。"], {s: PUCK[s] for s in ("puck_illusory_orb", "puck_waning_rift", "puck_phase_shift")}),
    _sequence("已有跳刀：沉默接梦境，留法球撤出", "已购买跳刀，能从视野外进入且队友已到跟进距离，法球和相位都留作退路。", [
        _step("队友到位后跳入", "先确认关键目标和落点，再用跳刀进入新月之痕能作用的位置；不为多框一个人跳进无支援区域。", item="blink"),
        _step("新月之痕先限制施法", "在队友能接伤害的一侧沉默关键目标，落点仍需保留撤退空间。", skill="puck_waning_rift"),
        _step("梦境覆盖要留住的英雄", "把梦境给准备逃离的关键英雄或多名聚集敌人，让队友跟进；目标不走出梦境时不要预设会触发破裂晕。", skill="puck_dream_coil"),
        _step("法球朝退路发出", "向队伍或安全地形规划法球路线，伤害有安全机会才补。", skill="puck_illusory_orb"),
        _step("相位躲反打，再转移撤出", "危险伤害将到达时相位，在法球还存在且位置安全时使用灵动之翼离开。", skill="puck_phase_shift"),
    ], ["这是已购买跳刀后的进场练习，不是所有帕克局都必须按这条出装。", "梦境破裂的额外控制有条件，不把目标一直留在圈内也算成破裂眩晕。", "不要把跳刀按成被持续伤害打断时也能随时逃走。"], PUCK),
]

LINA = {
    "lina_dragon_slave": [r"火焰", r"敌人"],
    "lina_light_strike_array": [r"眩晕"],
    "lina_fiery_soul": [r"技能击中一个敌人", r"攻击和移动速度", r"刷新持续时间", r"使用物品不会触发"],
    "lina_laguna_blade": [r"单个敌方单位", r"伤害生效.*延迟", r"躲避该伤害"],
}
LINA_SEQUENCES = [
    _sequence("有队友控制：光击阵接龙破斩，再补单体爆发", "队友能先限制目标，自己施法距离和魔法足够，目标尚未开启防护或救援。", [
        _step("等队友控制落地，放光击阵", "对已被限制的目标落点放光击阵，留意原控制结束时间，别在对手还自由走位时就认定必定命中。", skill="lina_light_strike_array"),
        _step("确认晕中后接龙破斩", "让火焰路线穿过关键目标；有其他敌人同路线时可以一并覆盖，仍以命中关键目标为先。", skill="lina_dragon_slave"),
        _step("需要补击杀时用神灭斩", "目标还活着且需要这段单体伤害时施放；有躲避或免疫窗口则等对方交掉或继续受控再放。", skill="lina_laguna_blade"),
        _step("利用炽魂接普攻", "技能实际命中后，在安全距离补普通攻击，不要为多打一发越过队友。", skill="lina_fiery_soul"),
    ], ["光击阵不是按下就立即命中的保证；看实际控制状态再接后续。", "神灭斩施放到伤害生效仍有延迟，不把已经按下当作击杀完成。"], LINA),
    _sequence("清线转输出：技能命中叠炽魂，留控制应对贴脸", "能在安全位置清线或打野，准备带着炽魂状态接下一次交战。", [
        _step("站在线路侧面找多目标路线", "选择能让龙破斩经过多个小兵的位置，同时给自己留后退空间。"),
        _step("龙破斩实际命中小兵", "让技能命中敌人取得炽魂，不要只为按技能而向空地施放。", skill="lina_dragon_slave"),
        _step("接普攻清理余下单位", "利用炽魂带来的攻速继续攻击，尽量用安全普攻处理剩余单位，保留魔法。", skill="lina_fiery_soul"),
        _step("交战前按需刷新，保留光击阵", "需要继续输出时找安全的技能命中刷新持续时间；附近可能被抓时不要为了多打小兵把光击阵随手交掉。", skill="lina_light_strike_array"),
    ], ["炽魂来自技能命中，落空和使用物品不会触发；不要把每次施法都算成加层。", "没有安全站位时先离开，不为保炽魂进入敌方视野深处。"], {s: LINA[s] for s in ("lina_dragon_slave", "lina_fiery_soul", "lina_light_strike_array")}),
    _sequence("被追时：光击阵放追击路线，命中后拉开", "敌方沿可预判路线追来，自己还能施法，队友或塔的方向能作为退路。", [
        _step("先朝队友方向走", "选择可得到接应的路线，观察敌人是否必须经过窄口；不要只顾回头丢技能。"),
        _step("光击阵预判追击落点", "把光击阵放在敌人将经过的位置，施法后继续撤退；没晕中就保持撤退，不强行接完整连招。", skill="lina_light_strike_array"),
        _step("确认晕中再补龙破斩", "安全距离内让龙破斩穿过被控制目标，借技能命中得到的炽魂移速调整距离。", skill="lina_dragon_slave"),
        _step("拉开后再决定反打", "队友接应且站位安全时才接普攻；敌方仍有多人跟进就继续走向队伍。", skill="lina_fiery_soul"),
    ], ["没有命中就没有这次炽魂收益；不要靠预想的移速加成制定必然逃生路线。", "光击阵命中与否要实际观察，不把预测落点当作稳定先手控制。"], {s: LINA[s] for s in ("lina_light_strike_array", "lina_dragon_slave", "lina_fiery_soul")}),
]

LIFESTEALER = {
    "life_stealer_rage": [r"减益免疫", r"魔法抗性和移动速度"],
    "life_stealer_open_wounds": [r"减缓.*移动速度", r"友军在攻击该单位时.*回复", r"逐渐恢复移动速度"],
    "life_stealer_feast": [r"每次攻击时", r"治疗"],
    "life_stealer_infest": [r"体内时每秒恢复", r"从宿主体内现身", r"无法对敌方英雄生效"],
}
LIFESTEALER_SEQUENCES = [
    _sequence("贴身集火：进入控制区前狂暴，伤口后持续打", "队友能跟进，目标在可接近范围，已确认敌方哪些控制无视减益免疫。", [
        _step("先接近到队友能跟的位置", "利用地形和队友先手接近，不要远远挂伤口后才开始赶路。"),
        _step("预计限制到来前开狂暴", "进入敌方控制或法术范围、需要继续贴身行动时开启狂暴，别把持续时间全用在走路上。", skill="life_stealer_rage"),
        _step("贴近后挂撕裂伤口", "队友和自己能立即攻击目标时再施放，利用前段较强减速开始集火。", skill="life_stealer_open_wounds"),
        _step("持续攻击兑现回复", "对同一目标接普通攻击并跟着调整位置，队友也需实际攻击才能得到伤口回复。", skill="life_stealer_feast"),
        _step("狂暴将结束时重看位置", "目标远离队友或敌方支援来到时停止深追，向队伍退；别只看攻击回血就一直站住。"),
    ], ["狂暴提供减益免疫和魔抗，不是无敌，也不挡所有控制。", "伤口减速逐渐减弱，不等于完整持续时间都能稳定黏住人。", "攻击回复不能保证扛住一轮爆发或连续控制。"], {s: LIFESTEALER[s] for s in ("life_stealer_rage", "life_stealer_open_wounds", "life_stealer_feast")}),
    _sequence("感染队友进场：先沟通宿主路线，再现身集火", "有愿意配合的友方英雄作为合法宿主，队友能安全接近关键目标，伤口与狂暴可用。", [
        _step("和队友约好进场点", "明确要抓谁、从哪边接近和何时现身；先检查宿主自身是否能安全到达。"),
        _step("感染友方宿主", "在施法距离内进入合法友方宿主，让宿主承担移动接近，本体在体内恢复。", skill="life_stealer_infest"),
        _step("宿主到位后现身", "等队友到能跟伤害的位置再从宿主体内现身，不要在接近途中提前出来。"),
        _step("需要行动保护时开启狂暴", "预计控制即将到来时用狂暴保证贴近窗口，留意无视免疫的限制。", skill="life_stealer_rage"),
        _step("伤口后与队友普攻集火", "近距离给目标撕裂伤口，趁前段减速强时共同攻击；失去跟进条件就退回队伍。", skill="life_stealer_open_wounds"),
    ], ["基础感染不能对敌方英雄使用，本套不要求神杖升级。", "感染队友不等于控制队友的移动；进场路线必须靠沟通。", "现身范围伤害不是保证击杀，仍要确认后续能贴身攻击。"], {s: LIFESTEALER[s] for s in ("life_stealer_infest", "life_stealer_rage", "life_stealer_open_wounds")}),
    _sequence("恢复与撤退：找合法宿主感染，安全位置再出来", "血量不足且感染可用，附近有可施法的友方单位或合法非英雄宿主，能选择安全撤退方向。", [
        _step("先找真实可用的宿主", "先确认附近宿主和距离，敌方英雄不能当作基础感染的逃生目标。"),
        _step("感染避开正面换血", "进入宿主，在体内按技能机制恢复，避免低血量时为了吸血继续硬打。", skill="life_stealer_infest"),
        _step("让宿主走到安全侧", "友方英雄宿主需要沟通移动；若是可控制的敌方非英雄或中立生物，再控制它向队友或安全方向移动。", skill="life_stealer_infest"),
        _step("看周围威胁再现身", "等位置安全且血量恢复到能行动的程度再出来；队友仍被围时重新评估，不为了现身伤害跳回敌人中间。"),
    ], ["感染不是一按就回满血，回复发生在宿主体内。", "合法宿主类型按当前基础技能核对，不套用神杖对敌方英雄的玩法。"], {"life_stealer_infest": [*LIFESTEALER["life_stealer_infest"], r"敌方非英雄单位或中立生物.*控制其进行移动和攻击"]}),
]

PLAYBOOKS = {
    113: {"hero_slug": "arcwarden", "build_plan": ARC_BUILD, "build_rules": ARC, "sequences": ARC_SEQUENCES},
    8: {"hero_slug": "juggernaut", "sequences": JUGG_SEQUENCES},
    35: {"hero_slug": "sniper", "sequences": SNIPER_SEQUENCES},
    13: {"hero_slug": "puck", "sequences": PUCK_SEQUENCES},
    25: {"hero_slug": "lina", "sequences": LINA_SEQUENCES},
    54: {"hero_slug": "lifestealer", "sequences": LIFESTEALER_SEQUENCES},
}


def operating_guide(hero: dict, abilities: list):
    """Return a fresh editorial learning guide, or None if no reviewed card fits.

    Check both raw flags and prepared descriptions/notes. Each sequence fails
    closed independently, so one changed ability does not keep a dependent card
    visible or remove unrelated, still-supported practice.
    """
    if not isinstance(hero, dict):
        return None
    entry = PLAYBOOKS.get(hero.get("id"))
    if not entry:
        return None
    current = _eligible(hero, abilities)
    sequences = [{key: deepcopy(value) for key, value in sequence.items() if key != "_rules"}
                 for sequence in entry["sequences"] if _matches(current, sequence["_rules"])]
    if hero.get("id") == 113:
        delay = _number(hero, "arc_warden_spark_wraith", "base_activation_delay")
        slow = _number(hero, "arc_warden_tempest_double", "max_slow")
        miss = _number(hero, "arc_warden_tempest_double", "max_blind_chance")
        for sequence in sequences:
            if delay is not None:
                sequence["cautions"].append(f"当前幽魂需要 {delay:g} 秒实体化，要提前放在退路，不能作为即时指向伤害。")
            if slow is not None and miss is not None:
                sequence["cautions"].append(f"当前分身随时间衰退，移动减速最高 {slow:g}%，攻击失准最高 {miss:g}%；不是离本体远减伤。")
    build = deepcopy(entry.get("build_plan")) if _matches(current, entry.get("build_rules", {})) else None
    if not sequences and not build:
        return None
    official = f"https://www.dota2.com/hero/{entry['hero_slug']}"
    sources = [official]
    if build and build.get("source_url") and build["source_url"] not in sources:
        sources.append(build["source_url"])
    return {"build_plan": build, "sequences": sequences, "source_urls": sources, "kind": "editorial_practice"}
