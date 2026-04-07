"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine, Area, AreaChart } from "recharts";

interface RewardChartProps {
  rewards?: number[];
  data?: { name: string; points: number }[];
  domain?: [number, number];
  color?: string;
}

export function RewardChart({ rewards, data: customData, domain, color = "#10b981" }: RewardChartProps) {
  const chartData = customData || (rewards || []).map((r, i) => ({
    name: `Step ${i + 1}`,
    points: parseFloat(r.toFixed(2)),
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-52 text-sm border border-zinc-900 rounded-lg text-zinc-600">
        Run analysis to see metric progression
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.15} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="name"
            stroke="#333"
            tick={{ fill: "#666", fontSize: 9 }}
            tickLine={false}
            axisLine={{ stroke: "#222" }}
          />
          <YAxis
            domain={domain || [-1, 1]}
            stroke="#333"
            tick={{ fill: "#666", fontSize: 9 }}
            tickLine={false}
            axisLine={{ stroke: "#222" }}
          />
          <ReferenceLine y={0} stroke="#333" strokeDasharray="3 3" />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0a0a0a",
              border: "1px solid #222",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            itemStyle={{ color: "#ededed" }}
            labelStyle={{ color: "#888" }}
          />
          <Area
            type="monotone"
            dataKey="points"
            stroke={color}
            strokeWidth={2}
            fill="url(#chartGrad)"
            dot={{ r: 3, fill: color, stroke: "#000", strokeWidth: 1 }}
            activeDot={{ r: 5, fill: color, stroke: "#000" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
