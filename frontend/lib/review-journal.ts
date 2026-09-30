import type { PlayerMatch } from "./types";

export const REVIEW_TAGS = ["对线", "出装", "节奏", "视野", "团战", "亮点"] as const;
export type ReviewTag = (typeof REVIEW_TAGS)[number];
export type CheckResult = "kept" | "missed" | "not_applicable";
export const CHECK_LABELS: Record<CheckResult, string> = {
  kept: "做到了", missed: "还需再试", not_applicable: "本局不适用",
};
export type MatchMemory = Pick<PlayerMatch, "match_id" | "hero_id" | "hero_name" | "hero_icon" | "start_time" | "played_at" | "win">;
export interface ReviewEntry {
  match: MatchMemory;
  tag: ReviewTag;
  note: string;
  reminder: string;
  createdAt: number;
  updatedAt: number;
  archived: boolean;
  focusStartedAt: number | null;
  checks: { matchId: string; result: CheckResult; checkedAt: number }[];
}
export interface ReviewJournal {
  version: 1;
  accountId: number;
  entries: ReviewEntry[];
  focusMatchId: string | null;
  seenMatchIds: string[];
}

export const journalKey = (accountId: number) => `dotasense-review-journal-v1:${accountId}`;
export const emptyJournal = (accountId: number): ReviewJournal => ({
  version: 1, accountId, entries: [], focusMatchId: null, seenMatchIds: [],
});

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("备份格式不正确");
  return value as Record<string, unknown>;
}
function text(value: unknown, max: number): string {
  if (typeof value !== "string" || value.length > max) throw new Error("记录文字格式不正确");
  return value;
}
function positive(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value <= 0) throw new Error("记录编号或时间不正确");
  return value;
}
function matchId(value: unknown): string {
  if (typeof value !== "string" || !/^\d{1,20}$/.test(value)) throw new Error("比赛编号不正确");
  return value;
}
function boolean(value: unknown): boolean {
  if (typeof value !== "boolean") throw new Error("记录状态不正确");
  return value;
}
function trustedIcon(value: unknown): string {
  const icon = text(value, 500);
  if (!icon) return "";
  try {
    const url = new URL(icon);
    return url.protocol === "https:" && ["cdn.cloudflare.steamstatic.com", "cdn.akamai.steamstatic.com", "cdn.steamstatic.com"].includes(url.hostname) ? icon : "";
  } catch { return ""; }
}

// Backup and browser storage share the same validator; neither is trusted input.
export function parseJournal(raw: string, accountId: number): ReviewJournal {
  if (raw.length > 4_000_000) throw new Error("备份过大，最多支持 4 MB");
  const data = object(JSON.parse(raw));
  if (data.version !== 1) throw new Error("暂不支持此备份版本");
  if (data.accountId !== accountId) throw new Error("备份属于其他玩家，请先切换到对应账号");
  if (!Array.isArray(data.entries) || data.entries.length > 1000) throw new Error("最多支持 1000 条复盘记录");
  const entries = data.entries.map((value): ReviewEntry => {
    const entry = object(value);
    const match = object(entry.match);
    if (!REVIEW_TAGS.includes(entry.tag as ReviewTag)) throw new Error("复盘分类不正确");
    if (!Array.isArray(entry.checks) || entry.checks.length > 1000) throw new Error("执行反馈格式不正确");
    const checks = entry.checks.map((value) => {
      const check = object(value);
      if (!["kept", "missed", "not_applicable"].includes(String(check.result))) throw new Error("执行反馈不正确");
      return { matchId: matchId(check.matchId), result: check.result as CheckResult, checkedAt: positive(check.checkedAt) };
    });
    if (new Set(checks.map((check) => check.matchId)).size !== checks.length) throw new Error("执行反馈存在重复比赛");
    return {
      match: {
        match_id: matchId(match.match_id), hero_id: positive(match.hero_id),
        hero_name: text(match.hero_name, 120), hero_icon: trustedIcon(match.hero_icon),
        start_time: positive(match.start_time), played_at: text(match.played_at, 80), win: boolean(match.win),
      },
      tag: entry.tag as ReviewTag, note: text(entry.note, 1200), reminder: text(entry.reminder, 160),
      createdAt: positive(entry.createdAt), updatedAt: positive(entry.updatedAt), archived: boolean(entry.archived),
      focusStartedAt: entry.focusStartedAt === null ? null : positive(entry.focusStartedAt), checks,
    };
  });
  if (new Set(entries.map((entry) => entry.match.match_id)).size !== entries.length) throw new Error("复盘记录存在重复比赛");
  const focusMatchId = data.focusMatchId === null ? null : matchId(data.focusMatchId);
  if (focusMatchId && !entries.some((entry) => entry.match.match_id === focusMatchId && entry.reminder.trim() && !entry.archived && entry.focusStartedAt)) {
    throw new Error("提醒关联的复盘记录不完整");
  }
  if (!Array.isArray(data.seenMatchIds) || data.seenMatchIds.length > 2000) throw new Error("回顾记录格式不正确");
  return { version: 1, accountId, entries, focusMatchId, seenMatchIds: [...new Set(data.seenMatchIds.map(matchId))] };
}

export function saveReview(
  state: ReviewJournal, match: MatchMemory, draft: { tag: ReviewTag; note: string; reminder: string }, pin: boolean, now = Date.now(),
): ReviewJournal {
  if (!draft.note.trim()) throw new Error("先记录一个观察或想法");
  const previous = state.entries.find((entry) => entry.match.match_id === match.match_id);
  const changedReminder = previous?.reminder !== draft.reminder.trim();
  const entry: ReviewEntry = {
    match: { match_id: match.match_id, hero_id: match.hero_id, hero_name: match.hero_name, hero_icon: match.hero_icon,
      start_time: match.start_time, played_at: match.played_at, win: match.win },
    tag: draft.tag, note: draft.note.trim(), reminder: draft.reminder.trim(),
    createdAt: previous?.createdAt ?? now, updatedAt: now, archived: false,
    focusStartedAt: changedReminder ? null : previous?.focusStartedAt ?? null,
    checks: changedReminder ? [] : previous?.checks ?? [],
  };
  let focusMatchId = state.focusMatchId;
  if (pin && entry.reminder) {
    if (focusMatchId !== match.match_id || !entry.focusStartedAt) entry.focusStartedAt = now;
    focusMatchId = match.match_id;
  } else if (focusMatchId === match.match_id) {
    focusMatchId = null;
  }
  return parseJournal(JSON.stringify({ ...state, focusMatchId,
    seenMatchIds: [...new Set([...state.seenMatchIds, match.match_id])].slice(-2000),
    entries: [entry, ...state.entries.filter((row) => row.match.match_id !== match.match_id)],
  }), state.accountId);
}

export function pinReview(state: ReviewJournal, id: string, now = Date.now()): ReviewJournal {
  const entry = state.entries.find((row) => row.match.match_id === id);
  if (!entry?.reminder || entry.archived) throw new Error("这条记录没有可用提醒");
  return { ...state, focusMatchId: id, entries: state.entries.map((row) => row !== entry ? row : {
    ...row, focusStartedAt: now, checks: [], updatedAt: now,
  }) };
}

export function archiveReview(state: ReviewJournal, id: string): ReviewJournal {
  return { ...state, focusMatchId: state.focusMatchId === id ? null : state.focusMatchId,
    entries: state.entries.map((entry) => entry.match.match_id !== id ? entry : { ...entry, archived: !entry.archived, updatedAt: Date.now() }) };
}

export function followUpMatches(entry: ReviewEntry, matches: PlayerMatch[]): PlayerMatch[] {
  if (!entry.focusStartedAt) return [];
  return orderedMatches(matches).filter((match) => match.hero_id === entry.match.hero_id && match.start_time * 1000 > entry.focusStartedAt!);
}

export function recordCheck(state: ReviewJournal, match: PlayerMatch, result: CheckResult): ReviewJournal {
  const entry = state.entries.find((row) => row.match.match_id === state.focusMatchId);
  if (!entry || !followUpMatches(entry, [match]).length) throw new Error("仅记录设置提醒后、同英雄比赛的执行反馈");
  const check = { matchId: match.match_id, result, checkedAt: Date.now() };
  return { ...state, entries: state.entries.map((row) => row !== entry ? row : {
    ...row, updatedAt: check.checkedAt, checks: [...row.checks.filter((row) => row.matchId !== match.match_id), check],
  }) };
}

export function mergeJournal(current: ReviewJournal, backup: ReviewJournal): ReviewJournal {
  if (current.accountId !== backup.accountId) throw new Error("不能合并其他玩家的备份");
  const entries = new Map(current.entries.map((entry) => [entry.match.match_id, entry]));
  // Restore missing entries only. Import must never silently overwrite newer user work.
  for (const entry of backup.entries) if (!entries.has(entry.match.match_id)) entries.set(entry.match.match_id, entry);
  return parseJournal(JSON.stringify({ ...current, entries: [...entries.values()],
    seenMatchIds: [...new Set([...current.seenMatchIds, ...backup.seenMatchIds])].slice(-2000),
    focusMatchId: current.focusMatchId ?? (backup.focusMatchId && !current.entries.some((entry) => entry.match.match_id === backup.focusMatchId) ? backup.focusMatchId : null),
  }), current.accountId);
}

export function orderedMatches(matches: PlayerMatch[]): PlayerMatch[] {
  const unique = new Map<string, PlayerMatch>();
  for (const match of matches) if (/^\d{1,20}$/.test(match.match_id) && Number.isFinite(match.start_time) && match.start_time > 0) unique.set(match.match_id, match);
  return [...unique.values()].sort((left, right) => right.start_time - left.start_time);
}

export function recentSession(matches: PlayerMatch[]): PlayerMatch[] {
  const ordered = orderedMatches(matches);
  if (!ordered.length) return [];
  const session = [ordered[0]];
  for (const match of ordered.slice(1)) {
    const newer = session[session.length - 1];
    if (!Number.isFinite(match.duration) || match.duration <= 0 || newer.start_time - (match.start_time + match.duration) > 90 * 60) break;
    session.push(match);
  }
  return session;
}

export function reviewCandidate(matches: PlayerMatch[], entries: ReviewEntry[]): { match: PlayerMatch; reason: string } | null {
  const unreviewed = matches.filter((match) => !entries.some((entry) => entry.match.match_id === match.match_id));
  const match = unreviewed.find((row) => row.replay_parsed) ?? unreviewed.find((row) => row.benchmark_available) ?? unreviewed[0];
  if (!match) return null;
  return { match, reason: match.replay_parsed ? "有时间线，可以核对装备与经济节点" : match.benchmark_available ? "有同英雄基准，可以对照这局结算" : "先记下这局印象，具体原因留待回看" };
}

export function sessionHighlight(matches: PlayerMatch[]): { match: PlayerMatch; label: string; percentile: number } | null {
  const labels: Record<string, string> = { gold_per_min: "GPM", xp_per_min: "XPM", kills_per_min: "每分钟击杀", last_hits_per_min: "每分钟补刀", hero_damage_per_min: "每分钟英雄伤害", hero_healing_per_min: "每分钟治疗", tower_damage: "建筑伤害" };
  let best: ReturnType<typeof sessionHighlight> = null;
  for (const match of matches) {
    if (!match.benchmark_available) continue;
    for (const [key, value] of Object.entries(match.benchmarks || {})) {
      if (!labels[key] || !value || !Number.isFinite(value.raw) || value.raw <= 0 || !Number.isFinite(value.pct) || value.pct < .75 || value.pct > 1) continue;
      const percentile = Math.round(value.pct * 100);
      if (!best || percentile > best.percentile) best = { match, label: labels[key], percentile };
    }
  }
  return best;
}
