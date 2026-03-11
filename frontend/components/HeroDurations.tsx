"use client";

import { useState, useEffect } from "react";
import { HeroDurationsData, AllHero } from "@/lib/types";
import { getHeroDurations, getAllHeroes } from "@/lib/api";

export default function HeroDurations() {
  const [heroes, setHeroes] = useState<AllHero[]>([]);
  const [selectedHero, setSelectedHero] = useState<number | null>(null);
  const [data, setData] = useState<HeroDurationsData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getAllHeroes().then(setHeroes).catch(() => {});
  }, []);

  const handleSelect = async (heroId: number) => {
    setSelectedHero(heroId);
    setLoading(true);
    try {
      const result = await getHeroDurations(heroId);
      setData(result);
    } catch {
      setData(null);
    }
    setLoading(false);
  };

  const durations = data?.durations ?? [];
  const maxGames = durations.length ? Math.max(...durations.map((d) => d.games)) : 1;

  return (
    <div className="card">
      <h3 className="section-title">英雄胜率 vs 时长</h3>
      <select
        className="bg-white/10 border border-white/20 rounded px-3 py-1.5 text-sm mb-4 text-white"
        value={selectedHero ?? ""}
        onChange={(e) => e.target.value && handleSelect(Number(e.target.value))}
      >
        <option value="">选择英雄 (全部 {heroes.length} 个)...</option>
        {heroes.map((h) => (
          <option key={h.hero_id} value={h.hero_id}>{h.hero_cn}</option>
        ))}
      </select>

      {loading && <div className="text-gray-400 text-sm">加载中...</div>}

      {data && !loading && durations.length > 0 && (
        <div>
          {/* Win rate bars colored by performance */}
          <div className="flex items-end gap-[2px] h-40 mb-1">
            {durations.map((d, i) => {
              const barHeight = (d.games / maxGames) * 100;
              const wrColor = d.winrate >= 55 ? "bg-green-500/60" : d.winrate >= 45 ? "bg-yellow-500/60" : "bg-red-500/60";
              return (
                <div key={i} className="flex-1 flex flex-col items-center justify-end group relative">
                  <div
                    className={`w-full ${wrColor} rounded-t-sm min-w-[6px] transition`}
                    style={{ height: `${barHeight}%` }}
                  />
                  <div className="absolute bottom-full mb-1 hidden group-hover:block bg-black/80 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                    {d.duration_min}min: {d.winrate}% ({d.games}场)
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>{durations[0]?.duration_min}min</span>
            <span>{durations[durations.length - 1]?.duration_min}min</span>
          </div>

          {/* Key data points */}
          <div className="mt-3 flex flex-wrap gap-2">
            {durations
              .filter((_, i) => i % Math.max(1, Math.floor(durations.length / 8)) === 0)
              .map((d) => (
                <div key={d.duration_min} className="stat-box text-center px-3 py-2">
                  <div className="text-xs text-gray-400">{d.duration_min}min</div>
                  <div className={`text-sm font-bold ${d.winrate >= 50 ? "text-green-400" : "text-red-400"}`}>
                    {d.winrate}%
                  </div>
                  <div className="text-xs text-gray-500">{d.games}场</div>
                </div>
              ))}
          </div>
        </div>
      )}

      {data && !loading && durations.length === 0 && (
        <div className="text-gray-500 text-sm">暂无数据</div>
      )}
    </div>
  );
}
