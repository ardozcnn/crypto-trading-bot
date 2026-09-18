import { useEffect, useState } from "react";
import { toast } from "sonner";
import { KeyRound, Trash2, PlugZap, Radio } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fmtUsd, signed, pnlClass, shortSymbol } from "@/lib/format";

export const LiveSettings = ({ onChange }) => {
  const [st, setSt] = useState(null);
  const [key, setKey] = useState("");
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => api.liveStatus().then(setSt).catch(() => {});
  useEffect(() => { load(); }, []);

  const act = async (fn, ok) => {
    setBusy(true);
    try {
      await fn();
      toast.success(ok);
      await load();
      onChange?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "İşlem başarısız");
      await load();
    } finally {
      setBusy(false);
    }
  };

  if (!st) return <div className="text-xs font-mono text-zinc-600">Yükleniyor…</div>;
  const live = st.mode === "live";
  const acc = st.account;

  return (
    <div className="space-y-3" data-testid="live-settings">
      <div className={`border rounded-sm p-2.5 flex items-center justify-between ${live ? "border-red-500/50 bg-red-500/5" : "border-white/10"}`} data-testid="live-mode-box">
        <div>
          <div className="text-xs font-semibold flex items-center gap-1.5"><Radio className={`w-3.5 h-3.5 ${live ? "text-red-400" : "text-zinc-500"}`} /> {live ? "CANLI TESTNET MODU" : "PAPER (SİMÜLASYON) MODU"}</div>
          <div className="text-[10px] text-zinc-500">{live ? "Emirler Binance Testnet hesabına gerçekten gönderiliyor" : "Emirler sanal bakiye üzerinde simüle ediliyor"}</div>
        </div>
        {live ? (
          <Button data-testid="live-mode-paper-button" size="sm" disabled={busy} onClick={() => act(() => api.liveMode("paper"), "PAPER moduna geçildi")} className="h-7 rounded-sm bg-zinc-700 hover:bg-zinc-600 text-white text-[11px] px-3">Paper'a Dön</Button>
        ) : (
          <Button data-testid="live-mode-live-button" size="sm" disabled={busy || !st.configured} onClick={() => { if (window.confirm("Bot artık Binance Testnet hesabında GERÇEK emir gönderecek (testnet fonu). Devam?")) act(() => api.liveMode("live"), "CANLI moda geçildi"); }} className="h-7 rounded-sm bg-red-500 hover:bg-red-600 text-white text-[11px] font-bold px-3">Canlıya Geç</Button>
        )}
      </div>

      {st.configured ? (
        <div className="border border-white/10 rounded-sm p-2.5 space-y-2" data-testid="live-credentials-box">
          <div className="flex items-center justify-between">
            <div className="text-xs font-mono"><KeyRound className="inline w-3 h-3 mr-1 text-[#00F0FF]" />API Key <span className="text-zinc-400" data-testid="live-key-masked">{st.api_key_masked}</span></div>
            <div className="flex gap-1">
              <Button data-testid="live-test-button" size="sm" variant="outline" disabled={busy} onClick={() => act(api.liveTest, "Bağlantı başarılı")} className="h-6 rounded-sm border-white/15 bg-transparent text-[10px] px-2"><PlugZap className="w-3 h-3 mr-1" />Test</Button>
              <Button data-testid="live-delete-button" size="sm" variant="outline" disabled={busy} onClick={() => { if (window.confirm("API anahtarı silinsin mi?")) act(api.liveDeleteCredentials, "Anahtar silindi"); }} className="h-6 rounded-sm border-red-500/30 text-red-400 bg-transparent text-[10px] px-2"><Trash2 className="w-3 h-3" /></Button>
            </div>
          </div>
          {acc && (
            <div className="grid grid-cols-3 gap-2 font-mono tabular-nums" data-testid="live-account">
              <div><div className="text-[9px] uppercase text-zinc-500">Cüzdan</div><div className="text-sm">{fmtUsd(acc.wallet_balance)} $</div></div>
              <div><div className="text-[9px] uppercase text-zinc-500">Kullanılabilir</div><div className="text-sm">{fmtUsd(acc.available)} $</div></div>
              <div><div className="text-[9px] uppercase text-zinc-500">Açık PnL</div><div className={`text-sm ${pnlClass(acc.unrealized_pnl)}`}>{signed(acc.unrealized_pnl)}</div></div>
              {acc.positions?.length > 0 && <div className="col-span-3 text-[10px] text-zinc-400">Testnet pozisyonları: {acc.positions.map((p) => `${shortSymbol(p.symbol)} ${p.amt > 0 ? "L" : "S"} ${Math.abs(p.amt)}`).join(" · ")}</div>}
            </div>
          )}
          {st.last_error && <div className="text-[10px] font-mono text-red-400" data-testid="live-error">{st.last_error}</div>}
        </div>
      ) : (
        <div className="space-y-2" data-testid="live-credentials-form">
          <div className="space-y-1">
            <Label htmlFor="live-api-key" className="text-[10px] uppercase tracking-wider text-zinc-500">Testnet API Key</Label>
            <Input id="live-api-key" data-testid="live-api-key-input" value={key} onChange={(e) => setKey(e.target.value)} placeholder="testnet.binancefuture.com → API Key" className="h-8 rounded-sm bg-[#09090b] border-white/10 font-mono text-xs" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="live-api-secret" className="text-[10px] uppercase tracking-wider text-zinc-500">Testnet API Secret</Label>
            <Input id="live-api-secret" data-testid="live-api-secret-input" type="password" value={secret} onChange={(e) => setSecret(e.target.value)} placeholder="••••••••" className="h-8 rounded-sm bg-[#09090b] border-white/10 font-mono text-xs" />
          </div>
          <Button data-testid="live-save-button" size="sm" disabled={busy || key.length < 20 || secret.length < 20} onClick={() => act(() => api.liveSaveCredentials(key, secret).then(() => { setKey(""); setSecret(""); }), "API anahtarı kaydedildi ve doğrulandı")} className="h-8 w-full rounded-sm bg-[#00F0FF] hover:bg-[#08D9E6] text-black text-[11px] font-bold">
            <KeyRound className="w-3 h-3 mr-1" /> Kaydet ve Doğrula
          </Button>
          <p className="text-[10px] text-zinc-500 leading-relaxed">Anahtar şifrelenerek saklanır, tarayıcıya geri gönderilmez. <a className="text-[#00F0FF] underline" href="https://testnet.binancefuture.com" target="_blank" rel="noreferrer">testnet.binancefuture.com</a> → giriş → sayfa altı "API Key" sekmesi. Sadece testnet anahtarı kullan; gerçek hesap anahtarı GİRME.</p>
        </div>
      )}
      <p className="text-[10px] text-zinc-500 leading-relaxed">Canlı modda bot MARKET emirlerle açar, reduce-only ile kapatır; miktarlar Binance LOT_SIZE adımına yuvarlanır. Kaldıraç her paritede otomatik ayarlanır. Paper kayıtları ve istatistikler aynı panelde devam eder.</p>
    </div>
  );
};
