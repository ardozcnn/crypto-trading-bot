import { useState } from "react";
import { Activity, Play, Square, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export const TopNav = ({ status, onChange }) => {
  const [busy, setBusy] = useState(false);
  const running = status?.running;

  const act = async (fn, msg) => {
    setBusy(true);
    try {
      await fn();
      toast.success(msg);
      onChange();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "İşlem başarısız");
    } finally {
      setBusy(false);
    }
  };

  return (
    <header className="h-14 border-b border-white/10 flex items-center justify-between px-4 bg-[#121214]" data-testid="top-nav">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-sm bg-[#00F0FF] flex items-center justify-center">
          <Activity className="w-5 h-5 text-black" strokeWidth={2.5} />
        </div>
        <div className="leading-tight">
          <div className="font-display font-extrabold tracking-tight text-base">SCALPX <span className="text-[#00F0FF]">TERMINAL</span></div>
          <div className={`text-[10px] font-mono uppercase ${status?.live ? "text-red-400 font-bold" : "text-zinc-500"}`} data-testid="mode-label">{status?.live ? "● " : ""}{status?.mode || "PAPER · FUTURES TESTNET"}</div>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs font-mono" data-testid="bot-status-indicator">
          <span className={`w-2.5 h-2.5 rounded-full ${running ? "bg-[#00F0FF] pulse-dot" : "bg-zinc-600"}`} />
          <span className={running ? "text-[#00F0FF]" : "text-zinc-400"}>{running ? "BOT ÇALIŞIYOR" : "BOT DURDU"}</span>
        </div>
        {running ? (
          <Button data-testid="bot-stop-button" disabled={busy} onClick={() => act(api.stop, "Bot durduruldu")} className="rounded-sm bg-red-500 hover:bg-red-600 text-white h-9 px-4 font-display font-bold uppercase text-xs">
            <Square className="w-3.5 h-3.5 mr-1.5" /> Botu Durdur
          </Button>
        ) : (
          <Button data-testid="bot-start-button" disabled={busy} onClick={() => act(api.start, "Bot başlatıldı")} className="rounded-sm bg-[#00F0FF] hover:bg-[#08D9E6] text-black h-9 px-4 font-display font-bold uppercase text-xs">
            <Play className="w-3.5 h-3.5 mr-1.5" /> Botu Başlat
          </Button>
        )}
        <Button data-testid="bot-reset-button" variant="outline" disabled={busy} onClick={() => { if (window.confirm("Tüm işlem geçmişi silinip bakiye sıfırlanacak. Emin misiniz?")) act(api.reset, "Hesap sıfırlandı"); }} className="rounded-sm border-white/15 bg-transparent hover:bg-white/5 text-zinc-300 h-9 px-3 text-xs">
          <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Sıfırla
        </Button>
      </div>
    </header>
  );
};
