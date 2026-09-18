import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

const usePoll = (fn, ms, deps = []) => {
  const [data, setData] = useState(null);
  const refresh = useCallback(() => fn().then(setData).catch(() => {}), deps); // eslint-disable-line
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, ms);
    return () => clearInterval(id);
  }, [refresh, ms]);
  return [data, refresh];
};

export const useBot = () => {
  const [status, refreshStatus] = usePoll(api.status, 3000);
  const [logs, refreshLogs] = usePoll(() => api.logs(120), 4000);
  const [trades, refreshTrades] = usePoll(() => api.trades(150), 6000);
  const [equity, refreshEquity] = usePoll(api.equity, 15000);
  const [signals] = usePoll(api.signals, 6000);
  const refreshAll = () => {
    refreshStatus();
    refreshLogs();
    refreshTrades();
    refreshEquity();
  };
  return { status, logs, trades, equity, signals, refreshAll };
};

export const useKlines = (symbol) => {
  const [data] = usePoll(() => api.klines(symbol, "1m", 120), 10000, [symbol]);
  return data;
};
