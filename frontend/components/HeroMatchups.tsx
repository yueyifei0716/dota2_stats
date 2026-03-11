"use client";

import { useState } from "react";
import { MatchupHero, HeroMatchup } from "@/lib/types";
import { getHeroMatchups } from "@/lib/api";

export default function HeroMatchups({ heroes }: { heroes: MatchupHero[] }) {
  const [selectedHero, setSelectedHero] = useState<number | null>(null);
  const [matchups, setMatchups] = useState<{ best: HeroMatchup[]; worst: HeroMatchup[] } | null>(null);
  const [loading, setLoading] = useState(false);

  if (!heroes.length) return null;

  const handleSelect = async (heroId: number) => {
    setSelectedHero(heroId);
    setLoading(true);
    try {
      const data = await getHeroMatchups(heroId);
      setMatchups(data);
    } catch {
      setMatchups(null);
    }
    setLoading(false);
  };

  return (
    <div className="card">
      <h3 className="section-title">英雄克制关系</h3>
      <select
        className="bg-white/10 border border-white/20 rounded px-3 py-1.5 text-sm mb-4 text-white"
        value={selectedHero ?? ""}
        onChange={(e) => e.target.value && handleSelect(Number(e.target.value))}
      >
        <option value="">选择英雄...</option>
        {heroes.map((h) => (
          <option key={h.hero_id} value={h.hero_id}>{h.hero_cn}</option>
        ))}
      </select>

      {loading && <div className="text-gray-400 text-sm">加载中...</div>}

      {matchups && !loading && (
        <div className="grid grid-cols-2 gap-6">
          <div>
            <h4 className="text-green-400 text-sm font-bold mb-2">克制 (高胜率)</h4>
            {matchups.best.map((m) => (
              <div key={m.hero_id} className="flex justify-between text-sm py-1 border-b border-white/5">
                <span>{m.hero_cn}</span>
                <span className="text-green-400">{m.winrate}% ({m.games}场)</span>
              </div>
            ))}
          </div>
          <div>
            <h4 className="text-red-400 text-sm font-bold mb-2">被克制 (低胜率)</h4>
            {matchups.worst.map((m) => (
              <div key={m.hero_id} className="flex justify-between text-sm py-1 border-b border-white/5">
                <span>{m.hero_cn}</span>
                <span className="text-red-400">{m.winrate}% ({m.games}场)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
