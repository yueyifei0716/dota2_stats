"use client";

import { useState, useEffect } from "react";
import { WardMapData, WardDot } from "@/lib/types";
import { getWardMap } from "@/lib/api";

const MAP_SIZE = 320;

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
    <div className="relative mx-auto aspect-square w-full max-w-[360px] overflow-hidden rounded-lg border border-white/10 bg-black/30">
      <img
        src="/minimap.jpg"
        alt="Dota 2 Map"
        className="absolute inset-0 w-full h-full object-cover"
        draggable={false}
      />
      <div className="absolute inset-0 bg-black/20" />
      <svg viewBox={`0 0 ${MAP_SIZE} ${MAP_SIZE}`} className="absolute inset-0 h-full w-full">
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

export default function WardMap({ accountId }: { accountId?: string | number }) {
  const [data, setData] = useState<WardMapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"obs" | "sen">("obs");

  useEffect(() => {
    getWardMap(accountId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [accountId]);

  const obsDots = Array.isArray(data?.obs) ? data.obs : [];
  const senDots = Array.isArray(data?.sen) ? data.sen : [];
  const allCounts = [...obsDots, ...senDots].map((d) => d.count);
  const maxCount = allCounts.length ? Math.max(...allCounts) : 1;
  const activeDots = tab === "obs" ? obsDots : senDots;

  return (
    <div className="card">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-xs font-black uppercase text-cyan-300">Vision Map</div>
          <h3 className="section-title mb-0 mt-2">眼位热力图</h3>
        </div>
        <div className="text-xs text-stone-500">OpenDota wardmap</div>
      </div>
      {loading ? (
        <div className="text-gray-400 text-sm">加载中...</div>
      ) : (
        <>
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setTab("obs")}
              className={`rounded-lg border px-3 py-2 text-xs font-black transition ${tab === "obs" ? "border-yellow-300/35 bg-yellow-300/15 text-yellow-200" : "border-white/10 bg-white/5 text-stone-400 hover:bg-white/10"}`}
            >
              侦查守卫 ({obsDots.length})
            </button>
            <button
              onClick={() => setTab("sen")}
              className={`rounded-lg border px-3 py-2 text-xs font-black transition ${tab === "sen" ? "border-cyan-300/35 bg-cyan-300/15 text-cyan-200" : "border-white/10 bg-white/5 text-stone-400 hover:bg-white/10"}`}
            >
              岗哨守卫 ({senDots.length})
            </button>
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,360px)_1fr] lg:items-center">
            <WardCanvas
              dots={activeDots}
              color={tab === "obs" ? "#f0c85a" : "#63c7c9"}
              glowColor={tab === "obs" ? "#fbbf24" : "#22d3ee"}
              maxCount={maxCount}
            />
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <div className="text-stone-500">侦查守卫点位</div>
                <div className="mt-2 text-2xl font-black text-yellow-200">{obsDots.length}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <div className="text-stone-500">岗哨守卫点位</div>
                <div className="mt-2 text-2xl font-black text-cyan-200">{senDots.length}</div>
              </div>
              <div className="col-span-2 rounded-lg border border-white/10 bg-black/20 p-3 leading-5 text-stone-400">
                数据来自 OpenDota 玩家 wardmap；如果账号或比赛没有公开解析记录，这里会为空。
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
