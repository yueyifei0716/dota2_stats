"use client";

import { useState, useEffect } from "react";
import { CountsData, CountItem } from "@/lib/types";
import { getCounts } from "@/lib/api";

type TabKey = "game_mode" | "lobby_type" | "side" | "lane_role";

const TABS: { key: TabKey; label: string }[] = [
  { key: "game_mode", label: "游戏模式" },
  { key: "lobby_type", label: "大厅类型" },
  { key: "side", label: "阵营" },
  { key: "lane_role", label: "路线" },
];

function CountBar({ item, maxGames }: { item: CountItem; maxGames: number }) {
  const pct = (item.games / maxGames) * 100;
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="w-28 text-sm truncate">{item.label}</div>
      <div className="flex-1 h-5 bg-white/5 rounded overflow-hidden relative">
        <div
          className="h-full bg-yellow-500/40 rounded"
          style={{ width: `${pct}%` }}
        />
        <span className="absolute inset-0 flex items-center px-2 text-xs text-white/80">
          {item.games}场
        </span>
      </div>
      <div className={`w-14 text-right text-sm font-medium ${item.winrate >= 50 ? "text-green-400" : "text-red-400"}`}>
        {item.winrate}%
      </div>
    </div>
  );
}

export default function GameCounts() {
  const [data, setData] = useState<CountsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<TabKey>("game_mode");

  useEffect(() => {
    getCounts()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const items = data?.[tab] ?? [];
  const maxGames = items.length ? Math.max(...items.map((i) => i.games)) : 1;

  return (
    <div className="card">
      <h3 className="section-title">游戏统计分布</h3>
      {loading ? (
        <div className="text-gray-400 text-sm">加载中...</div>
      ) : (
        <>
          <div className="flex gap-2 mb-4">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-3 py-1 rounded text-sm transition ${
                  tab === t.key
                    ? "bg-yellow-500/30 text-yellow-400"
                    : "bg-white/5 text-gray-400 hover:bg-white/10"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="space-y-0.5">
            {items.map((item) => (
              <CountBar key={item.label} item={item} maxGames={maxGames} />
            ))}
            {items.length === 0 && <div className="text-gray-500 text-sm">暂无数据</div>}
          </div>
        </>
      )}
    </div>
  );
}
