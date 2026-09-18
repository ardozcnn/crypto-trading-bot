import { useEffect, useState } from "react";
import { toast } from "sonner";
import { FlaskConical, Loader2 } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { signed, pnlClass, shortSymbol } from "@/lib/format";

const Metric = ({ label, base, cur, fmt = (v) => v, better = (a, b) => b > a, testId }) => {
  const improved = base != null && cur != null && better(base, cur);
  const worse = base != null && cur != null && better(cur, base);
  return (
    <div className="grid grid-cols-3 gap-2 items-baseline font-mono tabular-nums text-xs border-b border-white/5 py-1" data-testid={testId}>
      <span className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</span>
      <span className="text-zinc-400 text-right">{fmt(base ?? 0)}</span>
      <span className={`text-right font-semibold ${improved ? "text-profit" : worse ? "text-loss" : "text-white"}`}>{fmt(cur ?? 0)} {improved ? "▲" : worse ? "▼" : ""}</span>
    </div>
  );
};

const fmtD = (ms) => new Date(ms).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });

export const BacktestPanel = () => {
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);
  const running = st?.status === "running";

  useEffect(() => {
    let alive = true;
    const poll = () => api.backtestStatus().then((s) => alive && setSt(s)).catch(() => {});
    poll();
    const id = setInterval(poll, running ? 1500 : 8000);
    return () => { alive = false; clearInterval(id); };
  }, [running]);

  const run = async () => {
    setBusy(true);
    try {
      await api.backtestRun(30);
      toast.success("Backtest başlatıldı · 30 gün · 6 parite");
      setSt((s) => ({ ...(s || {}), status: "running", progress: {} }));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Başlatılamadı");
    } finally {
      setBusy(false);
    }
  };

  const r = st?.result;
  const b = r?.variants?.baseline;
  const c = r?.variants?.current;
  const curve = c && b ? mergeCurves(b.equity_curve, c.equity_curve) : [];

  return (
    <div className="h-full flex flex-col" data-testid="backtest-panel">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10 shrink-0">
        <div className="text-[11px] font-mono text-zinc-400" data-testid="backtest-meta">
          {r ? <>Son 30 gün · {r.candles.toLocaleString("en-US")} mum · {fmtD(r.from)} → {fmtD(r.to)} · {r.duration_sec}sn · çoklu sinyal stratejisi</> : "Henüz backtest yok · filtrelerin etkisini ölçmek için çalıştır"}
        </div>
        <Button data-testid="backtest-run-button" size="sm" disabled={busy || running} onClick={run} className="h-7 rounded-sm bg-[#00F0FF] hover:bg-[#08D9E6] text-black text-[11px] font-bold px-3">
          {running ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <FlaskConical className="w-3 h-3 mr-1" />} {running ? "Çalışıyor…" : "30 Gün Backtest"}
        </Button>
      </div>
      {running && (
        <div className="px-3 py-2 space-y-1 border-b border-white/10" data-testid="backtest-progress">
          {Object.entries(st.progress || {}).map(([s, p]) => (
            <div key={s} className="flex items-center gap-2 text-[10px] font-mono">
              <span className="w-12 text-zinc-400">{shortSymbol(s)}</span>
              <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden"><div className="h-full bg-[#00F0FF] transition-[width]" style={{ width: `${p}%` }} /></div>
              <span className="w-8 text-right text-zinc-500">{p}%</span>
            </div>
          ))}
        </div>
      )}
      {st?.status === "error" && <div className="p-3 text-xs font-mono text-red-400" data-testid="backtest-error">Hata: {st.error}</div>}
      {r && b && c && (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 p-3 overflow-auto scroll-thin">
          <div className="lg:col-span-4" data-testid="backtest-compare">
            <div className="grid grid-cols-3 gap-2 text-[10px] uppercase tracking-wider font-semibold pb-1 border-b border-white/10">
              <span className="text-zinc-500">Metrik</span><span className="text-right text-zinc-400">Eski Bot</span><span className="text-right text-[#00F0FF]">Yeni Bot</span>
            </div>
            <Metric testId="bt-pnl" label="Net PnL" base={b.pnl} cur={c.pnl} fmt={(v) => `${signed(v)} $`} />
            <Metric testId="bt-roi" label="ROI" base={b.roi_pct} cur={c.roi_pct} fmt={(v) => `${signed(v)}%`} />
            <Metric testId="bt-trades" label="İşlem" base={b.trades} cur={c.trades} better={() => false} />
            <Metric testId="bt-winrate" label="Kazanma" base={b.win_rate} cur={c.win_rate} fmt={(v) => `${v.toFixed(1)}%`} />
            <Metric testId="bt-pf" label="Profit Factor" base={b.profit_factor} cur={c.profit_factor} fmt={(v) => v.toFixed(2)} />
            <Metric testId="bt-avg" label="Ort. İşlem" base={b.avg_pnl} cur={c.avg_pnl} fmt={(v) => `${signed(v)} $`} />
            <Metric testId="bt-dd" label="Maks Düşüş" base={b.max_drawdown_pct} cur={c.max_drawdown_pct} fmt={(v) => `${v.toFixed(2)}%`} better={(a, bb) => bb < a} />
            <Metric testId="bt-worst" label="En Kötü İşlem" base={b.worst} cur={c.worst} fmt={(v) => `${signed(v)} $`} />
            <div className="mt-2 text-[10px] font-mono text-zinc-500 leading-relaxed" data-testid="backtest-verdict">
              {c.pnl > b.pnl
                ? <>Yeni filtreler 30 günde <span className="text-profit">{signed(c.pnl - b.pnl)} $</span> fark yarattı.</>
                : <>Yeni ayarlar bu dönemde <span className="text-loss">{signed(c.pnl - b.pnl)} $</span> daha düşük; filtreleri gevşetmeyi düşün.</>}
              {" "}Eski bot = filtresiz, skor 2.0, sabit TP/SL. Grid stratejisi backtest dışıdır.
            </div>
          </div>
          <div className="lg:col-span-5 min-h-[180px]" data-testid="backtest-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={curve} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <XAxis dataKey="t" tickFormatter={fmtD} stroke="#3f3f46" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} minTickGap={40} />
                <YAxis domain={["auto", "auto"]} stroke="#3f3f46" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} width={58} />
                <Tooltip contentStyle={{ background: "#121214", border: "1px solid rgba(255,255,255,0.1)", fontSize: 11, fontFamily: "JetBrains Mono" }} labelFormatter={(v) => new Date(v).toLocaleString("tr-TR")} />
                <ReferenceLine y={10000} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
                <Line type="monotone" dataKey="baseline" name="Eski" stroke="#71717a" dot={false} strokeWidth={1.5} connectNulls />
                <Line type="monotone" dataKey="current" name="Yeni" stroke="#00F0FF" dot={false} strokeWidth={2} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="lg:col-span-3 space-y-1" data-testid="backtest-symbols">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold pb-1 border-b border-white/10">Parite (Eski → Yeni)</div>
            {r.symbols.map((s) => {
              const bs = b.by_symbol.find((x) => x.symbol === s) || { pnl: 0, trades: 0 };
              const cs = c.by_symbol.find((x) => x.symbol === s) || { pnl: 0, trades: 0 };
              return (
                <div key={s} className="flex items-center justify-between font-mono tabular-nums text-[11px]" data-testid={`bt-sym-${s}`}>
                  <span className="text-zinc-300 w-12">{shortSymbol(s)}</span>
                  <span className={`${pnlClass(bs.pnl)} opacity-60`}>{signed(bs.pnl)} <span className="text-zinc-600">({bs.trades})</span></span>
                  <span className="text-zinc-600">→</span>
                  <span className={`font-semibold ${pnlClass(cs.pnl)}`}>{signed(cs.pnl)} <span className="text-zinc-600">({cs.trades})</span></span>
                </div>
              );
            })}
            <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold pt-2 pb-1 border-b border-white/10">Çıkış Sebebi (Yeni)</div>
            {c.exit_reasons.map((x) => (
              <div key={x.reason} className="flex items-center justify-between font-mono tabular-nums text-[11px]">
                <span className="text-zinc-400">{x.reason}</span>
                <span className={pnlClass(x.pnl)}>{x.trades}× · {signed(x.pnl)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {!r && !running && st?.status !== "error" && (
        <div className="flex-1 flex items-center justify-center text-xs font-mono text-zinc-600 bg-grid-pattern" data-testid="backtest-empty">Sonuç yok · "30 Gün Backtest" butonuna bas</div>
      )}
    </div>
  );
};

function mergeCurves(a, b) {
  const map = new Map();
  a.forEach((p) => map.set(p.t, { t: p.t, baseline: p.equity }));
  b.forEach((p) => map.set(p.t, { ...(map.get(p.t) || { t: p.t }), current: p.equity }));
  return [...map.values()].sort((x, y) => x.t - y.t);
}
