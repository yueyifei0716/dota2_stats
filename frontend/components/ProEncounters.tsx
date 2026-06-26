"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { ProEncountersData } from "@/lib/types";
import { getProEncounters } from "@/lib/api";

export default function ProEncounters() {
  const [data, setData] = useState<ProEncountersData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProEncounters()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const encounters = data?.encounters ?? [];

  return (
    <div className="card">
      <h3 className="section-title">职业选手对局</h3>
      {loading ? (
        <div className="text-gray-400 text-sm">加载中...</div>
      ) : encounters.length === 0 ? (
        <div className="text-gray-500 text-sm">暂无职业选手对局记录</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-xs border-b border-white/10">
                <th className="text-left py-2 font-medium">选手</th>
                <th className="text-left py-2 font-medium">战队</th>
                <th className="text-center py-2 font-medium">同队</th>
                <th className="text-center py-2 font-medium">对手</th>
                <th className="text-center py-2 font-medium">总场次</th>
              </tr>
            </thead>
            <tbody>
              {encounters.map((p, i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition">
                  <td className="py-2">
                    <div className="flex items-center gap-2">
                      {p.avatar && <Image src={p.avatar} alt="" width={24} height={24} className="w-6 h-6 rounded-full" unoptimized />}
                      <span className="font-medium">{p.name}</span>
                    </div>
                  </td>
                  <td className="py-2 text-gray-400">{p.team || "-"}</td>
                  <td className="py-2 text-center">
                    {p.with_games > 0 ? (
                      <span>
                        {p.with_games}场{" "}
                        <span className={p.with_games > 0 && p.with_wins / p.with_games >= 0.5 ? "text-green-400" : "text-red-400"}>
                          ({p.with_wins}胜)
                        </span>
                      </span>
                    ) : (
                      <span className="text-gray-600">-</span>
                    )}
                  </td>
                  <td className="py-2 text-center">
                    {p.against_games > 0 ? (
                      <span>
                        {p.against_games}场{" "}
                        <span className={p.against_games > 0 && p.against_wins / p.against_games >= 0.5 ? "text-green-400" : "text-red-400"}>
                          ({p.against_wins}胜)
                        </span>
                      </span>
                    ) : (
                      <span className="text-gray-600">-</span>
                    )}
                  </td>
                  <td className="py-2 text-center text-yellow-400 font-medium">{p.total_games}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
