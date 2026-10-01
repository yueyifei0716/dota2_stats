"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { ArrowRight, BookOpen, Coins, ExternalLink, LoaderCircle, RotateCcw, Search, Sparkles, Swords, X } from "lucide-react";
import { getGuideHeroes, getHeroBuilds, getHeroMechanics } from "@/lib/api";
import { defaultBuildGroup, patchLabel } from "@/lib/hero-evidence";
import type { AllHero, GuideItem, HeroBuilds, HeroGuideCatalog, HeroMechanics } from "@/lib/types";
import styles from "./HeroGuide.module.css";

const CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react";
const ALIASES: Record<number, string[]> = {
  2: ["axe", "斧头"], 7: ["es", "小牛", "牛头"], 8: ["jugg", "剑圣"],
  11: ["sf", "影魔"], 14: ["pudge", "屠夫"], 18: ["sven", "流浪剑客"],
  22: ["zeus", "宙斯"], 25: ["lina", "火女"], 26: ["lion", "莱恩"],
  35: ["sniper", "火枪"], 39: ["qop", "女王"], 49: ["dk", "龙骑"],
  71: ["sb", "白牛"], 74: ["invo", "卡尔"], 76: ["od", "黑鸟"],
  97: ["magnus", "猛犸"], 104: ["lc", "军团"], 106: ["es", "火猫"],
  107: ["es", "土猫"], 119: ["dw", "小仙女"], 120: ["pango", "滚滚"],
};
const ITEM_NAMES: Record<string, string> = {
  hand_of_midas: "迈达斯之手", orchid: "紫怨", bloodthorn: "血棘", travel_boots: "远行鞋", travel_boots_2: "远行鞋2级", aghanim_shard: "阿哈利姆魔晶", aghanims_shard: "阿哈利姆魔晶", bottle: "魔瓶", power_treads: "动力鞋",
  blink: "闪烁匕首", blade_mail: "刃甲", black_king_bar: "黑皇杖", sphere: "林肯法球",
  force_staff: "原力法杖", glimmer_cape: "微光披风", sheepstick: "邪恶镰刀",
  ultimate_scepter: "阿哈利姆神杖", hurricane_pike: "飓风长戟", pipe: "洞察烟斗",
  lotus_orb: "莲花法球", meteor_hammer: "陨星锤", manta: "幻影斧", maelstrom: "漩涡",
  mjollnir: "雷神之锤", desolator: "黯灭", butterfly: "蝴蝶", satanic: "撒旦之邪力",
  silver_edge: "白银之锋", shivas_guard: "希瓦的守护", heart: "恐鳌之心",
  overwhelming_blink: "盛势闪光", swift_blink: "迅疾闪光", arcane_blink: "奥术闪光",
  octarine_core: "玲珑心", aether_lens: "以太之镜", vladmir: "弗拉迪米尔的祭品",
  solar_crest: "炎阳纹章", spirit_vessel: "魂之灵瓮", battlefury: "狂战斧",
  yasha_and_kaya: "慧夜对剑", sange_and_yasha: "散夜对剑", kaya_and_sange: "慧心对剑",
  cyclone: "Eul 的神圣法杖", wind_waker: "风之杖", refresher: "刷新球", bloodstone: "血精石",
};

type Resource<T> = { heroId: number; data: T | null; error: string; loading: boolean };
const emptyResource = <T,>(heroId: number): Resource<T> => ({ heroId, data: null, error: "", loading: true });

function initialHero() {
  if (typeof window === "undefined") return 7;
  const hero = Number(new URLSearchParams(window.location.search).get("hero"));
  return Number.isInteger(hero) && hero > 0 && hero <= 2000 ? hero : 7;
}

function dateLabel(seconds: number | null) {
  if (!seconds) return "时间未核验";
  return new Date(seconds * 1000).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function itemName(item: GuideItem) {
  return ITEM_NAMES[item.slug] || item.name;
}

function Retry({ onClick, label }: { onClick: () => void; label: string }) {
  return <button type="button" className={styles.iconButton} onClick={onClick} aria-label={label} title={label}><RotateCcw size={16} /></button>;
}

function Loading({ children }: { children: string }) {
  return <div className={styles.status} role="status"><LoaderCircle size={16} className="animate-spin" /><span>{children}</span></div>;
}

function ItemIcon({ item, neutral = false }: { item: GuideItem; neutral?: boolean }) {
  return <span className={`${styles.itemSlot} ${neutral ? styles.neutralSlot : ""}`} title={item.item_id === null ? "装备未记录" : item.item_id ? itemName(item) : "空槽"}>
    {item.icon && <Image unoptimized src={item.icon} alt={itemName(item)} width={34} height={25} />}
    {(item.item_id === null || item.item_id > 0) && !item.icon && <span>?</span>}
  </span>;
}

function OperatingGuide({ mechanics }: { mechanics: Resource<HeroMechanics> }) {
  const data = mechanics.data;
  const guide = data?.operating_guide;
  if (!data || !guide) return null;
  return <section className={styles.section} aria-labelledby="operating-heading">
    <div className={styles.sectionHeading}><h2 id="operating-heading"><Swords size={18} />选到这个英雄，先这样打</h2><span>编辑教学 · 当前机制校核</span></div>
    {guide.build_plan && <div className={styles.starterPlan}>
      <h3 id="starter-items-heading">{guide.build_plan.label}</h3>
      <ol className={styles.itemRoute}>{guide.build_plan.steps.map((step, index) => <li key={`${step.item}:${index}`}>
        <span className={styles.stepNumber}>{index + 1}</span><Image unoptimized src={`${CDN}/items/${step.item}.png`} alt="" width={40} height={30} />
        <div><strong>{step.label}</strong><p>{step.reason}</p></div>
      </li>)}</ol>
      <div className={styles.branchGrid}>{guide.build_plan.branches.map((branch, index) => <article key={`${branch.item}:${index}`}>
        <Image unoptimized src={`${CDN}/items/${branch.item}.png`} alt="" width={34} height={25} /><div><strong>{branch.label}</strong><p>{branch.when}</p><small>{branch.reason}</small></div>
      </article>)}</div>
      <p className={styles.disclaimer}>{guide.build_plan.note}</p>
      <a className={styles.referenceLink} href={guide.build_plan.source_url} target="_blank" rel="noreferrer">出装教学依据<ExternalLink size={12} /></a>
    </div>}
    <div className={styles.playbookGrid} id="playbook-flows">{guide.sequences.map((sequence) => <article key={sequence.title} className={styles.playbook}>
      <h3>{sequence.title}</h3><p className={styles.when}>{sequence.when}</p>
      <ol>{sequence.steps.map((step, index) => {
        const skill = data.abilities.find((ability) => ability.slug === step.skill);
        const icon = skill?.icon || (step.item ? `${CDN}/items/${step.item}.png` : "");
        return <li key={`${step.label}:${index}`}><span className={styles.stepNumber}>{index + 1}</span>
          {icon && <Image unoptimized src={icon} alt="" width={28} height={28} />}<div><strong>{step.label}</strong><p>{step.detail}</p></div>
        </li>;
      })}</ol>
      <ul className={styles.cautionList}>{sequence.cautions.map((caution) => <li key={caution}>{caution}</li>)}</ul>
    </article>)}</div>
    <div className={styles.source}><span>练习流程依据机制推导，不是实测最优连招。</span>{guide.source_urls.map((url, index) => <a key={url} href={url} target="_blank" rel="noreferrer">{index === 0 ? "官方机制" : "构筑参考"}<ExternalLink size={12} /></a>)}</div>
  </section>;
}

function Equipment({ builds, onRetry, learningLane }: { builds: Resource<HeroBuilds>; onRetry: () => void; learningLane?: number | null }) {
  const data = builds.data;
  const [groupKey, setGroupKey] = useState("");
  const groups = data?.groups || [];
  const key = (group: typeof groups[number]) => `${group.patch_id}:${group.lane_role}`;
  const group = groups.find((entry) => key(entry) === groupKey) || (data ? defaultBuildGroup(data, builds.heroId, learningLane) : undefined);
  const candidates = group?.candidates || data?.candidates || [];
  return <section className={styles.section} aria-labelledby="equipment-heading">
    <div className={styles.sectionHeading}><h2 id="equipment-heading"><Coins size={18} />高分选手实际怎么买</h2><Retry onClick={onRetry} label="重新读取出装样本" /></div>
    {builds.loading ? <Loading>正在核验选手与近期天梯出装，首次读取可能需要约 20 秒</Loading> : builds.error ? <p className={styles.status} role="alert">{builds.error}</p> : data && <>
      <p className={styles.evidence}>近 {data.source.window_days} 天 · {data.source.players.length} 名榜内冠绝选手 · {data.sample} 场天梯完整样本 · 主版本 {patchLabel(data.patch_id, data)}</p>
      {groups.length > 0 && <label className={styles.groupPicker}>分别查看分路与版本<select aria-label="出装样本分组" value={group ? key(group) : ""} onChange={(event) => setGroupKey(event.target.value)}>{groups.map((entry) => <option key={key(entry)} value={key(entry)}>版本 {patchLabel(entry.patch_id, data)} · {entry.lane_name} · {entry.sample} 场 / {entry.players_count} 人 · {entry.purchase_log_sample} 场购买日志</option>)}</select></label>}
      {group && <p className={styles.evidence}>{group.lane_name}：{group.inventory_sample} 场完整装备，{group.players_count} 名选手；{group.purchase_log_sample} 场有购买事件。Replay 分路不等于 1–5 号位。{group.status === "small_sample" ? "本组样本稀少，仅作逐局参考。" : ""}</p>}
      {group && group.purchase_branches.length > 0 && <div className={styles.observedRoutes}><h3>真实购买记录中的分支</h3>{group.purchase_branches.map((branch) => <article key={branch.slugs.join(":")}>
        <div className={styles.observedItems}>{branch.items.map((item, index) => <span key={`${item.slug}:${index}`}><ItemIcon item={item} /><b>{itemName(item)}</b>{index < branch.items.length - 1 && <ArrowRight size={12} />}</span>)}</div>
        <p>{branch.matches}/{branch.sample} 场有购买事件的样本 · {branch.frequency}% · {branch.players} 名选手</p>
        <div className={styles.examples}>{branch.example_matches.slice(0, 3).map((id) => <a href={`https://www.opendota.com/matches/${id}`} key={id} target="_blank" rel="noreferrer">核对比赛 {id}<ExternalLink size={12} /></a>)}</div>
      </article>)}<p className={styles.disclaimer}>仅列实际记录的前三件主要成装；不同分支分别展示。单件购入中位数不代表共同购买路线。</p></div>}
      {group && !group.purchase_branches.length && <p className={styles.disclaimer}>本组没有可核验的主要装备购买顺序；结算持有不能反推先买什么。</p>}
      {group && group.purchase_items.length > 0 && <div className={styles.purchaseStats}><h3>本组实际购买频次</h3>{group.purchase_items.slice(0, 8).map((item) => <div key={item.slug}><ItemIcon item={item} /><span>{itemName(item)}</span><strong>{item.matches}/{item.sample} · {item.pick_rate}%</strong><small>{item.purchase_minute === null ? "时间样本不足" : `购入中位 ${item.purchase_minute} 分钟（${item.timing_sample} 场）`}</small></div>)}</div>}
      {candidates.length > 0 ? <div className={styles.candidates}>
        {candidates.map((item) => <article key={item.slug} className={styles.candidate}>
          <div className={styles.itemHeading}><Image unoptimized src={item.icon} alt="" width={64} height={46} /><div><h3 title={item.name}>{itemName(item)}</h3><span><Coins size={12} />{item.cost?.toLocaleString() ?? "价格未核验"}</span></div></div>
          <div className={styles.frequency}><strong>{item.pick_rate}%</strong><span>结算持有 · {item.matches}/{item.sample} 场</span></div>
          <p>{item.context}</p>
          {item.purchase_minute !== null && <div className={styles.timing}>购入时间中位数 {item.purchase_minute} 分钟 <span>（{item.timing_sample} 场有购买记录）</span></div>}
          <div className={styles.examples}>{item.example_matches.slice(0, 2).map((id, index) => <a key={id} href={`https://www.opendota.com/matches/${id}`} target="_blank" rel="noreferrer">比赛 {index + 1}<ExternalLink size={12} /></a>)}</div>
        </article>)}
      </div> : <p className={styles.empty}>{data.source.status === "unavailable" ? "高分选手或近期天梯接口暂时不可用，暂无可核验的装备候选。" : data.sample < 3 ? "核验到的高分选手天梯完整样本少于 3 场，暂不生成候选。" : "这批样本没有足够的成装记录。"}</p>}
      {data.source.budget_exhausted && <p className={styles.disclaimer}>部分上游读取用时较长，已停止继续等待；已核验样本保留，可稍后重新读取。</p>}
      {data.source.warnings?.length ? <p className={styles.disclaimer} role="status">{data.source.warnings.some((warning) => warning.reason === "rate_limited") ? "免费上游接口暂时限流，已保留可用证据；请稍后重新读取。" : "部分上游读取失败，当前只显示已核验记录。"}</p> : null}
      {data.source.stale && <p className={styles.disclaimer}>当前为先前真实缓存；选手核验与读取时间保留原值，尚未重新核验。</p>}
      <p className={styles.disclaimer}>仅纳入 OpenDota 记录为冠绝一世且有榜位的选手，以及他们的近期天梯排位。段位为资料读取结果，不是该场比赛时点的精确 MMR；位置与小版本未核验。持有频次不代表最优顺序或胜率提升。</p>
      {data.source.players.length > 0 && <details className={styles.rankSources}><summary>选手段位来源</summary><ul>{data.source.players.map((player) => <li key={player.account_id}><a href={player.url} target="_blank" rel="noreferrer">{player.name}<ExternalLink size={12} /></a><span>冠绝一世 · 榜位 #{player.leaderboard_rank} · 读取于 {dateLabel(player.checked_at)}</span></li>)}</ul></details>}
      {data.source.status === "partial" && <p className={styles.disclaimer}>部分上游数据暂不可用或来自缓存：读取 {data.source.attempted} 场，采用 {data.sample} 场同主版本记录。</p>}
      <div className={styles.source}><a href={data.source.url} target="_blank" rel="noreferrer">{data.source.label}<ExternalLink size={12} /></a><span>读取于 {dateLabel(data.source.fetched_at)}</span></div>
    </>}
  </section>;
}

function Mechanics({ mechanics, onRetry }: { mechanics: Resource<HeroMechanics>; onRetry: () => void }) {
  const data = mechanics.data;
  const practice = data?.practice;
  return <section className={styles.section} aria-labelledby="mechanics-heading">
    <div className={styles.sectionHeading}><h2 id="mechanics-heading"><Swords size={18} />机制细节与技能数值</h2><Retry onClick={onRetry} label="重新读取技能资料" /></div>
    {mechanics.loading ? <Loading>正在读取官方技能资料</Loading> : mechanics.error ? <p className={styles.status} role="alert">{mechanics.error}</p> : data && <>
      {practice && !data.operating_guide ? <div className={styles.practice}>
        <div className={styles.practiceHeading}><h3>{practice.title}</h3><span>练习连招</span></div>
        <ol className={styles.sequence}>{practice.steps.map((slug, index) => {
          const ability = data.abilities.find((entry) => entry.slug === slug);
          const name = ability?.name || ITEM_NAMES[slug] || (slug === "attack" ? "普通攻击" : slug);
          const icon = ability?.icon || (slug === "attack" ? "" : `${CDN}/items/${slug}.png`);
          return <li key={`${slug}:${index}`}><div>{icon ? <Image unoptimized src={icon} alt="" width={32} height={32} /> : <Swords size={23} />}<span>{name}</span></div>{index < practice.steps.length - 1 && <ArrowRight size={14} className={styles.stepArrow} />}</li>;
        })}</ol>
        <p>{practice.use_when}</p><p className={styles.watchOut}>{practice.watch_out}</p>
        {practice.steps.some((slug) => !data.abilities.some((ability) => ability.slug === slug) && slug !== "attack") && <div className={styles.disclaimer}>物品步骤以已经持有对应装备为前提，不是本局购买要求。</div>}
      </div> : null}
      {!data.operating_guide && (data.usage_tips.length > 0 ? <div className={styles.usage}>
        <div className={styles.practiceHeading}><h3>实际用法</h3><span>依据官方机制推导 · 非比赛统计</span></div>
        <ol className={styles.usageList}>{data.usage_tips.map((tip) => {
          const ability = data.abilities.find((entry) => entry.slug === tip.skill);
          return <li key={tip.skill}><div className={styles.usageHeading}>{ability && <Image unoptimized src={ability.icon} alt="" width={28} height={28} />}<h4>{tip.title}</h4></div><p>{tip.action}</p><details className={styles.tipEvidence}><summary>官方机制依据</summary>{tip.evidence.map((evidence) => <p key={evidence.skill}><strong>{evidence.name}</strong>{evidence.text}</p>)}<a href={data.source.url} target="_blank" rel="noreferrer">查看官方来源<ExternalLink size={12} /></a></details></li>;
        })}</ol>
        {!practice && <p className={styles.disclaimer}>深度连招尚未整理；以上为有当前机制依据的操作建议。</p>}
      </div> : <p className={styles.disclaimer}>{data.source.stale ? "当前官方机制未核验，暂不生成新的操作建议。" : "当前技能资料尚不足以支持操作建议，技巧暂缺。"}</p>)}
      <details className={styles.skillReference}><summary>查看官方技能说明与数值</summary><div className={styles.abilities}>{data.abilities.map((ability) => <article key={ability.slug} className={styles.ability}>
        <div className={styles.abilityHeading}>{ability.kind === "先天" ? <span className={styles.innateIcon} title="先天能力"><Sparkles size={21} /></span> : <Image unoptimized src={ability.icon} alt="" width={40} height={40} />}<div><h3>{ability.name}</h3><span>{ability.kind}</span></div></div>
        <p>{ability.description}</p>
        {ability.notes.length > 0 && <ul>{ability.notes.map((note, index) => <li key={index}>{note}</li>)}</ul>}
        <div className={styles.abilityNumbers}>{ability.cooldowns.some((value) => value > 0) && <span>冷却 {ability.cooldowns.join(" / ")} 秒</span>}{ability.mana_costs.some((value) => value > 0) && <span>耗蓝 {ability.mana_costs.join(" / ")}</span>}</div>
        {(ability.scepter || ability.shard) && <details className={styles.upgrades}><summary>神杖 / 魔晶</summary>{ability.scepter && <p><strong>神杖</strong>{ability.scepter}</p>}{ability.shard && <p><strong>魔晶</strong>{ability.shard}</p>}</details>}
      </article>)}</div></details>
      <div className={styles.source}><a href={data.source.url} target="_blank" rel="noreferrer">{data.source.label}<ExternalLink size={12} /></a><span>{data.source.stale ? "上游暂不可用 · 缓存于 " : "读取于 "}{dateLabel(data.source.fetched_at)}</span></div>
    </>}
  </section>;
}

function Matches({ builds }: { builds: Resource<HeroBuilds> }) {
  const [visible, setVisible] = useState(8);
  if (!builds.data?.matches.length) return null;
  return <section className={styles.section} aria-labelledby="guide-matches-heading">
    <div className={styles.sectionHeading}><h2 id="guide-matches-heading"><BookOpen size={18} />高分对局，直接看出装</h2><span>{builds.data.sample} 场</span></div>
    <div className={styles.matchList}>{builds.data.matches.slice(0, visible).map((match) => <a key={match.match_id} className={styles.match} href={`https://www.opendota.com/matches/${match.match_id}`} target="_blank" rel="noreferrer">
      <div className={styles.matchPlayer}><strong>{match.player}</strong><span>{match.match_type} · 冠绝一世 · 榜位 #{match.leaderboard_rank} · {dateLabel(match.start_time)} · {match.lane_name || "分路未记录"} · 版本 {patchLabel(match.patch_id, builds.data!)}</span></div>
      <div className={styles.matchResult}><span className={match.win === true ? styles.win : match.win === false ? styles.loss : ""}>{match.win === null ? "结果未核验" : match.win ? "胜利" : "失败"}</span><span>{match.kills ?? "?"} / {match.deaths ?? "?"} / {match.assists ?? "?"}</span></div>
      <div className={styles.inventory}>{match.items.map((item, index) => <ItemIcon key={index} item={item} />)}<ItemIcon item={match.neutral} neutral /></div>
      <ExternalLink size={13} className={styles.matchLink} />
    </a>)}</div>
    {visible < builds.data.matches.length && <button type="button" className={styles.showMore} onClick={() => setVisible((count) => count + 8)}>显示更多已核验对局（{visible}/{builds.data.matches.length}）</button>}
  </section>;
}

export default function HeroGuide({ recentHeroIds = [] }: { recentHeroIds?: number[] }) {
  const [heroId, setHeroId] = useState(initialHero);
  const [query, setQuery] = useState("");
  const [catalog, setCatalog] = useState<HeroGuideCatalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [catalogRetry, setCatalogRetry] = useState(0);
  const [mechanicsRetry, setMechanicsRetry] = useState(0);
  const [buildsRetry, setBuildsRetry] = useState(0);
  const [mechanics, setMechanics] = useState<Resource<HeroMechanics>>(emptyResource(heroId));
  const [builds, setBuilds] = useState<Resource<HeroBuilds>>(emptyResource(heroId));

  useEffect(() => {
    const controller = new AbortController();
    getGuideHeroes(controller.signal).then((result) => { if (!controller.signal.aborted) setCatalog(result); }).catch((error) => { if (!controller.signal.aborted) setCatalogError(error instanceof Error ? error.message : "英雄目录读取失败"); });
    return () => controller.abort();
  }, [catalogRetry]);

  useEffect(() => {
    const controller = new AbortController();
    getHeroMechanics(heroId, controller.signal).then((result) => {
      if (!controller.signal.aborted) setMechanics({ heroId, data: result, error: "", loading: false });
    }).catch((error) => {
      if (!controller.signal.aborted) setMechanics({ heroId, data: null, error: error instanceof Error ? error.message : "技能资料读取失败", loading: false });
    });
    return () => controller.abort();
  }, [heroId, mechanicsRetry]);

  useEffect(() => {
    const controller = new AbortController();
    getHeroBuilds(heroId, controller.signal, buildsRetry === 0).then((result) => {
      if (!controller.signal.aborted) setBuilds({ heroId, data: result, error: "", loading: false });
    }).catch((error) => {
      if (!controller.signal.aborted) setBuilds({ heroId, data: null, error: error instanceof Error ? error.message : "出装样本读取失败", loading: false });
    });
    return () => controller.abort();
  }, [heroId, buildsRetry]);

  const heroes = useMemo(() => {
    if (!catalog) return [];
    const search = query.trim().toLowerCase().replace(/\s+/g, "");
    if (search) {
      const searchable = catalog.heroes.map((hero) => ({ hero, names: [hero.hero_cn, hero.hero_en, String(hero.hero_id), ...(ALIASES[hero.hero_id] || [])].map((name) => name.toLowerCase().replace(/\s+/g, "")) }));
      const exact = searchable.filter((entry) => entry.names.includes(search));
      return (exact.length ? exact : searchable.filter((entry) => entry.names.some((name) => name.includes(search)))).map((entry) => entry.hero);
    }
    const ids = [...new Set([heroId, ...recentHeroIds, 7, 2, 26, 97, 104, 76, 120, 8])].slice(0, 8);
    return ids.map((id) => catalog.heroes.find((hero) => hero.hero_id === id)).filter((hero): hero is AllHero => Boolean(hero));
  }, [catalog, heroId, query, recentHeroIds]);
  const currentMechanics = mechanics.heroId === heroId ? mechanics : emptyResource<HeroMechanics>(heroId);
  const currentBuilds = builds.heroId === heroId ? builds : emptyResource<HeroBuilds>(heroId);
  const hero = catalog?.heroes.find((entry) => entry.hero_id === heroId) || currentMechanics.data?.hero;
  const chooseHero = (selected: AllHero) => {
    if (selected.hero_id !== heroId) {
      setMechanics(emptyResource(selected.hero_id));
      setBuilds(emptyResource(selected.hero_id));
      setBuildsRetry(0);
    }
    setHeroId(selected.hero_id);
    setQuery("");
    const url = new URL(window.location.href);
    url.searchParams.set("hero", String(selected.hero_id));
    window.history.replaceState(null, "", url);
  };

  return <div className={styles.guide}>
    <form className={styles.searchForm} role="search" onSubmit={(event) => { event.preventDefault(); if (heroes.length === 1) chooseHero(heroes[0]); }}>
      <label className={styles.search}><Search size={18} /><input type="search" aria-label="搜索英雄" placeholder="搜索英雄、英文名或简称" value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" />{query && <button type="button" className={styles.iconButton} onClick={() => setQuery("")} aria-label="清空英雄搜索" title="清空英雄搜索"><X size={15} /></button>}</label>
    </form>
    {catalogError ? <div className={styles.status} role="alert"><span>{catalogError}</span><Retry onClick={() => { setCatalogError(""); setCatalogRetry((value) => value + 1); }} label="重新读取英雄目录" /></div> : !catalog ? <Loading>正在读取英雄目录</Loading> : <>
      <div className={styles.heroList} aria-label={query ? "英雄搜索结果" : "常用英雄"}>{heroes.map((entry) => <button key={entry.hero_id} type="button" onClick={() => chooseHero(entry)} className={styles.heroChoice} aria-pressed={entry.hero_id === heroId}><Image unoptimized src={entry.hero_icon} alt="" width={48} height={34} /><span>{entry.hero_cn}</span></button>)}</div>
      {query && !heroes.length && <p className={styles.empty}>没有找到匹配的英雄。</p>}
      {catalog.stale && <p className={styles.disclaimer}>英雄目录来自{catalog.source === "Valve" ? "官方缓存" : catalog.source}，当前完整目录未核验。</p>}
    </>}
    <header className={styles.heroHeader}>{hero?.hero_icon && <Image unoptimized src={hero.hero_icon} alt="" width={116} height={82} />}<div><h1>{hero?.hero_cn || "英雄"}</h1><span>{hero?.hero_en || `#${heroId}`}</span></div><nav className={styles.sectionNav} aria-label="英雄资料"><a href={currentMechanics.data?.operating_guide?.build_plan ? "#starter-items-heading" : "#equipment-heading"}><Coins size={14} />装备</a><a href={currentMechanics.data?.operating_guide ? "#playbook-flows" : "#mechanics-heading"}><Swords size={14} />操作</a>{currentBuilds.data?.matches.length ? <a href="#guide-matches-heading"><BookOpen size={14} />比赛</a> : null}</nav></header>
    <OperatingGuide mechanics={currentMechanics} />
    <div className={styles.quickReference}>
      <Equipment key={heroId} builds={currentBuilds} learningLane={currentMechanics.data?.operating_guide?.preferred_lane_role} onRetry={() => { setBuilds(emptyResource(heroId)); setBuildsRetry((value) => value + 1); }} />
    </div>
    <Matches key={heroId} builds={currentBuilds} />
    <Mechanics mechanics={currentMechanics} onRetry={() => { setMechanics(emptyResource(heroId)); setMechanicsRetry((value) => value + 1); }} />
  </div>;
}
