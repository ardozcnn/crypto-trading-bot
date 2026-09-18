import { Clock, GitCompareArrows, ShieldCheck, ShieldAlert } from "lucide-react";
import { fmtDuration, signed, pnlClass, shortSymbol } from "@/lib/format";

const Box = ({ title, icon: Icon, children, testId, accent }) => (
  <div className="panel p-3 gap-2" data-testid={testId}>
    <div className="flex items-center justify-between">
      <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">{title}</span>
      <Icon className={`w-3.5 h-3.5 ${accent || "text-zinc-600"}`} />
    </div>
    {children}
  </div>
);

const StratRow = ({ name, p, testId }) => (
  <div className="grid grid-cols-5 gap-2 items-baseline font-mono tabular-nums text-[11px]" data-testid={testId}>
    <span className="font-display font-bold text-xs text-zinc-200">{name}</span>
    <span className={`text-sm font-semibold ${pnlClass(p?.pnl)}`}>{signed(p?.pnl ?? 0)} $</span>
    <span className="text-zinc-400">{p?.trades ?? 0} işlem</span>
    <span className={p?.win_rate >= 50 ? "text-profit" : "text-zinc-400"}>%{(p?.win_rate ?? 0).toFixed(0)} kazanç</span>
    <span className="text-zinc-400">PF {(p?.profit_factor ?? 0).toFixed(2)}</span>
  </div>
);

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");

export const PerformancePanel = ({ stats, running }) => {
  const u = stats?.uptime || {};
  const b = stats?.by_strategy || {};
  const p = stats?.protection || {};
  const winner = (b.grid?.pnl ?? 0) >= (b.multi?.pnl ?? 0) ? "Grid" : "Çoklu Sinyal";
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="performance-panel">
      <Box title="Aktif Süre" icon={Clock} testId="uptime-card" accent={running ? "text-[#00F0FF]" : undefined}>
        <div className="flex items-baseline gap-2">
          <span className="font-mono tabular-nums text-xl font-semibold text-white" data-testid="uptime-total">{fmtDuration(u.total_active_sec ?? 0)}</span>
          <span className="text-[10px] text-zinc-500 uppercase">toplam çalışma</span>
        </div>
        <div className="text-[11px] font-mono text-zinc-500 tabular-nums space-y-0.5">
          <div data-testid="uptime-session">Bu oturum: <span className={running ? "text-[#00F0FF]" : "text-zinc-400"}>{running ? fmtDuration(u.session_sec ?? 0) : "durdu"}</span></div>
          <div data-testid="uptime-first">İlk başlatma: {fmtDate(u.first_started_at)} · {u.calendar_days ?? 0} takvim günü</div>
        </div>
      </Box>
      <Box title="Strateji Karşılaştırma" icon={GitCompareArrows} testId="strategy-compare-card">
        <StratRow name="GRID" p={b.grid} testId="strategy-grid-row" />
        <StratRow name="ÇOKLU" p={b.multi} testId="strategy-multi-row" />
        <div className="text-[10px] font-mono text-zinc-500">En kârlı: <span className="text-[#00F0FF]">{winner}</span> · ort. işlem grid {signed(b.grid?.avg_pnl ?? 0)} / çoklu {signed(b.multi?.avg_pnl ?? 0)}</div>
      </Box>
      <Box title="Risk Koruması" icon={p.halted ? ShieldAlert : ShieldCheck} testId="protection-card" accent={p.halted ? "text-red-400" : "text-emerald-500"}>
        <div className="flex items-baseline gap-2">
          <span className={`font-mono tabular-nums text-xl font-semibold ${pnlClass(p.day_change_pct)}`} data-testid="protection-day-change">{p.day_change_pct >= 0 ? "+" : ""}{(p.day_change_pct ?? 0).toFixed(2)}%</span>
          <span className="text-[10px] text-zinc-500 uppercase">bugün · limit −{p.daily_loss_limit_pct ?? 0}%</span>
        </div>
        <div className="text-[11px] font-mono tabular-nums" data-testid="protection-status">
          {p.halted ? <span className="text-red-400">● GÜNLÜK LİMİT AŞILDI — yeni işlem yok</span> : <span className="text-emerald-500">● Aktif · gün başı {(p.day_start_equity ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 })} $</span>}
        </div>
        <div className="flex flex-wrap gap-1" data-testid="protection-blacklist">
          {(p.blacklist || []).length === 0 && <span className="text-[10px] font-mono text-zinc-600">Kara liste boş</span>}
          {(p.blacklist || []).map((x) => (
            <span key={x.symbol} className="rounded-full px-1.5 py-0.5 text-[9px] font-mono border border-red-500/40 text-red-400 bg-red-500/10" data-testid={`blacklist-${x.symbol}`}>
              {shortSymbol(x.symbol)} · {new Date(x.until).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}'e kadar
            </span>
          ))}
        </div>
      </Box>
    </div>
  );
};
