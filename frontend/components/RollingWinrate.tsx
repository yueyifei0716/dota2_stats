"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { RollingWinrateEntry } from "@/lib/types";

export default function RollingWinrate({ data }: { data: RollingWinrateEntry[] }) {
  if (!data.length) return null;

  return (
    <div className="card">
      <h3 className="section-title">滚动胜率 (10场窗口)</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="index" stroke="#888" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 100]} stroke="#888" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
            <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} formatter={(v) => [`${v}%`, "胜率"]} />
            <ReferenceLine y={50} stroke="#666" strokeDasharray="5 5" />
            <Line type="monotone" dataKey="winrate" stroke="#4fc3f7" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
