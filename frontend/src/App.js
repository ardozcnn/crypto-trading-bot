import { useState } from "react";
import "@/App.css";
import { Toaster } from "@/components/ui/sonner";
import { useBot } from "@/hooks/useBot";
import { TopNav } from "@/components/TopNav";
import { TickerStrip } from "@/components/TickerStrip";
import { StatsCards } from "@/components/StatsCards";
import { ChartPanel } from "@/components/ChartPanel";
import { ControlPanel } from "@/components/ControlPanel";
import { PositionsTable } from "@/components/PositionsTable";
import { TradesTable } from "@/components/TradesTable";
import { ActivityLog } from "@/components/ActivityLog";
import { EquityChart } from "@/components/EquityChart";
import { SignalsPanel } from "@/components/SignalsPanel";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

function App() {
  const { status, logs, trades, equity, signals, refreshAll } = useBot();
  const [symbol, setSymbol] = useState("BTCUSDT");
  const config = status?.config;

  return (
    <div className="App min-h-screen bg-[#09090b] text-white flex flex-col" data-testid="app-root">
      <Toaster theme="dark" position="bottom-right" toastOptions={{ className: "font-mono text-xs rounded-sm" }} />
      <TopNav status={status} onChange={refreshAll} />
      <TickerStrip tickers={status?.tickers || []} onSelect={setSymbol} />
      <main className="flex-1 grid grid-cols-1 xl:grid-cols-12 gap-3 p-3">
        <div className="xl:col-span-12">
          <StatsCards stats={status?.stats} running={status?.running} />
        </div>
        <div className="xl:col-span-8 flex flex-col gap-3">
          <ChartPanel symbol={symbol} setSymbol={setSymbol} symbols={config ? [...new Set([...config.symbols, ...config.grid.symbols])] : []} positions={status?.positions || []} />
          <SignalsPanel signals={signals || []} positions={status?.positions || []} onSelect={setSymbol} />
        </div>
        <div className="xl:col-span-4">
          <ControlPanel config={config} running={status?.running} onChange={refreshAll} />
        </div>
        <div className="xl:col-span-8 panel h-[420px]" data-testid="bottom-panel">
          <Tabs defaultValue="positions" className="flex flex-col h-full">
            <div className="panel-header !px-0">
              <TabsList className="h-full bg-transparent rounded-none p-0 gap-0">
                <TabsTrigger data-testid="tab-positions" value="positions" className="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-[#00F0FF] data-[state=active]:bg-transparent data-[state=active]:text-white text-zinc-400 px-4 text-xs font-display font-bold uppercase tracking-tight">
                  Açık Pozisyonlar <span className="ml-1.5 font-mono tabular-nums text-[#00F0FF]">{status?.positions?.length ?? 0}</span>
                </TabsTrigger>
                <TabsTrigger data-testid="tab-trades" value="trades" className="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-[#00F0FF] data-[state=active]:bg-transparent data-[state=active]:text-white text-zinc-400 px-4 text-xs font-display font-bold uppercase tracking-tight">
                  İşlem Geçmişi <span className="ml-1.5 font-mono tabular-nums text-zinc-500">{trades?.length ?? 0}</span>
                </TabsTrigger>
                <TabsTrigger data-testid="tab-equity" value="equity" className="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-[#00F0FF] data-[state=active]:bg-transparent data-[state=active]:text-white text-zinc-400 px-4 text-xs font-display font-bold uppercase tracking-tight">
                  Bakiye Eğrisi
                </TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value="positions" className="flex-1 m-0 overflow-auto scroll-thin">
              <PositionsTable positions={status?.positions || []} onChange={refreshAll} />
            </TabsContent>
            <TabsContent value="trades" className="flex-1 m-0 overflow-auto scroll-thin">
              <TradesTable trades={trades || []} />
            </TabsContent>
            <TabsContent value="equity" className="flex-1 m-0 p-2">
              <EquityChart equity={equity || []} initial={config?.initial_balance} />
            </TabsContent>
          </Tabs>
        </div>
        <div className="xl:col-span-4 h-[420px]">
          <ActivityLog logs={logs || []} />
        </div>
      </main>
    </div>
  );
}

export default App;
