import { useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { signed, pnlClass } from "@/lib/format";

const th = "text-[10px] uppercase tracking-wider text-zinc-500 h-8 font-semibold";
const num = "font-mono tabular-nums text-xs text-right py-1.5";
const fmtDay = (d) => new Date(`${d}T00:00:00Z`).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", weekday: "short" });

export const DailyReport = ({ refreshKey }) => {
  const [rows, setRows] = useState(null);
  useEffect(() => {
    api.dailyReport().then(setRows).catch(() => setRows([]));
  }, [refreshKey]);
  if (!rows) return <div className="p-4 text-xs font-mono text-zinc-600">Yükleniyor…</div>;
  if (!rows.length) return <div className="h-full flex items-center justify-center text-xs font-mono text-zinc-600 bg-grid-pattern" data-testid="daily-empty">Henüz günlük veri yok</div>;
  const max = Math.max(...rows.map((r) => Math.abs(r.pnl)), 1);
  return (
    <Table data-testid="daily-report-table">
      <TableHeader className="sticky top-0 bg-[#121214] z-10">
        <TableRow className="border-white/10 hover:bg-transparent">
          <TableHead className={th}>Gün</TableHead>
          <TableHead className={`${th} text-right`}>İşlem</TableHead>
          <TableHead className={`${th} text-right`}>Kazanç %</TableHead>
          <TableHead className={`${th} text-right`}>Grid</TableHead>
          <TableHead className={`${th} text-right`}>Çoklu</TableHead>
          <TableHead className={`${th} text-right`}>Komisyon</TableHead>
          <TableHead className={`${th} text-right`}>Gün PnL</TableHead>
          <TableHead className={`${th} w-40`}></TableHead>
          <TableHead className={`${th} text-right`}>Kümülatif</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.date} data-testid={`daily-row-${r.date}`} className="border-white/5 hover:bg-white/[0.03]">
            <TableCell className="py-1.5 font-mono text-xs">{fmtDay(r.date)}</TableCell>
            <TableCell className={`${num} text-zinc-300`}>{r.trades} <span className="text-zinc-600">({r.wins}K)</span></TableCell>
            <TableCell className={`${num} ${r.win_rate >= 50 ? "text-profit" : "text-zinc-400"}`}>{r.win_rate.toFixed(0)}%</TableCell>
            <TableCell className={`${num} ${pnlClass(r.grid_pnl)}`}>{signed(r.grid_pnl)}</TableCell>
            <TableCell className={`${num} ${pnlClass(r.multi_pnl)}`}>{signed(r.multi_pnl)}</TableCell>
            <TableCell className={`${num} text-zinc-500`}>-{r.fees.toFixed(2)}</TableCell>
            <TableCell className={`${num} font-semibold ${pnlClass(r.pnl)}`}>{signed(r.pnl)} $</TableCell>
            <TableCell className="py-1.5">
              <div className="h-2 w-full relative">
                <div className="absolute inset-y-0 left-1/2 w-px bg-white/15" />
                <div className={`absolute inset-y-0 ${r.pnl >= 0 ? "left-1/2 bg-emerald-500/70" : "right-1/2 bg-red-500/70"}`} style={{ width: `${Math.abs(r.pnl) / max * 50}%` }} />
              </div>
            </TableCell>
            <TableCell className={`${num} ${pnlClass(r.cumulative)}`}>{signed(r.cumulative)} $</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
