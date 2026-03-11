"use client";

import { Profile } from "@/lib/types";

export default function ProfileCard({ profile }: { profile: Profile }) {
  const winRate = profile.total_wins + profile.total_losses > 0
    ? ((profile.total_wins / (profile.total_wins + profile.total_losses)) * 100).toFixed(1)
    : "0.0";

  return (
    <div className="card">
      <div className="flex items-center gap-6 flex-wrap">
        <h2 className="text-2xl font-bold text-white">{profile.username || "玩家"}</h2>
        <div className="flex items-center gap-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-gray-900 px-4 py-1.5 rounded-full font-bold text-sm">
          {profile.rank_icon && (
            <img src={profile.rank_icon} alt="" className="w-6 h-6" />
          )}
          <span>{profile.rank_name || "未校准"}</span>
        </div>
        {profile.current_mmr > 0 && (
          <span className="text-yellow-400 font-bold text-lg">MMR: {profile.current_mmr}</span>
        )}
        <div className="ml-auto flex gap-6 text-sm">
          <span className="text-green-400">{profile.total_wins} 胜</span>
          <span className="text-red-400">{profile.total_losses} 负</span>
          <span className="text-yellow-400">{winRate}%</span>
        </div>
      </div>
    </div>
  );
}
