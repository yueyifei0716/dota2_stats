"use client";

import type { FormEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
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
  getMetaOverview,
  getPlayerDashboard,
  searchPlayers,
} from "@/lib/api";
import type {
  GlobalMetaOverview,
  PlayerDashboardData,
  PlayerHeroStat,
  PlayerMatch,
  PlayerMetaHero,
  PlayerSearchResult,
} from "@/lib/types";
import WardMap from "@/components/WardMap";

const DEFAULT_ACCOUNT_ID = "894447460";
const STORAGE_KEY = "dota2-dashboard-account-id";

type AppTab = "meta" | "player" | "matches";

const APP_TABS: { key: AppTab; label: string; detail: string }[] = [
  { key: "player", label: "Home", detail: "我的面板" },
  { key: "meta", label: "Meta", detail: "全局大盘" },
  { key: "matches", label: "Matches", detail: "比赛与趋势" },
];

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

function DataImage({
  src,
  alt = "",
  className,
  size = 40,
}: {
  src: string;
  alt?: string;
  className?: string;
  size?: number;
}) {
  return <Image src={src} alt={alt} width={size} height={size} className={className} unoptimized />;
}

function ProductNav({
  data,
  copied,
  onCopyProfile,
}: {
  data: PlayerDashboardData | null;
  copied: boolean;
  onCopyProfile: () => void;
}) {
  return (
    <header className="product-nav">
      <div>
        <div className="text-xs font-black uppercase text-yellow-300">DotaSense</div>
        <div className="mt-1 text-sm text-stone-400">Global meta intelligence + personal performance dashboard</div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onCopyProfile}
          disabled={!data}
          className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-xs font-bold text-stone-100 transition hover:border-cyan-300/50 disabled:opacity-50"
        >
          {copied ? "已复制公开页" : "分享公开页"}
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
        const active = activeTab === tab.key;
        const disabled = !data && tab.key === "matches";
        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            disabled={disabled}
            className={`workspace-tab ${active ? "workspace-tab-active" : ""}`}
            aria-current={active ? "page" : undefined}
          >
            <span className="text-sm font-black">{tab.label}</span>
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
            <DataImage src={profile.avatar} className="h-16 w-16 rounded-lg border border-white/10 object-cover" size={64} />
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
        <span className="text-xl text-stone-500">⌕</span>
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
      <button className="command-submit" disabled={loading}>
        {loading ? "Loading" : "Enter"}
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
            {player.avatar ? <DataImage src={player.avatar} className="h-10 w-10 rounded object-cover" size={40} /> : <div className="h-10 w-10 rounded bg-white/10" />}
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
          {hero.hero_icon && <DataImage src={hero.hero_icon} className="h-8 w-8 rounded object-cover" size={32} />}
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
                      <th className="py-3 pr-4">职业样本</th>
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
                <div className="mb-3 text-sm font-black text-stone-100">职业样本信号</div>
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
            {hero.hero_icon && <DataImage src={hero.hero_icon} className="h-10 w-10 rounded object-cover" size={40} />}
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
                    {fit.hero_icon && <DataImage src={fit.hero_icon} className="h-8 w-8 rounded object-cover" size={32} />}
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
                    {build.hero_icon && <DataImage src={build.hero_icon} className="h-9 w-9 rounded object-cover" size={36} />}
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
                      <DataImage src={item.icon} className="h-7 w-7 rounded border border-white/10 bg-black/30 object-cover" size={28} />
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
                {match.hero_icon && <DataImage src={match.hero_icon} className="h-10 w-10 rounded object-cover" size={40} />}
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
                  <DataImage
                    key={`${match.match_id}-history-${index}`}
                    src={url}
                    className="h-7 w-7 rounded border border-white/10 bg-black/30 object-cover"
                    size={28}
                  />
                ))}
                {match.item_neutral_icon && (
                  <DataImage
                    src={match.item_neutral_icon}
                    className="h-7 w-7 rounded border border-yellow-300/40 bg-yellow-300/10 object-cover"
                    size={28}
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
                      {match.hero_icon && <DataImage src={match.hero_icon} className="h-8 w-8 rounded object-cover" size={32} />}
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
                        <DataImage
                          key={`${match.match_id}-${index}`}
                          src={url}
                          className="h-7 w-7 rounded border border-white/10 bg-black/30 object-cover"
                          size={28}
                        />
                      ))}
                      {match.item_neutral_icon && (
                        <DataImage
                          src={match.item_neutral_icon}
                          className="h-7 w-7 rounded border border-yellow-300/40 bg-yellow-300/10 object-cover"
                          size={28}
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
  const [searchResults, setSearchResults] = useState<PlayerSearchResult[]>([]);
  const [metaLoading, setMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<AppTab>("player");

  const loadPlayer = useCallback(async (targetAccountId: string, targetLimit: number) => {
    setLoading(true);
    setError("");
    try {
      const result = await getPlayerDashboard(targetAccountId, targetLimit);
      setData(result);
      window.localStorage.setItem(STORAGE_KEY, targetAccountId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
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

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmed = query.trim();
      if (!trimmed) return;
      setActiveTab("player");

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
    setActiveTab("player");
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
        <ProductNav data={data} copied={copied} onCopyProfile={copyProfileLink} />
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

        {activeTab === "meta" && <GlobalMetaDashboard meta={meta} loading={metaLoading} error={metaError} />}

        {activeTab === "player" && (
          <section id="personal-dashboard" className="space-y-4">
            <div className="card">
              <div className="text-xs font-black uppercase text-yellow-300">Personal Dashboard</div>
              <h1 className="mt-2 text-3xl font-black text-stone-50">个人战绩面板</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-400">
                输入自己的 account_id 或玩家名，查看近期状态、英雄池、OpenDota 分路、出装和打法对照。
              </p>
            </div>
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
                    OpenDota 部分接口暂时不可用，当前显示已成功获取的数据。稍后刷新会自动补齐。
                  </div>
                )}
                <CoachBrief data={data} />
                <SummaryGrid data={data} />
                <MatchHistoryList matches={data.recent_matches} limit={5} compact onOpenAll={() => setActiveTab("matches")} />
                <WardMap accountId={data.profile.account_id} />
                <PersonalMetaLab data={data} />
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_420px]">
                  <HeroStrip title="近期英雄池" heroes={data.hero_pool} />
                  <CountsPanel data={data} />
                </div>
                <HeroStrip title="生涯常用英雄" heroes={data.lifetime_heroes} />
                <div className="pb-4 text-right text-xs text-stone-600">Updated {data.updated_at}</div>
              </>
            )}
          </section>
        )}

        {activeTab === "matches" && (
          <section className="space-y-4">
            <div className="card">
              <div className="text-xs font-black uppercase text-cyan-300">Match Center</div>
              <h1 className="mt-2 text-3xl font-black text-stone-50">比赛详情与趋势</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-400">
                当前玩家的滚动胜率、段位轨迹、时间窗口和最近比赛明细集中在这里。
              </p>
            </div>
            {!data && <div className="card text-sm text-stone-400">玩家数据加载中，或请先在 Player tab 选择账号。</div>}
            {data && (
              <>
                {data.warnings.length > 0 && (
                  <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-4 py-3 text-xs text-yellow-100">
                    OpenDota 部分比赛详情暂时不可用，当前显示已成功获取的数据。
                  </div>
                )}
                <MatchHistoryList matches={data.recent_matches} limit={12} />
                <MatchTable matches={data.recent_matches} />
                {hasCharts && <Charts data={data} />}
                <div className="pb-4 text-right text-xs text-stone-600">Updated {data.updated_at}</div>
              </>
            )}
          </section>
        )}

      </div>
    </main>
  );
}
