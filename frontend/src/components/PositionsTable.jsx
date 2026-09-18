import { X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtPrice, fmtUsd, signed, fmtPct, pnlClass, fmtTime, shortSymbol } from "@/lib/format";

const th = "text-[10px] uppercase tracking-wider text-zinc-500 h-8 font-semibold";
const num = "font-mono tabular-nums text-xs text-right";

export const PositionsTable = ({ positions, onChange }) => {
  const close = async (id) => {
    try {
      await api.closePosition(id);
      toast.success("Pozisyon kapatıldı");
      onChange();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Kapatılamadı");
    }
  };
  const closeAll = async () => {
    try {
      const r = await api.closeAll();
      toast.success(`${r.closed} pozisyon kapatıldı`);
      onChange();
    } catch {
      toast.error("Kapatılamadı");
    }
  };
  if (!positions.length) {
    return <div className="h-full flex items-center justify-center text-xs font-mono text-zinc-600 bg-grid-pattern" data-testid="positions-empty">Açık pozisyon yok · bot sinyal bekliyor</div>;
  }
  return (
    <Table data-testid="positions-table">
      <TableHeader className="sticky top-0 bg-[#121214] z-10">
        <TableRow className="border-white/10 hover:bg-transparent">
          <TableHead className={th}>Parite</TableHead>
          <TableHead className={th}>Yön</TableHead>
          <TableHead className={th}>Strateji</TableHead>
          <TableHead className={`${th} text-right`}>Giriş</TableHead>
          <TableHead className={`${th} text-right`}>Mark</TableHead>
          <TableHead className={`${th} text-right`}>TP / SL</TableHead>
          <TableHead className={`${th} text-right`}>Marj</TableHead>
          <TableHead className={`${th} text-right`}>PnL</TableHead>
          <TableHead className={`${th} text-right`}>ROE</TableHead>
          <TableHead className={th}>Açılış</TableHead>
          <TableHead className={`${th} text-right`}>
            <button data-testid="close-all-button" onClick={closeAll} className="text-red-400 hover:text-red-300 normal-case">Tümünü Kapat</button>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((p) => (
          <TableRow key={p.id} data-testid="position-row" className="border-white/5 hover:bg-white/[0.03] row-in">
            <TableCell className="font-mono text-xs font-semibold py-2">{shortSymbol(p.symbol)} <span className="text-zinc-500">{p.leverage}x</span></TableCell>
            <TableCell className="py-2"><span className={`rounded-sm px-1.5 py-0.5 text-[10px] font-mono font-bold ${p.side === "LONG" ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>{p.side}</span></TableCell>
            <TableCell className="py-2 text-[10px] font-mono uppercase text-zinc-400">{p.strategy === "grid" ? "GRID" : "SİNYAL"}</TableCell>
            <TableCell className={`${num} py-2`}>{fmtPrice(p.entry_price)}</TableCell>
            <TableCell className={`${num} py-2`}>{fmtPrice(p.mark_price)}</TableCell>
            <TableCell className={`${num} py-2`}><span className="text-emerald-400">{fmtPrice(p.tp)}</span> / <span className="text-red-400">{fmtPrice(p.trailing_sl ?? p.sl)}</span>{p.trailing_sl && <span className="text-[#00F0FF] ml-1">T</span>}</TableCell>
            <TableCell className={`${num} py-2`}>{fmtUsd(p.margin)}</TableCell>
            <TableCell className={`${num} py-2 font-semibold ${pnlClass(p.unrealized_pnl)}`}>{signed(p.unrealized_pnl)}</TableCell>
            <TableCell className={`${num} py-2 ${pnlClass(p.roe_pct)}`}>{fmtPct(p.roe_pct)}</TableCell>
            <TableCell className="py-2 font-mono text-[11px] text-zinc-500 tabular-nums">{fmtTime(p.opened_at)}</TableCell>
            <TableCell className="py-2 text-right">
              <button data-testid={`close-position-${p.id}`} onClick={() => close(p.id)} className="text-zinc-500 hover:text-red-400 transition-colors" title="Kapat"><X className="w-3.5 h-3.5 inline" /></button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
