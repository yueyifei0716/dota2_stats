"use client";

import { RecentTrend as TrendType } from "@/lib/types";

function DiffBadge({ value, suffix = "" }: { value: number; suffix?: string }) {
  const color = value > 0 ? "text-green-400" : value < 0 ? "text-red-400" : "text-gray-400";
  const prefix = value > 0 ? "+" : "";
  return <span className={`text-xs font-bold ${color}`}>{prefix}{value}{suffix}</span>;
}

export default function RecentTrend({ data }: { data: TrendType }) {
  if (!data.recent.games && !data.previous.games) return null;

  return (
    <div className="card">
      <h3 className="section-title">近期趋势 (7天对比)</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-gray-400 mb-2">本周 ({data.recent.games}场)</div>
          <div className="space-y-1 text-sm">
            <div>胜率: <span className="text-yellow-400">{data.recent.winrate}%</span></div>
            <div>KDA: <span className="text-cyan-400">{data.recent.avg_kda}</span></div>
            <div>影响力: <span className="text-purple-400">{data.recent.avg_impact}</span></div>
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 mb-2">上周 ({data.previous.games}场)</div>
          <div className="space-y-1 text-sm">
            <div>胜率: <span className="text-yellow-400">{data.previous.winrate}%</span> <DiffBadge value={data.winrate_diff} suffix="%" /></div>
            <div>KDA: <span className="text-cyan-400">{data.previous.avg_kda}</span> <DiffBadge value={data.kda_diff} /></div>
            <div>影响力: <span className="text-purple-400">{data.previous.avg_impact}</span> <DiffBadge value={data.impact_diff} /></div>
          </div>
        </div>
      </div>
    </div>
  );
}
