"""Conservative play suggestions supported by the current base-skill text."""

import re


# Advice is an inference, not a claim about measured high-rank play. Every entry
# needs its mechanism in today's response; upgrade-only skills are not eligible.
SPECIFIC_TIPS = [
    ("juggernaut_healing_ward", [r"治疗", r"可以移动|可以控制"], "让治疗守卫跟在队伍后方",
     "团战或推塔需要续航时放出治疗守卫，再单独控制它跟在受伤队友后方，让队友留在治疗范围里。不要让守卫随本体一起冲到最前面。"),
    ("juggernaut_omni_slash", [r"附近的.*敌方单位"], "无敌斩前先看周围目标",
     "尽量等要击杀的英雄与兵线、其他敌人分开后再开无敌斩，减少斩击转移到其他单位的机会；别只看主目标的血量。"),
    ("puck_illusory_orb", [r"飞行过程中", r"灵动之翼", r"传送到法球"], "先发退路法球，再决定是否传送",
     "需要撤退时先向安全方向发出法球，观察它的位置，在飞行过程中用灵动之翼转移。切入时也先确认落点和队友位置，不要看到命中就立即传过去。"),
    ("puck_phase_shift", [r"任何动作.*中止", r"无敌|免疫伤害"], "相位躲伤害时别提前移动",
     "看到攻击或技能伤害将到达时用相位转移躲避；不要紧接着下达移动或其他动作而提前结束保护。先想好结束后的退路，再恢复行动。"),
    ("lina_fiery_soul", [r"技能击中.*敌人|技能命中.*敌人", r"攻击.*速度", r"刷新持续时间"], "技能命中后接普攻，维持炽魂",
     "先用技能命中敌人取得炽魂，再接普通攻击利用攻速。持续交战时在安全位置补一次技能命中来刷新持续时间；落空或只用物品不等于获得炽魂。"),
    ("lina_laguna_blade", [r"伤害生效.*延迟", r"躲避"], "神灭斩配合控制，不把施放当作命中",
     "目标有躲避伤害的手段时，等队友控制住或它交掉该手段后再放神灭斩。施放后仍有伤害延迟，不要因为已经按下技能就认定击杀完成。"),
    ("sniper_take_aim", [r"自身.*减速", r"锥形"], "瞄准前先站稳，别开着追人",
     "先在队友后方找到能持续攻击的位置，再开瞄准并朝向要打的目标。自身减速且视野集中在前方，敌人绕侧或贴近时优先重新调整站位，不要开着瞄准追人。"),
    ("sniper_shrapnel", [r"视野", r"能量.*恢复"], "用榴霰弹先确认区域，再跟进",
     "追击或准备走进看不清的区域时，先把榴霰弹放到目标区域，等视野确认敌人位置再跟进。能量需要时间恢复，不要一次把所有次数交在同一处而没有后续区域覆盖。"),
    ("gyrocopter_flak_cannon", [r"只有主要目标.*攻击特效"], "把关键英雄设为高射火炮的主目标",
     "开启高射火炮后，直接攻击你需要集中伤害的关键英雄，让其余敌人吃范围攻击；不要把对小兵的攻击当成对周围英雄也能触发全部攻击特效。"),
    ("life_stealer_open_wounds", [r"减缓.*移动速度", r"攻击.*伤害回复", r"逐渐恢复移动速度"], "撕裂伤口后立即集火，别浪费前段减速",
     "队友能马上攻击目标时再挂撕裂伤口，趁前段减速强时贴上并集火；不要先挂上、再慢慢赶路。友军要实际攻击这个目标才能兑现回复，技能本身不是给全队直接加血。"),
    ("life_stealer_infest", [r"体内时.*恢复", r"现身", r"无法对敌方英雄生效"], "感染用于恢复与转移，基础技能别选敌方英雄",
     "需要恢复或随友方单位接近战场时，先感染合法宿主，在体内恢复后再决定现身位置。基础感染不能对敌方英雄使用；不要把神杖升级后的目标范围当成开局就有的能力。"),
    ("morphling_waveform", [r"向前涌进", r"无敌"], "波浪前先选安全终点",
     "追击时让波浪路径经过目标，但终点仍要能接上队友；撤退时把终点放在安全一侧。无敌只在波浪形态中，不要把终点停在敌人包围里。"),
    ("death_prophet_exorcism", [r"回到她身上.*再次攻击", r"持续时间结束后.*治疗"], "驱使恶灵时维持目标接触，别等开大就回血",
     "开大后在队友能保护的位置持续靠近要攻击的目标，让恶灵来回攻击；不要刚开大就退到目标范围外。治疗在持续时间结束后结算，不能把它当作立即抬血的救命技能。"),
    ("viper_poison_attack", [r"普通攻击", r"移动速度和魔法抗性", r"叠加"], "毒性攻击连续打同一目标",
     "需要压制一个目标时连续用毒性攻击打它，利用叠加的减速和魔抗降低接后续伤害；不要每一下都换目标，让原目标的叠加效果白白断掉。仍要控制追击距离，别为叠层脱离队友。"),
    ("enchantress_impetus", [r"目标越远.*伤害越高", r"距离.*弹道击中"], "推进出手后仍维持距离",
     "推进出手后继续保持与目标的安全距离，而不是主动贴上去；伤害看弹道命中时的距离。目标追你时向安全侧拉扯，但不要为了距离加成独自走进敌方包围。"),
    ("spirit_breaker_charge_of_darkness", [r"目标.*阵亡", r"最近的.*敌方单位"], "冲刺低血量目标时留意目标转移",
     "冲刺前先看队友能否跟进和路线终点，尤其是目标已经很残时；它在到达前阵亡会让冲刺转向附近敌人，别一直按原目标的位置预判切入结果。"),
    ("alchemist_unstable_concoction", [r"倒计时", r"自己手中爆炸"], "摇药看倒计时，留出投掷时间",
     "先确认附近有能投掷的敌方英雄，再开始摇药；边移动找投掷位置，盯住头顶倒计时，留出反应和投掷时间。不要只为追求最长眩晕而一直等，超过时限会在自己手中爆炸。"),
    ("invoker_invoke", [r"三个球的排列顺序无关", r"交换现有技能.*不会.*冷却"], "按需要的球组合切技能，别浪费时间重排",
     "交战前先准备这轮要用的元素球组合再祈唤；组合相同不必为排列顺序反复重按。已有技能需要换位置时可直接交换，不要把这种交换误当成重新祈唤而一直等待冷却。复杂法术衔接另需练习。"),
    ("obsidian_destroyer_astral_imprisonment", [r"无敌和无法行动", r"神智之蚀"], "禁锢期间别让队友伤害打空",
     "需要限制关键目标或保护英雄时使用星体禁锢，并提醒队友等它结束再接普通伤害。神智之蚀有明确例外可作用于禁锢目标，但不能把这个例外套给队友的所有技能。"),
    ("lone_druid_spirit_bear", [r"距离超过.*不能攻击", r"熊灵死亡.*反冲伤害"], "熊灵进场时本体要跟上距离",
     "熊灵准备攻击时，让本体在队友保护下跟进，避免超过允许距离后熊灵不能攻击。熊灵被集中攻击时及时后撤，不要只顾本体而让熊灵阵亡触发反冲伤害。"),
    ("rubick_telekinesis", [r"次级技能.*扔往目标方向", r"自身不会受到范围眩晕"], "抬起后选落点，不把范围晕算到主目标",
     "抬起目标后，用次级技能把落点选在队友能跟伤害的位置；想打范围眩晕时再看落点附近的其他敌人。落下的主目标本身不会吃到这个范围眩晕，别按它还能多晕一轮来衔接。"),
    ("naga_siren_song_of_the_siren", [r"无敌状态", r"提前停止"], "海妖之歌先重排站位，再统一停歌",
     "开歌争取撤退或重新站位的时间，让队友先到能衔接的位置再统一结束。歌里的敌人无敌，别让队友此时把伤害技能全交掉；计划跟控制时先沟通停歌时机。"),
    ("visage_summon_familiars", [r"石像形态.*无敌", r"迅速回复生命值", r"已有的佣兽.*死亡"], "佣兽危险时石像保命，别误重召",
     "佣兽被集火时用它的石像形态争取无敌和回血，靠近敌人落地也能提供控制。已有健康佣兽时别随手重按召唤：重新召唤会让原有佣兽死亡。"),
    ("medusa_mystic_snake", [r"每次跳跃后.*伤害", r"返回.*恢复魔法值"], "异蛇利用多目标弹跳，等它回来再算回蓝",
     "敌人靠近兵线或多个单位时，让异蛇有连续弹跳的机会；它返回到本体后才恢复魔法。蓝量很紧时不要一施放就按已经回蓝来继续交高耗蓝技能。"),
    ("shredder_timber_chain", [r"第一棵.*树", r"拉向那棵树"], "锯链先看第一棵树，不只看准星终点",
     "出锯链前确认路线上的第一棵树就是想去的落点，避免被更近的树提前拦住；撤退时也先找真实存在的树，再决定方向，而不是对空地交锯链。"),
    ("terrorblade_sunder", [r"血量百分比.*互换", r"减益免疫.*不会被影响生命值"], "魂断看血量比例和目标免疫",
     "准备魂断续命时先找当前生命百分比比你高的合法目标，别只看它的绝对血量。减益免疫的敌人不会被影响生命值，不能把这种目标当作可靠的换血对象。"),
    ("oracle_purifying_flames", [r"造成.*伤害", r"逐渐恢复生命值", r"友方和敌方"], "涤罪之焰先伤后回血，区分敌友",
     "给队友续航时要给后续恢复留出时间，不能把涤罪之焰当成立刻抬血。对敌人则要确认队伍能跟上伤害，避免伤害后留下持续恢复，反而帮助它活下来。"),
    ("storm_spirit_overload", [r"施法时.*电荷", r"下次攻击.*释放", r"效果不会叠加"], "施法后接一次普攻，别把超负荷连着覆盖",
     "技能施放后在安全攻击距离内接一次普攻，释放超负荷电荷，再接下一次技能。需要持续输出时不要只连续施法不攻击：超负荷不会叠加，使用物品也不会补上电荷。"),
]


def _bits(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    try:
        number = int(value)
        return number if number >= 0 else None
    except ValueError:
        return None


def _generic_tip(raw, ability):
    name, description = ability["name"], ability["description"]
    facts = " ".join([description, *ability["notes"]])
    behavior = _bits(raw.get("behavior")) or 0
    active = not behavior & 2
    conditional = bool(re.search(r"如果|有.*概率|(?:死亡|结束|断开)时|每当", description))
    if active and (behavior & 128 or re.match(r"持续施法\s*[-：]", description)) and not re.search(r"可以.*移动|可以.*使用物品", facts):
        return "channel", f"{name}需要完整施法空间", f"在队友能保护、敌方难以接近的位置开始{name}；持续施法期间不要用移动或其他施法指令提前中止它。对方仍有打断手段时，先等控制交掉或让队友先限制对手。"
    if active and re.search(r"下(?:一)?次.*攻击", description):
        return "next_attack", f"{name}之后要接上攻击", f"准备用{name}打人时，先确认能接近目标，再在强化生效后接普通攻击。不要开完强化就走开，让下一次攻击的收益白白等掉。"
    if active and re.search(r"提供.*视野|给予.*视野|拥有目标区域的视野", facts):
        return "vision", f"先用{name}探区域", f"进入看不清的坡上、树林或追击路线前，先用{name}取得对应区域的视野，再根据看到的位置跟进；不要本体先走进去再补技能。"
    if active and re.search(r"进入隐身|变为隐身|隐身状态", description) and not re.search(r"显形|隐身单位|隐身不能", description):
        return "invisibility", f"{name}用于调整接近路线", f"需要接近或脱离敌人时，用{name}改变路线再选落点；先观察敌方真视和探测手段，不要把隐身当作已经脱离危险。"
    if active and re.search(r"减益免疫", description):
        return "immunity", f"{name}在限制到来前准备好", f"预计将被减速或其他减益妨碍行动时，提前准备{name}并在需要行动的窗口开启。减益免疫不等于所有伤害都无效，也不要默认能挡住无视免疫的技能。"
    if active and not conditional and not re.search(r"无法|不能|不会", description):
        if behavior & 16 and re.search(r"眩晕|晕眩", description):
            return "area_control", f"{name}接在目标受限的时机", f"队友已经限制目标、或目标必须经过某个位置时，把{name}放在它所在或将经过的位置，提高命中把握。接控制时留意已有控制剩余时间，别一开始就把所有控制重叠。"
        if re.search(r"沉默", description):
            return "silence", f"{name}先限制依赖技能的目标", f"对手准备靠技能逃走、反打或救人时，先用{name}限制施法，再让队友跟伤害；沉默不是眩晕，不要因此认为目标无法移动或普攻。"
        if re.search(r"缴械", description):
            return "disarm", f"{name}卡住对方普攻窗口", f"对方依赖普通攻击输出、准备贴身打人时，用{name}限制攻击。缴械不是沉默，对手仍可能用技能反打，不要在此期间放松站位。"
        if re.search(r"缠绕|束缚", description):
            return "root", f"{name}先封住移动路线", f"目标准备跑出队友攻击范围时，先用{name}限制移动，再跟上伤害；别把限制移动当成完整眩晕，对手仍可能有施法或其他应对手段。"
        if re.search(r"眩晕|晕眩", description) and (_bits(raw.get("target_team")) or 0) & 2:
            return "unit_control", f"{name}留给关键目标", f"需要击杀或阻止对手逃走时，先确认队友能跟上，再用{name}控制关键目标；有弹道或延迟时，等控制实际生效后再跟后续技能。"
    if (active and ((_bits(raw.get("target_team")) or 0) & 1 or re.search(r"友方|友军", description)) and
            re.search(r"治疗(?:一个|目标|友方|友军|他们)|(?:恢复|回复).{0,8}生命值", description) and
            not re.search(r"无法|不能.*治疗|治疗.*增强|生命恢复增强", description)):
        return "heal", f"{name}先照顾正在受伤的队友", f"看到队友进入持续交战、血量开始下降时准备{name}，让治疗用于有缺口的生命值，而不是等到它已经倒下。施放时仍要保持自己能撤出的站位。"
    if active and re.search(r"驱散类型：强驱散|施加强驱散", facts):
        return "strong_dispel", f"{name}留作解除限制的窗口", f"需要解除可驱散的减益时，在自己还能施法的窗口使用{name}，先确认合法目标和效果生效时间。能强驱散不等于中了所有控制后都能按出来；驱散生效后及时调整位置。"
    if active and re.search(r"短距离传送|传送至目标地点|瞬间移动|向前冲刺|向前冲锋|向目标地点跳跃", description):
        return "mobility", f"{name}先选落点再交", f"使用{name}前先选落点：追击落到队友能跟伤害的位置，撤退落向安全侧；不要只看距离是否够得着，就把自己送进对方多人范围。"
    if active and re.search(r"敌", description) and re.search(r"减速|降低.*移动速度|减缓.*移动", description) and not re.search(r"自身.*减速|如果", description):
        return "slow", f"{name}为后续伤害争取距离", f"追击目标时先用{name}限制其移动，再缩短距离跟伤害；不要把减速当作眩晕，仍要防备它施法或反打。"
    if active and re.search(r"降低.*护甲|减少.*护甲", description):
        return "armor", f"{name}接在物理集火之前", f"队友准备物理集火时，先让{name}的减甲效果作用到要击杀的目标，再衔接攻击；不要等这一轮攻击已经打完才补减甲。"
    if re.search(r"攻击", description) and re.search(r"吸血|生命偷取", description):
        return "lifesteal", f"{name}的续航需要打出攻击", "血量不足但仍有安全攻击机会时，让攻击兑现生命偷取收益；敌方能一轮击杀或控制你时先撤开，不要只因为有吸血就硬扛。"
    return None


def usage_tips(hero, abilities):
    eligible = {}
    for raw in hero.get("abilities", []):
        if (not isinstance(raw, dict) or raw.get("is_item") or raw.get("ability_is_granted_by_scepter") or
                raw.get("ability_is_granted_by_shard") or _bits(raw.get("behavior")) is None or _bits(raw["behavior"]) & 1):
            continue
        eligible[raw.get("name")] = raw
    prepared = {ability["slug"]: ability for ability in abilities if ability["slug"] in eligible and ability["description"]}
    tips, used_skills, topics = [], set(), set()

    def add(slug, topic, title, action):
        ability = prepared[slug]
        tips.append({"skill": slug, "title": title, "action": action,
                     "evidence": [{"skill": slug, "name": ability["name"], "text": " ".join([ability["description"], *ability["notes"]])}]})
        used_skills.add(slug)
        topics.add(topic)

    for slug, patterns, title, action in SPECIFIC_TIPS:
        ability = prepared.get(slug)
        if ability and all(re.search(pattern, " ".join([ability["description"], *ability["notes"]])) for pattern in patterns):
            add(slug, slug, title, action)
    for slug, ability in prepared.items():
        if len(tips) >= 3:
            break
        if slug in used_skills:
            continue
        tip = _generic_tip(eligible[slug], ability)
        if tip and tip[0] not in topics:
            add(slug, *tip)
    return tips[:3]
