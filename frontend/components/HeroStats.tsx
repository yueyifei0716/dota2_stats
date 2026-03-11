"use client";

import { HeroStat } from "@/lib/types";

function HeroList({ heroes, title, color }: { heroes: HeroStat[]; title: string; color: string }) {
  return (
    <div>
      <h4 className={`text-sm font-bold mb-2 ${color}`}>{title}</h4>
      <div className="space-y-1.5">
        {heroes.map((h) => (
          <div key={h.hero_cn} className="flex items-center gap-2 bg-white/5 rounded px-3 py-1.5">
            {h.hero_icon && <img src={h.hero_icon} alt="" className="w-7 h-7 rounded" />}
            <span className="text-sm flex-1">{h.hero_cn}</span>
            <span className="text-xs text-gray-400">{h.games}场</span>
            <span className={`text-xs font-bold ${Number(h.win_rate) >= 50 ? "text-green-400" : "text-red-400"}`}>
              {h.win_rate}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HeroStats({ heroStats, bestHeroes, worstHeroes }: { heroStats: HeroStat[]; bestHeroes: HeroStat[]; worstHeroes: HeroStat[] }) {
  return (
    <div className="card">
      <h3 className="section-title">英雄统计</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <HeroList heroes={bestHeroes} title="最佳英雄 (≥10场)" color="text-green-400" />
        <HeroList heroes={worstHeroes} title="最差英雄 (≥10场)" color="text-red-400" />
        <HeroList heroes={heroStats.slice(0, 5)} title="最常用英雄" color="text-yellow-400" />
      </div>
    </div>
  );
}
