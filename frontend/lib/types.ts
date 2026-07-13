export interface Profile {
  username: string;
  rank_tier: number | null;
  rank_name: string;
  rank_icon: string | null;
  current_mmr: number;
  estimated_mmr: number;
  total_wins: number;
  total_losses: number;
  win_rate: number;
}

export interface Match {
  match_id: string;
  hero_cn: string;
  hero_icon: string;
  win: string;
  kills: number;
  deaths: number;
  assists: number;
  adv_kills?: number;
  adv_deaths?: number;
  adv_assists?: number;
  duration: number;
  timestamp: string;
  game_mode: string;
  lobby_type: string;
  item_icons: string[];
  item_neutral_icon: string;
  impact_score: number;
  badges: Badge[];
  effective_role: number;
  role_name: string;
  note?: string;
  gpm?: number;
  xpm?: number;
  hero_damage?: number;
  tower_damage?: number;
}

export interface Badge {
  icon: string;
  text: string;
  class: string;
}

export interface HeroStat {
  hero_cn: string;
  hero_icon: string;
  hero_id: number;
  games: number;
  wins: number;
  win_rate: number;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
}

export interface MmrEntry {
  date: string;
  mmr: number;
}

export interface RankHistoryEntry {
  date: string;
  tier: number;
  label: string;
}

export interface RolePerf {
  role: string;
  lane_role: number;
  games: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
  avg_impact: number;
}

export interface RollingWinrateEntry {
  index: number;
  winrate: number;
}

export interface TimeEntry {
  label: string;
  games: number;
  wins: number;
  winrate: number;
}

export interface TrendStats {
  winrate: number;
  avg_kda: number;
  avg_impact: number;
  games: number;
}

export interface RecentTrend {
  recent: TrendStats;
  previous: TrendStats;
  winrate_diff: number;
  kda_diff: number;
  impact_diff: number;
}

export interface Peer {
  personaname: string;
  with_games: number;
  with_win: number;
  win_rate?: number;
  avatar?: string;
  avatarfull?: string;
}

export interface HeroMatchup {
  hero_id: number;
  hero_cn: string;
  games: number;
  wins: number;
  winrate: number;
}

export interface MatchupHero {
  hero_id: number;
  hero_cn: string;
  hero_en: string;
}

export interface MostPlayedHero {
  name: string;
  icon: string;
  count: number;
}

export interface HeroFilter {
  name: string;
  icon: string;
}

export interface Ranking {
  hero_id: number;
  hero_cn: string;
  hero_icon: string;
  percent_rank: number;
  top_percent: number;
}

// ── New feature types ──

export interface WardDot {
  x: number;
  y: number;
  count: number;
}

export interface WardMapData {
  obs: WardDot[];
  sen: WardDot[];
}

export interface HistogramBucket {
  x: number;
  games: number;
}

export interface HistogramData {
  field: string;
  buckets: HistogramBucket[];
}

export interface CountItem {
  label: string;
  games: number;
  wins: number;
  winrate: number;
}

export interface CountsData {
  game_mode?: CountItem[];
  lobby_type?: CountItem[];
  side?: CountItem[];
  lane_role?: CountItem[];
  patch?: CountItem[];
}

export interface HeroItem {
  item_id: number;
  name: string;
  icon: string;
  count: number;
}

export interface RoleItems {
  role: number;
  role_name: string;
  games: number;
  items: HeroItem[];
}

export interface GlobalItems {
  start_game: HeroItem[];
  early_game: HeroItem[];
  mid_game: HeroItem[];
  late_game: HeroItem[];
}

export interface HeroItemsData {
  by_role: RoleItems[];
  global: GlobalItems;
}

export interface DurationBucket {
  duration_min: number;
  label: string;
  games: number;
  wins: number;
  winrate: number;
}

export interface HeroDurationsData {
  durations: DurationBucket[];
}

export interface ProEncounter {
  name: string;
  team: string;
  avatar: string;
  with_games: number;
  with_wins: number;
  against_games: number;
  against_wins: number;
  total_games: number;
  last_played?: number;
}

export interface ProEncountersData {
  encounters: ProEncounter[];
}

export interface AllHero {
  hero_id: number;
  hero_cn: string;
  hero_en: string;
  hero_icon: string;
}

export interface PlayerSearchResult {
  account_id: number;
  username: string;
  avatar: string;
  last_match_time?: string;
  similarity?: number;
}

export interface PlayerSearchResponse {
  results: PlayerSearchResult[];
  warnings: string[];
}

export interface PlayerProfile {
  account_id: number;
  username: string;
  avatar: string;
  profile_url: string;
  country: string;
  rank_tier: number;
  rank_name: string;
  rank_icon: string | null;
  leaderboard_rank?: number | null;
  total_wins: number;
  total_losses: number;
  total_games: number;
  lifetime_win_rate: number;
}

export interface PlayerTrendBucket {
  games: number;
  win_rate: number;
  kda: number;
  form_score: number;
}

export interface PlayerSummary {
  games: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_kills: number;
  avg_deaths: number;
  avg_assists: number;
  avg_kda: number;
  avg_duration_min: number;
  avg_form_score: number;
  streak: { count: number; label: string };
  last_played: string;
  trend: {
    recent: PlayerTrendBucket;
    previous: PlayerTrendBucket;
    win_rate_diff: number;
    kda_diff: number;
    form_diff: number;
  };
}

export interface PlayerMatch {
  match_id: string;
  hero_id: number;
  hero_name: string;
  hero_icon: string;
  win: boolean;
  kills: number;
  deaths: number;
  assists: number;
  kda: number;
  duration: number;
  duration_text: string;
  start_time: number;
  played_at: string;
  game_mode: string;
  lobby_type: string;
  party_size: number;
  player_slot: number;
  is_radiant: boolean;
  side: "Radiant" | "Dire";
  lane_role: number;
  lane_role_name: string;
  role_name: string;
  role_source: "stratz" | "parsed" | "unknown";
  position: number;
  position_key: string;
  position_name: string;
  position_source: "stratz" | "unavailable";
  stratz_role: string;
  stratz_lane: string;
  stratz_imp: number | null;
  stratz_award: string;
  performance_available: boolean;
  form_score: number;
  detail_available: boolean;
  benchmark_available: boolean;
  benchmarks: Record<string, { raw: number; pct: number }>;
  replay_parsed: boolean;
  evidence_level: "limited" | "verified" | "parsed";
  level: number;
  gold_per_min: number;
  xp_per_min: number;
  last_hits: number;
  denies: number;
  net_worth: number;
  hero_damage: number;
  tower_damage: number;
  hero_healing: number;
  items: { item_id: number; name: string; icon: string }[];
  item_icons: string[];
  neutral_item: { item_id: number; name: string; icon: string };
  item_neutral_icon: string;
  equipment_available: boolean;
  equipment_source: "stratz" | "opendota" | "unavailable";
  opendota_url: string;
}

export interface PlayerHeroStat {
  hero_id: number;
  hero_name: string;
  hero_icon: string;
  games: number;
  wins: number;
  win_rate: number;
  avg_kda?: number;
  last_played?: string;
}

export interface PlayerMetaRole {
  key: string;
  label: string;
}

export interface PlayerMetaHero {
  hero_id: number;
  hero_name: string;
  hero_icon: string;
  role_key: string;
  role_label: string;
  matches: number;
  wins: number;
  win_rate: number;
  meta_score: number;
  contest_rate: number;
  pro_pick: number;
  pro_win: number;
}

export interface PlayerHeroMeta {
  source: string;
  roles: PlayerMetaRole[];
  top: PlayerMetaHero[];
  by_scope: Record<string, PlayerMetaHero[]>;
}

export interface GlobalMetaOverview {
  source: string;
  scope: string;
  available: boolean;
  status: "ready" | "empty" | "not_configured" | "unavailable";
  period_start: string;
  period_end: string;
  hero_meta: PlayerHeroMeta;
  snapshot: {
    heroes: number;
    total_matches: number;
    total_pro_picks: number;
    top_contested_hero: string;
    top_contested_rate: number;
  };
  role_leaders: Record<string, PlayerMetaHero[]>;
  volume_leaders: PlayerMetaHero[];
  pro_signal: PlayerMetaHero[];
  high_confidence: PlayerMetaHero[];
  warnings: string[];
  updated_at: string;
}

export interface PlayerMetaFit {
  hero_id: number;
  hero_name: string;
  hero_icon: string;
  position: number;
  position_key: string;
  position_name: string;
  personal_games: number;
  personal_win_rate: number;
  meta_role: string;
  meta_matches: number;
  meta_win_rate: number;
  meta_score: number;
  gap: number;
  verdict: string;
}

export interface PlayerBuildSignature {
  hero_id: number;
  hero_name: string;
  hero_icon: string;
  lane_role: number;
  lane_role_name: string;
  position: number;
  position_key: string;
  position_name: string;
  role_name: string;
  games: number;
  wins: number;
  win_rate: number;
  avg_kda: number;
  items: { item_id: number; icon: string; count: number }[];
}

export interface PlayerRoleMatrix {
  position: number;
  position_key: string;
  position_name: string;
  role_name: string;
  games: number;
  win_rate: number;
  avg_kda: number;
  avg_gpm: number;
  avg_xpm: number;
  avg_last_hits: number;
  avg_damage: number;
  avg_imp: number | null;
  awards: number;
  top_hero: string;
}

export interface PlayerCountItem {
  label: string;
  games: number;
  wins: number;
  winrate: number;
}

export interface PlayerCoachReadiness {
  label: string;
  score: number;
  tone: "green" | "red" | "gold" | "cyan";
  reason: string;
}

export interface PlayerCoachInsight {
  title: string;
  metric: string;
  body: string;
  action: string;
  tone: "green" | "red" | "gold" | "cyan";
}

export interface PlayerTrainingStep {
  label: string;
  focus: string;
  drill: string;
  success_metric: string;
}

export interface PlayerProPreview {
  title: string;
  detail: string;
}

export interface PlayerCoachPack {
  readiness: PlayerCoachReadiness;
  insights: PlayerCoachInsight[];
  training_plan: PlayerTrainingStep[];
  signature_hero?: PlayerHeroStat;
  recent_deaths: number;
  pro_preview: PlayerProPreview[];
}

export interface PlayerDashboardData {
  profile: PlayerProfile;
  summary: PlayerSummary;
  recent_matches: PlayerMatch[];
  hero_pool: PlayerHeroStat[];
  lifetime_heroes: PlayerHeroStat[];
  hero_meta: PlayerHeroMeta;
  meta_fit: PlayerMetaFit[];
  build_signatures: PlayerBuildSignature[];
  role_matrix: PlayerRoleMatrix[];
  position_coverage: {
    verified_matches: number;
    total_matches: number;
    coverage_rate: number;
    source: string;
  };
  rank_history: RankHistoryEntry[];
  rolling_winrate: RollingWinrateEntry[];
  time_analysis: TimeEntry[];
  weekday_analysis: TimeEntry[];
  counts: {
    game_mode?: PlayerCountItem[];
    lobby_type?: PlayerCountItem[];
    lane_role?: PlayerCountItem[];
    lane_role_summary?: {
      known_games: number;
      total_games: number;
      coverage_rate: number;
    };
  };
  coach: PlayerCoachPack;
  warnings: string[];
  data_stage: "quick" | "deep";
  updated_at: string;
}

export interface MatchScorecardMetric {
  key: string;
  label: string;
  unit: string;
  value: number;
  percentile: number;
}

export interface MatchScorecardEvidence {
  key: string;
  label: string;
  status: "verified" | "parsed" | "unavailable";
  detail: string;
}

export interface PlayerMatchScorecard {
  match: {
    match_id: string;
    hero_id: number;
    hero_name: string;
    hero_icon: string;
    win: boolean;
    kills: number;
    deaths: number;
    assists: number;
    kda: number;
    duration_text: string;
    played_at: string;
    items: { item_id: number; icon: string }[];
  };
  metrics: MatchScorecardMetric[];
  headline: string;
  finding: string;
  action: string;
  evidence: MatchScorecardEvidence[];
  replay_parsed: boolean;
  source: string;
  updated_at: string;
}

export interface CommercialPlan {
  key: "founder" | "review" | "team";
  name: string;
  price: string;
  checkout_configured: boolean;
}

export interface CommercialConfig {
  plans: CommercialPlan[];
  sales_contact: string;
  sales_url: string;
  discord_url: string;
  webhook_configured: boolean;
  access_code_configured: boolean;
}

export interface CommercialLeadPayload {
  account_id?: number;
  plan: string;
  contact: string;
  role?: string;
  goal?: string;
  source?: string;
}

export interface CommercialLeadResponse {
  ok: boolean;
  plan: string;
  lead_delivered: boolean;
  checkout_url: string;
  next_step: "checkout" | "manual_contact";
}

export interface CommercialAccessResponse {
  ok: boolean;
  account_id?: number;
  access_token: string;
  expires_at: number;
  plan: string;
  ttl_seconds: number;
}

export interface CommercialAccessVerifyResponse {
  ok: boolean;
  account_id?: number;
  plan: string;
  expires_at: number;
}

export interface PlayerReviewSection {
  title: string;
  finding: string;
  evidence: string;
  action: string;
}

export interface PlayerReviewPlanStep {
  day: string;
  focus: string;
  task: string;
  metric: string;
}

export interface PlayerReviewMatch {
  match_id: string;
  hero: string;
  reason: string;
}

export interface PlayerReview {
  headline: string;
  score: number;
  summary: string;
  sections: PlayerReviewSection[];
  weekly_plan: PlayerReviewPlanStep[];
  priority_matches: PlayerReviewMatch[];
  model_note: string;
}

export interface PlayerReviewResponse {
  locked: boolean;
  source: "deterministic_preview" | "deterministic_fallback" | "deepseek" | string;
  review: PlayerReview;
  paywall?: {
    title: string;
    detail: string;
  };
  warnings: string[];
  updated_at: string;
}

export interface DashboardData {
  profile: Profile;
  stats: {
    recent_wins: number;
    recent_losses: number;
    streak_count: number;
    streak_label: string;
    most_played_recent: MostPlayedHero[];
  };
  hero_stats: HeroStat[];
  best_heroes: HeroStat[];
  worst_heroes: HeroStat[];
  all_heroes: HeroFilter[];
  mmr: { dates: string[]; values: number[] };
  rank_history: RankHistoryEntry[];
  top_rankings: Ranking[];
  role_performance: RolePerf[];
  rolling_winrate: RollingWinrateEntry[];
  time_analysis: TimeEntry[];
  weekday_analysis: TimeEntry[];
  recent_trend: RecentTrend;
  peers: Peer[];
  matchup_heroes: MatchupHero[];
}
