import { Label } from "@/components/ui/label";
import { shortSymbol } from "@/lib/format";

export const SymbolPicker = ({ label, all, selected, onChange, testId }) => {
  const toggle = (s) => onChange(selected.includes(s) ? selected.filter((x) => x !== s) : [...selected, s]);
  return (
    <div className="space-y-1.5" data-testid={`${testId}-picker`}>
      <div className="flex justify-between">
        <Label className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</Label>
        <span className="text-[10px] font-mono text-zinc-500 tabular-nums">{selected.length} seçili</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {all.map((s) => (
          <button key={s} data-testid={`${testId}-${s}`} onClick={() => toggle(s)} className={`px-2 h-6 text-[10px] font-mono rounded-sm border transition-colors ${selected.includes(s) ? "border-[#00F0FF]/60 bg-[#00F0FF]/10 text-[#00F0FF]" : "border-white/10 text-zinc-500 hover:text-zinc-200 hover:bg-white/5"}`}>
            {shortSymbol(s)}
          </button>
        ))}
      </div>
    </div>
  );
};
