"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { HeroItemsData, HeroItem, AllHero } from "@/lib/types";
import { getHeroItems, getAllHeroes } from "@/lib/api";

function ItemRow({ items, title }: { items: HeroItem[]; title: string }) {
  if (!items.length) return null;
  return (
    <div>
      <h4 className="text-xs font-bold text-gray-400 mb-2 uppercase">{title}</h4>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <div key={item.item_id} className="group relative">
            <Image
              src={item.icon}
              alt={item.name}
              width={36}
              height={28}
              className="w-9 h-7 rounded border border-white/10 hover:border-yellow-400/50 transition"
              unoptimized
            />
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-black/90 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
              {item.name.replace(/_/g, " ")} ({item.count})
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HeroItemPopularity() {
  const [heroes, setHeroes] = useState<AllHero[]>([]);
  const [selectedHero, setSelectedHero] = useState<number | null>(null);
  const [data, setData] = useState<HeroItemsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"role" | "global">("role");

  useEffect(() => {
    getAllHeroes().then(setHeroes).catch(() => {});
  }, []);

  const handleSelect = async (heroId: number) => {
    setSelectedHero(heroId);
    setLoading(true);
    try {
      const result = await getHeroItems(heroId);
      setData(result);
      // Default to role tab if player has role data, otherwise global
      setTab(result.by_role.length > 0 ? "role" : "global");
    } catch {
      setData(null);
    }
    setLoading(false);
  };

  const hasRoleData = data && data.by_role.length > 0;
  const hasGlobalData = data && data.global && Object.values(data.global).some((arr) => arr.length > 0);

  return (
    <div className="card">
      <h3 className="section-title">英雄出装推荐</h3>
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

      {data && !loading && (
        <>
          {/* Tab switcher */}
          {(hasRoleData || hasGlobalData) && (
            <div className="flex gap-2 mb-4">
              {hasRoleData && (
                <button
                  onClick={() => setTab("role")}
                  className={`px-3 py-1 rounded text-sm transition ${
                    tab === "role" ? "bg-yellow-500/30 text-yellow-400" : "bg-white/5 text-gray-400 hover:bg-white/10"
                  }`}
                >
                  按 OpenDota 分路
                </button>
              )}
              {hasGlobalData && (
                <button
                  onClick={() => setTab("global")}
                  className={`px-3 py-1 rounded text-sm transition ${
                    tab === "global" ? "bg-cyan-500/30 text-cyan-400" : "bg-white/5 text-gray-400 hover:bg-white/10"
                  }`}
                >
                  全局推荐
                </button>
              )}
            </div>
          )}

          {/* Role-based items */}
          {tab === "role" && hasRoleData && (
            <div className="space-y-4">
              {data.by_role.map((r) => (
                <div key={r.role} className="stat-box">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-bold text-yellow-400">{r.role_name}</span>
                    <span className="text-xs text-gray-500">({r.games}场)</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {r.items.map((item) => (
                      <div key={item.item_id} className="group relative">
                        <Image
                          src={item.icon}
                          alt={item.name}
                          width={36}
                          height={28}
                          className="w-9 h-7 rounded border border-white/10 hover:border-yellow-400/50 transition"
                          unoptimized
                        />
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-black/90 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                          {item.name.replace(/_/g, " ")} ({item.count}次)
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Global items */}
          {tab === "global" && hasGlobalData && (
            <div className="space-y-4">
              <ItemRow items={data.global.start_game} title="初始装备" />
              <ItemRow items={data.global.early_game} title="前期核心" />
              <ItemRow items={data.global.mid_game} title="中期装备" />
              <ItemRow items={data.global.late_game} title="后期装备" />
            </div>
          )}

          {!hasRoleData && !hasGlobalData && (
            <div className="text-gray-500 text-sm">暂无出装数据</div>
          )}
        </>
      )}
    </div>
  );
}
