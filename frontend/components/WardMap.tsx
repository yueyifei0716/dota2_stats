"use client";

import { useState, useEffect } from "react";
import { WardMapData, WardDot } from "@/lib/types";
import { getWardMap } from "@/lib/api";

const MAP_SIZE = 300;

function WardCanvas({
  dots,
  color,
  glowColor,
  maxCount,
}: {
  dots: WardDot[];
  color: string;
  glowColor: string;
  maxCount: number;
}) {
  if (!dots.length) return <div className="text-gray-500 text-sm">暂无数据</div>;

  return (
    <div className="relative rounded-lg overflow-hidden" style={{ width: MAP_SIZE, height: MAP_SIZE }}>
      <img
        src="/minimap.jpg"
        alt="Dota 2 Map"
        className="absolute inset-0 w-full h-full object-cover"
        draggable={false}
      />
      <div className="absolute inset-0 bg-black/20" />
      <svg width={MAP_SIZE} height={MAP_SIZE} className="absolute inset-0">
        <defs>
          <filter id="ward-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {dots.map((d, i) => {
          const intensity = d.count / maxCount;
          const opacity = 0.9 + intensity * 0.1;
          const r = 2 + intensity * 4;
          const cx = d.x * MAP_SIZE;
          const cy = d.y * MAP_SIZE;
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r={r * 2} fill={glowColor} opacity={intensity * 0.3} />
              <circle cx={cx} cy={cy} r={r} fill={color} opacity={opacity} filter="url(#ward-glow)" />
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function WardMap() {
  const [data, setData] = useState<WardMapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"obs" | "sen">("obs");

  useEffect(() => {
    getWardMap()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const obsDots = Array.isArray(data?.obs) ? data.obs : [];
  const senDots = Array.isArray(data?.sen) ? data.sen : [];
  const allCounts = [...obsDots, ...senDots].map((d) => d.count);
  const maxCount = allCounts.length ? Math.max(...allCounts) : 1;
  const activeDots = tab === "obs" ? obsDots : senDots;

  return (
    <div className="card">
      <h3 className="section-title">眼位热力图</h3>
      {loading ? (
        <div className="text-gray-400 text-sm">加载中...</div>
      ) : (
        <>
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setTab("obs")}
              className={`px-3 py-1 rounded text-sm transition ${tab === "obs" ? "bg-yellow-500/30 text-yellow-400" : "bg-white/5 text-gray-400 hover:bg-white/10"}`}
            >
              侦查守卫 ({obsDots.length})
            </button>
            <button
              onClick={() => setTab("sen")}
              className={`px-3 py-1 rounded text-sm transition ${tab === "sen" ? "bg-blue-500/30 text-blue-400" : "bg-white/5 text-gray-400 hover:bg-white/10"}`}
            >
              岗哨守卫 ({senDots.length})
            </button>
          </div>
          <div className="flex justify-center">
            <WardCanvas
              dots={activeDots}
              color={tab === "obs" ? "#facc15" : "#60a5fa"}
              glowColor={tab === "obs" ? "#fbbf24" : "#3b82f6"}
              maxCount={maxCount}
            />
          </div>
        </>
      )}
    </div>
  );
}
