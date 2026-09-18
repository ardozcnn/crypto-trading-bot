import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from "recharts";
import { fmtUsd, fmtTime } from "@/lib/format";

export const EquityChart = ({ equity, initial }) => {
  if (!equity.length) {
    return <div className="h-full flex items-center justify-center text-xs font-mono text-zinc-600 bg-grid-pattern" data-testid="equity-empty">Bot çalışırken bakiye eğrisi burada oluşur</div>;
  }
  const data = equity.map((e) => ({ ...e, time: fmtTime(e.t) }));
  const last = data[data.length - 1].equity;
  const up = last >= (initial ?? data[0].equity);
  const color = up ? "#10b981" : "#ef4444";
  return (
    <div className="h-full" data-testid="equity-chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="eqFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
          <XAxis dataKey="time" tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={false} minTickGap={50} />
          <YAxis domain={["auto", "auto"]} orientation="right" tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={false} tickFormatter={(v) => fmtUsd(v, 0)} width={64} />
          <Tooltip contentStyle={{ background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 2, fontFamily: "JetBrains Mono", fontSize: 11 }} formatter={(v, n) => [`${fmtUsd(v)} $`, n === "equity" ? "Toplam" : "Serbest"]} />
          {initial && <ReferenceLine y={initial} stroke="rgba(255,255,255,0.2)" strokeDasharray="4 4" />}
          <Area type="monotone" dataKey="equity" stroke={color} strokeWidth={1.6} fill="url(#eqFill)" dot={false} isAnimationActive={false} />
          <Area type="monotone" dataKey="balance" stroke="rgba(0,240,255,0.5)" strokeWidth={1} fill="none" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
