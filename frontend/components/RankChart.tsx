"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { RankHistoryEntry } from "@/lib/types";

export default function RankChart({ data }: { data: RankHistoryEntry[] }) {
  if (!data.length) return null;

  const minTier = Math.min(...data.map((d) => d.tier)) - 2;
  const maxTier = Math.max(...data.map((d) => d.tier)) + 2;

  return (
    <div className="card">
      <h3 className="section-title">段位历史</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="date" stroke="#888" tick={{ fontSize: 11 }} />
            <YAxis
              domain={[minTier, maxTier]}
              stroke="#888"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => {
                const entry = data.find((d) => d.tier === v);
                return entry?.label || String(v);
              }}
            />
            <Tooltip
              contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }}
              formatter={(value) => {
                const entry = data.find((d) => d.tier === Number(value));
                return [entry?.label || String(value), "段位"];
              }}
            />
            <Line type="monotone" dataKey="tier" stroke="#ffd700" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
