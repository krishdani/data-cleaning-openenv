"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine, Area, AreaChart } from "recharts";

interface RewardChartProps {
  rewards: number[];
}

export function RewardChart({ rewards }: RewardChartProps) {
  if (!rewards || rewards.length === 0) {
    return (
      <div className="flex items-center justify-center h-52 text-sm border border-zinc-900 rounded-lg text-zinc-600">
        Run the cleaning pipeline to see reward progression
      </div>
    );
  }

  const data = rewards.map((r, i) => ({
    step: `Step ${i + 1}`,
    reward: parseFloat(r.toFixed(2)),
  }));

  return (
    <div className="w-full h-52">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="rewardGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="step"
            stroke="#333"
            tick={{ fill: "#666", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#222" }}
          />
          <YAxis
            domain={[-1, 1]}
            stroke="#333"
            tick={{ fill: "#666", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#222" }}
            ticks={[-1, -0.5, 0, 0.5, 1]}
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
            dataKey="reward"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#rewardGrad)"
            dot={{ r: 4, fill: "#10b981", stroke: "#000", strokeWidth: 2 }}
            activeDot={{ r: 6, fill: "#34d399", stroke: "#000" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
