import { Wallet, TrendingUp, Target, Zap, Layers, Percent } from "lucide-react";
import { fmtUsd, signed, fmtPct, pnlClass } from "@/lib/format";

const Card = ({ label, value, sub, icon: Icon, valueClass = "text-white", testId }) => (
  <div className="panel p-3 justify-between min-h-[84px]" data-testid={testId}>
    <div className="flex items-center justify-between">
      <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">{label}</span>
      <Icon className="w-3.5 h-3.5 text-zinc-600" />
    </div>
    <div className={`font-mono tabular-nums text-xl font-semibold ${valueClass}`}>{value}</div>
    {sub && <div className="text-[11px] font-mono text-zinc-500 tabular-nums">{sub}</div>}
  </div>
);

export const StatsCards = ({ stats }) => {
  const s = stats || {};
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3" data-testid="stats-cards">
      <Card testId="stat-balance" label="Hesap Bakiyesi" icon={Wallet} value={`${fmtUsd(s.equity)} $`} sub={`Serbest: ${fmtUsd(s.balance)} · Marj: ${fmtUsd(s.margin_used)}`} />
      <Card testId="stat-today-pnl" label="Günlük PnL" icon={Zap} value={`${signed(s.today_pnl)} $`} valueClass={pnlClass(s.today_pnl)} sub={`${s.today_trades ?? 0} işlem bugün`} />
      <Card testId="stat-realized" label="Toplam Kâr/Zarar" icon={TrendingUp} value={`${signed(s.realized_pnl)} $`} valueClass={pnlClass(s.realized_pnl)} sub={`ROI ${fmtPct(s.roi_pct ?? 0)}`} />
      <Card testId="stat-unrealized" label="Açık PnL" icon={Layers} value={`${signed(s.unrealized_pnl)} $`} valueClass={pnlClass(s.unrealized_pnl)} sub={`${s.open_positions ?? 0} açık pozisyon`} />
      <Card testId="stat-winrate" label="Kazanma Oranı" icon={Target} value={`${(s.win_rate ?? 0).toFixed(1)}%`} valueClass={s.win_rate >= 50 ? "text-profit" : "text-white"} sub={`${s.wins ?? 0}K / ${s.losses ?? 0}Z · ${s.total_trades ?? 0} toplam`} />
      <Card testId="stat-pf" label="Profit Factor" icon={Percent} value={(s.profit_factor ?? 0).toFixed(2)} valueClass={s.profit_factor >= 1 ? "text-profit" : "text-white"} sub={`En iyi ${signed(s.best_trade)} · En kötü ${signed(s.worst_trade)}`} />
    </div>
  );
};
