"use client";

import type { FormEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BookOpen,
  Check,
  Circle,
  Crown,
  FlaskConical,
  LoaderCircle,
  Search,
  Share2,
  ShieldCheck,
  Target,
  TrendingUp,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  createCommercialLead,
  getCommercialConfig,
  getMetaOverview,
  getPlayerDashboard,
  getPlayerMatchScorecard,
  getPlayerQuickDashboard,
  getPlayerReview,
  getPlayerReviewPreview,
  searchPlayers,
  unlockCommercialAccess,
  verifyCommercialAccess,
} from "@/lib/api";
import type {
  CommercialConfig,
  GlobalMetaOverview,
  PlayerDashboardData,
  PlayerHeroStat,
  PlayerMatch,
  PlayerMatchScorecard,
  PlayerMetaHero,
  PlayerReview,
  PlayerReviewResponse,
  PlayerSearchResult,
} from "@/lib/types";
import WardMap from "@/components/WardMap";

const DEFAULT_ACCOUNT_ID = "894447460";
const STORAGE_KEY = "dota2-dashboard-account-id";
const PRO_ACCESS_STORAGE_PREFIX = "dota2-pro-access-token";

type AppTab = "today" | "lab" | "pool" | "meta" | "progress";

const APP_TABS: { key: AppTab; label: string; detail: string; icon: LucideIcon }[] = [
  { key: "today", label: "Today", detail: "今日任务", icon: Target },
  { key: "lab", label: "Match Lab", detail: "比赛复盘", icon: FlaskConical },
  { key: "pool", label: "Hero Pool", detail: "英雄池", icon: BookOpen },
  { key: "meta", label: "Meta", detail: "全局环境", icon: Activity },
  { key: "progress", label: "Progress", detail: "训练进度", icon: TrendingUp },
];

const COMMERCIAL_OFFERS = [
  {
    key: "founder",
    title: "Founder Pro",
    price: "¥19/月",
    buyer: "认真冲分玩家",
    promise: "每周一份个人复盘、英雄池建议和下一组排位计划。",
    accent: "gold",
  },
  {
    key: "review",
    title: "单次复盘",
    price: "¥49/次",
    buyer: "想先验证价值",
    promise: "选择 3-5 场关键比赛，输出死亡、节奏、出装和分路问题。",
    accent: "cyan",
  },
  {
    key: "team",
    title: "战队空间",
    price: "¥199/月",
    buyer: "五排/高校队/小队",
    promise: "追踪多个账号、常用阵容、队友组合和赛前 BP 建议。",
    accent: "green",
  },
] as const;

function initialAccountId() {
  if (typeof window === "undefined") return DEFAULT_ACCOUNT_ID;
  const params = new URLSearchParams(window.location.search);
  return params.get("player") || window.localStorage.getItem(STORAGE_KEY) || DEFAULT_ACCOUNT_ID;
}

function numberClass(value: number) {
  if (value > 0) return "text-green-300";
  if (value < 0) return "text-red-300";
  return "text-stone-400";
}

function signed(value: number, suffix = "") {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value}${suffix}`;
}

function compactNumber(value: number) {
  if (!value) return "-";
  if (value >= 1000) return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k`;
  return String(value);
}

function toneClasses(tone: "gold" | "green" | "red" | "cyan") {
  return {
    gold: "border-yellow-300/25 bg-yellow-300/10 text-yellow-200",
    green: "border-green-300/25 bg-green-300/10 text-green-200",
    red: "border-red-300/25 bg-red-300/10 text-red-200",
    cyan: "border-cyan-300/25 bg-cyan-300/10 text-cyan-200",
  }[tone];
}

function checkoutConfigured(config: CommercialConfig | null, planKey: string) {
  return Boolean(config?.plans.find((plan) => plan.key === planKey)?.checkout_configured);
}

function ProductNav({
  data,
  copied,
  onCopyProfile,
  onOpenPro,
}: {
  data: PlayerDashboardData | null;
  copied: boolean;
  onCopyProfile: () => void;
  onOpenPro: () => void;
}) {
  return (
    <header className="product-nav">
      <div>
        <div className="text-xs font-black uppercase text-yellow-300">DotaSense</div>
        <div className="mt-1 text-sm text-stone-400">把最近比赛变成下一组三局的训练计划</div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onCopyProfile}
          disabled={!data}
          className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-xs font-bold text-stone-100 transition hover:border-cyan-300/50 disabled:opacity-50"
        >
          <Share2 size={15} aria-hidden="true" />
          {copied ? "已复制公开页" : "分享公开页"}
        </button>
        <button
          type="button"
          onClick={onOpenPro}
          className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-yellow-300/40 bg-yellow-300 px-3 py-2 text-xs font-black text-stone-950"
        >
          <Crown size={15} aria-hidden="true" />
          升级 Pro
        </button>
      </div>
    </header>
  );
}

function WorkspaceTabs({
  activeTab,
  onChange,
  data,
}: {
  activeTab: AppTab;
  onChange: (tab: AppTab) => void;
  data: PlayerDashboardData | null;
}) {
  return (
    <nav className="workspace-tabs" aria-label="DotaSense sections">
      {APP_TABS.map((tab) => {
        const Icon = tab.icon;
        const active = activeTab === tab.key;
        const disabled = !data && (tab.key === "lab" || tab.key === "pool" || tab.key === "progress");
        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            disabled={disabled}
            className={`workspace-tab ${active ? "workspace-tab-active" : ""}`}
            aria-current={active ? "page" : undefined}
          >
            <span className="flex items-center gap-2 text-sm font-black"><Icon size={16} aria-hidden="true" />{tab.label}</span>
            <span className="text-[11px] text-stone-500">{tab.detail}</span>
          </button>
        );
      })}
    </nav>
  );
}

function MetricCard({
  label,
  value,
  detail,
  tone = "gold",
}: {
  label: string;
  value: string;
  detail?: ReactNode;
  tone?: "gold" | "green" | "red" | "cyan";
}) {
  const toneClass = {
    gold: "text-yellow-300",
    green: "text-green-300",
    red: "text-red-300",
    cyan: "text-cyan-300",
  }[tone];

  return (
    <div className="stat-box min-h-[116px]">
      <div className="text-xs text-stone-400">{label}</div>
      <div className={`mt-3 text-3xl font-black tabular-nums ${toneClass}`}>{value}</div>
      {detail && <div className="mt-2 text-xs text-stone-400">{detail}</div>}
    </div>
  );
}

function ProfileHeader({
  data,
  query,
  setQuery,
  limit,
  setLimit,
  loading,
  onSubmit,
  showSearch = true,
}: {
  data: PlayerDashboardData | null;
  query: string;
  setQuery: (value: string) => void;
  limit: number;
  setLimit: (value: number) => void;
  loading: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  showSearch?: boolean;
}) {
  const profile = data?.profile;
  return (
    <div className="card overflow-hidden">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-center gap-4">
          {profile?.avatar ? (
            <img src={profile.avatar} alt="" className="h-16 w-16 rounded-lg border border-white/10 object-cover" />
          ) : (
            <div className="h-16 w-16 rounded-lg border border-white/10 bg-white/10" />
          )}
          <div>
            <div className="text-xs uppercase text-stone-400">OpenDota account</div>
            <h1 className="mt-1 text-3xl font-black text-stone-50">{profile?.username || "Dota 2 Dashboard"}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-stone-400">
              <span className="rounded border border-white/10 bg-white/5 px-2 py-1 tabular-nums">ID {profile?.account_id || DEFAULT_ACCOUNT_ID}</span>
              <span className="rounded border border-yellow-300/20 bg-yellow-300/10 px-2 py-1 text-yellow-200">{profile?.rank_name || "未校准"}</span>
              {profile?.leaderboard_rank && (
                <span className="rounded border border-cyan-300/20 bg-cyan-300/10 px-2 py-1 text-cyan-200">
                  #{profile.leaderboard_rank}
                </span>
              )}
            </div>
          </div>
        </div>

        {showSearch && (
          <form onSubmit={onSubmit} className="flex w-full flex-col gap-2 sm:flex-row lg:w-auto">
            <input
              className="h-11 min-w-0 rounded-lg border border-white/15 bg-black/25 px-3 text-sm text-stone-100 outline-none transition focus:border-yellow-300/70"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="account_id 或玩家名"
            />
            <select
              className="h-11 rounded-lg border border-white/15 bg-black/25 px-3 text-sm text-stone-100 outline-none"
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value))}
            >
              <option value={30}>最近 30 场</option>
              <option value={50}>最近 50 场</option>
              <option value={80}>最近 80 场</option>
            </select>
            <button
              className="h-11 rounded-lg border border-yellow-300/30 bg-yellow-300 px-4 text-sm font-black text-stone-950 transition hover:bg-yellow-200 disabled:opacity-60"
              disabled={loading}
            >
              {loading ? "加载中" : "查看"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function CommandSearch({
  query,
  setQuery,
  limit,
  setLimit,
  loading,
  onSubmit,
}: {
  query: string;
  setQuery: (value: string) => void;
  limit: number;
  setLimit: (value: number) => void;
  loading: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form onSubmit={onSubmit} className="command-search">
      <div className="command-search-input">
        <Search size={18} className="shrink-0 text-stone-500" aria-hidden="true" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search players or account id"
          className="min-w-0 flex-1 bg-transparent text-base font-bold text-stone-100 outline-none placeholder:text-stone-500"
        />
      </div>
      <select
        className="command-select"
        value={limit}
        onChange={(event) => setLimit(Number(event.target.value))}
        aria-label="Match sample size"
      >
        <option value={30}>30</option>
        <option value={50}>50</option>
        <option value={80}>80</option>
      </select>
      <button className="command-submit inline-flex items-center justify-center gap-2" disabled={loading}>
        {loading && <LoaderCircle size={16} className="animate-spin" aria-hidden="true" />}
        {loading ? "加载中" : "查看"}
      </button>
      <div className="command-keys" aria-hidden="true">
        <span>ctrl</span>
        <span>K</span>
      </div>
    </form>
  );
}

function SearchResults({ results, onPick }: { results: PlayerSearchResult[]; onPick: (accountId: number) => void }) {
  if (!results.length) return null;

  return (
    <div className="card">
      <h2 className="section-title">搜索结果</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {results.map((player) => (
          <button
            key={player.account_id}
            onClick={() => onPick(player.account_id)}
            className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-3 text-left transition hover:border-yellow-300/50 hover:bg-yellow-300/10"
          >
            {player.avatar ? <img src={player.avatar} alt="" className="h-10 w-10 rounded object-cover" /> : <div className="h-10 w-10 rounded bg-white/10" />}
            <span className="min-w-0">
              <span className="block truncate text-sm font-bold text-stone-100">{player.username}</span>
              <span className="block text-xs text-stone-500 tabular-nums">{player.account_id}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function GlobalHeroRow({ hero, rank }: { hero: PlayerMetaHero; rank: number }) {
  return (
    <tr className="border-b border-white/5 transition hover:bg-white/[0.035]">
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2">
          {hero.hero_icon && <img src={hero.hero_icon} alt="" className="h-8 w-8 rounded object-cover" />}
          <span>
            <span className="block font-black text-stone-100">{hero.hero_name}</span>
            <span className="text-xs text-stone-500">#{rank}</span>
          </span>
        </div>
      </td>
      <td className="py-3 pr-4 text-stone-300">{hero.role_label}</td>
      <td className={`py-3 pr-4 font-black tabular-nums ${hero.win_rate >= 52 ? "text-green-300" : "text-stone-300"}`}>
        {hero.win_rate}%
      </td>
      <td className="py-3 pr-4 tabular-nums text-stone-400">{compactNumber(hero.matches)}</td>
      <td className="py-3 pr-4">
        <div className="flex min-w-[110px] items-center gap-2">
          <div className="h-2 flex-1 rounded bg-white/10">
            <div className="h-2 rounded bg-cyan-300" style={{ width: `${Math.min(hero.contest_rate, 100)}%` }} />
          </div>
          <span className="w-10 text-right text-xs tabular-nums text-stone-500">{hero.contest_rate}%</span>
        </div>
      </td>
      <td className="py-3 pr-4 font-black tabular-nums text-yellow-300">{hero.meta_score}</td>
      <td className="py-3 pr-4 text-xs tabular-nums text-stone-500">{hero.pro_pick ? `${hero.pro_win}/${hero.pro_pick}` : "-"}</td>
    </tr>
  );
}

function GlobalMetaDashboard({
  meta,
  loading,
  error,
}: {
  meta: GlobalMetaOverview | null;
  loading: boolean;
  error: string;
}) {
  const [roleKey, setRoleKey] = useState("overall");
  const [heroQuery, setHeroQuery] = useState("");
  const roles = meta?.hero_meta.roles.length ? meta.hero_meta.roles : [{ key: "overall", label: "All" }];
  const activeHeroes = meta?.hero_meta.by_scope[roleKey] || meta?.hero_meta.top || [];
  const filteredHeroes = activeHeroes.filter((hero) => hero.hero_name.toLowerCase().includes(heroQuery.trim().toLowerCase()));
  const roleLabels = new Map(roles.map((role) => [role.key, role.label]));

  return (
    <section id="global-meta" className="card">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <div className="text-xs font-black uppercase text-cyan-300">Global Meta</div>
          <h1 className="mt-2 text-3xl font-black text-stone-50">全局大数据大盘</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-400">
            基于 OpenDota heroStats 的全英雄公开总体样本和可用职业字段，先看版本环境，再进入个人表现。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {roles.map((role) => (
            <button
              key={role.key}
              type="button"
              onClick={() => setRoleKey(role.key)}
              className={`rounded-lg border px-3 py-2 text-xs font-black transition ${
                roleKey === role.key
                  ? "border-cyan-300/60 bg-cyan-300 text-stone-950"
                  : "border-white/10 bg-white/[0.04] text-stone-300 hover:border-cyan-300/40"
              }`}
            >
              {role.label}
            </button>
          ))}
        </div>
      </div>

      {error && !meta && <div className="mt-5 rounded-lg border border-red-300/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">{error}</div>}
      {loading && !meta && <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.04] px-4 py-5 text-sm text-stone-400">正在加载全局英雄样本...</div>}

      {meta && (
        <>
          <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricCard label="全局英雄数" value={String(meta.snapshot.heroes)} detail={meta.source} tone="cyan" />
            <MetricCard label="公开样本量" value={compactNumber(meta.snapshot.total_matches)} detail="pub_pick / pub_win 总体" tone="gold" />
            <MetricCard label="职业字段样本" value={compactNumber(meta.snapshot.total_pro_picks)} detail="OpenDota pro_pick/pro_win" tone="green" />
            <MetricCard
              label="最高热度英雄"
              value={meta.snapshot.top_contested_rate ? `${meta.snapshot.top_contested_rate}%` : "-"}
              detail={meta.snapshot.top_contested_hero || "样本不足"}
              tone="red"
            />
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,0.7fr)]">
            <div className="min-w-0 rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-sm font-black text-stone-100">All-Player Hero Meta</div>
                  <div className="mt-1 text-xs text-stone-500">{roleLabels.get(roleKey) || "All"} · top {filteredHeroes.length}</div>
                </div>
                <input
                  value={heroQuery}
                  onChange={(event) => setHeroQuery(event.target.value)}
                  className="h-9 rounded-lg border border-white/10 bg-black/30 px-3 text-xs text-stone-100 outline-none transition focus:border-cyan-300/60"
                  placeholder="搜索英雄"
                />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px] text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs uppercase text-stone-500">
                      <th className="py-3 pr-4">Hero</th>
                      <th className="py-3 pr-4">Scope</th>
                      <th className="py-3 pr-4">WR</th>
                      <th className="py-3 pr-4">Matches</th>
                      <th className="py-3 pr-4">Contest</th>
                      <th className="py-3 pr-4">Score</th>
                      <th className="py-3 pr-4">Pro</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHeroes.slice(0, 18).map((hero, index) => (
                      <GlobalHeroRow key={`${hero.role_key}-${hero.hero_id}`} hero={hero} rank={index + 1} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="mb-3 text-sm font-black text-stone-100">Most Played</div>
                <div className="space-y-2">
                  {meta.volume_leaders.slice(0, 6).map((hero, index) => (
                    <div key={hero.hero_id} className="grid grid-cols-[24px_1fr_72px] items-center gap-2 text-xs">
                      <span className="font-black text-stone-500">#{index + 1}</span>
                      <span className="truncate text-stone-200">{hero.hero_name}</span>
                      <span className="text-right tabular-nums text-cyan-200">{compactNumber(hero.matches)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="mb-3 text-sm font-black text-stone-100">Pro Signal</div>
                <div className="space-y-2">
                  {meta.pro_signal.slice(0, 6).map((hero, index) => (
                    <div key={hero.hero_id} className="grid grid-cols-[24px_1fr_72px] items-center gap-2 text-xs">
                      <span className="font-black text-stone-500">#{index + 1}</span>
                      <span className="truncate text-stone-200">{hero.hero_name}</span>
                      <span className="text-right tabular-nums text-yellow-200">{hero.pro_win}/{hero.pro_pick}</span>
                    </div>
                  ))}
                  {!meta.pro_signal.length && <div className="text-sm text-stone-500">暂无职业样本字段</div>}
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="mb-3 text-sm font-black text-stone-100">High Confidence WR</div>
                <div className="space-y-2">
                  {meta.high_confidence.slice(0, 6).map((hero, index) => (
                    <div key={hero.hero_id} className="grid grid-cols-[24px_1fr_72px] items-center gap-2 text-xs">
                      <span className="font-black text-stone-500">#{index + 1}</span>
                      <span className="truncate text-stone-200">{hero.hero_name}</span>
                      <span className="text-right tabular-nums text-green-200">{hero.win_rate}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {meta.warnings.length > 0 && (
            <div className="mt-4 rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-4 py-3 text-xs text-yellow-100">
              OpenDota 全局接口暂时有部分警告，当前展示已成功获取的数据。
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ThreeMatchMission({ data, expanded = false }: { data: PlayerDashboardData; expanded?: boolean }) {
  const storageKey = `dota2-training-mission-${data.profile.account_id}`;
  const [startedAt, setStartedAt] = useState(() => typeof window === "undefined" ? 0 : Number(window.localStorage.getItem(storageKey) || 0));
  const step = data.coach.training_plan[0];
  const recommendedHero = data.coach.signature_hero || data.hero_pool[0];

  const challengeMatches = startedAt
    ? data.recent_matches
        .filter((match) => match.start_time * 1000 > startedAt)
        .sort((left, right) => left.start_time - right.start_time)
        .slice(0, 3)
    : [];
  const complete = challengeMatches.length >= 3;

  const startMission = () => {
    const timestamp = Date.now();
    window.localStorage.setItem(storageKey, String(timestamp));
    setStartedAt(timestamp);
  };

  const resetMission = () => {
    window.localStorage.removeItem(storageKey);
    setStartedAt(0);
  };

  return (
    <section className="mission-console" aria-label="三局训练挑战">
      <div className="mission-brief">
        <div className="flex flex-wrap items-center gap-2">
          <span className="evidence-chip evidence-verified"><ShieldCheck size={14} aria-hidden="true" />基于最近 {data.summary.games} 场</span>
          <span className={`evidence-chip ${complete ? "evidence-parsed" : "evidence-limited"}`}>
            {complete ? <Check size={14} aria-hidden="true" /> : <Circle size={14} aria-hidden="true" />}
            {complete ? "挑战完成" : `${challengeMatches.length}/3 场`}
          </span>
        </div>
        <div className="mt-4 text-xs font-black text-yellow-300">当前训练目标</div>
        <h1 className="mission-title">{step?.focus || "压缩英雄池"}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300">
          {step?.drill || `连续三局优先使用 ${recommendedHero?.hero_name || "最高熟练度英雄"}，每局记录一次最主要的失误。`}
        </p>
        <div className="mt-4 text-sm font-black text-cyan-100">成功标准：{step?.success_metric || "完成三局并留下可比较的数据"}</div>
        <div className="mt-5 flex flex-wrap gap-2">
          {!startedAt ? (
            <button type="button" onClick={startMission} className="mission-primary"><Target size={17} aria-hidden="true" />开始三局挑战</button>
          ) : (
            <button type="button" onClick={resetMission} className="mission-secondary">重新开始</button>
          )}
          {recommendedHero && (
            <span className="mission-hero">
              {recommendedHero.hero_icon && <img src={recommendedHero.hero_icon} alt="" />}
              推荐：{recommendedHero.hero_name}
            </span>
          )}
        </div>
      </div>

      <div className="mission-track">
        {[0, 1, 2].map((slot) => {
          const match = challengeMatches[slot];
          return (
            <div key={slot} className={`mission-slot ${match ? "mission-slot-filled" : ""}`}>
              <div className="mission-slot-index">0{slot + 1}</div>
              {match ? (
                <>
                  {match.hero_icon && <img src={match.hero_icon} alt="" className="mission-slot-hero" />}
                  <div className="min-w-0">
                    <div className="truncate text-sm font-black text-stone-100">{match.hero_name}</div>
                    <div className={`mt-1 text-xs font-black ${match.win ? "text-green-300" : "text-red-300"}`}>
                      {match.win ? "胜" : "负"} · {match.kills}/{match.deaths}/{match.assists}
                    </div>
                  </div>
                </>
              ) : (
                <div className="mission-slot-empty"><div className="text-sm font-black text-stone-400">等待比赛</div><div className="mt-1 text-xs text-stone-600">刷新后自动记录</div></div>
              )}
            </div>
          );
        })}
        {expanded && startedAt > 0 && <div className="mission-started">开始于 {new Date(startedAt).toLocaleString("zh-CN", { hour12: false })}</div>}
      </div>
    </section>
  );
}

function EvidenceCoverage({ data, deepLoading }: { data: PlayerDashboardData; deepLoading: boolean }) {
  const sample = data.recent_matches.slice(0, 20);
  const rows = [
    { label: "比赛结算", value: sample.filter((match) => match.detail_available).length, total: sample.length, tone: "verified" },
    { label: "英雄百分位", value: sample.filter((match) => match.benchmark_available).length, total: sample.length, tone: "verified" },
    { label: "Replay 事件", value: sample.filter((match) => match.replay_parsed).length, total: sample.length, tone: "parsed" },
    { label: "可靠分路", value: sample.filter((match) => match.lane_role > 0).length, total: sample.length, tone: "limited" },
  ];

  return (
    <section className="evidence-coverage">
      <div>
        <div className="flex items-center gap-2 text-sm font-black text-stone-100">
          {deepLoading ? <LoaderCircle size={16} className="animate-spin text-cyan-300" /> : <ShieldCheck size={16} className="text-green-300" />}
          {deepLoading ? "正在补全深度证据" : "数据证据覆盖"}
        </div>
        <p className="mt-2 text-xs leading-5 text-stone-500">缺少 Replay 或分路时，DotaSense 会明确停止推断。</p>
      </div>
      <div className="evidence-grid">
        {rows.map((row) => (
          <div key={row.label} className="evidence-stat">
            <div className="text-xs text-stone-500">{row.label}</div>
            <div className="mt-1 text-lg font-black tabular-nums text-stone-100">{row.value}/{row.total}</div>
            <div className={`evidence-bar evidence-bar-${row.tone}`} style={{ "--coverage": `${row.total ? (row.value / row.total) * 100 : 0}%` } as React.CSSProperties} />
          </div>
        ))}
      </div>
    </section>
  );
}

function MatchLab({ data }: { data: PlayerDashboardData }) {
  const candidates = useMemo(() => data.recent_matches.slice(0, 8), [data.recent_matches]);
  const [selectedMatchId, setSelectedMatchId] = useState(candidates[0]?.match_id || "");
  const [scorecard, setScorecard] = useState<PlayerMatchScorecard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const effectiveMatchId = candidates.some((match) => match.match_id === selectedMatchId) ? selectedMatchId : candidates[0]?.match_id || "";

  useEffect(() => {
    let active = true;
    if (!effectiveMatchId) return;
    async function loadScorecard() {
      await Promise.resolve();
      if (!active) return;
      setLoading(true);
      setError("");
      try {
        const result = await getPlayerMatchScorecard(data.profile.account_id, effectiveMatchId);
        if (active) setScorecard(result);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "评分卡加载失败");
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadScorecard();
    return () => { active = false; };
  }, [data.profile.account_id, effectiveMatchId]);

  return (
    <section className="match-lab">
      <div className="match-lab-header">
        <div>
          <div className="text-xs font-black text-cyan-300">MATCH LAB</div>
          <h1 className="mt-2 text-3xl font-black text-stone-50">单局证据评分卡</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-400">先比较同英雄百分位，再决定下一组三局只改哪一项。</p>
        </div>
        <span className="evidence-chip evidence-verified"><ShieldCheck size={14} />不做位置推断</span>
      </div>

      <div className="match-picker" aria-label="选择最近比赛">
        {candidates.map((match) => (
          <button key={match.match_id} type="button" onClick={() => setSelectedMatchId(match.match_id)} className={`match-pick ${effectiveMatchId === match.match_id ? "match-pick-active" : ""}`}>
            {match.hero_icon && <img src={match.hero_icon} alt="" />}
            <span className="min-w-0 text-left">
              <span className="block truncate text-xs font-black text-stone-100">{match.hero_name}</span>
              <span className={`mt-1 block text-[11px] font-black ${match.win ? "text-green-300" : "text-red-300"}`}>{match.win ? "胜" : "负"} · {match.kills}/{match.deaths}/{match.assists}</span>
            </span>
          </button>
        ))}
      </div>

      {loading && <div className="match-lab-loading"><LoaderCircle size={18} className="animate-spin" />正在读取比赛与英雄基准...</div>}
      {error && <div className="rounded-lg border border-red-300/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">{error}</div>}

      {scorecard && !loading && (
        <div className="scorecard-layout">
          <div className="scorecard-main">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-center gap-3">
                {scorecard.match.hero_icon && <img src={scorecard.match.hero_icon} alt="" className="h-14 w-14 rounded-md object-cover" />}
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-2xl font-black text-stone-50">{scorecard.match.hero_name}</h2>
                    <span className={scorecard.match.win ? "text-green-300" : "text-red-300"}>{scorecard.match.win ? "胜" : "负"}</span>
                  </div>
                  <div className="mt-1 text-sm tabular-nums text-stone-400">{scorecard.match.kills}/{scorecard.match.deaths}/{scorecard.match.assists} · KDA {scorecard.match.kda} · {scorecard.match.duration_text}</div>
                </div>
              </div>
              <span className={`evidence-chip ${scorecard.replay_parsed ? "evidence-parsed" : "evidence-limited"}`}>{scorecard.replay_parsed ? "Replay 已解析" : "结算数据模式"}</span>
            </div>

            <div className="scorecard-metrics">
              {scorecard.metrics.map((metric) => (
                <div key={metric.key} className="scorecard-metric">
                  <div className="flex items-center justify-between gap-2"><span className="text-xs text-stone-500">{metric.label}</span><span className="text-xs font-black tabular-nums text-cyan-200">P{metric.percentile}</span></div>
                  <div className="mt-2 flex items-end justify-between gap-2"><span className="text-xl font-black tabular-nums text-stone-100">{metric.value}</span><span className="text-[11px] text-stone-600">{metric.unit}</span></div>
                  <div className="percentile-track"><span style={{ width: `${metric.percentile}%` }} /></div>
                </div>
              ))}
            </div>

            <div className="scorecard-callout">
              <div className="text-xs font-black text-yellow-300">下一组三局只改这一项</div>
              <h3 className="mt-2 text-xl font-black text-stone-50">{scorecard.headline}</h3>
              <p className="mt-2 text-sm leading-6 text-stone-400">{scorecard.finding}</p>
              <p className="mt-3 text-sm font-bold leading-6 text-cyan-100">{scorecard.action}</p>
            </div>
          </div>

          <aside className="scorecard-evidence">
            <div className="text-sm font-black text-stone-100">证据清单</div>
            {scorecard.evidence.map((item) => (
              <div key={item.key} className="evidence-row">
                <div className="flex items-center justify-between gap-2"><span className="text-sm font-black text-stone-200">{item.label}</span><span className={`evidence-chip evidence-${item.status}`}>{item.status === "unavailable" ? "不可用" : item.status === "parsed" ? "已解析" : "已验证"}</span></div>
                <p className="mt-2 text-xs leading-5 text-stone-500">{item.detail}</p>
              </div>
            ))}
          </aside>
        </div>
      )}
    </section>
  );
}

function CoachBrief({ data }: { data: PlayerDashboardData }) {
  const { coach, summary } = data;
  const signature = coach.signature_hero;

  return (
    <section className="grid grid-cols-1 gap-4 xl:grid-cols-[420px_1fr]">
      <div className="card relative overflow-hidden">
        <div className="coach-radar" />
        <div className="relative">
          <div className="flex items-center justify-between gap-3">
            <h2 className="section-title mb-0">今日指挥台</h2>
            <span className={`rounded-lg border px-2.5 py-1 text-xs font-black ${toneClasses(coach.readiness.tone)}`}>
              {coach.readiness.label}
            </span>
          </div>
          <div className="mt-6 flex items-end gap-3">
            <div className="text-6xl font-black tabular-nums text-stone-50">{coach.readiness.score}</div>
            <div className="pb-2 text-xs uppercase tracking-[0.22em] text-stone-500">coach score</div>
          </div>
          <p className="mt-4 max-w-[34rem] text-sm leading-6 text-stone-300">{coach.readiness.reason}</p>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <div className="text-xs text-stone-500">近期死亡均值</div>
              <div className="mt-2 text-2xl font-black text-red-300">{coach.recent_deaths}</div>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <div className="text-xs text-stone-500">主打资产</div>
              <div className="mt-2 truncate text-lg font-black text-cyan-200">{signature?.hero_name || "积累样本"}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {coach.insights.map((insight) => (
          <div key={insight.title} className="card">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs font-black uppercase tracking-[0.18em] text-stone-500">{insight.title}</div>
                <div className="mt-2 text-2xl font-black text-stone-50">{insight.metric}</div>
              </div>
              <span className={`rounded-lg border px-2 py-1 text-[11px] font-black ${toneClasses(insight.tone)}`}>live</span>
            </div>
            <p className="mt-4 text-sm leading-6 text-stone-300">{insight.body}</p>
            <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.04] p-3 text-xs leading-5 text-yellow-100">
              {insight.action}
            </div>
          </div>
        ))}
      </div>

      <div className="card xl:col-span-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="section-title mb-0">三步训练计划</h2>
            <div className="mt-2 text-sm text-stone-400">基于最近 {summary.games} 场生成</div>
          </div>
          <span className="w-fit rounded-lg border border-cyan-300/25 bg-cyan-300/10 px-3 py-2 text-xs font-black text-cyan-200">Coach Preview</span>
        </div>
        <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
          {coach.training_plan.map((step, index) => (
            <div key={step.label} className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase text-stone-500">{step.label}</span>
                <span className="text-sm font-black text-yellow-300">0{index + 1}</span>
              </div>
              <div className="mt-3 text-lg font-black text-stone-100">{step.focus}</div>
              <p className="mt-3 text-sm leading-6 text-stone-300">{step.drill}</p>
              <div className="mt-4 border-t border-white/10 pt-3 text-xs text-green-200">{step.success_metric}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function SummaryGrid({ data }: { data: PlayerDashboardData }) {
  const { summary, profile } = data;
  const trend = summary.trend;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
      <MetricCard
        label={`最近 ${summary.games} 场胜率`}
        value={`${summary.win_rate}%`}
        detail={`${summary.wins}胜 / ${summary.losses}负`}
        tone={summary.win_rate >= 50 ? "green" : "red"}
      />
      <MetricCard
        label="近期 KDA"
        value={String(summary.avg_kda)}
        detail={`${summary.avg_kills}/${summary.avg_deaths}/${summary.avg_assists}`}
        tone="cyan"
      />
      <MetricCard
        label="状态评分"
        value={String(summary.avg_form_score)}
        detail={<span className={numberClass(trend.form_diff)}>{signed(trend.form_diff)} vs 前 10 场</span>}
      />
      <MetricCard
        label="当前走势"
        value={summary.streak.count ? `${summary.streak.count}${summary.streak.label}` : "-"}
        detail={`最近对局 ${summary.last_played || "-"}`}
        tone={summary.streak.label === "连胜" ? "green" : "red"}
      />
      <MetricCard
        label="生涯胜率"
        value={`${profile.lifetime_win_rate}%`}
        detail={`${profile.total_wins}胜 / ${profile.total_losses}负`}
        tone={profile.lifetime_win_rate >= 50 ? "green" : "red"}
      />
      <MetricCard
        label="平均时长"
        value={`${summary.avg_duration_min}m`}
        detail={<span className={numberClass(trend.win_rate_diff)}>{signed(trend.win_rate_diff, "%")} 胜率变化</span>}
        tone="cyan"
      />
    </div>
  );
}

function HeroStrip({ title, heroes }: { title: string; heroes: PlayerHeroStat[] }) {
  if (!heroes.length) return null;

  return (
    <div className="card">
      <h2 className="section-title">{title}</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {heroes.slice(0, 9).map((hero) => (
          <div key={hero.hero_id} className="flex items-center gap-3 rounded-lg border border-white/10 bg-black/20 p-3">
            {hero.hero_icon && <img src={hero.hero_icon} alt="" className="h-10 w-10 rounded object-cover" />}
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-bold text-stone-100">{hero.hero_name}</div>
              <div className="mt-1 flex items-center gap-2 text-xs text-stone-400">
                <span>{hero.games}场</span>
                <span className={hero.win_rate >= 50 ? "text-green-300" : "text-red-300"}>{hero.win_rate}%</span>
                {hero.avg_kda && <span className="text-cyan-300">KDA {hero.avg_kda}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Charts({ data }: { data: PlayerDashboardData }) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <div className="card">
        <h2 className="section-title">滚动胜率</h2>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data.rolling_winrate}>
            <defs>
              <linearGradient id="winrateFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="#54d18a" stopOpacity={0.36} />
                <stop offset="95%" stopColor="#54d18a" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
            <XAxis dataKey="index" stroke="#9a9589" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 100]} stroke="#9a9589" tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
            <Tooltip contentStyle={{ background: "#171813", border: "1px solid rgba(255,255,255,0.16)", borderRadius: 8 }} />
            <Area type="monotone" dataKey="winrate" stroke="#54d18a" strokeWidth={2} fill="url(#winrateFill)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2 className="section-title">段位轨迹</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.rank_history}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
            <XAxis dataKey="date" stroke="#9a9589" tick={{ fontSize: 11 }} />
            <YAxis stroke="#9a9589" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#171813", border: "1px solid rgba(255,255,255,0.16)", borderRadius: 8 }} />
            <Line type="monotone" dataKey="tier" stroke="#f0c85a" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2 className="section-title">时段表现</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.time_analysis}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="#9a9589" tick={{ fontSize: 11 }} />
            <YAxis stroke="#9a9589" tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
            <Tooltip contentStyle={{ background: "#171813", border: "1px solid rgba(255,255,255,0.16)", borderRadius: 8 }} />
            <Bar dataKey="winrate" name="胜率" fill="#63c7c9" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2 className="section-title">星期表现</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.weekday_analysis}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="#9a9589" tick={{ fontSize: 11 }} />
            <YAxis stroke="#9a9589" tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
            <Tooltip contentStyle={{ background: "#171813", border: "1px solid rgba(255,255,255,0.16)", borderRadius: 8 }} />
            <Bar dataKey="winrate" name="胜率" fill="#f0c85a" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function CountsPanel({ data }: { data: PlayerDashboardData }) {
  const roles = data.counts.lane_role || [];
  const modes = data.counts.game_mode || [];
  if (!roles.length && !modes.length) return null;

  return (
    <div className="card">
      <h2 className="section-title">长期分布</h2>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {[{ title: "常见分路", items: roles }, { title: "常见模式", items: modes }].map((section) => (
          <div key={section.title} className="space-y-3">
            <div className="text-xs font-bold uppercase text-stone-500">{section.title}</div>
            {section.items.slice(0, 5).map((item) => (
              <div key={item.label}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-stone-300">{item.label}</span>
                  <span className="text-stone-500">{item.games}场 · {item.winrate}%</span>
                </div>
                <div className="h-2 rounded bg-white/10">
                  <div className="h-2 rounded bg-yellow-300" style={{ width: `${Math.min(item.winrate, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function PersonalMetaLab({ data }: { data: PlayerDashboardData }) {
  if (!data.meta_fit.length && !data.build_signatures.length && !data.role_matrix.length) return null;

  return (
    <section className="card">
      <div className="mb-5">
        <div className="text-xs font-black uppercase text-yellow-300">Personal Meta</div>
        <h2 className="mt-2 text-2xl font-black text-stone-50">个人打法对照</h2>
        <div className="mt-2 text-xs text-stone-500">只看当前玩家：英雄池是否顺版本、OpenDota 分路样本是否稳定、最近出装是否形成套路。</div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <div className="mb-3 text-sm font-black text-stone-100">你的英雄 vs 全局 Meta</div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {data.meta_fit.slice(0, 6).map((fit) => (
              <div key={fit.hero_id} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    {fit.hero_icon && <img src={fit.hero_icon} alt="" className="h-8 w-8 rounded object-cover" />}
                    <div className="min-w-0">
                      <div className="truncate text-sm font-black text-stone-100">{fit.hero_name}</div>
                      <div className="text-xs text-stone-500">{fit.meta_role} · {compactNumber(fit.meta_matches)} global games</div>
                    </div>
                  </div>
                  <span className={`rounded border px-2 py-1 text-[11px] font-black ${fit.gap >= 0 ? "border-green-300/25 bg-green-300/10 text-green-200" : "border-red-300/25 bg-red-300/10 text-red-200"}`}>
                    {signed(fit.gap, "%")}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <div className="text-stone-500">你的 WR</div>
                    <div className="mt-1 font-black text-stone-100">{fit.personal_win_rate}%</div>
                  </div>
                  <div>
                    <div className="text-stone-500">全局 WR</div>
                    <div className="mt-1 font-black text-cyan-200">{fit.meta_win_rate}%</div>
                  </div>
                  <div>
                    <div className="text-stone-500">判断</div>
                    <div className="mt-1 font-black text-yellow-200">{fit.verdict}</div>
                  </div>
                </div>
              </div>
            ))}
            {!data.meta_fit.length && <div className="text-sm text-stone-500">暂无足够英雄样本</div>}
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <div className="mb-3 text-sm font-black text-stone-100">OpenDota 分路样本</div>
          <div className="grid grid-cols-1 gap-2">
            {data.role_matrix.map((role) => (
              <div key={role.lane_role} className="grid grid-cols-[92px_1fr_68px] items-center gap-3 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-xs">
                <div>
                  <div className="font-black text-stone-100">{role.role_name}</div>
                  <div className="text-stone-500">{role.games} 场</div>
                </div>
                <div className="min-w-0">
                  <div className="truncate text-stone-400">{role.top_hero || "样本积累"}</div>
                  <div className="mt-1 text-stone-500">{role.avg_gpm} GPM · KDA {role.avg_kda}</div>
                </div>
                <div className={`text-right font-black tabular-nums ${role.win_rate >= 50 ? "text-green-300" : "text-red-300"}`}>
                  {role.win_rate}%
                </div>
              </div>
            ))}
            {!data.role_matrix.length && <div className="text-sm text-stone-500">近期比赛没有 OpenDota 分路解析样本</div>}
          </div>
        </div>
      </div>

      {data.build_signatures.length > 0 && (
        <div className="mt-4 rounded-lg border border-white/10 bg-black/20 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-black text-stone-100">Recent Build Signatures</div>
            <div className="text-xs text-stone-500">当前玩家最近解析比赛聚合</div>
          </div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 2xl:grid-cols-4">
            {data.build_signatures.slice(0, 8).map((build) => (
              <div key={`${build.hero_id}-${build.lane_role}`} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    {build.hero_icon && <img src={build.hero_icon} alt="" className="h-9 w-9 rounded object-cover" />}
                    <div className="min-w-0">
                      <div className="truncate text-sm font-black text-stone-100">{build.hero_name}</div>
                      <div className="text-xs text-stone-500">{build.role_name} · {build.games}场</div>
                    </div>
                  </div>
                  <div className={`text-right text-sm font-black tabular-nums ${build.win_rate >= 50 ? "text-green-300" : "text-red-300"}`}>
                    {build.win_rate}%
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-1">
                  {build.items.map((item) => (
                    <span key={item.item_id} className="relative">
                      <img src={item.icon} alt="" className="h-7 w-7 rounded border border-white/10 bg-black/30 object-cover" />
                      {item.count > 1 && (
                        <span className="absolute -right-1 -top-1 rounded bg-yellow-300 px-1 text-[10px] font-black text-stone-950">{item.count}</span>
                      )}
                    </span>
                  ))}
                </div>
                <div className="mt-3 text-xs text-cyan-200">KDA {build.avg_kda}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function ProLeadForm({
  data,
  commercialConfig,
}: {
  data: PlayerDashboardData;
  commercialConfig: CommercialConfig | null;
}) {
  const [plan, setPlan] = useState("founder");
  const [contact, setContact] = useState("");
  const [role, setRole] = useState("");
  const [goal, setGoal] = useState("");
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const selectedOffer = COMMERCIAL_OFFERS.find((offer) => offer.key === plan) || COMMERCIAL_OFFERS[0];
  const configured = checkoutConfigured(commercialConfig, plan);

  const submitLead = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!contact.trim()) return;
    setSubmitting(true);
    setStatus("");
    try {
      const result = await createCommercialLead({
        account_id: data.profile.account_id,
        plan,
        contact,
        role,
        goal,
        source: "progress_upgrade",
      });
      if (result.checkout_url) {
        window.location.assign(result.checkout_url);
        return;
      }
      setStatus("已记录开通申请。支付链接未启用时，会按你留下的联系方式人工开通。");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "提交失败，请稍后再试。");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submitLead} className="pro-lead-form">
      <div>
        <div className="text-xs font-black uppercase text-cyan-300">DotaSense Pro</div>
        <h3 className="mt-2 text-2xl font-black text-stone-50">保存完整训练历史</h3>
        <p className="mt-2 text-sm leading-6 text-stone-400">
          Pro 会保存每次三局挑战、完整 AI 复盘和长期趋势。留下联系方式即可申请创始会员。
        </p>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {COMMERCIAL_OFFERS.map((offer) => (
          <label
            key={offer.key}
            className={`cursor-pointer rounded-lg border p-3 transition ${plan === offer.key ? "border-yellow-300/50 bg-yellow-300/10" : "border-white/10 bg-black/20 hover:border-cyan-300/30"}`}
          >
            <input
              type="radio"
              name="plan"
              value={offer.key}
              checked={plan === offer.key}
              onChange={(event) => setPlan(event.target.value)}
              className="sr-only"
            />
            <div className="flex items-center justify-between gap-3">
              <span className="font-black text-stone-100">{offer.title}</span>
              <span className="text-sm font-black text-yellow-200">{offer.price}</span>
            </div>
            <div className="mt-2 text-xs leading-5 text-stone-400">{offer.promise}</div>
          </label>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3">
        <input
          value={contact}
          onChange={(event) => setContact(event.target.value)}
          required
          className="rounded-lg border border-white/10 bg-black/30 px-3 py-3 text-sm text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-yellow-300/50"
          placeholder="微信 / 邮箱"
        />
        <input
          value={role}
          onChange={(event) => setRole(event.target.value)}
          className="rounded-lg border border-white/10 bg-black/30 px-3 py-3 text-sm text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-cyan-300/50"
          placeholder="你的分段、位置或队伍身份"
        />
        <textarea
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          className="min-h-[96px] rounded-lg border border-white/10 bg-black/30 px-3 py-3 text-sm text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-cyan-300/50"
          placeholder="这周最想解决的问题，例如死亡太多、英雄池混乱、上分停滞"
        />
      </div>

      <button
        type="submit"
        disabled={submitting || !contact.trim()}
        className="rounded-lg bg-yellow-300 px-4 py-3 text-sm font-black text-stone-950 transition hover:bg-yellow-200 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? "提交中..." : configured ? `提交并购买 ${selectedOffer.price}` : `申请开通 ${selectedOffer.price}`}
      </button>
      {status && <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-3 py-2 text-xs leading-5 text-yellow-100">{status}</div>}
    </form>
  );
}

function ReviewReport({
  review,
  source,
  locked,
}: {
  review: PlayerReview;
  source: string;
  locked: boolean;
}) {
  const sourceLabel = source === "deepseek" ? "DeepSeek + evidence guard" : locked ? "免费预览" : "规则复盘";

  return (
    <div className="ai-review-report">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded border px-2 py-1 text-[11px] font-black ${locked ? "border-yellow-300/25 bg-yellow-300/10 text-yellow-200" : "border-green-300/25 bg-green-300/10 text-green-200"}`}>
              {locked ? "预览" : "PRO 已解锁"}
            </span>
            <span className="rounded border border-cyan-300/20 bg-cyan-300/10 px-2 py-1 text-[11px] font-black text-cyan-200">
              {sourceLabel}
            </span>
          </div>
          <h3 className="mt-3 text-2xl font-black text-stone-50">{review.headline}</h3>
          <p className="mt-3 max-w-4xl text-sm leading-6 text-stone-300">{review.summary}</p>
        </div>
        <div className="review-score">
          <div className="text-xs font-black uppercase text-stone-500">训练评分</div>
          <div className="mt-2 text-5xl font-black tabular-nums text-yellow-200">{review.score || "-"}</div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-2">
        {review.sections.map((section) => (
          <div key={section.title} className="review-section">
            <div className="text-xs font-black uppercase text-yellow-300">{section.title}</div>
            <div className="mt-3 text-sm font-black leading-6 text-stone-100">{section.finding}</div>
            <div className="mt-3 rounded-lg border border-white/10 bg-black/20 p-3 text-xs leading-5 text-stone-400">{section.evidence}</div>
            <div className="mt-3 text-sm leading-6 text-cyan-100">{section.action}</div>
          </div>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="review-plan">
          <div className="mb-3 text-sm font-black text-stone-100">7 天训练计划</div>
          <div className="grid grid-cols-1 gap-2">
            {review.weekly_plan.map((step) => (
              <div key={`${step.day}-${step.focus}`} className="grid grid-cols-1 gap-2 rounded-lg border border-white/10 bg-white/[0.035] p-3 md:grid-cols-[88px_1fr_180px]">
                <div className="text-xs font-black text-yellow-300">{step.day}</div>
                <div className="min-w-0">
                  <div className="font-black text-stone-100">{step.focus}</div>
                  <div className="mt-1 text-xs leading-5 text-stone-400">{step.task}</div>
                </div>
                <div className="text-xs leading-5 text-green-200">{step.metric}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="review-plan">
          <div className="mb-3 text-sm font-black text-stone-100">优先复盘比赛</div>
          <div className="space-y-2">
            {review.priority_matches.map((match) => (
              <a
                key={match.match_id}
                href={`https://www.opendota.com/matches/${match.match_id}`}
                target="_blank"
                rel="noreferrer"
                className="block rounded-lg border border-white/10 bg-white/[0.035] p-3 transition hover:border-yellow-300/40"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-black text-stone-100">{match.hero || "Match"}</span>
                  <span className="text-xs tabular-nums text-stone-500">{match.match_id}</span>
                </div>
                <div className="mt-2 text-xs leading-5 text-stone-400">{match.reason}</div>
              </a>
            ))}
            {!review.priority_matches.length && <div className="text-sm text-stone-500">暂无明显输局样本。</div>}
          </div>
        </div>
      </div>

      {review.model_note && <div className="mt-4 text-xs leading-5 text-stone-500">{review.model_note}</div>}
    </div>
  );
}

function AiReviewPanel({
  data,
  commercialConfig,
}: {
  data: PlayerDashboardData;
  commercialConfig: CommercialConfig | null;
}) {
  const accountId = data.profile.account_id;
  const storageKey = useMemo(() => `${PRO_ACCESS_STORAGE_PREFIX}:${accountId}`, [accountId]);
  const [preview, setPreview] = useState<PlayerReviewResponse | null>(null);
  const [fullReview, setFullReview] = useState<PlayerReviewResponse | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const [accessStatus, setAccessStatus] = useState("");
  const [reviewError, setReviewError] = useState("");
  const [previewLoading, setPreviewLoading] = useState(true);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [unlockLoading, setUnlockLoading] = useState(false);

  const accessReady = Boolean(commercialConfig?.access_code_configured);
  const activeReview = fullReview || preview;

  useEffect(() => {
    let active = true;
    setPreview(null);
    setPreviewLoading(true);
    setReviewError("");
    void getPlayerReviewPreview(accountId, 30)
      .then((result) => {
        if (active) setPreview(result);
      })
      .catch((err) => {
        if (active) setReviewError(err instanceof Error ? err.message : "复盘预览加载失败");
      })
      .finally(() => {
        if (active) setPreviewLoading(false);
      });
    return () => {
      active = false;
    };
  }, [accountId]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let active = true;
    const stored = window.localStorage.getItem(storageKey) || "";
    setFullReview(null);
    setAccessToken("");
    setAccessStatus("");
    setAccessCode("");
    if (!stored) return;

    void verifyCommercialAccess(stored, accountId)
      .then((result) => {
        if (!active) return;
        if (result.ok) {
          setAccessToken(stored);
          setAccessStatus("已识别本账号 Pro 权益，可以生成完整复盘。");
        } else {
          window.localStorage.removeItem(storageKey);
        }
      })
      .catch(() => {
        if (active) window.localStorage.removeItem(storageKey);
      });

    return () => {
      active = false;
    };
  }, [accountId, storageKey]);

  const generateReview = useCallback(
    async (tokenOverride?: string) => {
      const token = tokenOverride || accessToken;
      if (!token) {
        setAccessStatus("请输入购买后获得的访问码解锁完整复盘。");
        return;
      }
      setReviewLoading(true);
      setReviewError("");
      try {
        const result = await getPlayerReview(accountId, token, 50);
        setFullReview(result);
        setAccessStatus(result.source === "deepseek" ? "完整 AI 复盘已生成。" : "完整复盘已生成；AI 模型不可用时使用本地规则兜底。");
      } catch (err) {
        setReviewError(err instanceof Error ? err.message : "完整复盘生成失败");
        if (err instanceof Error && err.message.includes("Pro access")) {
          window.localStorage.removeItem(storageKey);
          setAccessToken("");
        }
      } finally {
        setReviewLoading(false);
      }
    },
    [accessToken, accountId, storageKey],
  );

  const submitAccessCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!accessReady) {
      setAccessStatus("自动开通码还未启用。请先提交购买意向，人工开通后再输入访问码。");
      return;
    }
    if (!accessCode.trim()) return;

    setUnlockLoading(true);
    setReviewError("");
    setAccessStatus("");
    try {
      const result = await unlockCommercialAccess({
        code: accessCode,
        account_id: accountId,
        plan: "founder",
      });
      setAccessToken(result.access_token);
      window.localStorage.setItem(storageKey, result.access_token);
      setAccessStatus("Pro 已解锁，正在生成完整 AI 复盘。");
      await generateReview(result.access_token);
    } catch (err) {
      setAccessStatus(err instanceof Error ? err.message : "访问码验证失败");
    } finally {
      setUnlockLoading(false);
    }
  };

  return (
    <section className="ai-review-panel">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="text-xs font-black uppercase text-cyan-300">DEEP REVIEW</div>
          <h2 className="mt-2 text-3xl font-black text-stone-50">深度训练报告</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-400">
            每条结论都受证据边界约束；没有 Replay 事件时，只使用结算数据、英雄百分位和可验证的训练动作。
          </p>
        </div>
        <div className="review-unlock">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-xs font-black uppercase text-stone-500">Access</div>
              <div className={`mt-1 text-sm font-black ${accessToken ? "text-green-200" : "text-yellow-200"}`}>
                {accessToken ? "Pro 已解锁" : accessReady ? "输入访问码解锁" : "等待人工开通"}
              </div>
            </div>
            <button
              type="button"
              onClick={() => void generateReview()}
              disabled={!accessToken || reviewLoading}
              className="rounded-lg border border-green-300/30 bg-green-300/10 px-3 py-2 text-xs font-black text-green-200 transition hover:bg-green-300 hover:text-stone-950 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {reviewLoading ? "生成中..." : "生成完整复盘"}
            </button>
          </div>

          <form onSubmit={submitAccessCode} className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
            <input
              value={accessCode}
              onChange={(event) => setAccessCode(event.target.value)}
              disabled={!accessReady || unlockLoading}
              className="rounded-lg border border-white/10 bg-black/30 px-3 py-3 text-sm text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-yellow-300/50 disabled:opacity-50"
              placeholder={accessReady ? "输入购买后获得的访问码" : "自动访问码暂未启用"}
            />
            <button
              type="submit"
              disabled={!accessReady || unlockLoading || !accessCode.trim()}
              className="rounded-lg bg-yellow-300 px-4 py-3 text-sm font-black text-stone-950 transition hover:bg-yellow-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {unlockLoading ? "验证中..." : "解锁"}
            </button>
          </form>
          {accessStatus && <div className="mt-3 rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-3 py-2 text-xs leading-5 text-yellow-100">{accessStatus}</div>}
          {reviewError && <div className="mt-3 rounded-lg border border-red-300/20 bg-red-400/10 px-3 py-2 text-xs leading-5 text-red-100">{reviewError}</div>}
        </div>
      </div>

      <div className="mt-5">
        {previewLoading && <div className="rounded-lg border border-white/10 bg-black/20 px-4 py-5 text-sm text-stone-400">正在生成复盘预览...</div>}
        {activeReview?.review && (
          <ReviewReport review={activeReview.review} source={activeReview.source} locked={activeReview.locked && !fullReview} />
        )}
      </div>
    </section>
  );
}

function ProPanel({ data, commercialConfig }: { data: PlayerDashboardData; commercialConfig: CommercialConfig | null }) {
  const benefits = [
    { title: "训练记忆", detail: "保存每次目标、三局结果与成功标准，形成个人长期样本。" },
    { title: "证据化复盘", detail: "区分结算数据、英雄基准和 Replay 事件，不用推断冒充事实。" },
    { title: "英雄池计划", detail: "按继续上分、专项训练和暂时停用管理英雄池。" },
    { title: "每周总结", detail: "把本周最稳定优势和最大短板整理成下一周计划。" },
  ];

  return (
    <section className="space-y-4">
      <div className="pro-panel">
        <div className="max-w-2xl">
          <div className="text-xs font-black uppercase text-yellow-300">DotaSense Pro</div>
          <h2 className="mt-3 text-3xl font-black text-stone-50">把每组三局变成长期进步</h2>
          <p className="mt-3 text-sm leading-6 text-stone-300">免费版帮助你找到一次问题；Pro 保存挑战、复盘与长期趋势，让下一次训练建立在上一次结果之上。</p>
          <div className="mt-5 flex flex-wrap gap-2 text-xs">
            <span className="evidence-chip evidence-verified">90 天训练历史</span>
            <span className="evidence-chip evidence-verified">无限深度复盘</span>
            <span className="evidence-chip evidence-parsed">自适应三局挑战</span>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {benefits.map((feature) => (
            <div key={feature.title} className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="flex items-center justify-between gap-2"><div className="font-black text-stone-100">{feature.title}</div><Crown size={15} className="text-yellow-300" /></div>
              <p className="mt-3 text-sm leading-6 text-stone-400">{feature.detail}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="commercial-pricing">
          {COMMERCIAL_OFFERS.map((offer) => (
            <div key={offer.key} className="commercial-plan">
              <div className="flex items-start justify-between gap-4">
                <div><div className="text-xs font-black uppercase text-stone-500">{offer.buyer}</div><h3 className="mt-2 text-2xl font-black text-stone-50">{offer.title}</h3></div>
                <div className="text-right"><div className="text-2xl font-black text-yellow-200">{offer.price}</div><div className={`mt-2 rounded border px-2 py-1 text-[11px] font-black ${checkoutConfigured(commercialConfig, offer.key) ? "border-green-300/25 bg-green-300/10 text-green-200" : "border-stone-500/25 bg-white/[0.035] text-stone-400"}`}>{checkoutConfigured(commercialConfig, offer.key) ? "可直接付款" : "申请开通"}</div></div>
              </div>
              <p className="mt-4 text-sm leading-6 text-stone-400">{offer.promise}</p>
            </div>
          ))}
        </div>
        <ProLeadForm data={data} commercialConfig={commercialConfig} />
      </div>
    </section>
  );
}
function MatchHistoryList({
  matches,
  limit = 8,
  compact = false,
  onOpenAll,
}: {
  matches: PlayerMatch[];
  limit?: number;
  compact?: boolean;
  onOpenAll?: () => void;
}) {
  if (!matches.length) return null;

  return (
    <div className="card">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="section-title mb-0">个人比赛历史</h2>
          <div className="mt-2 text-xs text-stone-500">最近 {Math.min(matches.length, limit)} 场，按时间倒序。</div>
        </div>
        {onOpenAll && (
          <button
            type="button"
            onClick={onOpenAll}
            className="w-fit rounded-lg border border-yellow-300/30 bg-yellow-300/10 px-3 py-2 text-xs font-black text-yellow-200 transition hover:bg-yellow-300 hover:text-stone-950"
          >
            查看全部比赛
          </button>
        )}
      </div>
      <div className="space-y-2">
        {matches.slice(0, limit).map((match) => {
          const itemIcons = (match.item_icons ?? []).filter(Boolean).slice(0, compact ? 4 : 6);
          const opendotaUrl = match.opendota_url || `https://www.opendota.com/matches/${match.match_id}`;

          return (
            <div
              key={match.match_id}
              className="grid grid-cols-1 gap-3 rounded-lg border border-white/10 bg-black/20 p-3 transition hover:border-cyan-300/30 hover:bg-white/[0.035] lg:grid-cols-[minmax(220px,1.2fr)_120px_160px_minmax(160px,0.8fr)_90px]"
            >
              <div className="flex min-w-0 items-center gap-3">
                {match.hero_icon && <img src={match.hero_icon} alt="" className="h-10 w-10 rounded object-cover" />}
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-black text-stone-100">{match.hero_name}</span>
                    <span className={`rounded px-2 py-0.5 text-[11px] font-black ${match.win ? "bg-green-400/15 text-green-300" : "bg-red-400/15 text-red-300"}`}>
                      {match.win ? "胜" : "负"}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-stone-500">{match.game_mode} · {match.role_name}</div>
                </div>
              </div>
              <div className="tabular-nums">
                <div className="text-sm font-black text-stone-100">{match.kills}/{match.deaths}/{match.assists}</div>
                <div className="text-xs text-cyan-300">KDA {match.kda}</div>
              </div>
              <div className="tabular-nums">
                <div className="text-sm font-black text-yellow-300">{match.gold_per_min || "-"} GPM</div>
                <div className="text-xs text-stone-500">{match.duration_text} · Lv {match.level || "-"}</div>
              </div>
              <div className="flex flex-wrap items-center gap-1">
                {itemIcons.map((url, index) => (
                  <img
                    key={`${match.match_id}-history-${index}`}
                    src={url}
                    alt=""
                    className="h-7 w-7 rounded border border-white/10 bg-black/30 object-cover"
                  />
                ))}
                {match.item_neutral_icon && (
                  <img
                    src={match.item_neutral_icon}
                    alt=""
                    className="h-7 w-7 rounded border border-yellow-300/40 bg-yellow-300/10 object-cover"
                  />
                )}
                {!itemIcons.length && !match.item_neutral_icon && <span className="text-xs text-stone-500">未解析出装</span>}
              </div>
              <div className="flex items-center justify-between gap-3 lg:block lg:text-right">
                <div className="text-xs text-stone-500">{match.played_at}</div>
                <a
                  href={opendotaUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-0 inline-block rounded border border-white/10 bg-white/[0.04] px-2 py-1 text-xs font-bold text-stone-300 transition hover:border-yellow-300/50 hover:text-yellow-200 lg:mt-2"
                >
                  OpenDota
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MatchTable({ matches }: { matches: PlayerMatch[] }) {
  if (!matches.length) return null;

  const compact = (value: number) => {
    if (!value) return "-";
    if (value >= 1000) return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k`;
    return String(value);
  };

  const detailCount = matches.slice(0, 20).filter((match) => match.detail_available).length;

  return (
    <div className="card">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="section-title mb-0">最近比赛详情</h2>
          <div className="mt-2 text-xs text-stone-500">
            已尽量补全出装、经济、补刀和伤害；未解析比赛会显示摘要字段。
          </div>
        </div>
        <span className="w-fit rounded-lg border border-cyan-300/25 bg-cyan-300/10 px-3 py-2 text-xs font-black text-cyan-200">
          {detailCount}/{Math.min(matches.length, 20)} 场详情
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1180px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase text-stone-500">
              <th className="py-3 pr-4">英雄</th>
              <th className="py-3 pr-4">结果</th>
              <th className="py-3 pr-4">KDA</th>
              <th className="py-3 pr-4">经济</th>
              <th className="py-3 pr-4">补刀</th>
              <th className="py-3 pr-4">伤害</th>
              <th className="py-3 pr-4">出装</th>
              <th className="py-3 pr-4">模式 / OpenDota 分路</th>
              <th className="py-3 pr-4">时间</th>
              <th className="py-3 pr-4">详情</th>
            </tr>
          </thead>
          <tbody>
            {matches.slice(0, 20).map((match) => {
              const itemIcons = (match.item_icons ?? []).filter(Boolean);
              const opendotaUrl = match.opendota_url || `https://www.opendota.com/matches/${match.match_id}`;

              return (
                <tr key={match.match_id} className="border-b border-white/5 transition hover:bg-white/[0.035]">
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      {match.hero_icon && <img src={match.hero_icon} alt="" className="h-8 w-8 rounded object-cover" />}
                      <span>
                        <span className="block font-bold text-stone-100">{match.hero_name}</span>
                        <span className="text-xs text-stone-500">Lv {match.level || "-"}</span>
                      </span>
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    <span className={`rounded px-2 py-1 text-xs font-black ${match.win ? "bg-green-400/15 text-green-300" : "bg-red-400/15 text-red-300"}`}>
                      {match.win ? "胜" : "负"}
                    </span>
                  </td>
                  <td className="py-3 pr-4 tabular-nums">
                    <div className="font-black text-stone-100">{match.kills}/{match.deaths}/{match.assists}</div>
                    <div className="text-xs text-cyan-300">KDA {match.kda}</div>
                    <div className="text-xs text-yellow-300">评分 {match.form_score}</div>
                  </td>
                  <td className="py-3 pr-4 tabular-nums">
                    <div className="font-black text-yellow-300">{match.gold_per_min || "-"} GPM</div>
                    <div className="text-xs text-cyan-300">{match.xp_per_min || "-"} XPM</div>
                    <div className="text-xs text-stone-500">NW {compact(match.net_worth)}</div>
                  </td>
                  <td className="py-3 pr-4 tabular-nums">
                    <div className="font-black text-stone-200">{match.last_hits || "-"} LH</div>
                    <div className="text-xs text-stone-500">{match.denies || 0} deny</div>
                  </td>
                  <td className="py-3 pr-4 tabular-nums">
                    <div className="font-black text-red-300">{compact(match.hero_damage)}</div>
                    <div className="text-xs text-yellow-300">塔 {compact(match.tower_damage)}</div>
                    {match.hero_healing > 0 && <div className="text-xs text-green-300">治疗 {compact(match.hero_healing)}</div>}
                  </td>
                  <td className="py-3 pr-4">
                    <div className="flex min-w-[190px] flex-wrap gap-1">
                      {itemIcons.map((url, index) => (
                        <img
                          key={`${match.match_id}-${index}`}
                          src={url}
                          alt=""
                          className="h-7 w-7 rounded border border-white/10 bg-black/30 object-cover"
                        />
                      ))}
                      {match.item_neutral_icon && (
                        <img
                          src={match.item_neutral_icon}
                          alt=""
                          className="h-7 w-7 rounded border border-yellow-300/40 bg-yellow-300/10 object-cover"
                        />
                      )}
                      {!itemIcons.length && !match.item_neutral_icon && (
                        <span className="rounded border border-white/10 bg-white/[0.04] px-2 py-1 text-xs text-stone-500">
                          未解析
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    <div className="font-bold text-stone-300">{match.game_mode}</div>
                    <div className="text-xs text-stone-500">{match.role_name} · {match.lobby_type}</div>
                  </td>
                  <td className="py-3 pr-4 tabular-nums">
                    <div className="font-bold text-stone-300">{match.duration_text}</div>
                    <div className="text-xs text-stone-500">{match.played_at}</div>
                  </td>
                  <td className="py-3 pr-4">
                    <a
                      href={opendotaUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded border border-white/10 bg-white/[0.04] px-2 py-1 text-xs font-bold text-stone-300 transition hover:border-yellow-300/50 hover:text-yellow-200"
                    >
                      OpenDota
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Home() {
  const [accountId, setAccountId] = useState(initialAccountId);
  const [query, setQuery] = useState(accountId);
  const [limit, setLimit] = useState(50);
  const [meta, setMeta] = useState<GlobalMetaOverview | null>(null);
  const [data, setData] = useState<PlayerDashboardData | null>(null);
  const [commercialConfig, setCommercialConfig] = useState<CommercialConfig | null>(null);
  const [searchResults, setSearchResults] = useState<PlayerSearchResult[]>([]);
  const [metaLoading, setMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState("");
  const [loading, setLoading] = useState(false);
  const [deepLoading, setDeepLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<AppTab>("today");
  const loadRequestRef = useRef(0);

  const loadPlayer = useCallback(async (targetAccountId: string, targetLimit: number) => {
    const requestId = ++loadRequestRef.current;
    setLoading(true);
    setDeepLoading(true);
    setError("");
    setData(null);
    let quickLoaded = false;
    try {
      const quick = await getPlayerQuickDashboard(targetAccountId, targetLimit);
      if (requestId !== loadRequestRef.current) return;
      setData(quick);
      quickLoaded = true;
      window.localStorage.setItem(STORAGE_KEY, targetAccountId);
    } catch (err) {
      if (requestId === loadRequestRef.current) setError(err instanceof Error ? err.message : "快速数据加载失败");
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false);
    }

    try {
      const deep = await getPlayerDashboard(targetAccountId, targetLimit);
      if (requestId !== loadRequestRef.current) return;
      setData(deep);
      setError("");
      window.localStorage.setItem(STORAGE_KEY, targetAccountId);
    } catch (err) {
      if (requestId === loadRequestRef.current) {
        setError(quickLoaded ? "已显示快速数据，深度比赛证据暂时未能补全。" : err instanceof Error ? err.message : "加载失败");
      }
    } finally {
      if (requestId === loadRequestRef.current) setDeepLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPlayer(accountId, limit);
  }, [accountId, limit, loadPlayer]);

  useEffect(() => {
    let active = true;
    async function loadMeta() {
      setMetaLoading(true);
      setMetaError("");
      try {
        const result = await getMetaOverview();
        if (active) setMeta(result);
      } catch (err) {
        if (active) setMetaError(err instanceof Error ? err.message : "全局大盘加载失败");
      } finally {
        if (active) setMetaLoading(false);
      }
    }
    void loadMeta();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    async function loadCommercialConfig() {
      try {
        const result = await getCommercialConfig();
        if (active) setCommercialConfig(result);
      } catch {
        if (active) setCommercialConfig(null);
      }
    }
    void loadCommercialConfig();
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmed = query.trim();
      if (!trimmed) return;
      setActiveTab("today");

      if (/^\d+$/.test(trimmed)) {
        setSearchResults([]);
        setAccountId(trimmed);
        return;
      }

      setLoading(true);
      setError("");
      try {
        const result = await searchPlayers(trimmed);
        setSearchResults(result.results);
        if (!result.results.length) {
          setError(result.warnings[0] || "没有找到匹配玩家，也可以直接输入 account_id 查看");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "搜索失败");
      } finally {
        setLoading(false);
      }
    },
    [query],
  );

  const pickPlayer = useCallback((nextAccountId: number) => {
    const id = String(nextAccountId);
    setQuery(id);
    setSearchResults([]);
    setAccountId(id);
    setActiveTab("today");
  }, []);

  const copyProfileLink = useCallback(() => {
    if (!data || typeof window === "undefined") return;
    const url = `${window.location.origin}/p/${data.profile.account_id}`;
    if (!navigator.clipboard) return;
    void navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    });
  }, [data]);

  const hasCharts = useMemo(() => Boolean(data?.rolling_winrate.length || data?.rank_history.length), [data]);

  return (
    <main className="mx-auto max-w-[1480px] px-4 py-4 sm:px-6 lg:px-8">
      <div className="space-y-4">
        <ProductNav data={data} copied={copied} onCopyProfile={copyProfileLink} onOpenPro={() => setActiveTab("progress")} />
        <WorkspaceTabs activeTab={activeTab} onChange={setActiveTab} data={data} />
        <CommandSearch
          query={query}
          setQuery={setQuery}
          limit={limit}
          setLimit={setLimit}
          loading={loading}
          onSubmit={handleSubmit}
        />
        {error && <div className="rounded-lg border border-red-300/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">{error}</div>}
        <SearchResults results={searchResults} onPick={pickPlayer} />
        {!data && loading && <div className="cockpit-loading"><LoaderCircle size={20} className="animate-spin" /><div><div className="font-black text-stone-200">正在读取最近比赛</div><div className="mt-1 text-xs text-stone-500">先显示今日任务，深度证据随后补全。</div></div></div>}

        {activeTab === "meta" && <GlobalMetaDashboard meta={meta} loading={metaLoading} error={metaError} />}

        {activeTab === "today" && (
          <section id="personal-dashboard" className="space-y-4">
            <ProfileHeader
              data={data}
              query={query}
              setQuery={setQuery}
              limit={limit}
              setLimit={setLimit}
              loading={loading}
              onSubmit={handleSubmit}
              showSearch={false}
            />

            {data && (
              <>
                {data.warnings.length > 0 && (
                  <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-4 py-3 text-xs text-yellow-100">
                    OpenDota 部分数据暂时不可用，当前只显示已验证的数据。
                  </div>
                )}
                <ThreeMatchMission data={data} />
                <EvidenceCoverage data={data} deepLoading={deepLoading} />
                <MatchHistoryList matches={data.recent_matches} limit={3} compact onOpenAll={() => setActiveTab("lab")} />
                <div className="pb-4 text-right text-xs text-stone-600">Updated {data.updated_at}</div>
              </>
            )}
          </section>
        )}

        {activeTab === "lab" && (
          <section className="space-y-4">
            {data && (
              <>
                <MatchLab data={data} />
                <AiReviewPanel data={data} commercialConfig={commercialConfig} />
                <MatchTable matches={data.recent_matches} />
                <div className="pb-4 text-right text-xs text-stone-600">Updated {data.updated_at}</div>
              </>
            )}
          </section>
        )}

        {activeTab === "pool" && data && (
          <section className="space-y-4">
            <div className="page-intro"><div className="text-xs font-black text-yellow-300">HERO POOL</div><h1>英雄池训练室</h1><p>把英雄分成继续上分、专项训练和暂时观察；全局数据只做参照，不冒充分位置 Meta。</p></div>
            <PersonalMetaLab data={data} />
            <WardMap accountId={data.profile.account_id} />
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_420px]"><HeroStrip title="近期英雄池" heroes={data.hero_pool} /><CountsPanel data={data} /></div>
            <HeroStrip title="生涯常用英雄" heroes={data.lifetime_heroes} />
          </section>
        )}

        {activeTab === "progress" && (
          <section className="space-y-4">
            {data && <>
              <div className="page-intro"><div className="text-xs font-black text-green-300">PROGRESS</div><h1>训练进度</h1><p>用同一个目标完成三局，再比较趋势；长期历史和自动周报由 Pro 保存。</p></div>
              <ThreeMatchMission data={data} expanded />
              <SummaryGrid data={data} />
              <CoachBrief data={data} />
              {hasCharts && <Charts data={data} />}
              <ProPanel data={data} commercialConfig={commercialConfig} />
            </>}
          </section>
        )}
      </div>
    </main>
  );
}
