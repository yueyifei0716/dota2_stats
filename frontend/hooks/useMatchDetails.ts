"use client";

import { useEffect, useRef, useState } from "react";
import { getPlayerMatchDetails } from "@/lib/api";
import { cachedMatchDetail, mergeMatchDetail } from "@/lib/match-details-cache";
import type { PlayerMatch } from "@/lib/types";

type Detail = Partial<PlayerMatch> & { match_id: string };

export function useMatchDetails(accountId: number, matches: PlayerMatch[], enabled = true) {
  const cache = useRef<{ accountId: number; rows: Record<string, Detail> }>({ accountId, rows: {} });
  const [view, setView] = useState<{ accountId: number; rows: Record<string, Detail> }>({ accountId, rows: {} });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const ids = matches.filter((match) => !match.detail_available).map((match) => match.match_id).join(",");

  useEffect(() => {
    const controller = new AbortController();
    if (cache.current.accountId !== accountId) cache.current = { accountId, rows: {} };
    const pending = ids.split(",").filter((id) => id && !cachedMatchDetail(accountId, id) && !cache.current.rows[id]?.detail_available);
    async function load() {
      await Promise.resolve();
      if (controller.signal.aborted) return;
      setLoading(false);
      setError("");
      if (!enabled || !accountId || !pending.length) return;
      setLoading(true);
      try {
        // One batch at a time; the API allows at most eight IDs and three workers.
        for (let start = 0; start < pending.length; start += 8) {
          const result = await getPlayerMatchDetails(accountId, pending.slice(start, start + 8), controller.signal);
          if (controller.signal.aborted) return;
          for (const row of result.matches) cache.current.rows[row.match_id] = row;
          if (result.matches.some((row) => row.detail_error)) setError("部分比赛详情暂未读取成功，可重试；已读取的数据保留。");
          setView({ accountId, rows: { ...cache.current.rows } });
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "比赛详情读取失败，可重试");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [accountId, ids, enabled, retryCount]);

  // Account identity prevents a late response from leaking another player's data.
  return {
    matches: matches.map((match) => mergeMatchDetail(
      mergeMatchDetail(match, view.accountId === accountId ? view.rows[match.match_id] : undefined),
      cachedMatchDetail(accountId, match.match_id),
    )),
    loading,
    error,
    retry: () => setRetryCount((value) => value + 1),
  };
}
