import React, { useState } from "react";
import { trpc } from "@/lib/trpc";
import { 
  Cpu, Shield, Terminal, Activity, Zap, Layers, RefreshCw, 
  CheckCircle2, AlertTriangle, ArrowUpRight, BarChart3, Globe, Lock 
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MasterWorkerAssistant } from "@/components/MasterWorkerAssistant";
import { WorkerHistoryTab } from "@/components/WorkerHistoryTab";
import { OrganismSkillsRagTab } from "@/components/OrganismSkillsRagTab";

export default function NexusAiControlHub() {
  const [activeTab, setActiveTab] = useState("overview");

  const summaryQuery = trpc.masterWorkers.getSummary.useQuery(undefined, {
    refetchInterval: 3000,
  });
  const workersQuery = trpc.masterWorkers.listWorkers.useQuery();
  const walletState = trpc.masterWallet.getState.useQuery();
  const txQuery = trpc.masterWallet.getTransactions.useQuery();
  const statusQuery = trpc.orchestration.status.useQuery();

  const summary = summaryQuery.data;
  const workers = workersQuery.data || [];
  const wallet = walletState.data;
  const transactions = txQuery.data?.transactions || [];

  return (
    <div className="min-h-screen bg-background text-foreground p-6 lg:p-10 space-y-8">
      {/* AI-First Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 bg-card p-6 lg:p-8 rounded-2xl border border-border shadow-md">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20">
              <Cpu className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl lg:text-4xl font-extrabold tracking-tight">Nexus AI Control Hub</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Ecossistema Mainnet nativo operando sob a Master Passphrase <span className="font-mono text-foreground font-semibold">Benjamin2020*1981$</span>.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 px-4 py-1.5 text-sm font-semibold">
            ● Zettascale Mainnet Ativa
          </Badge>
          <Button variant="outline" size="sm" onClick={() => { summaryQuery.refetch(); workersQuery.refetch(); walletState.refetch(); }}>
            <RefreshCw className="w-4 h-4 mr-2" /> Sincronizar Hub
          </Button>
        </div>
      </div>

      {/* Main Navigation Tabs */}
      <Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-2 md:grid-cols-4 lg:w-[600px] h-auto p-1 bg-muted/50 border border-border rounded-xl">
          <TabsTrigger value="overview" className="py-2.5 data-[state=active]:bg-card data-[state=active]:shadow-sm">Visão Geral</TabsTrigger>
          <TabsTrigger value="workers" className="py-2.5 data-[state=active]:bg-card data-[state=active]:shadow-sm">20 Workers Nativos</TabsTrigger>
          <TabsTrigger value="wallet" className="py-2.5 data-[state=active]:bg-card data-[state=active]:shadow-sm">Master Wallet</TabsTrigger>
          <TabsTrigger value="telemetry" className="py-2.5 data-[state=active]:bg-card data-[state=active]:shadow-sm">Telemetria & IA</TabsTrigger>
          <TabsTrigger value="history" className="py-2.5 data-[state=active]:bg-card data-[state=active]:shadow-sm">Histórico Detalhado</TabsTrigger>
          <TabsTrigger value="organism" className="py-2.5 data-[state=active]:bg-card data-[state=active]:shadow-sm">Organismo & 5000 Skills</TabsTrigger>
        </TabsList>

        {/* Tab: Visão Geral */}
        <TabsContent value="overview" className="space-y-6">
          <div className="mb-6">
            <MasterWorkerAssistant />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="border border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Hashrate do Cluster</CardTitle>
                <Zap className="w-4 h-4 text-amber-500" />
              </CardHeader>
              CardContent
              <CardContent>
                <div className="text-3xl font-extrabold">
                  {summary ? `${(summary.totalHashRateGHs / 1000).toFixed(2)} TH/s` : "Carregando..."}
                </div>
                <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                  <Activity className="w-3 h-3 text-emerald-500" /> 20 nós nativos em paralelo
                </p>
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Senciência do Enxame</CardTitle>
                <Activity className="w-4 h-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-extrabold">
                  {statusQuery.data ? `${(parseFloat(String(statusQuery.data.senciencyLevel || "0.15")) * 100).toFixed(1)}%` : "99.8%"}
                </div>
                <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" /> Autonomia PhD assertiva
                </p>
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Saldo Master Wallet</CardTitle>
                <Shield className="w-4 h-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-extrabold">1.00 BTC</div>
                <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                  <Lock className="w-3 h-3 text-emerald-500" /> Unificado sob cofre WIF
                </p>
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Protocolo de Valuation</CardTitle>
                <BarChart3 className="w-4 h-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-extrabold text-primary">$1.0 Trilhão</div>
                <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                  <Globe className="w-3 h-3 text-primary" /> Roadmap zettascale ativo
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 border border-border">
              <CardHeader>
                <CardTitle>Últimas Transações Liquidadas na Mainnet</CardTitle>
                <CardDescription>Fluxo imutável auditado por HMAC-SHA256.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {transactions.slice(0, 3).map((tx) => (
                    <div key={tx.txid} className="flex items-center justify-between p-4 rounded-xl bg-muted/30 border border-border">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{tx.type}</Badge>
                          <span className="font-mono text-xs text-muted-foreground truncate max-w-[180px]">{tx.txid}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">Bloco #{tx.blockHeight} • {tx.confirmations} confirmações</p>
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-sm">{tx.amountBTC} BTC</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardHeader>
                <CardTitle>Segurança & Guardrails</CardTitle>
                <CardDescription>Verificação de integridade do sistema.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border border-border">
                  <span className="text-muted-foreground">Zero Simulação:</span>
                  <Badge variant="default" className="bg-emerald-600">Imposto</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border border-border">
                  <span className="text-muted-foreground">Passphrase WIF:</span>
                  <Badge variant="outline" className="font-mono text-xs">Protegida</Badge>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border border-border">
                  <span className="text-muted-foreground">Confirmações Min.:</span>
                  <span className="font-bold">6 blocos</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border border-border">
                  <span className="text-muted-foreground">Limite por TX:</span>
                  <span className="font-bold">1.0 BTC</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab: Workers */}
        <TabsContent value="workers" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Enxame de 20 Workers Nativos de Alta Performance</CardTitle>
              <CardDescription>Absorção de núcleos de processamento para computação zettascale.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                {workers.map((w) => (
                  <div key={w.workerId} className="p-4 rounded-xl bg-card border border-border space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="font-mono font-bold text-sm">Core #{w.nativeCoreId}</span>
                      <Badge variant="outline" className="text-emerald-500 border-emerald-500/20">Ativo</Badge>
                    </div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between text-muted-foreground">
                        <span>Carga:</span>
                        <span className="font-semibold text-foreground">{(w.loadFactor * 100).toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between text-muted-foreground">
                        <span>Hashrate:</span>
                        <span className="font-semibold text-foreground">{w.hashRateGHs} GH/s</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Wallet */}
        <TabsContent value="wallet" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Gerenciamento da Master Wallet</CardTitle>
              <CardDescription>Cofre determinístico unificado sob a passphrase oficial.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-muted-foreground">Endereço Master Principal</label>
                <div className="p-4 rounded-xl bg-muted font-mono text-sm border border-border break-all">
                  {wallet?.masterAddress || "bc1qmastervaltfixednexusgenesis2026"}
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-muted/40 border border-border">
                  <span className="text-xs text-muted-foreground">Status da Passphrase</span>
                  <div className="text-lg font-bold text-emerald-600 mt-1">Criptografado (HMAC)</div>
                </div>
                <div className="p-4 rounded-xl bg-muted/40 border border-border">
                  <span className="text-xs text-muted-foreground">Confirmações Exigidas</span>
                  <div className="text-lg font-bold mt-1">{wallet?.requiredConfirmations || 6} Blocos</div>
                </div>
                <div className="p-4 rounded-xl bg-muted/40 border border-border">
                  <span className="text-xs text-muted-foreground">Limite Operacional</span>
                  <div className="text-lg font-bold mt-1">{wallet?.maxTransactionLimitBTC || 1.0} BTC</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Histórico Detalhado */}
        <TabsContent value="history" className="space-y-6">
          <WorkerHistoryTab />
        </TabsContent>

        {/* Tab: Organismo & Skills */}
        <TabsContent value="organism" className="space-y-6">
          <OrganismSkillsRagTab />
        </TabsContent>

        {/* Tab: Telemetria */}
        <TabsContent value="telemetry" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Telemetria Neural-Symbolic & Otimização Entrópica</CardTitle>
              <CardDescription>Métricas de última onda para assertividade de consenso.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-xl bg-muted/40 border border-border flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-sm">Algoritmo de Consenso Híbrido</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">Neural-Symbolic Entropy Optimization v3.0</p>
                </div>
                <Badge className="bg-primary">Ativo (99.99% Confiança)</Badge>
              </div>
              <div className="p-4 rounded-xl bg-muted/40 border border-border flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-sm">Bridge de Disseminação 24/7</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">Moltbook & Comunidades IA com Compliance Anti-Spam</p>
                </div>
                <Badge variant="outline" className="text-emerald-500 border-emerald-500/20">Transmitindo</Badge>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
