import React, { useState } from "react";
import { trpc } from "@/lib/trpc";
import { Cpu, Activity, Zap, RefreshCw, ShieldCheck, Server } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function MasterWorkersWidget() {
  const summaryQuery = trpc.masterWorkers.getSummary.useQuery(undefined, {
    refetchInterval: 3000, // Atualização a cada 3 segundos
  });
  const workersQuery = trpc.masterWorkers.listWorkers.useQuery();

  const [selectedWorker, setSelectedWorker] = useState<string | null>(null);

  const data = summaryQuery.data;
  const workers = workersQuery.data || [];

  return (
    <Card className="col-span-1 md:col-span-2 lg:col-span-3 border border-border shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-6 h-6 text-primary" />
            <CardTitle className="text-xl font-bold">Cluster Zettascale (20 Native Workers)</CardTitle>
          </div>
          <CardDescription>
            Monitoramento em tempo real da carga, taxa de hash e status de processamento dos núcleos nativos.
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
            {data?.clusterStatus || "ONLINE"}
          </Badge>
          <Button variant="ghost" size="icon" onClick={() => { summaryQuery.refetch(); workersQuery.refetch(); }}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-muted/50 p-4 rounded-lg border border-border">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <Server className="w-3.5 h-3.5 text-primary" /> Hashrate Total do Cluster
            </div>
            <div className="text-2xl font-bold mt-1">
              {data ? `${(data.totalHashRateGHs / 1000).toFixed(2)} TH/s` : "Calculando..."}
            </div>
          </div>
          <div className="bg-muted/50 p-4 rounded-lg border border-border">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <Activity className="w-3.5 h-3.5 text-emerald-500" /> Fator Médio de Carga
            </div>
            <div className="text-2xl font-bold mt-1">
              {data ? `${(data.averageLoadFactor * 100).toFixed(1)}%` : "0%"}
            </div>
          </div>
          <div className="bg-muted/50 p-4 rounded-lg border border-border">
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Master Guard Vault
            </div>
            <div className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">
              Ativo (20/20)
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-500" /> Status Individual dos 20 Workers Nativos
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-2 max-h-[220px] overflow-y-auto pr-2">
            {workers.map((w) => (
              <button
                key={w.workerId}
                onClick={() => setSelectedWorker(w.workerId)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  selectedWorker === w.workerId
                    ? "bg-primary/20 border-primary"
                    : "bg-card hover:bg-muted/50 border-border"
                }`}
              >
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="font-bold">#{w.nativeCoreId}</span>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                </div>
                <div className="text-[11px] font-semibold mt-1 truncate">{w.workerId}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">
                  {(w.loadFactor * 100).toFixed(0)}% carga
                </div>
              </button>
            ))}
          </div>
        </div>

        {selectedWorker && (
          <div className="bg-card p-4 rounded-lg border border-primary/30 flex items-center justify-between">
            <div>
              <span className="text-xs text-muted-foreground">Worker Selecionado:</span>
              <span className="font-mono font-bold text-sm ml-2">{selectedWorker}</span>
            </div>
            <Button variant="outline" size="sm" onClick={() => setSelectedWorker(null)}>
              Fechar Detalhes
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
