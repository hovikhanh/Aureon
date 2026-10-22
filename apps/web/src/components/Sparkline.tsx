"use client";
import { Line, LineChart, ResponsiveContainer } from "recharts";

/** Tiny trend line (06 §7.5). Data comes straight from the API `*_trend` series. */
export function Sparkline({ values, label, color = "var(--primary)" }: { values: number[]; label: string; color?: string }) {
  if (values.length < 2) return <div className="h-10" aria-hidden />;
  const data = values.map((v, i) => ({ i, v }));
  return (
    <div className="h-10 w-full" role="img" aria-label={label} data-testid="sparkline">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 2, bottom: 4, left: 2 }}>
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
