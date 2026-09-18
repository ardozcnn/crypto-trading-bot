import { fmtTime, shortSymbol } from "@/lib/format";

const tone = {
  trade: "text-[#00F0FF]",
  win: "text-emerald-400",
  loss: "text-red-400",
  warn: "text-amber-400",
  error: "text-red-500",
  info: "text-zinc-300",
};

export const ActivityLog = ({ logs }) => (
  <div className="panel h-full" data-testid="activity-log">
    <div className="panel-header">
      <span className="panel-title">Sinyal / Bot Logları</span>
      <span className="text-[10px] font-mono text-zinc-500 tabular-nums">{logs.length} kayıt</span>
    </div>
    <div className="flex-1 overflow-auto scroll-thin font-mono text-[11px] leading-relaxed">
      {logs.length === 0 && <div className="p-4 text-zinc-600">Henüz log yok. Botu başlatın.</div>}
      {logs.map((l) => (
        <div key={l.id} data-testid="log-row" className="flex gap-2 px-3 py-1 border-b border-white/[0.04] hover:bg-white/[0.02] row-in">
          <span className="text-zinc-600 tabular-nums shrink-0">{fmtTime(l.ts)}</span>
          {l.symbol && <span className="text-zinc-400 shrink-0 w-12">{shortSymbol(l.symbol)}</span>}
          <span className={`${tone[l.level] || "text-zinc-300"} break-words`}>{l.msg}</span>
        </div>
      ))}
    </div>
  </div>
);
