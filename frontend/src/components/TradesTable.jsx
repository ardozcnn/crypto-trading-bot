import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtPrice, signed, fmtPct, pnlClass, fmtTime, fmtDuration, shortSymbol } from "@/lib/format";

const th = "text-[10px] uppercase tracking-wider text-zinc-500 h-8 font-semibold";
const num = "font-mono tabular-nums text-xs text-right py-1.5";

export const TradesTable = ({ trades }) => {
  if (!trades.length) {
    return <div className="h-full flex items-center justify-center text-xs font-mono text-zinc-600 bg-grid-pattern" data-testid="trades-empty">Henüz kapanan işlem yok</div>;
  }
  return (
    <Table data-testid="trades-table">
      <TableHeader className="sticky top-0 bg-[#121214] z-10">
        <TableRow className="border-white/10 hover:bg-transparent">
          <TableHead className={th}>Kapanış</TableHead>
          <TableHead className={th}>Parite</TableHead>
          <TableHead className={th}>Yön</TableHead>
          <TableHead className={`${th} text-right`}>Giriş</TableHead>
          <TableHead className={`${th} text-right`}>Çıkış</TableHead>
          <TableHead className={`${th} text-right`}>PnL</TableHead>
          <TableHead className={`${th} text-right`}>ROE</TableHead>
          <TableHead className={`${th} text-right`}>Süre</TableHead>
          <TableHead className={th}>Sebep</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.map((t) => (
          <TableRow key={t.id} data-testid="trade-row" className="border-white/5 hover:bg-white/[0.03]">
            <TableCell className="py-1.5 font-mono text-[11px] text-zinc-500 tabular-nums">{fmtTime(t.closed_at)}</TableCell>
            <TableCell className="py-1.5 font-mono text-xs font-semibold">{shortSymbol(t.symbol)} <span className="text-zinc-600 text-[10px]">{t.strategy === "grid" ? "G" : "S"}</span></TableCell>
            <TableCell className="py-1.5"><span className={`text-[10px] font-mono font-bold ${t.side === "LONG" ? "text-emerald-400" : "text-red-400"}`}>{t.side}</span></TableCell>
            <TableCell className={num}>{fmtPrice(t.entry_price)}</TableCell>
            <TableCell className={num}>{fmtPrice(t.exit_price)}</TableCell>
            <TableCell className={`${num} font-semibold ${pnlClass(t.pnl)}`}>{signed(t.pnl)}</TableCell>
            <TableCell className={`${num} ${pnlClass(t.pnl_pct)}`}>{fmtPct(t.pnl_pct, 1)}</TableCell>
            <TableCell className={`${num} text-zinc-400`}>{fmtDuration(t.duration_sec)}</TableCell>
            <TableCell className="py-1.5 text-[10px] font-mono text-zinc-400">{t.exit_reason}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
