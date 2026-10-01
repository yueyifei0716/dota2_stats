import type { PlayerMatch } from "./types";

export type MatchDetail = Partial<PlayerMatch> & { match_id: string };
const MAX_ROWS = 256;
const TTL_MS = 10 * 60 * 1000;
const MAX_SOURCE_AGE_MS = 24 * 60 * 60 * 1000;
const rows = new Map<string, { detail: MatchDetail; receivedAt: number }>();
const key = (accountId: string | number, matchId: string) => `${Number(accountId)}:${matchId}`;

export function cachedMatchDetail(accountId: string | number, matchId: string, now = Date.now()): MatchDetail | undefined {
  const entry = rows.get(key(accountId, matchId));
  if (!entry) return;
  const source = entry.detail.detail_fetched_at;
  if (now - entry.receivedAt >= TTL_MS || (typeof source === "number" &&
      (now - source * 1000 > MAX_SOURCE_AGE_MS || now < source * 1000))) {
    rows.delete(key(accountId, matchId));
    return;
  }
  return entry.detail;
}

export function rememberMatchDetails(accountId: string | number, details: MatchDetail[], now = Date.now()) {
  if (!Number.isInteger(Number(accountId)) || Number(accountId) <= 0) return;
  for (const detail of details) {
    // An unavailable refresh must never replace a successful scoreboard.
    if (!detail.detail_available || !/^[1-9]\d*$/.test(detail.match_id)) continue;
    const cacheKey = key(accountId, detail.match_id);
    const previous = cachedMatchDetail(accountId, detail.match_id, now);
    if (typeof previous?.detail_fetched_at === "number" &&
        (typeof detail.detail_fetched_at !== "number" || detail.detail_fetched_at < previous.detail_fetched_at)) continue;
    rows.delete(cacheKey);
    rows.set(cacheKey, { detail: { ...detail, detail_status: "ready", detail_error: detail.detail_error || "" }, receivedAt: now });
  }
  while (rows.size > MAX_ROWS) rows.delete(rows.keys().next().value!);
}

export function mergeMatchDetail(match: PlayerMatch, detail?: MatchDetail): PlayerMatch {
  if (!detail || (match.detail_available && !detail.detail_available)) return match;
  if (match.detail_available && typeof match.detail_fetched_at === "number" &&
      typeof detail.detail_fetched_at === "number" && detail.detail_fetched_at < match.detail_fetched_at) return match;
  return { ...match, ...detail };
}
