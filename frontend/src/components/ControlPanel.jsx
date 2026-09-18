import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { SymbolPicker } from "@/components/SymbolPicker";

const Field = ({ label, id, value, onChange, step = "0.01", suffix }) => (
  <div className="space-y-1">
    <Label htmlFor={id} className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</Label>
    <div className="relative">
      <Input id={id} data-testid={`cfg-${id}`} type="number" step={step} value={value ?? ""} onChange={(e) => onChange(parseFloat(e.target.value))} className="h-8 rounded-sm bg-[#09090b] border-white/10 font-mono text-xs tabular-nums focus-visible:ring-[#00F0FF]/50 pr-8" />
      {suffix && <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-mono text-zinc-500">{suffix}</span>}
    </div>
  </div>
);

const STRATS = [
  { v: "both", l: "Çoklu Sinyal + Grid" },
  { v: "multi", l: "Çoklu Sinyal" },
  { v: "grid", l: "Sadece Grid" },
];

export const ControlPanel = ({ config, onChange }) => {
  const [c, setC] = useState(config);
  const [allSymbols, setAllSymbols] = useState([]);
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (config && !c) setC(config); }, [config]); // eslint-disable-line
  useEffect(() => { api.symbols().then(setAllSymbols).catch(() => {}); }, []);
  if (!c) return <div className="panel h-full p-4 text-xs font-mono text-zinc-600">Ayarlar yükleniyor…</div>;

  const set = (k, v) => setC({ ...c, [k]: v });
  const setInd = (k, v) => setC({ ...c, indicators: { ...c.indicators, [k]: v } });
  const setGrid = (k, v) => setC({ ...c, grid: { ...c.grid, [k]: v } });

  const save = async () => {
    setSaving(true);
    try {
      await api.updateConfig(c);
      toast.success("Ayarlar kaydedildi");
      onChange();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Kaydedilemedi");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="panel h-full" data-testid="control-panel">
      <div className="panel-header">
        <span className="panel-title">Bot Kontrol Paneli</span>
        <Button data-testid="cfg-save-button" size="sm" disabled={saving} onClick={save} className="h-7 rounded-sm bg-[#00F0FF] hover:bg-[#08D9E6] text-black text-[11px] font-bold px-3">
          <Save className="w-3 h-3 mr-1" /> Kaydet
        </Button>
      </div>
      <Tabs defaultValue="general" className="flex-1 flex flex-col">
        <TabsList className="h-auto bg-transparent rounded-none p-0 border-b border-white/10 w-full justify-start">
          {[["general", "Genel"], ["risk", "Risk"], ["indicators", "Göstergeler"], ["grid", "Grid"]].map(([v, l]) => (
            <TabsTrigger key={v} value={v} data-testid={`cfg-tab-${v}`} className="rounded-none border-b-2 border-transparent data-[state=active]:border-[#00F0FF] data-[state=active]:bg-transparent data-[state=active]:text-white text-zinc-400 text-xs px-3 py-2">{l}</TabsTrigger>
          ))}
        </TabsList>
        <div className="p-3 space-y-4 overflow-auto scroll-thin flex-1">
          <TabsContent value="general" className="m-0 space-y-4">
            <div className="space-y-1.5">
              <Label className="text-[10px] uppercase tracking-wider text-zinc-500">Strateji</Label>
              <div className="grid grid-cols-3 gap-1">
                {STRATS.map((s) => (
                  <button key={s.v} data-testid={`strategy-${s.v}`} onClick={() => set("strategy", s.v)} className={`h-8 text-[11px] rounded-sm border transition-colors ${c.strategy === s.v ? "border-[#00F0FF]/60 bg-[#00F0FF]/10 text-[#00F0FF]" : "border-white/10 text-zinc-400 hover:bg-white/5"}`}>{s.l}</button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between"><Label className="text-[10px] uppercase tracking-wider text-zinc-500">Kaldıraç</Label><span className="font-mono text-xs text-[#00F0FF] tabular-nums" data-testid="leverage-value">{c.leverage}x</span></div>
              <Slider data-testid="leverage-slider" value={[c.leverage]} min={1} max={50} step={1} onValueChange={([v]) => set("leverage", v)} />
            </div>
            <SymbolPicker label="İşlem Pariteleri (Çoklu Sinyal)" all={allSymbols} selected={c.symbols} onChange={(v) => set("symbols", v)} testId="symbols" />
            <div className="grid grid-cols-2 gap-2">
              <Field id="initial_balance" label="Başlangıç Bakiyesi" value={c.initial_balance} onChange={(v) => set("initial_balance", v)} step="100" suffix="$" />
              <Field id="max_open_positions" label="Maks Açık Pozisyon" value={c.max_open_positions} onChange={(v) => set("max_open_positions", v)} step="1" />
            </div>
          </TabsContent>
          <TabsContent value="risk" className="m-0 space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <Field id="risk_per_trade_pct" label="İşlem Başı Marj" value={c.risk_per_trade_pct} onChange={(v) => set("risk_per_trade_pct", v)} step="0.5" suffix="%" />
              <Field id="min_score" label="Min. Sinyal Skoru" value={c.min_score} onChange={(v) => set("min_score", v)} step="0.5" />
              <Field id="tp_pct" label="Take Profit" value={c.tp_pct} onChange={(v) => set("tp_pct", v)} step="0.05" suffix="%" />
              <Field id="sl_pct" label="Stop Loss" value={c.sl_pct} onChange={(v) => set("sl_pct", v)} step="0.05" suffix="%" />
              <Field id="max_hold_minutes" label="Maks Tutma Süresi" value={c.max_hold_minutes} onChange={(v) => set("max_hold_minutes", v)} step="1" suffix="dk" />
              <Field id="cooldown_seconds" label="Bekleme Süresi" value={c.cooldown_seconds} onChange={(v) => set("cooldown_seconds", v)} step="5" suffix="sn" />
            </div>
            <div className="flex items-center justify-between border border-white/10 rounded-sm p-2.5">
              <div>
                <div className="text-xs font-semibold">Trailing Stop</div>
                <div className="text-[10px] text-zinc-500">Kâr kilitleme: zirveyi takip eden stop</div>
              </div>
              <Switch data-testid="cfg-trailing" checked={c.trailing} onCheckedChange={(v) => set("trailing", v)} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Field id="trailing_activation_pct" label="Trailing Aktivasyon" value={c.trailing_activation_pct} onChange={(v) => set("trailing_activation_pct", v)} step="0.05" suffix="%" />
              <Field id="trailing_distance_pct" label="Trailing Mesafe" value={c.trailing_distance_pct} onChange={(v) => set("trailing_distance_pct", v)} step="0.05" suffix="%" />
            </div>
            <p className="text-[10px] text-zinc-500 leading-relaxed">TP/SL fiyat yüzdesidir. {c.leverage}x kaldıraçta {c.tp_pct}% TP ≈ marj üzerinde <span className="font-mono text-profit">+{(c.tp_pct * c.leverage).toFixed(1)}%</span>, {c.sl_pct}% SL ≈ <span className="font-mono text-loss">-{(c.sl_pct * c.leverage).toFixed(1)}%</span>.</p>
          </TabsContent>
          <TabsContent value="indicators" className="m-0 grid grid-cols-2 gap-2">
            <Field id="rsi_period" label="RSI Periyot" value={c.indicators.rsi_period} onChange={(v) => setInd("rsi_period", v)} step="1" />
            <Field id="rsi_buy" label="RSI Alım Eşiği" value={c.indicators.rsi_buy} onChange={(v) => setInd("rsi_buy", v)} step="1" />
            <Field id="rsi_sell" label="RSI Satım Eşiği" value={c.indicators.rsi_sell} onChange={(v) => setInd("rsi_sell", v)} step="1" />
            <Field id="ema_fast" label="EMA Hızlı" value={c.indicators.ema_fast} onChange={(v) => setInd("ema_fast", v)} step="1" />
            <Field id="ema_slow" label="EMA Yavaş" value={c.indicators.ema_slow} onChange={(v) => setInd("ema_slow", v)} step="1" />
            <Field id="bb_period" label="Bollinger Periyot" value={c.indicators.bb_period} onChange={(v) => setInd("bb_period", v)} step="1" />
            <Field id="bb_std" label="Bollinger Std" value={c.indicators.bb_std} onChange={(v) => setInd("bb_std", v)} step="0.1" />
            <Field id="macd_fast" label="MACD Hızlı" value={c.indicators.macd_fast} onChange={(v) => setInd("macd_fast", v)} step="1" />
            <Field id="macd_slow" label="MACD Yavaş" value={c.indicators.macd_slow} onChange={(v) => setInd("macd_slow", v)} step="1" />
            <Field id="macd_signal" label="MACD Sinyal" value={c.indicators.macd_signal} onChange={(v) => setInd("macd_signal", v)} step="1" />
          </TabsContent>
          <TabsContent value="grid" className="m-0 space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <Field id="grid_levels" label="Seviye (±)" value={c.grid.levels} onChange={(v) => setGrid("levels", v)} step="1" />
              <Field id="grid_spacing_pct" label="Aralık" value={c.grid.spacing_pct} onChange={(v) => setGrid("spacing_pct", v)} step="0.05" suffix="%" />
              <Field id="grid_size_pct" label="Emir Marjı" value={c.grid.size_pct} onChange={(v) => setGrid("size_pct", v)} step="0.5" suffix="%" />
            </div>
            <SymbolPicker label="Grid Pariteleri" all={allSymbols} selected={c.grid.symbols} onChange={(v) => setGrid("symbols", v)} testId="grid-symbols" />
            <p className="text-[10px] text-zinc-500 leading-relaxed">Fiyat merkezin altındaki her seviyeyi aşağı kestiğinde LONG, üstündeki seviyeyi yukarı kestiğinde SHORT açılır; hedef bir sonraki seviyedir. Fiyat bant dışına çıkarsa grid yeniden merkezlenir.</p>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
};
