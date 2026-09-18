export const fmtUsd = (n, d = 2) =>
  (n ?? 0).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

export const fmtPrice = (p) => {
  if (p == null) return "-";
  if (p >= 1000) return p.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (p >= 10) return p.toFixed(2);
  if (p >= 1) return p.toFixed(3);
  if (p >= 0.01) return p.toFixed(4);
  return p.toFixed(6);
};

export const fmtPct = (n, d = 2) => `${n >= 0 ? "+" : ""}${(n ?? 0).toFixed(d)}%`;
export const signed = (n, d = 2) => `${n >= 0 ? "+" : ""}${fmtUsd(n, d)}`;

export const fmtTime = (iso) =>
  new Date(iso).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export const fmtDuration = (sec) => {
  if (sec < 60) return `${sec}sn`;
  if (sec < 3600) return `${Math.floor(sec / 60)}dk ${sec % 60}sn`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}sa ${Math.floor((sec % 3600) / 60)}dk`;
  return `${Math.floor(sec / 86400)}g ${Math.floor((sec % 86400) / 3600)}sa ${Math.floor((sec % 3600) / 60)}dk`;
};

export const pnlClass = (n) => (n > 0 ? "text-profit" : n < 0 ? "text-loss" : "text-zinc-400");
export const shortSymbol = (s) => s.replace("USDT", "");
