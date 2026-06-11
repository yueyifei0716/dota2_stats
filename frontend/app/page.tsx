"use client";

import type { FormEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
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
import { getPlayerDashboard, searchPlayers } from "@/lib/api";
import type { PlayerDashboardData, PlayerHeroStat, PlayerMatch, PlayerSearchResult } from "@/lib/types";

const DEFAULT_ACCOUNT_ID = "894447460";
const STORAGE_KEY = "dota2-dashboard-account-id";

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

function toneClasses(tone: "gold" | "green" | "red" | "cyan") {
  return {
    gold: "border-yellow-300/25 bg-yellow-300/10 text-yellow-200",
    green: "border-green-300/25 bg-green-300/10 text-green-200",
    red: "border-red-300/25 bg-red-300/10 text-red-200",
    cyan: "border-cyan-300/25 bg-cyan-300/10 text-cyan-200",
  }[tone];
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
        <div className="text-xs font-black uppercase tracking-[0.28em] text-yellow-300">DotaSense</div>
        <div className="mt-1 text-sm text-stone-400">Personal ranked intelligence</div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-stone-400">Free Scout</span>
        <button
          type="button"
          onClick={onCopyProfile}
          disabled={!data}
          className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-xs font-bold text-stone-100 transition hover:border-cyan-300/50 disabled:opacity-50"
        >
          {copied ? "已复制公开页" : "分享公开页"}
        </button>
        <button type="button" className="rounded-lg border border-yellow-300/40 bg-yellow-300 px-3 py-2 text-xs font-black text-stone-950">
          Pro
        </button>
      </div>
    </header>
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
}: {
  data: PlayerDashboardData | null;
  query: string;
  setQuery: (value: string) => void;
  limit: number;
  setLimit: (value: number) => void;
  loading: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
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
      </div>
    </div>
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

function ProPanel({ data }: { data: PlayerDashboardData }) {
  return (
    <section className="pro-panel">
      <div className="max-w-2xl">
        <div className="text-xs font-black uppercase tracking-[0.24em] text-yellow-300">DotaSense Pro</div>
        <h2 className="mt-3 text-3xl font-black text-stone-50">把数据变成下一局的决策优势</h2>
        <p className="mt-3 text-sm leading-6 text-stone-300">
          免费版负责看清现状，Pro 负责把你的历史样本、版本环境和高分打法合并成可执行的训练系统。
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <button type="button" className="rounded-lg bg-yellow-300 px-4 py-2 text-sm font-black text-stone-950">加入候补名单</button>
          <button type="button" className="rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-sm font-bold text-stone-100">查看样例报告</button>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {data.coach.pro_preview.map((feature) => (
          <div key={feature.title} className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="font-black text-stone-100">{feature.title}</div>
              <span className="rounded border border-yellow-300/25 bg-yellow-300/10 px-2 py-1 text-[11px] font-black text-yellow-200">PRO</span>
            </div>
            <p className="mt-3 text-sm leading-6 text-stone-400">{feature.detail}</p>
          </div>
        ))}
      </div>
    </section>
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
              <th className="py-3 pr-4">模式 / 分路定位</th>
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
  const [data, setData] = useState<PlayerDashboardData | null>(null);
  const [searchResults, setSearchResults] = useState<PlayerSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

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

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmed = query.trim();
      if (!trimmed) return;

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
        <ProfileHeader
          data={data}
          query={query}
          setQuery={setQuery}
          limit={limit}
          setLimit={setLimit}
          loading={loading}
          onSubmit={handleSubmit}
        />

        {error && <div className="rounded-lg border border-red-300/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">{error}</div>}
        <SearchResults results={searchResults} onPick={pickPlayer} />

        {data && (
          <>
            {data.warnings.length > 0 && (
              <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-4 py-3 text-xs text-yellow-100">
                OpenDota 部分接口暂时不可用，当前显示已成功获取的数据。稍后刷新会自动补齐。
              </div>
            )}
            <CoachBrief data={data} />
            <SummaryGrid data={data} />
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_420px]">
              <HeroStrip title="近期英雄池" heroes={data.hero_pool} />
              <CountsPanel data={data} />
            </div>
            <HeroStrip title="生涯常用英雄" heroes={data.lifetime_heroes} />
            <ProPanel data={data} />
            {hasCharts && <Charts data={data} />}
            <MatchTable matches={data.recent_matches} />
            <div className="pb-4 text-right text-xs text-stone-600">Updated {data.updated_at}</div>
          </>
        )}
      </div>
    </main>
  );
}
