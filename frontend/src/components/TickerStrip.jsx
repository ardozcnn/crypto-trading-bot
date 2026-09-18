import { fmtPrice, fmtPct, shortSymbol } from "@/lib/format";

export const TickerStrip = ({ tickers, onSelect }) => {
  if (!tickers.length) {
    return <div className="h-10 border-b border-white/5 bg-[#09090b] flex items-center px-4 text-xs font-mono text-zinc-600" data-testid="ticker-strip">Piyasa verisi yükleniyor…</div>;
  }
  const items = [...tickers, ...tickers];
  return (
    <div className="h-10 border-b border-white/5 bg-[#09090b] flex items-center overflow-hidden text-xs font-mono" data-testid="ticker-strip">
      <div className="ticker-track flex items-center whitespace-nowrap">
        {items.map((t, i) => (
          <button key={`${t.symbol}-${i}`} onClick={() => onSelect(t.symbol)} data-testid={`ticker-${t.symbol}`} className="flex items-center gap-2 px-5 h-10 hover:bg-white/5 transition-colors border-r border-white/5">
            <span className="text-zinc-300 font-semibold">{shortSymbol(t.symbol)}</span>
            <span className="text-white tabular-nums">{fmtPrice(t.price)}</span>
            <span className={`tabular-nums ${t.change_pct >= 0 ? "text-profit" : "text-loss"}`}>{fmtPct(t.change_pct)}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
