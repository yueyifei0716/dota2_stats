"use client";

import { Peer } from "@/lib/types";

export default function PeersSection({ peers }: { peers: Peer[] }) {
  if (!peers.length) return null;

  return (
    <div className="card">
      <h3 className="section-title">常用队友</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {peers.map((p, i) => {
          const wr = p.with_games > 0 ? ((p.with_win / p.with_games) * 100).toFixed(1) : "0.0";
          return (
            <div key={i} className="stat-box flex items-center gap-3">
              {p.avatarfull && <img src={p.avatarfull} alt="" className="w-8 h-8 rounded-full" />}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{p.personaname}</div>
                <div className="text-xs text-gray-400">
                  {p.with_games}场 · <span className={Number(wr) >= 50 ? "text-green-400" : "text-red-400"}>{wr}%</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
