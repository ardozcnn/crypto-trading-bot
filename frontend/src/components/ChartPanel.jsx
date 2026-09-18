import { useMemo } from "react";
import { ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from "recharts";
import { useKlines } from "@/hooks/useBot";
import { fmtPrice, fmtTime, shortSymbol } from "@/lib/format";

const IndicatorPill = ({ label, value, tone = "zinc" }) => (
  <span className={`rounded-full px-2 py-0.5 text-[10px] uppercase font-mono border ${tone === "up" ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10" : tone === "down" ? "border-red-500/40 text-red-400 bg-red-500/10" : "border-white/10 text-zinc-400"}`}>
    {label} <span className="tabular-nums font-semibold">{value}</span>
  </span>
);

export const ChartPanel = ({ symbol, setSymbol, symbols, positions }) => {
  const data = useKlines(symbol);
  const candles = useMemo(() => (data?.candles || []).map((c) => ({ ...c, time: fmtTime(new Date(c.t).toISOString()) })), [data]);
  const last = candles[candles.length - 1];
  const domain = useMemo(() => {
    if (!candles.length) return ["auto", "auto"];
    const vals = candles.flatMap((c) => [c.l, c.h, c.bb_upper, c.bb_lower]).filter((v) => v != null);
    const min = Math.min(...vals), max = Math.max(...vals), pad = (max - min) * 0.08;
    return [min - pad, max + pad];
  }, [candles]);
  const pos = positions.filter((p) => p.symbol === symbol);
  const rsiTone = last ? (last.rsi < 35 ? "up" : last.rsi > 65 ? "down" : "zinc") : "zinc";

  return (
    <div className="panel h-[400px]" data-testid="chart-panel">
      <div className="panel-header">
        <div className="flex items-center gap-1 overflow-x-auto scroll-thin">
          {symbols.map((s) => (
            <button key={s} onClick={() => setSymbol(s)} data-testid={`chart-symbol-${s}`} className={`px-2.5 h-7 text-xs font-mono font-semibold rounded-sm transition-colors ${s === symbol ? "bg-[#00F0FF]/15 text-[#00F0FF]" : "text-zinc-400 hover:text-white hover:bg-white/5"}`}>
              {shortSymbol(s)}
            </button>
          ))}
        </div>
        {last && (
          <div className="flex items-center gap-2">
            <span className="font-mono tabular-nums text-sm font-semibold" data-testid="chart-last-price">{fmtPrice(last.c)}</span>
            <IndicatorPill label="RSI" value={last.rsi?.toFixed(1)} tone={rsiTone} />
            <IndicatorPill label="MACD" value={last.macd_hist?.toFixed(3)} tone={last.macd_hist > 0 ? "up" : "down"} />
            <IndicatorPill label="EMA" value={last.ema_fast > last.ema_slow ? "BULL" : "BEAR"} tone={last.ema_fast > last.ema_slow ? "up" : "down"} />
          </div>
        )}
      </div>
      <div className="flex-1 bg-grid-pattern">
        {candles.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={candles} margin={{ top: 12, right: 8, left: 0, bottom: 4 }}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00F0FF" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#00F0FF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="time" tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={false} minTickGap={40} />
              <YAxis domain={domain} orientation="right" tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} tickLine={false} axisLine={false} tickFormatter={fmtPrice} width={70} />
              <Tooltip contentStyle={{ background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 2, fontFamily: "JetBrains Mono", fontSize: 11 }} labelStyle={{ color: "#a1a1aa" }} formatter={(v, n) => [fmtPrice(v), n]} />
              <Area type="monotone" dataKey="bb_upper" stroke="rgba(112,0,255,0.5)" strokeDasharray="3 3" fill="none" dot={false} name="BB Üst" isAnimationActive={false} />
              <Area type="monotone" dataKey="bb_lower" stroke="rgba(112,0,255,0.5)" strokeDasharray="3 3" fill="none" dot={false} name="BB Alt" isAnimationActive={false} />
              <Area type="monotone" dataKey="c" stroke="#00F0FF" strokeWidth={1.6} fill="url(#priceFill)" dot={false} name="Fiyat" isAnimationActive={false} />
              <Line type="monotone" dataKey="ema_fast" stroke="#10b981" strokeWidth={1} dot={false} name="EMA 9" isAnimationActive={false} />
              <Line type="monotone" dataKey="ema_slow" stroke="#f59e0b" strokeWidth={1} dot={false} name="EMA 21" isAnimationActive={false} />
              {pos.map((p) => (
                <ReferenceLine key={p.id} y={p.entry_price} stroke={p.side === "LONG" ? "#10b981" : "#ef4444"} strokeDasharray="4 2" label={{ value: `${p.side} ${fmtPrice(p.entry_price)}`, fill: p.side === "LONG" ? "#10b981" : "#ef4444", fontSize: 10, position: "insideLeft", fontFamily: "JetBrains Mono" }} />
              ))}
              {data?.grid?.buy?.map((lvl, i) => <ReferenceLine key={`b${i}`} y={lvl} stroke="rgba(16,185,129,0.25)" strokeDasharray="2 4" />)}
              {data?.grid?.sell?.map((lvl, i) => <ReferenceLine key={`s${i}`} y={lvl} stroke="rgba(239,68,68,0.25)" strokeDasharray="2 4" />)}
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-xs font-mono text-zinc-600">Grafik yükleniyor…</div>
        )}
      </div>
    </div>
  );
};
