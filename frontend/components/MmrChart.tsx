"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";

interface Props {
  dates: string[];
  values: number[];
}

export default function MmrChart({ dates, values }: Props) {
  if (!dates.length) return null;

  const chartData = dates.map((d, i) => ({ date: d, mmr: values[i] }));
  const minMmr = Math.min(...values) - 50;
  const maxMmr = Math.max(...values) + 50;

  return (
    <div className="card">
      <h3 className="section-title">MMR 历史</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="mmrGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ffd700" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ffd700" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="date" stroke="#888" tick={{ fontSize: 11 }} />
            <YAxis domain={[minMmr, maxMmr]} stroke="#888" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} />
            <Area type="monotone" dataKey="mmr" stroke="#ffd700" fill="url(#mmrGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
