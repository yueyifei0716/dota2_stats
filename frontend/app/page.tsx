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
  ExternalLink,
  LayoutDashboard,
  ListFilter,
  LoaderCircle,
  RotateCcw,
  Search,
  Share2,
  ShieldCheck,
  SlidersHorizontal,
  Swords,
  Target,
  TrendingUp,
  X,
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
  cancelTrainingMission,
  confirmMatchPosition,
  getCommercialConfig,
  getMetaOverview,
  getPlayerDashboard,
  getPlayerMatchScorecard,
  getPlayerQuickDashboard,
  getPlayerReview,
  getPlayerReviewPreview,
  searchPlayers,
  startTrainingMission,
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
type LabView = "scorecard" | "report" | "vision" | "history";

const APP_TABS: { key: AppTab; label: string; detail: string; icon: LucideIcon }[] = [
  { key: "today", label: "我的", detail: "个人总览", icon: LayoutDashboard },
  { key: "lab", label: "复盘", detail: "比赛与复盘", icon: Swords },
  { key: "pool", label: "英雄池", detail: "英雄与训练", icon: BookOpen },
  { key: "meta", label: "Meta", detail: "全局环境", icon: Activity },
  { key: "progress", label: "进步", detail: "训练进度", icon: TrendingUp },
];

const LAB_VIEWS: { key: LabView; label: string; icon: LucideIcon }[] = [
  { key: "scorecard", label: "单局", icon: Target },
  { key: "report", label: "AI 报告", icon: Activity },
  { key: "vision", label: "视野", icon: ShieldCheck },
  { key: "history", label: "比赛列表", icon: ListFilter },
];

const POSITION_OPTIONS = [
  { value: 1, label: "1号位", detail: "核心" },
  { value: 2, label: "2号位", detail: "中单" },
  { value: 3, label: "3号位", detail: "劣势路" },
  { value: 4, label: "4号位", detail: "游走" },
  { value: 5, label: "5号位", detail: "硬辅" },
] as const;

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

function stratzAwardLabel(award: string) {
  return {
    MVP: "MVP",
    TOP_CORE: "最佳核心",
    TOP_SUPPORT: "最佳辅助",
  }[award] || "";
}

// OpenDota 的 /search 长期超时，所以除了名字搜索之外，要能直接吃下用户手里
// 已有的标识：Steam64 ID、Steam 个人主页链接，以及 Dotabuff / OpenDota /
// STRATZ 的选手页链接。全部是本地换算，不依赖任何上游接口。
// Steam64 超过 Number.MAX_SAFE_INTEGER，必须用 BigInt，否则减法会丢精度。
const STEAM64_BASE = BigInt("76561197960265728");
const PLAYER_URL_PATTERN = /(?:steamcommunity\.com\/profiles\/|(?:dotabuff\.com|opendota\.com|stratz\.com)\/players\/)(\d+)/i;

function resolveAccountId(input: string): string | null {
  const text = input.trim();
  if (!text) return null;

  const fromUrl = text.match(PLAYER_URL_PATTERN);
  const digits = fromUrl ? fromUrl[1] : (/^\d+$/.test(text) ? text : null);
  if (!digits) return null;

  try {
    const value = BigInt(digits);
    const accountId = value >= STEAM64_BASE ? value - STEAM64_BASE : value;
    return accountId > BigInt(0) ? accountId.toString() : null;
  } catch {
    return null;
  }
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

type CopyState = "idle" | "done" | "failed";

const COPY_LABELS: Record<CopyState, string> = {
  idle: "复制公开页链接",
  done: "公开页链接已复制",
  failed: "复制失败，请手动复制地址栏链接",
};

function ProductNav({
  data,
  copyState,
  onCopyProfile,
  onOpenPro,
}: {
  data: PlayerDashboardData | null;
  copyState: CopyState;
  onCopyProfile: () => void;
  onOpenPro: () => void;
}) {
  return (
    <div className="product-nav">
      <div className="product-brand">
        <div className="product-mark">DS</div>
        <div className="min-w-0">
          <div className="product-name">DotaSense</div>
          <div className="product-tagline">Player intelligence</div>
        </div>
      </div>
      <div className="product-actions">
        <button
          type="button"
          onClick={onCopyProfile}
          disabled={!data}
          className="icon-command"
          data-copy={copyState}
          aria-label={COPY_LABELS[copyState]}
          title={COPY_LABELS[copyState]}
        >
          <span className="icon-swap">
            <Share2 size={15} className="icon-swap-idle" aria-hidden="true" />
            <Check size={15} className="icon-swap-done" aria-hidden="true" />
            <X size={15} className="icon-swap-failed" aria-hidden="true" />
          </span>
        </button>
        <button
          type="button"
          onClick={onOpenPro}
          className="pro-command"
        >
          <Crown size={15} aria-hidden="true" />
          升级 Pro
        </button>
      </div>
    </div>
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
            title={tab.detail}
          >
            <span><Icon size={16} aria-hidden="true" />{tab.label}</span>
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

function ProfileHeader({ data, deepLoading }: { data: PlayerDashboardData | null; deepLoading: boolean }) {
  const profile = data?.profile;
  const summary = data?.summary;
  const topHero = data?.hero_pool[0];
  const trend = summary?.trend.win_rate_diff || 0;
  const gpmSamples = data?.recent_matches.filter((match) => match.gold_per_min > 0) || [];
  const averageGpm = gpmSamples.length
    ? Math.round(gpmSamples.reduce((sum, match) => sum + match.gold_per_min, 0) / gpmSamples.length)
    : null;
  return (
    <section className="player-command-bar" aria-label="玩家近期决策摘要">
      <div className="player-identity-compact">
        <div className="flex min-w-0 items-center gap-3">
          {profile?.avatar ? (
            <img src={profile.avatar} alt="" className="player-avatar-compact" />
          ) : (
            <div className="player-avatar-compact bg-white/10" />
          )}
          <div className="min-w-0">
            <div className="profile-overline">
              <ShieldCheck size={12} aria-hidden="true" />
              Player overview
            </div>
            <h1 className="player-title">{profile?.username || "Dota 2 Dashboard"}</h1>
            <div className="player-meta">
              {profile ? `${profile.total_games} 场生涯 · ${profile.lifetime_win_rate}% · ID ${profile.account_id}` : `ID ${DEFAULT_ACCOUNT_ID}`}
            </div>
          </div>
        </div>
      </div>

      <div className="player-kpi-strip" aria-label="近期关键指标">
        <div><span>近期胜率</span><strong className="text-green-300">{summary ? `${summary.win_rate}%` : "-"}</strong><small>{summary?.games || 0} 场样本</small></div>
        <div><span>胜率趋势</span><strong className={numberClass(trend)}>{summary ? signed(trend, "pp") : "-"}</strong><small>较前一窗口</small></div>
        <div><span>平均 KDA</span><strong>{summary?.avg_kda ?? "-"}</strong><small>{summary ? `${summary.avg_kills}/${summary.avg_deaths}/${summary.avg_assists}` : "-"}</small></div>
        <div><span>平均 GPM</span><strong>{averageGpm ?? "-"}</strong><small>{gpmSamples.length ? `${gpmSamples.length} 场详情` : "等待详情"}</small></div>
        <div className="player-top-hero">
          <span>近期主力</span>
          <strong>{topHero?.hero_name || "-"}</strong>
          <small>{topHero ? `${topHero.games} 场 · ${topHero.win_rate}%` : "等待比赛"}</small>
        </div>
      </div>

      <div className="player-rank-compact">
        {profile?.rank_icon ? <img src={profile.rank_icon} alt="" /> : <div className="player-rank-placeholder" />}
        <div>
          <span>当前段位</span>
          <strong>{profile?.rank_name || "未校准"}</strong>
          <small className="flex items-center gap-1">
            {deepLoading ? <LoaderCircle size={11} className="animate-spin" aria-hidden="true" /> : <Check size={11} aria-hidden="true" />}
            {deepLoading ? "补全详情" : `${data?.recent_matches.length || 0} 场已载入`}
          </small>
        </div>
      </div>
    </section>
  );
}

function DashboardRail({ data }: { data: PlayerDashboardData }) {
  const formScore = Math.max(0, Math.min(100, Math.round(data.summary.avg_form_score || 0)));
  const positionGames = data.role_matrix.reduce((sum, row) => sum + row.games, 0);
  const positionRows = POSITION_OPTIONS.map((position) => {
    const row = data.role_matrix.find((item) => item.position === position.value);
    return {
      ...position,
      games: row?.games || 0,
      share: positionGames && row ? Math.round(row.games / positionGames * 100) : 0,
    };
  });

  return (
    <aside className="dashboard-rail" aria-label="近期数据摘要">
      <section className="rail-section">
        <div className="rail-heading">
          <h2>近期状态</h2>
          <span>近 {data.summary.games} 场</span>
        </div>
        <div className="form-summary">
          <div
            className="form-score-ring"
            style={{ background: `conic-gradient(var(--positive) 0 ${formScore}%, var(--surface-muted) ${formScore}% 100%)` }}
          >
            <div><strong>{formScore || "-"}</strong><span>状态分</span></div>
          </div>
          <div className="form-facts">
            <div><span>近期胜率</span><strong className="text-green-300">{data.summary.win_rate}%</strong></div>
            <div><span>平均 KDA</span><strong>{data.summary.avg_kda}</strong></div>
            <div><span>平均死亡</span><strong className="text-red-300">{data.summary.avg_deaths}</strong></div>
          </div>
        </div>
      </section>

      <section className="rail-section">
        <div className="rail-heading">
          <h2>近期英雄池</h2>
          <span>胜率</span>
        </div>
        {data.hero_pool.length ? (
          <div className="rail-hero-pool">
            {data.hero_pool.slice(0, 4).map((hero) => (
              <div key={hero.hero_id} className="rail-hero">
                {hero.hero_icon ? <img src={hero.hero_icon} alt="" /> : <div className="rail-hero-placeholder" />}
                <strong title={hero.hero_name}>{hero.hero_name}</strong>
                <span>{hero.win_rate}% · {hero.games}场</span>
              </div>
            ))}
          </div>
        ) : <div className="rail-empty">暂无公开英雄样本</div>}
      </section>

      <section className="rail-section">
        <div className="rail-heading">
          <h2>五位置分布</h2>
          <span>{positionGames ? `${positionGames} 场已确认` : "无已确认位置"}</span>
        </div>
        {positionGames ? (
          <div className="position-distribution">
            {positionRows.map((row) => (
              <div key={row.value} className="position-row">
                <span>{row.label}</span>
                <div><i style={{ width: `${row.share}%` }} /></div>
                <strong>{row.share}%</strong>
              </div>
            ))}
          </div>
        ) : <div className="rail-empty">仅在 STRATZ 或用户确认位置后显示</div>}
      </section>
    </aside>
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
          placeholder="玩家名、account id、Steam 链接或 Steam64 ID"
          className="min-w-0 flex-1 bg-transparent text-sm font-bold text-stone-100 outline-none placeholder:text-stone-500"
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
            className="search-result-card flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-3 text-left transition hover:border-yellow-300/50 hover:bg-yellow-300/10"
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

type MatchExplorerFilters = {
  hero: string;
  position: string;
  result: string;
  side: string;
  mode: string;
  lobby: string;
  party: string;
  range: string;
};

const DEFAULT_MATCH_FILTERS: MatchExplorerFilters = {
  hero: "all",
  position: "all",
  result: "all",
  side: "all",
  mode: "all",
  lobby: "all",
  party: "all",
  range: "all",
};

function ExplorerSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="explorer-filter">
      <span>{label}</span>
      <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

function PlayerDataExplorer({ data, equipmentLoading, onOpenMatches }: { data: PlayerDashboardData; equipmentLoading: boolean; onOpenMatches: () => void }) {
  const [filters, setFilters] = useState<MatchExplorerFilters>(DEFAULT_MATCH_FILTERS);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  const heroOptions = useMemo(() => {
    const heroes = new Map<number, string>();
    data.recent_matches.forEach((match) => heroes.set(match.hero_id, match.hero_name));
    return Array.from(heroes, ([value, label]) => ({ value: String(value), label }))
      .sort((a, b) => a.label.localeCompare(b.label, "zh-CN"));
  }, [data.recent_matches]);

  const modeOptions = useMemo(
    () => Array.from(new Set(data.recent_matches.map((match) => match.game_mode))).sort().map((label) => ({ value: label, label })),
    [data.recent_matches],
  );
  const lobbyOptions = useMemo(
    () => Array.from(new Set(data.recent_matches.map((match) => match.lobby_type))).sort().map((label) => ({ value: label, label })),
    [data.recent_matches],
  );

  const filteredMatches = useMemo(() => {
    const latestMatchTime = Math.max(...data.recent_matches.map((match) => match.start_time), 0) * 1000;
    const dayMs = 24 * 60 * 60 * 1000;
    return data.recent_matches.filter((match) => {
      if (filters.hero !== "all" && String(match.hero_id) !== filters.hero) return false;
      if (filters.position !== "all" && match.position_key !== filters.position) return false;
      if (filters.result === "win" && !match.win) return false;
      if (filters.result === "loss" && match.win) return false;
      if (filters.side !== "all" && match.side !== filters.side) return false;
      if (filters.mode !== "all" && match.game_mode !== filters.mode) return false;
      if (filters.lobby !== "all" && match.lobby_type !== filters.lobby) return false;
      if (filters.party === "solo" && match.party_size !== 1) return false;
      if (filters.party === "party" && match.party_size <= 1) return false;
      if (filters.range !== "all" && match.start_time * 1000 < latestMatchTime - Number(filters.range) * dayMs) return false;
      return true;
    });
  }, [data.recent_matches, filters]);

  const detailMatches = filteredMatches.filter((match) => match.detail_available);
  const wins = filteredMatches.filter((match) => match.win).length;
  const activeFilterCount = Object.values(filters).filter((value) => value !== "all").length;
  const advancedFilterCount = [filters.side, filters.mode, filters.lobby, filters.party].filter((value) => value !== "all").length;

  function pair(matches: PlayerMatch[], getter: (match: PlayerMatch) => number, digits = 0) {
    if (!matches.length) return { average: "-", maximum: "-" };
    const values = matches.map(getter);
    const average = values.reduce((sum, value) => sum + value, 0) / values.length;
    return { average: average.toFixed(digits), maximum: Math.max(...values).toFixed(digits) };
  }

  const deaths = pair(filteredMatches, (match) => match.deaths, 1);
  const kda = pair(filteredMatches, (match) => match.kda, 2);
  const gpm = pair(detailMatches, (match) => match.gold_per_min);
  const impMatches = filteredMatches.filter((match) => match.stratz_imp !== null);
  const imp = pair(impMatches, (match) => match.stratz_imp || 0, 1);
  const heroDamage = pair(detailMatches, (match) => match.hero_damage);
  const metrics = [
    { label: "筛选胜率", average: filteredMatches.length ? `${Math.round(wins / filteredMatches.length * 100)}%` : "-", detail: `${wins}胜 ${filteredMatches.length - wins}负`, tone: "green" },
    { label: "平均 KDA", average: kda.average, detail: kda.maximum === "-" ? "-" : `峰值 ${kda.maximum}`, tone: "gold" },
    { label: "平均死亡", average: deaths.average, detail: deaths.maximum === "-" ? "-" : `峰值 ${deaths.maximum}`, tone: "red" },
    { label: "平均 GPM", average: gpm.average, detail: gpm.maximum === "-" ? `${detailMatches.length} 场详情` : `峰值 ${gpm.maximum}`, tone: "gold" },
    { label: "平均 IMP", average: imp.average, detail: `${impMatches.length} 场 STRATZ 评分`, tone: "cyan" },
    { label: "平均伤害", average: heroDamage.average === "-" ? "-" : compactNumber(Number(heroDamage.average)), detail: heroDamage.maximum === "-" ? `${detailMatches.length} 场详情` : `峰值 ${compactNumber(Number(heroDamage.maximum))}`, tone: "red" },
  ];

  const updateFilter = (key: keyof MatchExplorerFilters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  return (
    <>
      <section className="data-explorer" aria-label="个人比赛筛选与统计">
        <div className="data-explorer-header">
          <div className="flex min-w-0 items-center gap-2">
            <ListFilter size={15} className="shrink-0 text-cyan-300" aria-hidden="true" />
            <h2>个人比赛历史</h2>
            <span className="explorer-depth-note">{data.data_stage === "quick" ? "深度数据加载中" : `${data.position_coverage.covered_matches} 场已确认位置`}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="explorer-result-count">{filteredMatches.length}/{data.recent_matches.length} 场</span>
            <button type="button" className="explorer-reset" onClick={() => setFilters(DEFAULT_MATCH_FILTERS)} disabled={!activeFilterCount} aria-label="重置筛选" title="重置筛选">
              <RotateCcw size={15} aria-hidden="true" />
              <span>重置</span>
            </button>
          </div>
        </div>

        <div className="explorer-filter-toolbar">
          <div className="explorer-filters explorer-filters-primary">
            <ExplorerSelect label="英雄" value={filters.hero} onChange={(value) => updateFilter("hero", value)} options={[{ value: "all", label: "全部英雄" }, ...heroOptions]} />
            <ExplorerSelect label="位置" value={filters.position} onChange={(value) => updateFilter("position", value)} options={[{ value: "all", label: "全部位置" }, { value: "pos1", label: "1号位 核心" }, { value: "pos2", label: "2号位 中单" }, { value: "pos3", label: "3号位 劣势路" }, { value: "pos4", label: "4号位 游走" }, { value: "pos5", label: "5号位 硬辅" }]} />
            <ExplorerSelect label="结果" value={filters.result} onChange={(value) => updateFilter("result", value)} options={[{ value: "all", label: "全部结果" }, { value: "win", label: "胜利" }, { value: "loss", label: "失败" }]} />
            <ExplorerSelect label="日期" value={filters.range} onChange={(value) => updateFilter("range", value)} options={[{ value: "all", label: "全部日期" }, { value: "7", label: "最近 7 天" }, { value: "30", label: "最近 30 天" }, { value: "90", label: "最近 90 天" }]} />
          </div>
          <button type="button" className={`explorer-more ${showAdvancedFilters || advancedFilterCount ? "explorer-more-active" : ""}`} onClick={() => setShowAdvancedFilters((current) => !current)} aria-expanded={showAdvancedFilters}>
            <SlidersHorizontal size={15} aria-hidden="true" />
            <span>更多</span>
            {advancedFilterCount > 0 && <b>{advancedFilterCount}</b>}
          </button>
        </div>
        {showAdvancedFilters && (
          <div className="explorer-filters explorer-filters-advanced">
            <ExplorerSelect label="阵营" value={filters.side} onChange={(value) => updateFilter("side", value)} options={[{ value: "all", label: "全部阵营" }, { value: "Radiant", label: "Radiant" }, { value: "Dire", label: "Dire" }]} />
            <ExplorerSelect label="模式" value={filters.mode} onChange={(value) => updateFilter("mode", value)} options={[{ value: "all", label: "全部模式" }, ...modeOptions]} />
            <ExplorerSelect label="匹配类型" value={filters.lobby} onChange={(value) => updateFilter("lobby", value)} options={[{ value: "all", label: "全部匹配" }, ...lobbyOptions]} />
            <ExplorerSelect label="组队" value={filters.party} onChange={(value) => updateFilter("party", value)} options={[{ value: "all", label: "全部队列" }, { value: "solo", label: "单排" }, { value: "party", label: "组排" }]} />
          </div>
        )}

        <div className="explorer-metrics">
          {metrics.map((metric) => (
            <div key={metric.label} className={`explorer-metric explorer-metric-${metric.tone}`}>
              <span>{metric.label}</span>
              <strong>{metric.average}</strong>
              <small>{metric.detail}</small>
            </div>
          ))}
        </div>
      </section>

      {filteredMatches.length ? (
        <MatchHistoryList matches={filteredMatches} limit={8} equipmentLoading={equipmentLoading} onOpenAll={onOpenMatches} />
      ) : (
        <div className="card explorer-empty">
          <div><strong>没有符合条件的比赛</strong><span>当前已加载 {data.recent_matches.length} 场公开比赛。</span></div>
          <button type="button" onClick={() => setFilters(DEFAULT_MATCH_FILTERS)}>清除筛选</button>
        </div>
      )}
    </>
  );
}

function GlobalHeroRow({ hero, rank }: { hero: PlayerMetaHero; rank: number }) {
  return (
    <tr className="meta-table-row">
      <td>
        <div className="flex items-center gap-2">
          <span className="meta-rank">{rank}</span>
          {hero.hero_icon && <img src={hero.hero_icon} alt="" className="h-8 w-8 rounded object-cover" />}
          <span>
            <span className="block font-black text-stone-100">{hero.hero_name}</span>
            <span className="text-[10px] text-stone-500">{hero.role_label}</span>
          </span>
        </div>
      </td>
      <td className={`font-black tabular-nums ${hero.win_rate >= 52 ? "text-green-300" : "text-stone-300"}`}>
        {hero.win_rate}%
      </td>
      <td className="font-black tabular-nums text-yellow-300">{hero.meta_score}%</td>
      <td className="tabular-nums text-stone-300">{compactNumber(hero.matches)}</td>
      <td className="tabular-nums text-cyan-200">{hero.contest_rate}%</td>
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
  const [roleKey, setRoleKey] = useState("pos1");
  const [heroQuery, setHeroQuery] = useState("");
  const [sortKey, setSortKey] = useState<"score" | "winrate" | "samples">("score");
  const roles = meta?.hero_meta.roles.length ? meta.hero_meta.roles : [
    { key: "pos1", label: "1号位 核心" },
    { key: "pos2", label: "2号位 中单" },
    { key: "pos3", label: "3号位 劣势路" },
    { key: "pos4", label: "4号位 游走" },
    { key: "pos5", label: "5号位 硬辅" },
  ];
  const activeRoleKey = roles.some((role) => role.key === roleKey) ? roleKey : roles[0].key;
  const activeHeroes = meta?.hero_meta.by_scope[activeRoleKey] || [];
  const positionSamples = activeHeroes.reduce((sum, hero) => sum + hero.matches, 0);
  const minimumSample = Math.max(100, Math.ceil(positionSamples * 0.001));
  const qualifiedHeroes = activeHeroes.filter((hero) => hero.matches >= minimumSample);
  const searchTerm = heroQuery.trim().toLowerCase();
  const filteredHeroes = (searchTerm ? activeHeroes : qualifiedHeroes)
    .filter((hero) => hero.hero_name.toLowerCase().includes(searchTerm))
    .sort((left, right) => {
      if (sortKey === "winrate") return right.win_rate - left.win_rate || right.matches - left.matches;
      if (sortKey === "samples") return right.matches - left.matches || right.meta_score - left.meta_score;
      return right.meta_score - left.meta_score || right.matches - left.matches;
  });
  const activeRole = roles.find((role) => role.key === activeRoleKey);
  const volumeLeader = [...activeHeroes].sort((left, right) => right.matches - left.matches)[0];
  const scoreLeader = [...qualifiedHeroes].sort((left, right) => right.meta_score - left.meta_score)[0];
  const hasMetaData = Boolean(meta?.available && activeHeroes.length);
  const freshnessState = meta?.freshness?.state || "unknown";
  const freshnessLabel = {
    fresh: "数据新鲜",
    stale: "数据偏旧",
    expired: "数据已过期",
    unknown: "日期未核验",
  }[freshnessState];

  return (
    <section id="global-meta" className="meta-workspace">
      <div className="meta-toolbar">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase text-cyan-300">Ranked roles meta</div>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1>五位置英雄 Meta</h1>
            <span>{meta?.source || "STRATZ GraphQL heroStats"}</span>
            {meta && <span className={`meta-freshness meta-freshness-${freshnessState}`}>{freshnessLabel}</span>}
          </div>
        </div>
        <div className="meta-role-tabs" aria-label="位置选择">
          {roles.map((role) => (
            <button
              key={role.key}
              type="button"
              onClick={() => setRoleKey(role.key)}
              className={activeRoleKey === role.key ? "active" : ""}
            >
              {role.label}
            </button>
          ))}
        </div>
      </div>

      {error && !meta && <div className="meta-state text-red-200">{error}</div>}
      {loading && !meta && <div className="meta-state text-stone-400">正在加载五位置英雄样本...</div>}

      {meta && !meta.available && (
        <div className="meta-state meta-data-boundary">
          <strong>五位置数据暂时不可用</strong>
          <span>已停止展示基于分路、经济或补刀数据推断的位置排名。</span>
        </div>
      )}

      {meta?.available && !activeHeroes.length && (
        <div className="meta-state meta-data-boundary">
          <strong>{activeRole?.label || "当前位置"}暂无有效样本</strong>
          <span>该位置不会使用其他分路数据补齐。</span>
        </div>
      )}

      {meta && hasMetaData && (
        <>
          {(freshnessState === "stale" || freshnessState === "expired") && (
            <div className="meta-warning">当前快照距今天 {meta.freshness?.age_days ?? "-"} 天，只保留历史参考价值，不作为本周上分推荐。</div>
          )}
          <div className="meta-snapshot-strip">
            <div><span>当前位置</span><strong>{activeRole?.label || "-"}</strong></div>
            <div><span>达标英雄</span><strong>{qualifiedHeroes.length}</strong><small>共 {activeHeroes.length}</small></div>
            <div><span>位置样本</span><strong>{compactNumber(positionSamples)}</strong></div>
            <div><span>最大样本</span><strong>{volumeLeader?.hero_name || "-"}</strong><small>{volumeLeader ? compactNumber(volumeLeader.matches) : "-"}</small></div>
            <div><span>校准胜率首位</span><strong>{scoreLeader?.hero_name || "-"}</strong><small>{scoreLeader ? `${scoreLeader.meta_score}%` : "-"}</small></div>
          </div>

          <div className="meta-table-toolbar">
            <div className="meta-sort-control" aria-label="排序方式">
              {([
                ["score", "校准胜率"],
                ["winrate", "原始胜率"],
                ["samples", "样本量"],
              ] as const).map(([key, label]) => (
                <button key={key} type="button" onClick={() => setSortKey(key)} className={sortKey === key ? "active" : ""}>{label}</button>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <span className="hidden text-xs text-stone-500 sm:inline">{filteredHeroes.length} 个英雄 · ≥{compactNumber(minimumSample)} 场</span>
              <div className="meta-hero-search">
                <Search size={14} aria-hidden="true" />
                <input
                  value={heroQuery}
                  onChange={(event) => setHeroQuery(event.target.value)}
                  placeholder="搜索英雄"
                />
              </div>
            </div>
          </div>

          <div className="meta-table-scroll">
            <table className="meta-table">
              <thead>
                <tr>
                  <th>英雄</th>
                  <th>胜率</th>
                  <th>校准胜率</th>
                  <th>样本</th>
                  <th>位置选取率</th>
                </tr>
              </thead>
              <tbody>
                {filteredHeroes.slice(0, 24).map((hero, index) => (
                  <GlobalHeroRow key={`${hero.role_key}-${hero.hero_id}`} hero={hero} rank={index + 1} />
                ))}
              </tbody>
            </table>
          </div>

          {meta.warnings.length > 0 && (
            <div className="meta-warning">STRATZ 当前返回部分警告，榜单仅展示已验证的位置样本。</div>
          )}
          <div className="meta-footnote">STRATZ · Divine/Immortal · {meta.period_start} 至 {meta.period_end} · {meta.data_freshness === "weekly_snapshot" ? "已验证周快照" : "实时"} · {freshnessLabel}。1–5 号位来自 Ranked Roles，不使用 lane_role、GPM 或补刀数推断；默认至少 {compactNumber(minimumSample)} 个位置样本，搜索仍可查看长尾英雄。</div>
        </>
      )}
    </section>
  );
}

function missionValue(value: number | null | undefined, focusKey: string) {
  if (value === null || value === undefined) return "-";
  if (focusKey === "gold_per_min") return Math.round(value).toLocaleString("zh-CN");
  return value.toFixed(focusKey === "kda" ? 2 : 1);
}

function ThreeMatchMission({
  data,
  expanded = false,
  busy = false,
  onStart,
  onCancel,
}: {
  data: PlayerDashboardData;
  expanded?: boolean;
  busy?: boolean;
  onStart: (focusKey: string) => Promise<void>;
  onCancel: (missionId: string) => Promise<void>;
}) {
  const currentRecommendation = data.training.recommendation;
  const activeMission = data.training.active_mission;
  const completedMission = data.training.history.find((mission) => mission.status === "completed" && mission.result);
  const visibleMission = activeMission || completedMission;
  const recommendation = visibleMission?.recommendation || currentRecommendation;
  const progress = activeMission?.progress || completedMission?.result || undefined;
  const challengeMatches = progress?.matches || [];
  const complete = Boolean(completedMission && !activeMission);
  const achieved = complete ? progress?.achieved : null;
  const missionAvailable = currentRecommendation.available;
  const recommendedHero = recommendation.recommended_hero;
  const unit = recommendation.unit ? ` ${recommendation.unit}` : "";
  const baseline = recommendation.baseline_value === null
    ? "-"
    : `${missionValue(recommendation.baseline_value, recommendation.focus_key)}${unit}`;
  const target = recommendation.target_value === null
    ? "-"
    : `${recommendation.direction === "lower" ? "≤" : "≥"}${missionValue(recommendation.target_value, recommendation.focus_key)}${unit}`;

  const start = () => missionAvailable ? onStart(currentRecommendation.focus_key) : Promise.resolve();
  const cancel = () => activeMission ? onCancel(activeMission.id) : Promise.resolve();

  // 达标只庆祝「这一次真的从未达标变成达标」。首次渲染仅记录基线，
  // 否则每次组件挂载（切 Tab 回来、重新拉数据）都会重放一遍。
  // 用 WAAPI 直接驱动，避免在 effect 里 setState 触发级联渲染。
  const celebrateRef = useRef<HTMLElement | null>(null);
  const achievedBefore = useRef<boolean | null>(null);

  useEffect(() => {
    const nowAchieved = Boolean(complete && achieved);
    const previous = achievedBefore.current;
    achievedBefore.current = nowAchieved;
    if (previous === null || previous || !nowAchieved) return;

    const node = celebrateRef.current;
    if (!node || typeof node.animate !== "function") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const pop = node.animate(
      [
        { transform: "scale(1)" },
        { transform: "scale(1.06)", offset: 0.38 },
        { transform: "scale(1)" },
      ],
      { duration: 420, easing: "cubic-bezier(0.34, 1.4, 0.64, 1)" },
    );
    return () => pop.cancel();
  }, [complete, achieved]);

  if (!expanded) {
    return (
      <section className="mission-compact" aria-label="三局训练挑战">
        <div className="mission-compact-icon"><Target size={18} aria-hidden="true" /></div>
        <div className="mission-compact-copy">
          <span>{activeMission ? "三局训练中" : complete ? "上一轮结果" : "下一组三局"}</span>
          <strong>{recommendation.title}</strong>
          <small>{activeMission || complete ? `${recommendation.metric_label} ${baseline} → ${target}` : recommendation.reason}</small>
        </div>
        {recommendedHero.hero_id > 0 && (
          <div className="mission-compact-hero">
            {recommendedHero.hero_icon && <img src={recommendedHero.hero_icon} alt="" />}
            <span>{recommendedHero.hero_name}</span>
          </div>
        )}
        <div ref={celebrateRef as React.RefObject<HTMLDivElement>} className={`mission-compact-progress ${complete && achieved ? "complete" : ""}`}>
          <span>{complete ? (achieved ? "达标" : "待改进") : "进度"}</span>
          <strong>{activeMission ? `${progress?.completed_games || 0}/3` : complete ? missionValue(progress?.current_value, recommendation.focus_key) : "0/3"}</strong>
        </div>
        <button
          type="button"
          onClick={() => void (activeMission ? cancel() : start())}
          disabled={busy || (!activeMission && !missionAvailable)}
          className={activeMission ? "mission-secondary" : "mission-primary"}
        >
          {busy ? <LoaderCircle size={15} className="animate-spin" aria-hidden="true" /> : activeMission ? <RotateCcw size={15} aria-hidden="true" /> : <Target size={15} aria-hidden="true" />}
          {activeMission ? "结束" : !missionAvailable ? "暂无数据" : complete ? "新一轮" : "开始"}
        </button>
      </section>
    );
  }

  return (
    <section className="mission-console" aria-label="三局训练挑战">
      <div className="mission-brief">
        <div className="flex flex-wrap items-center gap-2">
          <span className="evidence-chip evidence-verified"><ShieldCheck size={14} aria-hidden="true" />最近 {recommendation.baseline_games} 场基线</span>
          <span ref={celebrateRef as React.RefObject<HTMLSpanElement>} className={`evidence-chip ${complete && achieved ? "evidence-parsed" : "evidence-limited"}`}>
            {complete && achieved ? <Check size={14} aria-hidden="true" /> : <Circle size={14} aria-hidden="true" />}
            {activeMission ? `${progress?.completed_games || 0}/3 场` : complete ? (achieved ? "目标达成" : "已完成，未达标") : "尚未开始"}
          </span>
        </div>
        <div className="mt-4 text-xs font-black text-yellow-300">{activeMission ? "当前训练目标" : complete ? "最近一次训练" : "建议训练目标"}</div>
        <h1 className="mission-title">{recommendation.title}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300">{recommendation.reason}</p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-400">{recommendation.drill}</p>
        <div className="mission-target-row">
          <div><span>训练前</span><strong>{baseline}</strong></div>
          <div><span>三局目标</span><strong>{target}</strong></div>
          <div><span>当前结果</span><strong>{missionValue(progress?.current_value, recommendation.focus_key)}{progress?.current_value !== null && progress?.current_value !== undefined ? unit : ""}</strong></div>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {!activeMission ? (
            <button type="button" onClick={() => void start()} disabled={busy || !missionAvailable} className="mission-primary">
              {busy ? <LoaderCircle size={17} className="animate-spin" aria-hidden="true" /> : <Target size={17} aria-hidden="true" />}
              {!missionAvailable ? "暂无可用比赛" : complete ? "开始新一轮" : "开始三局挑战"}
            </button>
          ) : (
            <button type="button" onClick={() => void cancel()} disabled={busy} className="mission-secondary">
              {busy && <LoaderCircle size={15} className="animate-spin" aria-hidden="true" />}
              结束本轮
            </button>
          )}
          {recommendedHero.hero_id > 0 && (
            <span className="mission-hero">
              {recommendedHero.hero_icon && <img src={recommendedHero.hero_icon} alt="" />}
              优先：{recommendedHero.hero_name}
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
                    <div className="flex items-center justify-between gap-3">
                      <div className="truncate text-sm font-black text-stone-100">{match.hero_name}</div>
                      <div className="shrink-0 text-sm font-black text-yellow-200">{missionValue(match.metric_value, recommendation.focus_key)}{unit}</div>
                    </div>
                    <div className={`mt-1 text-xs font-black ${match.win ? "text-green-300" : "text-red-300"}`}>
                      {match.win ? "胜" : "负"} · {match.kills}/{match.deaths}/{match.assists} · {match.played_at}
                    </div>
                  </div>
                </>
              ) : (
                <div className="mission-slot-empty"><div className="text-sm font-black text-stone-400">等待新比赛</div><div className="mt-1 text-xs text-stone-600">仅记录开始任务后的公开比赛</div></div>
              )}
            </div>
          );
        })}
        {visibleMission && <div className="mission-started">开始于 {new Date(visibleMission.started_at * 1000).toLocaleString("zh-CN", { hour12: false })}</div>}
      </div>
    </section>
  );
}

function DataQualityStrip({ data, deepLoading }: { data: PlayerDashboardData; deepLoading: boolean }) {
  const quality = data.data_quality;
  const positionMatches = quality.verified_position_matches + quality.confirmed_position_matches;
  const rows = [
    { label: "比赛详情", value: quality.detail_matches },
    { label: "出装记录", value: quality.equipment_matches },
    { label: "英雄基准", value: quality.benchmark_matches },
    { label: "事件复盘", value: quality.replay_matches },
    { label: "位置确认", value: positionMatches },
  ];

  return (
    <section className="quality-strip" aria-label="数据覆盖">
      <div className="quality-strip-title">
        {deepLoading ? <LoaderCircle size={15} className="animate-spin text-cyan-300" /> : <ShieldCheck size={15} className="text-green-300" />}
        <span>{deepLoading ? "深度数据加载中" : `最近 ${quality.sample_games} 场数据覆盖`}</span>
      </div>
      {rows.map((row) => (
        <div key={row.label} className="quality-strip-stat" title={`${row.label}：${row.value}/${quality.sample_games} 场`}>
          <span>{row.label}</span>
          <strong>{row.value}/{quality.sample_games}</strong>
        </div>
      ))}
    </section>
  );
}

function MatchStoryPanel({ scorecard }: { scorecard: PlayerMatchScorecard }) {
  const story = scorecard.story;
  if (!story.available) return null;

  const displayStoryValue = (value: number | undefined, suffix = "") => value === undefined ? "-" : `${value}${suffix}`;
  const summary = [
    { label: "英雄击杀", value: displayStoryValue(story.summary.hero_kills) },
    { label: "参战率", value: displayStoryValue(story.summary.teamfight_participation, "%") },
    {
      label: "侦查 / 岗哨",
      value: story.summary.observer_wards === undefined && story.summary.sentry_wards === undefined
        ? "-"
        : `${displayStoryValue(story.summary.observer_wards)} / ${displayStoryValue(story.summary.sentry_wards)}`,
    },
    { label: "关键装备时间", value: displayStoryValue(story.summary.major_item_timings) },
  ];
  const hasAdvantageSeries = story.economy.some((point) => point.team_advantage !== null);
  const chapterIcons: Record<string, LucideIcon> = {
    lane: Activity,
    combat: Swords,
    item: BookOpen,
    vision: ShieldCheck,
    objective: Target,
    turning: TrendingUp,
    result: Check,
  };

  return (
    <section className="match-story" aria-label="比赛叙事">
      <div className="match-story-heading">
        <div>
          <div className="text-xs font-black text-green-300">MATCH STORY</div>
          <h3>关键节点与经济走势</h3>
        </div>
        <span className="evidence-chip evidence-parsed"><Check size={13} aria-hidden="true" />Replay 事件</span>
      </div>

      <div className="match-story-summary">
        {summary.map((item) => <div key={item.label}><span>{item.label}</span><strong>{item.value}</strong></div>)}
      </div>

      <div className="match-story-grid">
        {hasAdvantageSeries && (
          <div className="story-chart">
            <div className="story-panel-label">己方经济差</div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={story.economy} margin={{ top: 12, right: 8, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="storyAdvantage" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.28} />
                    <stop offset="95%" stopColor="var(--accent)" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="minute" tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tickFormatter={(value) => compactNumber(Number(value))} tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, color: "var(--text-primary)", fontSize: 12 }}
                  labelFormatter={(value) => `${value} 分钟`}
                  formatter={(value) => [Number(value).toLocaleString("zh-CN"), "己方经济差"]}
                />
                <Area type="monotone" dataKey="team_advantage" stroke="var(--accent)" strokeWidth={2} fill="url(#storyAdvantage)" connectNulls={false} />
              </AreaChart>
            </ResponsiveContainer>
            <p>正值代表己方领先。最大变化为全队事件，不归因于单个操作。</p>
          </div>
        )}

        <div className={`story-timeline ${hasAdvantageSeries ? "" : "story-timeline-wide"}`}>
          {story.chapters.map((chapter) => {
            const ChapterIcon = chapterIcons[chapter.type] || Circle;
            return (
              <div key={chapter.key} className={`story-chapter story-chapter-${chapter.tone}`}>
                <div className="story-time">{chapter.time_text}</div>
                <div className="story-node"><ChapterIcon size={14} aria-hidden="true" /></div>
                <div className="story-copy">
                  <div className="flex items-center gap-2">
                    {chapter.item?.icon && <img src={chapter.item.icon} alt="" />}
                    <strong>{chapter.title}</strong>
                  </div>
                  <p>{chapter.detail}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function MatchLab({
  data,
  positionBusy,
  onConfirmPosition,
}: {
  data: PlayerDashboardData;
  positionBusy: string;
  onConfirmPosition: (matchId: string, position: number) => Promise<void>;
}) {
  const candidates = useMemo(() => data.recent_matches.slice(0, 8), [data.recent_matches]);
  const [selectedMatchId, setSelectedMatchId] = useState(candidates[0]?.match_id || "");
  const [scorecard, setScorecard] = useState<PlayerMatchScorecard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const effectiveMatchId = candidates.some((match) => match.match_id === selectedMatchId) ? selectedMatchId : candidates[0]?.match_id || "";
  const selectedMatch = candidates.find((match) => match.match_id === effectiveMatchId);

  useEffect(() => {
    let active = true;
    if (!effectiveMatchId) return;
    async function loadScorecard() {
      await Promise.resolve();
      if (!active) return;
      setLoading(true);
      setError("");
      setScorecard(null);
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

      {selectedMatch && (
        <div className="position-confirm">
          <div className="position-confirm-copy">
            <span>本局位置</span>
            <strong>{selectedMatch.position_name || "选择实际位置"}</strong>
            <small>
              {selectedMatch.position_source === "stratz"
                ? "来源：STRATZ Ranked Roles"
                : selectedMatch.position_source === "user_confirmed"
                  ? "来源：玩家确认"
                  : "来源：待确认"}
            </small>
          </div>
          {selectedMatch.position_source === "stratz" ? (
            <span className="evidence-chip evidence-verified"><ShieldCheck size={13} aria-hidden="true" />已验证</span>
          ) : (
            <div className="position-options" aria-label="确认本局位置">
              {POSITION_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => void onConfirmPosition(selectedMatch.match_id, option.value)}
                  disabled={positionBusy === selectedMatch.match_id}
                  className={selectedMatch.position === option.value && selectedMatch.position_source === "user_confirmed" ? "active" : ""}
                  title={`${option.label} ${option.detail}`}
                >
                  {positionBusy === selectedMatch.match_id && selectedMatch.position === option.value ? <LoaderCircle size={13} className="animate-spin" /> : option.value}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

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

            <MatchStoryPanel scorecard={scorecard} />
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
    <section className="hero-strip">
      <h2>{title}</h2>
      <div className="hero-strip-grid">
        {heroes.slice(0, 9).map((hero) => (
          <div key={hero.hero_id} className="hero-strip-item">
            {hero.hero_icon ? <img src={hero.hero_icon} alt="" /> : <div className="hero-strip-placeholder" />}
            <div>
              <strong>{hero.hero_name}</strong>
              <div>
                <span>{hero.games}场</span>
                <span className={hero.win_rate >= 50 ? "text-green-300" : "text-red-300"}>{hero.win_rate}%</span>
                {hero.avg_kda && <span className="text-cyan-300">KDA {hero.avg_kda}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
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
                <stop offset="5%" stopColor="var(--positive)" stopOpacity={0.30} />
                <stop offset="95%" stopColor="var(--positive)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
            <XAxis dataKey="index" stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 100]} stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
            <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, color: "var(--text-primary)" }} />
            <Area type="monotone" dataKey="winrate" stroke="var(--positive)" strokeWidth={2} fill="url(#winrateFill)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2 className="section-title">段位轨迹</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.rank_history}>
            <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
            <XAxis dataKey="date" stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} />
            <YAxis stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, color: "var(--text-primary)" }} />
            <Line type="monotone" dataKey="tier" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2 className="section-title">时段表现</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.time_analysis}>
            <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} />
            <YAxis stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
            <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, color: "var(--text-primary)" }} />
            <Bar dataKey="winrate" name="胜率" fill="var(--accent)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2 className="section-title">星期表现</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.weekday_analysis}>
            <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} />
            <YAxis stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} tickFormatter={(value) => `${value}%`} />
            <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8, color: "var(--text-primary)" }} />
            <Bar dataKey="winrate" name="胜率" fill="var(--accent)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function CountsPanel({ data }: { data: PlayerDashboardData }) {
  const positions = data.role_matrix.map((role) => ({
    label: role.position_name,
    games: role.games,
    wins: Math.round(role.games * role.win_rate / 100),
    winrate: role.win_rate,
  }));
  const modes = data.counts.game_mode || [];
  if (!positions.length && !modes.length) return null;

  const sections = [
    {
      title: "近期位置",
      detail: `${data.position_coverage.verified_matches}/${data.position_coverage.total_matches} 场由 STRATZ Ranked Roles 验证`,
      items: positions,
    },
    { title: "游戏模式", detail: "", items: modes },
  ];

  return (
    <div className="card">
      <h2 className="section-title">长期分布</h2>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {sections.map((section) => {
          const maxGames = Math.max(...section.items.map((item) => item.games), 1);
          return (
          <div key={section.title} className="space-y-3">
            <div>
              <div className="text-xs font-bold uppercase text-stone-500">{section.title}</div>
              {section.detail && <div className="mt-1 text-[11px] text-stone-600">{section.detail}</div>}
            </div>
            {section.items.slice(0, 5).map((item) => (
              <div key={item.label}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-stone-300">{item.label}</span>
                  <span className="text-stone-500">{item.games}场 · 胜率 {item.winrate}%</span>
                </div>
                <div className="h-2 rounded bg-white/10">
                  <div className="h-2 rounded bg-yellow-300" style={{ width: `${item.games / maxGames * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
          );
        })}
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
        <div className="mt-2 text-xs text-stone-500">按真实位置对照当前版本：同一英雄在不同位置分别计算，不混合核心与辅助样本。</div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <div className="mb-3 text-sm font-black text-stone-100">你的英雄 vs 全局 Meta</div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {data.meta_fit.slice(0, 6).map((fit) => (
              <div key={`${fit.position_key}-${fit.hero_id}`} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    {fit.hero_icon && <img src={fit.hero_icon} alt="" className="h-8 w-8 rounded object-cover" />}
                    <div className="min-w-0">
                      <div className="truncate text-sm font-black text-stone-100">{fit.hero_name}</div>
                      <div className="text-xs text-stone-500">{fit.meta_role} · {compactNumber(fit.meta_matches)} 场全局样本</div>
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
          <div className="mb-3 text-sm font-black text-stone-100">STRATZ 五位置表现</div>
          <div className="grid grid-cols-1 gap-2">
            {data.role_matrix.map((role) => (
              <div key={role.position_key} className="grid grid-cols-[112px_1fr_68px] items-center gap-3 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-xs">
                <div>
                  <div className="font-black text-stone-100">{role.position_name}</div>
                  <div className="text-stone-500">{role.games} 场</div>
                </div>
                <div className="min-w-0">
                  <div className="truncate text-stone-400">{role.top_hero || "样本积累"}</div>
                  <div className="mt-1 text-stone-500">{role.avg_gpm} GPM · IMP {role.avg_imp === null ? "-" : signed(role.avg_imp)}</div>
                  {role.awards > 0 && <div className="mt-1 text-yellow-200">{role.awards} 次比赛奖项</div>}
                </div>
                <div className={`text-right font-black tabular-nums ${role.win_rate >= 50 ? "text-green-300" : "text-red-300"}`}>
                  {role.win_rate}%
                </div>
              </div>
            ))}
            {!data.role_matrix.length && <div className="text-sm text-stone-500">近期比赛没有可验证的位置样本</div>}
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
              <div key={`${build.hero_id}-${build.position_key}`} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
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
function EquipmentSlots({ match, compact = false, loading = false }: { match: PlayerMatch; compact?: boolean; loading?: boolean }) {
  if (!match.equipment_available) {
    if (loading) {
      return (
        <div className="equipment-loadout equipment-loadout-loading" aria-label="装备加载中">
          <div className="equipment-group">
            {Array.from({ length: 6 }, (_, index) => <span key={index} className="equipment-slot equipment-slot-loading" />)}
          </div>
        </div>
      );
    }
    return <span className="text-xs text-stone-500">无公开装备记录</span>;
  }

  const emptyItem = { item_id: 0, name: "", icon: "" };
  const inventory = Array.from({ length: 6 }, (_, index) => match.items?.[index] || emptyItem);
  const neutral = match.neutral_item?.item_id > 0 ? match.neutral_item : null;

  const slot = (item: PlayerMatch["items"][number], index: number, kind: "inventory" | "neutral") => {
    const title = item.name || (item.item_id ? `物品 ${item.item_id}` : `空装备槽 ${index + 1}`);
    const className = `equipment-slot equipment-slot-${kind} ${!item.item_id ? "equipment-slot-empty" : ""} ${item.item_id && !item.icon ? "equipment-slot-missing" : ""}`;
    if (!item.item_id || !item.icon) return <span key={`${kind}-${index}`} className={className} title={title}>{item.item_id ? "?" : ""}</span>;
    return <img key={`${kind}-${index}`} src={item.icon} alt={item.name || "Dota 2 item"} title={title} className={className} />;
  };

  return (
    <div className={`equipment-loadout ${compact ? "equipment-loadout-compact" : ""}`}>
      <div className="equipment-group" aria-label="主装备">{inventory.map((item, index) => slot(item, index, "inventory"))}</div>
      {neutral && <div className="equipment-group equipment-group-secondary" aria-label="中立装备">{slot(neutral, 0, "neutral")}</div>}
    </div>
  );
}

function MatchHistoryList({
  matches,
  limit = 8,
  compact = false,
  equipmentLoading = false,
  onOpenAll,
}: {
  matches: PlayerMatch[];
  limit?: number;
  compact?: boolean;
  equipmentLoading?: boolean;
  onOpenAll?: () => void;
}) {
  if (!matches.length) return null;
  const equipmentCoverage = matches.filter((match) => match.equipment_available).length;

  return (
    <section className="match-history-panel">
      <div className="match-history-header">
        <div>
          <h2>最近比赛</h2>
          <div>
            最近 {Math.min(matches.length, limit)} 场，按时间倒序 · {equipmentLoading ? "装备补全中" : `${equipmentCoverage}/${matches.length} 场 6+1 装备`}
          </div>
        </div>
        {onOpenAll && (
          <button
            type="button"
            onClick={onOpenAll}
            className="match-history-all"
          >
            <ListFilter size={14} aria-hidden="true" />
            <span>查看全部比赛</span>
          </button>
        )}
      </div>
      <div className="match-history-list">
        {matches.slice(0, limit).map((match) => {
          const opendotaUrl = match.opendota_url || `https://www.opendota.com/matches/${match.match_id}`;

          return (
            <article key={match.match_id} className="match-history-row">
              <div className="match-hero-cell">
                {match.hero_icon ? <img src={match.hero_icon} alt="" /> : <div className="match-hero-placeholder" />}
                <div>
                  <div className="match-hero-name">
                    <strong>{match.hero_name}</strong>
                    <span className={match.win ? "match-result match-result-win" : "match-result match-result-loss"}>{match.win ? "胜" : "负"}</span>
                    {match.position_name && <span className="match-position">{match.position_name}</span>}
                  </div>
                  <div className="match-row-meta">
                    {match.game_mode} · {match.side}{match.party_size > 1 ? ` · ${match.party_size}人组排` : match.party_size === 1 ? " · 单排" : ""}
                  </div>
                </div>
              </div>
              <div className="match-stat-cell">
                <strong>{match.kills}/{match.deaths}/{match.assists}</strong>
                <span>KDA {match.kda}</span>
                <div className="match-awards">
                  {match.stratz_imp !== null && <span className={numberClass(match.stratz_imp)}>IMP {signed(match.stratz_imp)}</span>}
                  {stratzAwardLabel(match.stratz_award) && <span className="text-yellow-300">{stratzAwardLabel(match.stratz_award)}</span>}
                </div>
              </div>
              <div className="match-economy-cell">
                <strong>{match.gold_per_min || "-"} GPM</strong>
                <span>{match.duration_text} · Lv {match.level || "-"}</span>
              </div>
              <div className="match-equipment-cell"><EquipmentSlots match={match} compact={compact} loading={equipmentLoading} /></div>
              <div className="match-date-cell">
                <span>{match.played_at}</span>
                <a
                  href={opendotaUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="match-external-link"
                  aria-label={`在 OpenDota 查看 ${match.hero_name} 比赛`}
                  title="在 OpenDota 查看"
                >
                  <ExternalLink size={14} aria-hidden="true" />
                </a>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function MatchTable({ matches, equipmentLoading = false }: { matches: PlayerMatch[]; equipmentLoading?: boolean }) {
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
            已获取详情的比赛展示出装、经济、补刀和伤害，其余保留基础结算数据。
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
              <th className="py-3 pr-4">模式 / 阵营</th>
              <th className="py-3 pr-4">时间</th>
              <th className="py-3 pr-4">详情</th>
            </tr>
          </thead>
          <tbody>
            {matches.slice(0, 20).map((match) => {
              const opendotaUrl = match.opendota_url || `https://www.opendota.com/matches/${match.match_id}`;

              return (
                <tr key={match.match_id} className="border-b border-white/5 transition hover:bg-white/[0.035]">
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      {match.hero_icon && <img src={match.hero_icon} alt="" className="h-8 w-8 rounded object-cover" />}
                      <span>
                        <span className="block font-bold text-stone-100">{match.hero_name}</span>
                        <span className="text-xs text-stone-500">{match.position_name ? `${match.position_name} · ` : ""}Lv {match.level || "-"}</span>
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
                    {match.stratz_imp !== null && <div className={`text-xs font-black ${numberClass(match.stratz_imp)}`}>IMP {signed(match.stratz_imp)}</div>}
                    {stratzAwardLabel(match.stratz_award) && <div className="text-xs font-black text-yellow-300">{stratzAwardLabel(match.stratz_award)}</div>}
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
                    <div className="min-w-[220px]"><EquipmentSlots match={match} compact loading={equipmentLoading} /></div>
                  </td>
                  <td className="py-3 pr-4">
                    <div className="font-bold text-stone-300">{match.game_mode}</div>
                    <div className="text-xs text-stone-500">{match.side} · {match.lobby_type}</div>
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
  const [copyState, setCopyState] = useState<CopyState>("idle");
  const [activeTab, setActiveTab] = useState<AppTab>("today");
  const [labView, setLabView] = useState<LabView>("scorecard");
  const [missionBusy, setMissionBusy] = useState(false);
  const [positionBusy, setPositionBusy] = useState("");
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

      const resolved = resolveAccountId(trimmed);
      if (resolved) {
        setSearchResults([]);
        setError("");
        setAccountId(resolved);
        return;
      }

      setLoading(true);
      setError("");
      try {
        const result = await searchPlayers(trimmed);
        setSearchResults(result.results);
        if (!result.results.length) {
          // 后端 warning 是给日志看的，不直接展示；用户只需要知道该怎么办。
          setError(result.warnings.length
            ? "搜索服务暂时不可用。可以粘贴 Steam 个人主页链接或 account id 直接查看。"
            : "没有找到匹配玩家。可以粘贴 Steam 个人主页链接或 account id 直接查看。");
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

    // 剪贴板 API 在非安全上下文缺失，被拒时也会 reject（权限、文档失焦、部分浏览器策略）。
    // 两种情况都要落到 execCommand 降级，再失败就明确告诉用户，不能静默吞掉。
    const copyViaSelection = () => {
      try {
        const field = document.createElement("textarea");
        field.value = url;
        field.setAttribute("readonly", "");
        field.style.position = "fixed";
        field.style.opacity = "0";
        field.style.pointerEvents = "none";
        document.body.appendChild(field);
        field.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(field);
        return ok;
      } catch {
        return false;
      }
    };

    const settle = (ok: boolean) => {
      setCopyState(ok ? "done" : "failed");
      window.setTimeout(() => setCopyState("idle"), 1800);
    };

    if (navigator.clipboard) {
      void navigator.clipboard.writeText(url).then(
        () => settle(true),
        () => settle(copyViaSelection()),
      );
      return;
    }
    settle(copyViaSelection());
  }, [data]);

  const handleStartMission = useCallback(async (focusKey: string) => {
    if (!data) return;
    const targetAccountId = data.profile.account_id;
    setMissionBusy(true);
    setError("");
    try {
      const training = await startTrainingMission(targetAccountId, focusKey);
      setData((current) => current?.profile.account_id === targetAccountId ? { ...current, training } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "训练任务创建失败");
    } finally {
      setMissionBusy(false);
    }
  }, [data]);

  const handleCancelMission = useCallback(async (missionId: string) => {
    if (!data) return;
    const targetAccountId = data.profile.account_id;
    setMissionBusy(true);
    setError("");
    try {
      const training = await cancelTrainingMission(targetAccountId, missionId);
      setData((current) => current?.profile.account_id === targetAccountId ? { ...current, training } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "训练任务更新失败");
    } finally {
      setMissionBusy(false);
    }
  }, [data]);

  const handleConfirmPosition = useCallback(async (matchId: string, position: number) => {
    if (!data) return;
    const targetAccountId = data.profile.account_id;
    setPositionBusy(matchId);
    setError("");
    try {
      const label = await confirmMatchPosition(targetAccountId, matchId, position);
      setData((current) => {
        if (!current || current.profile.account_id !== targetAccountId) return current;
        const previous = current.recent_matches.find((match) => match.match_id === matchId);
        if (!previous || previous.position_source === "stratz") return current;
        const isNewConfirmation = previous.position_source !== "user_confirmed";
        const confirmedMatches = current.position_coverage.confirmed_matches + (isNewConfirmation ? 1 : 0);
        const coveredMatches = current.position_coverage.covered_matches + (isNewConfirmation ? 1 : 0);
        return {
          ...current,
          recent_matches: current.recent_matches.map((match) => match.match_id === matchId ? {
            ...match,
            position: label.position,
            position_key: label.position_key,
            position_name: label.position_name,
            position_source: "user_confirmed",
            role_name: label.position_name,
            role_source: "user_confirmed",
          } : match),
          position_coverage: {
            ...current.position_coverage,
            confirmed_matches: confirmedMatches,
            covered_matches: coveredMatches,
            coverage_rate: current.position_coverage.total_matches
              ? Math.round(coveredMatches / current.position_coverage.total_matches * 1000) / 10
              : 0,
          },
          data_quality: {
            ...current.data_quality,
            confirmed_position_matches: current.data_quality.confirmed_position_matches + (isNewConfirmation ? 1 : 0),
          },
        };
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "位置确认失败");
    } finally {
      setPositionBusy("");
    }
  }, [data]);

  const hasCharts = useMemo(() => Boolean(data?.rolling_winrate.length || data?.rank_history.length), [data]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
        <ProductNav data={data} copyState={copyState} onCopyProfile={copyProfileLink} onOpenPro={() => setActiveTab("progress")} />
        <WorkspaceTabs activeTab={activeTab} onChange={setActiveTab} data={data} />
        </div>
      </header>
      <main className="app-main">
      <div className="app-content">
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
          <section id="personal-dashboard" className="space-y-3">
            <ProfileHeader data={data} deepLoading={deepLoading} />

            {data && (
              <>
                <div className="dashboard-workspace">
                  <div className="dashboard-primary">
                    <ThreeMatchMission data={data} busy={missionBusy} onStart={handleStartMission} onCancel={handleCancelMission} />
                    <PlayerDataExplorer
                      key={data.profile.account_id}
                      data={data}
                      equipmentLoading={deepLoading}
                      onOpenMatches={() => {
                        setLabView("history");
                        setActiveTab("lab");
                      }}
                    />
                  </div>
                  <DashboardRail data={data} />
                </div>
                <div className="updated-at">Updated {data.updated_at}</div>
              </>
            )}
          </section>
        )}

        {activeTab === "lab" && (
          <section className="space-y-4">
            {data && (
              <>
                <nav className="lab-subnav" aria-label="复盘视图">
                  {LAB_VIEWS.map((view) => {
                    const Icon = view.icon;
                    return (
                      <button
                        key={view.key}
                        type="button"
                        onClick={() => setLabView(view.key)}
                        className={labView === view.key ? "active" : ""}
                        aria-current={labView === view.key ? "page" : undefined}
                      >
                        <Icon size={15} aria-hidden="true" />
                        {view.label}
                      </button>
                    );
                  })}
                </nav>

                {labView === "scorecard" && <>
                  <MatchLab data={data} positionBusy={positionBusy} onConfirmPosition={handleConfirmPosition} />
                  <DataQualityStrip data={data} deepLoading={deepLoading} />
                  {data.warnings.length > 0 && (
                    <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-4 py-3 text-xs text-yellow-100">
                      部分外部数据源暂时不可用，当前复盘只显示已验证的数据。
                    </div>
                  )}
                </>}
                {labView === "report" && <AiReviewPanel data={data} commercialConfig={commercialConfig} />}
                {labView === "vision" && <WardMap accountId={data.profile.account_id} />}
                {labView === "history" && <MatchTable matches={data.recent_matches} equipmentLoading={deepLoading} />}
                <div className="updated-at">Updated {data.updated_at}</div>
              </>
            )}
          </section>
        )}

        {activeTab === "pool" && data && (
          <section className="space-y-4">
            <div className="page-intro"><div className="text-xs font-black text-yellow-300">HERO POOL</div><h1>英雄池训练室</h1></div>
            <PersonalMetaLab data={data} />
            <div className="hero-pool-layout"><HeroStrip title="近期英雄池" heroes={data.hero_pool} /><CountsPanel data={data} /></div>
            <HeroStrip title="生涯常用英雄" heroes={data.lifetime_heroes} />
          </section>
        )}

        {activeTab === "progress" && (
          <section className="space-y-4">
            {data && <>
              <div className="page-intro"><div className="text-xs font-black text-green-300">PROGRESS</div><h1>训练进度</h1></div>
              <ThreeMatchMission data={data} expanded busy={missionBusy} onStart={handleStartMission} onCancel={handleCancelMission} />
              <SummaryGrid data={data} />
              <CoachBrief data={data} />
              {hasCharts && <Charts data={data} />}
              <ProPanel data={data} commercialConfig={commercialConfig} />
            </>}
          </section>
        )}
      </div>
      </main>
    </div>
  );
}
