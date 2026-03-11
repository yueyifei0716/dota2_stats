"use client";

import { useState, useEffect } from "react";
import { Match, HeroFilter } from "@/lib/types";
import { getMatches, saveMatchNote } from "@/lib/api";
import { formatDuration, ROLE_NAMES } from "@/lib/constants";

export default function MatchTable({ allHeroes }: { allHeroes: HeroFilter[] }) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [heroFilter, setHeroFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState<number | undefined>();
  const [editingNote, setEditingNote] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");

  const fetchMatches = async () => {
    setLoading(true);
    try {
      const data = await getMatches({ hero: heroFilter || undefined, role: roleFilter });
      setMatches(data);
    } catch {
      /* ignore */
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchMatches();
  }, [heroFilter, roleFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSaveNote = async (matchId: string) => {
    await saveMatchNote(matchId, noteText);
    setEditingNote(null);
    fetchMatches();
  };

  const wins = matches.filter((m) => m.win === "Win").length;
  const losses = matches.length - wins;

  return (
    <div className="card">
      <div className="flex items-center gap-4 mb-4 flex-wrap">
        <h3 className="section-title mb-0">比赛记录</h3>
        <select
          className="bg-white/10 border border-white/20 rounded px-2 py-1 text-sm text-white"
          value={heroFilter}
          onChange={(e) => setHeroFilter(e.target.value)}
        >
          <option value="">全部英雄</option>
          {allHeroes.map((h) => (
            <option key={h.name} value={h.name}>{h.name}</option>
          ))}
        </select>
        <select
          className="bg-white/10 border border-white/20 rounded px-2 py-1 text-sm text-white"
          value={roleFilter ?? ""}
          onChange={(e) => setRoleFilter(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">全部位置</option>
          {Object.entries(ROLE_NAMES).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <span className="text-sm text-gray-400 ml-auto">
          <span className="text-green-400">{wins}胜</span> / <span className="text-red-400">{losses}负</span>
          {matches.length > 0 && <span className="text-yellow-400 ml-1">({((wins / matches.length) * 100).toFixed(1)}%)</span>}
        </span>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-8">加载中...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-white/10">
                <th className="text-left py-2 px-2">英雄</th>
                <th className="text-center py-2 px-2">结果</th>
                <th className="text-center py-2 px-2">KDA</th>
                <th className="text-center py-2 px-2">位置</th>
                <th className="text-center py-2 px-2">影响力</th>
                <th className="text-center py-2 px-2">时长</th>
                <th className="text-center py-2 px-2">物品</th>
                <th className="text-center py-2 px-2">徽章</th>
                <th className="text-left py-2 px-2">笔记</th>
              </tr>
            </thead>
            <tbody>
              {matches.map((m) => {
                const k = Number(m.adv_kills ?? m.kills);
                const d = Number(m.adv_deaths ?? m.deaths);
                const a = Number(m.adv_assists ?? m.assists);
                return (
                  <tr key={m.match_id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        {m.hero_icon && <img src={m.hero_icon} alt="" className="w-8 h-8 rounded" />}
                        <span className="text-xs">{m.hero_cn}</span>
                      </div>
                    </td>
                    <td className="text-center py-2 px-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${m.win === "Win" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                        {m.win === "Win" ? "胜" : "负"}
                      </span>
                    </td>
                    <td className="text-center py-2 px-2 text-xs">{k}/{d}/{a}</td>
                    <td className="text-center py-2 px-2 text-xs text-gray-400">{m.role_name}</td>
                    <td className="text-center py-2 px-2">
                      <span className={`text-xs font-bold ${m.impact_score >= 70 ? "text-yellow-400" : m.impact_score >= 40 ? "text-cyan-400" : "text-gray-400"}`}>
                        {m.impact_score}
                      </span>
                    </td>
                    <td className="text-center py-2 px-2 text-xs text-gray-400">{m.duration}</td>
                    <td className="py-2 px-2">
                      <div className="flex gap-0.5 justify-center">
                        {m.item_icons.filter(Boolean).map((url, i) => (
                          <img key={i} src={url} alt="" className="w-6 h-6 rounded" />
                        ))}
                        {m.item_neutral_icon && <img src={m.item_neutral_icon} alt="" className="w-6 h-6 rounded ring-1 ring-yellow-500/50" />}
                      </div>
                    </td>
                    <td className="text-center py-2 px-2">
                      {m.badges.map((b, i) => (
                        <span key={i} className="mr-1" title={b.text}>{b.icon}</span>
                      ))}
                    </td>
                    <td className="py-2 px-2 min-w-[120px]">
                      {editingNote === m.match_id ? (
                        <div className="flex gap-1">
                          <input
                            className="bg-white/10 border border-white/20 rounded px-1.5 py-0.5 text-xs flex-1 text-white"
                            value={noteText}
                            onChange={(e) => setNoteText(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSaveNote(m.match_id)}
                          />
                          <button onClick={() => handleSaveNote(m.match_id)} className="text-green-400 text-xs">✓</button>
                          <button onClick={() => setEditingNote(null)} className="text-red-400 text-xs">✕</button>
                        </div>
                      ) : (
                        <div
                          className="text-xs text-gray-400 cursor-pointer hover:text-white truncate max-w-[150px]"
                          onClick={() => { setEditingNote(m.match_id); setNoteText(m.note || ""); }}
                          title={m.note || "点击添加笔记"}
                        >
                          {m.note || "..."}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
