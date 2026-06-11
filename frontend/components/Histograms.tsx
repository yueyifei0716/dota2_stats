"use client";

import { useCallback, useEffect, useState } from "react";
import { HistogramData } from "@/lib/types";
import { getHistogram } from "@/lib/api";

const FIELDS = [
  { key: "gold_per_min", label: "GPM" },
  { key: "xp_per_min", label: "XPM" },
  { key: "kills", label: "击杀" },
  { key: "deaths", label: "死亡" },
  { key: "assists", label: "助攻" },
  { key: "hero_damage", label: "英雄伤害" },
  { key: "tower_damage", label: "推塔伤害" },
  { key: "last_hits", label: "补刀" },
  { key: "duration", label: "时长" },
];

export default function Histograms() {
  const [data, setData] = useState<HistogramData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedField, setSelectedField] = useState("gold_per_min");

  const loadData = useCallback(async (field: string) => {
    setSelectedField(field);
    setLoading(true);
    try {
      const result = await getHistogram(field);
      setData(result);
    } catch {
      setData(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadData("gold_per_min");
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadData]);

  const maxGames = data ? Math.max(...data.buckets.map((b) => b.games), 1) : 1;

  return (
    <div className="card">
      <h3 className="section-title">数据分布</h3>

      <div className="flex flex-wrap gap-2 mb-4">
        {FIELDS.map((f) => (
          <button
            key={f.key}
            onClick={() => loadData(f.key)}
            className={`px-3 py-1 rounded text-xs transition ${
              selectedField === f.key && data
                ? "bg-yellow-500/30 text-yellow-400"
                : "bg-white/5 text-gray-400 hover:bg-white/10"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <div className="text-gray-400 text-sm">加载中...</div>}

      {data && !loading && data.buckets.length > 0 && (
        <div className="mt-2">
          <div className="flex items-end gap-[2px] h-40">
            {data.buckets.map((b, i) => {
              const height = (b.games / maxGames) * 100;
              return (
                <div key={i} className="flex-1 h-full flex flex-col items-center justify-end group relative">
                  <div
                    className="w-full bg-yellow-500/60 rounded-t-sm hover:bg-yellow-400/80 transition min-w-[3px]"
                    style={{ height: `${height}%` }}
                  />
                  <div className="absolute bottom-full mb-1 hidden group-hover:block bg-black/80 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                    {selectedField === "duration" ? `${Math.floor(b.x / 60)}min` : b.x}: {b.games}场
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>
              {selectedField === "duration"
                ? `${Math.floor(data.buckets[0]?.x / 60 || 0)}min`
                : data.buckets[0]?.x}
            </span>
            <span>
              {selectedField === "duration"
                ? `${Math.floor(data.buckets[data.buckets.length - 1]?.x / 60 || 0)}min`
                : data.buckets[data.buckets.length - 1]?.x}
            </span>
          </div>
        </div>
      )}

      {data && !loading && data.buckets.length === 0 && (
        <div className="text-gray-500 text-sm">暂无数据</div>
      )}

      {!data && !loading && (
        <div className="text-gray-500 text-sm">点击上方按钮查看数据分布</div>
      )}
    </div>
  );
}
