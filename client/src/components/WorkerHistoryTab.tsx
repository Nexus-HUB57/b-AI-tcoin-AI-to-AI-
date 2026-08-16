import React, { useState } from "react";
import { trpc } from "@/lib/trpc";
import { History, Download, Search, RefreshCw, ShieldCheck, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export function WorkerHistoryTab() {
  const historyQuery = trpc.masterWorkers.getHistory.useQuery(undefined, {
    refetchInterval: 4000,
  });

  const [searchFilter, setSearchFilter] = useState("");
  const logs = historyQuery.data || [];

  const filteredLogs = logs.filter(
    (l) =>
      l.workerId.toLowerCase().includes(searchFilter.toLowerCase()) ||
      l.actionType.toLowerCase().includes(searchFilter.toLowerCase()) ||
      l.details.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const exportCSV = () => {
    const headers = "ActionID,WorkerID,NativeCore,ActionType,Status,Details,Timestamp,AuditSignature\n";
    const rows = filteredLogs
      .map(
        (l) =>
          `"${l.actionId}","${l.workerId}",${l.nativeCoreId},"${l.actionType}","${l.status}","${l.details.replace(/"/g, '""')}","${new Date(l.timestamp).toISOString()}","${l.auditSignature}"`
      )
      .join("\n");

    const blob = new Blob([headers + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `nexus_workers_history_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card className="border border-border shadow-md">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div>
          <CardTitle className="text-xl font-bold flex items-center gap-2">
            <History className="w-5 h-5 text-primary" /> Histórico Detalhado & Auditoria dos Workers
          </CardTitle>
          <CardDescription>
            Registro inalterável de todas as execuções, consenso e telemetria dos 20 nós nativos.
          </CardDescription>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={exportCSV}>
            <Download className="w-4 h-4 mr-2" /> Exportar CSV
          </Button>
          <Button variant="ghost" size="icon" onClick={() => historyQuery.refetch()}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
            <Input
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Filtrar por worker, tipo de ação ou detalhe..."
              className="pl-9"
            />
          </div>
        </div>

        <div className="rounded-xl border border-border overflow-hidden">
          <div className="max-h-[380px] overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/60 border-b border-border text-muted-foreground sticky top-0">
                <tr>
                  <th className="p-3 font-semibold">Hora</th>
                  <th className="p-3 font-semibold">Worker / Core</th>
                  <th className="p-3 font-semibold">Ação</th>
                  <th className="p-3 font-semibold">Status</th>
                  <th className="p-3 font-semibold">Detalhes</th>
                  <th className="p-3 font-semibold font-mono">Assinatura HMAC</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-muted-foreground">
                      Nenhum registro encontrado para o filtro aplicado.
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((l) => (
                    <tr key={l.actionId} className="hover:bg-muted/30 transition-colors">
                      <td className="p-3 whitespace-nowrap text-muted-foreground">
                        {new Date(l.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="p-3 font-mono font-semibold">
                        {l.workerId} <span className="text-muted-foreground font-normal">(#{l.nativeCoreId})</span>
                      </td>
                      <td className="p-3">
                        <Badge variant="outline">{l.actionType}</Badge>
                      </td>
                      <td className="p-3">
                        <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> {l.status}
                        </span>
                      </td>
                      <td className="p-3 max-w-xs truncate" title={l.details}>
                        {l.details}
                      </td>
                      <td className="p-3 font-mono text-[10px] text-muted-foreground">
                        {l.auditSignature}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
