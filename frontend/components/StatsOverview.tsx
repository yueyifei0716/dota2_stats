"use client";

import Image from "next/image";
import { DashboardData } from "@/lib/types";

export default function StatsOverview({ data }: { data: DashboardData }) {
  const { stats } = data;
  const recentTotal = stats.recent_wins + stats.recent_losses;
  const recentWr = recentTotal > 0 ? ((stats.recent_wins / recentTotal) * 100).toFixed(1) : "0.0";

  return (
    <div className="card">
      <h3 className="section-title">统计概览</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-box">
          <div className="text-sm text-gray-400">最近 20 场</div>
          <div className="text-xl font-bold">
            <span className="text-green-400">{stats.recent_wins}</span>
            <span className="text-gray-500"> / </span>
            <span className="text-red-400">{stats.recent_losses}</span>
          </div>
          <div className="text-yellow-400 text-sm">{recentWr}%</div>
        </div>
        <div className="stat-box">
          <div className="text-sm text-gray-400">当前</div>
          <div className={`text-xl font-bold ${stats.streak_label === "连胜" ? "text-green-400" : "text-red-400"}`}>
            {stats.streak_count} {stats.streak_label}
          </div>
        </div>
        <div className="stat-box col-span-2">
          <div className="text-sm text-gray-400 mb-2">最常用英雄</div>
          <div className="flex gap-3 flex-wrap">
            {stats.most_played_recent.map((h) => (
              <div key={h.name} className="flex items-center gap-1.5 bg-white/5 rounded px-2 py-1">
                {h.icon && <Image src={h.icon} alt="" width={24} height={24} className="w-6 h-6 rounded" unoptimized />}
                <span className="text-sm">{h.name}</span>
                <span className="text-xs text-gray-400">×{h.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
