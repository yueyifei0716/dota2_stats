"use client";

import { Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Line } from "recharts";
import { TimeEntry } from "@/lib/types";

function AnalysisChart({ data, title }: { data: TimeEntry[]; title: string }) {
  if (!data.length) return null;

  return (
    <div className="card">
      <h3 className="section-title">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="label" stroke="#888" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" stroke="#4fc3f7" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
            <YAxis yAxisId="right" orientation="right" stroke="#ffd700" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }} />
            <Bar yAxisId="left" dataKey="winrate" fill="#4fc3f7" fillOpacity={0.7} name="胜率 %" radius={[4, 4, 0, 0]} />
            <Line yAxisId="right" type="monotone" dataKey="games" stroke="#ffd700" strokeWidth={2} name="场次" dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function TimeAnalysis({ timeData, weekdayData }: { timeData: TimeEntry[]; weekdayData: TimeEntry[] }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <AnalysisChart data={timeData} title="时段分析" />
      <AnalysisChart data={weekdayData} title="星期分析" />
    </div>
  );
}
