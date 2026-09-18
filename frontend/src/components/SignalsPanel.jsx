import { fmtPrice, shortSymbol } from "@/lib/format";

const Vote = ({ label, v }) => (
  <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-mono uppercase border ${v > 0 ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10" : v < 0 ? "border-red-500/40 text-red-400 bg-red-500/10" : "border-white/10 text-zinc-500"}`}>
    {label}{v > 0 ? "+" : ""}{v || 0}
  </span>
);

export const SignalsPanel = ({ signals, positions, onSelect }) => (
  <div className="panel" data-testid="signals-panel">
    <div className="panel-header">
      <span className="panel-title">Canlı Sinyal Tarayıcı</span>
      <span className="text-[10px] font-mono text-zinc-500">RSI · MACD · BB · EMA → skor ≥ eşik + 15m trend · ADX · hacim filtresi</span>
    </div>
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 divide-x divide-y divide-white/5">
      {signals.length === 0 && <div className="col-span-6 p-4 text-xs font-mono text-zinc-600">Sinyaller hesaplanıyor…</div>}
      {signals.map((s) => {
        const inPos = positions.find((p) => p.symbol === s.symbol);
        return (
          <button key={s.symbol} onClick={() => onSelect(s.symbol)} data-testid={`signal-${s.symbol}`} className="text-left p-2.5 hover:bg-white/[0.03] transition-colors">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-semibold">{shortSymbol(s.symbol)}</span>
              <span className={`font-mono tabular-nums text-xs font-bold ${s.score > 0 ? "text-profit" : s.score < 0 ? "text-loss" : "text-zinc-500"}`}>{s.score > 0 ? "+" : ""}{s.score}</span>
            </div>
            <div className="flex items-center justify-between font-mono tabular-nums text-[11px] mt-0.5">
              <span className="text-zinc-400">{fmtPrice(s.close)}</span>
              <span className="text-[9px] text-zinc-500" data-testid={`signal-meta-${s.symbol}`}>
                {s.htf_trend && <span className={s.htf_trend === "UP" ? "text-profit" : s.htf_trend === "DOWN" ? "text-loss" : "text-zinc-500"}>15m {s.htf_trend === "UP" ? "▲" : s.htf_trend === "DOWN" ? "▼" : "▬"}</span>}
                {" "}ADX {Math.round(s.adx ?? 0)} · V {(s.vol_ratio ?? 1).toFixed(1)}x
              </span>
            </div>
            <div className="flex flex-wrap gap-1 mt-1.5">
              <Vote label="RSI" v={s.votes.rsi} />
              <Vote label="MACD" v={s.votes.macd} />
              <Vote label="BB" v={s.votes.bb} />
              <Vote label="EMA" v={s.votes.ema} />
            </div>
            <div className="mt-1.5 text-[10px] font-mono truncate" data-testid={`signal-state-${s.symbol}`}>
              {inPos ? <span className={inPos.side === "LONG" ? "text-profit" : "text-loss"}>● {inPos.side} AÇIK</span>
                : s.blacklisted ? <span className="text-red-400">⛔ kara listede</span>
                : s.side ? <span className={s.side === "LONG" ? "text-profit" : "text-loss"}>▶ {s.side} SİNYALİ</span>
                : s.blocked ? <span className="text-amber-400" title={s.blocked}>⊘ {s.raw_side} engellendi · {s.blocked}</span>
                : <span className="text-zinc-600">bekliyor</span>}
            </div>
          </button>
        );
      })}
    </div>
  </div>
);
