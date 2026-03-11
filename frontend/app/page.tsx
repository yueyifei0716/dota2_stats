"use client";

import { useApi } from "@/hooks/useApi";
import { getDashboard } from "@/lib/api";
import ProfileCard from "@/components/ProfileCard";
import StatsOverview from "@/components/StatsOverview";
import MmrChart from "@/components/MmrChart";
import RankChart from "@/components/RankChart";
import RollingWinrate from "@/components/RollingWinrate";
import TimeAnalysis from "@/components/TimeAnalysis";
import RolePerformance from "@/components/RolePerformance";
import HeroStats from "@/components/HeroStats";
import HeroMatchups from "@/components/HeroMatchups";
import PeersSection from "@/components/PeersSection";
import RecentTrend from "@/components/RecentTrend";
import MatchTable from "@/components/MatchTable";
import UpdateButton from "@/components/UpdateButton";

export default function Home() {
  const { data, loading, error, refetch } = useApi(getDashboard);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-yellow-400 text-xl">加载中...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-400 text-xl">加载失败: {error || "无数据"}</div>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto px-5 py-5">
      <h1 className="text-center text-4xl font-bold text-yellow-400 mb-8 drop-shadow-lg">
        Dota 2 数据分析
      </h1>

      <div className="space-y-6">
        <ProfileCard profile={data.profile} />
        <StatsOverview data={data} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MmrChart dates={data.mmr.dates} values={data.mmr.values} />
          <RankChart data={data.rank_history} />
        </div>

        <RollingWinrate data={data.rolling_winrate} />
        <TimeAnalysis timeData={data.time_analysis} weekdayData={data.weekday_analysis} />
        <RolePerformance data={data.role_performance} />
        <HeroStats heroStats={data.hero_stats} bestHeroes={data.best_heroes} worstHeroes={data.worst_heroes} />
        <HeroMatchups heroes={data.matchup_heroes} />
        <PeersSection peers={data.peers} />
        <RecentTrend data={data.recent_trend} />
        <MatchTable allHeroes={data.all_heroes} />
      </div>

      <UpdateButton onUpdated={refetch} />
    </div>
  );
}
