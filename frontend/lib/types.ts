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
  lane_role: number;
  lane_role_name: string;
  position_rank: number;
  position_name: string;
  role_name: string;
  role_source: "parsed" | "estimated" | "parsed+estimated" | "unknown";
  form_score: number;
  detail_available: boolean;
  level: number;
  gold_per_min: number;
  xp_per_min: number;
  last_hits: number;
  denies: number;
  net_worth: number;
  hero_damage: number;
  tower_damage: number;
  hero_healing: number;
  items: { item_id: number; icon: string }[];
  item_icons: string[];
  neutral_item: { item_id: number; icon: string };
  item_neutral_icon: string;
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
  rank_history: RankHistoryEntry[];
  rolling_winrate: RollingWinrateEntry[];
  time_analysis: TimeEntry[];
  weekday_analysis: TimeEntry[];
  counts: {
    game_mode?: PlayerCountItem[];
    lobby_type?: PlayerCountItem[];
    lane_role?: PlayerCountItem[];
  };
  coach: PlayerCoachPack;
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
