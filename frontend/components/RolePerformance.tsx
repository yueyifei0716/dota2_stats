"use client";

import { RolePerf } from "@/lib/types";

export default function RolePerformance({ data }: { data: RolePerf[] }) {
  if (!data.length) return null;

  return (
    <div className="card">
      <h3 className="section-title">分路表现</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {data.map((r) => (
          <div key={r.lane_role} className="stat-box">
            <div className="text-sm font-bold text-yellow-400 mb-2">{r.role}</div>
            <div className="text-xs text-gray-400 space-y-1">
              <div className="flex justify-between">
                <span>场次</span>
                <span className="text-white">{r.games}</span>
              </div>
              <div className="flex justify-between">
                <span>胜率</span>
                <span className={r.win_rate >= 50 ? "text-green-400" : "text-red-400"}>{r.win_rate}%</span>
              </div>
              <div className="flex justify-between">
                <span>KDA</span>
                <span className="text-white">{r.avg_kills}/{r.avg_deaths}/{r.avg_assists}</span>
              </div>
              <div className="flex justify-between">
                <span>影响力</span>
                <span className="text-cyan-400">{r.avg_impact}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
