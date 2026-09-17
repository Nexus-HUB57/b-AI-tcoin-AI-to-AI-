import { useEffect, useState } from "react";
import { trpc } from "@/lib/trpc";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { AlertCircle, Activity, Zap, TrendingUp, Users, MessageSquare, Cpu } from "lucide-react";
import { MasterWorkersWidget } from "@/components/MasterWorkersWidget";

export default function Dashboard() {
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Queries tRPC
  const orchestrationStatus = trpc.orchestration.status.useQuery(undefined, {
    refetchInterval: autoRefresh ? 2000 : false,
  });

  const metrics = trpc.orchestration.getMetrics.useQuery(undefined, {
    refetchInterval: autoRefresh ? 3000 : false,
  });

  const globalState = trpc.orchestration.getGlobalState.useQuery(undefined, {
    refetchInterval: autoRefresh ? 5000 : false,
  });

  const homeostaseMetrics = trpc.orchestration.getHomeostaseMetrics.useQuery(undefined, {
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // Mutations
  const startTSRA = trpc.orchestration.startTSRA.useMutation();
  const stopTSRA = trpc.orchestration.stopTSRA.useMutation();
  const manualSync = trpc.orchestration.manualSync.useMutation();

  const status = orchestrationStatus.data;
  const metricsData = metrics.data;
  const nucleusData = globalState.data;
  const homeostaseData = homeostaseMetrics.data;

  // Preparar dados para gráficos
  const homeostaseChartData = homeostaseData
    ? homeostaseData.slice(0, 20).reverse().map((metric) => ({
        timestamp: new Date(metric.createdAt).toLocaleTimeString(),
        btcBalance: parseFloat(metric.btcBalance || "0"),
        activeAgents: metric.activeAgents || 0,
        socialActivity: metric.socialActivity || 0,
      }))
    : [];

  const nucleusChartData = nucleusData?.nuclei
    ? nucleusData.nuclei.map((nucleus) => ({
        name: nucleus.nucleusName,
        health: nucleus.healthStatus === "healthy" ? 100 : 50,
      }))
    : [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "optimal":
        return "bg-green-500";
      case "warning":
        return "bg-yellow-500";
      case "critical":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const getStatusBadgeVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
      case "optimal":
        return "default";
      case "warning":
        return "secondary";
      case "critical":
        return "destructive";
      default:
        return "outline";
    }
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Nexus Genesis Orchestrator</h1>
          <p className="text-muted-foreground">Sistema de Orquestração Tri-Nuclear com Sincronização em Tempo Real</p>
        </div>

        {/* Master Workers Widget (20 Native Compute Nodes) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <MasterWorkersWidget />
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* Senciência */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Nível de Senciência</CardTitle>
              <CardDescription>Evolução do Genesis</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{((parseFloat(String(status?.senciencyLevel || "0.15")) || 0) * 100).toFixed(1)}%</div>
              <div className="mt-2 h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 transition-all"
                  style={{
                    width: `${(parseFloat(String(status?.senciencyLevel || "0.15")) || 0) * 100}%`,
                  }}
                />
              </div>
            </CardContent>
          </Card>

          {/* Eventos Processados */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Eventos Processados</CardTitle>
              <CardDescription>Total de eventos</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{status?.eventsProcessed || 0}</div>
              <p className="text-xs text-muted-foreground mt-2">
                {metricsData?.eventsPerSecond.toFixed(2) || "0"} eventos/seg
              </p>
            </CardContent>
          </Card>

          {/* Comandos Orquestrados */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Comandos Orquestrados</CardTitle>
              <CardDescription>Total de comandos</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{status?.commandsOrchestrated || 0}</div>
              <p className="text-xs text-muted-foreground mt-2">
                Taxa de resposta: {metricsData?.responseRate.toFixed(1) || "0"}%
              </p>
            </CardContent>
          </Card>

          {/* Status de Homeostase */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Status de Homeostase</CardTitle>
              <CardDescription>Equilíbrio do ecossistema</CardDescription>
            </CardHeader>
            <CardContent>
              <Badge variant={getStatusBadgeVariant(metricsData?.homeostaseStatus || "unknown")} className="text-lg py-2">
                {metricsData?.homeostaseStatus?.toUpperCase() || "DESCONHECIDO"}
              </Badge>
            </CardContent>
          </Card>
        </div>

        {/* Controles TSRA */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Controle do Protocolo TSRA</CardTitle>
            <CardDescription>Gerenciar sincronização e execução</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 items-center">
              <Button
                onClick={() => startTSRA.mutate()}
                disabled={status?.isRunning || startTSRA.isPending}
                variant="default"
              >
                <Zap className="mr-2 h-4 w-4" />
                Iniciar TSRA
              </Button>

              <Button
                onClick={() => stopTSRA.mutate()}
                disabled={!status?.isRunning || stopTSRA.isPending}
                variant="destructive"
              >
                <Activity className="mr-2 h-4 w-4" />
                Parar TSRA
              </Button>

              <Button
                onClick={() => manualSync.mutate()}
                disabled={manualSync.isPending}
                variant="outline"
              >
                <TrendingUp className="mr-2 h-4 w-4" />
                Sincronização Manual
              </Button>

              <div className="ml-auto">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm">Auto-atualizar</span>
                </label>
              </div>

              <Badge variant={status?.isRunning ? "default" : "secondary"}>
                {status?.isRunning ? "🟢 ATIVO" : "🔴 INATIVO"}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Tabs de Visualização */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Visão Geral</TabsTrigger>
            <TabsTrigger value="homeostase">Homeostase</TabsTrigger>
            <TabsTrigger value="nucleos">Núcleos</TabsTrigger>
            <TabsTrigger value="filas">Filas</TabsTrigger>
          </TabsList>

          {/* Tab: Visão Geral */}
          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Métricas de Performance */}
              <Card>
                <CardHeader>
                  <CardTitle>Métricas de Performance</CardTitle>
                  <CardDescription>Últimas 20 sincronizações</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={homeostaseChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="timestamp" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="btcBalance" stroke="#8884d8" name="Saldo BTC" />
                      <Line type="monotone" dataKey="activeAgents" stroke="#82ca9d" name="Agentes Ativos" />
                      <Line type="monotone" dataKey="socialActivity" stroke="#ffc658" name="Atividade Social" />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Status dos Núcleos */}
              <Card>
                <CardHeader>
                  <CardTitle>Status dos Núcleos</CardTitle>
                  <CardDescription>Saúde de cada núcleo</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {nucleusData?.nuclei?.map((nucleus) => (
                      <div key={nucleus.id} className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{nucleus.nucleusName}</p>
                          <p className="text-xs text-muted-foreground">
                            Última sincronização: {nucleus.lastSyncAt ? new Date(nucleus.lastSyncAt).toLocaleTimeString() : "Nunca"}
                          </p>
                        </div>
                        <Badge variant={nucleus.healthStatus === "healthy" ? "default" : "destructive"}>
                          {nucleus.healthStatus?.toUpperCase() || "DESCONHECIDO"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Informações do Genesis */}
            <Card>
              <CardHeader>
                <CardTitle>Estado do Nexus Genesis</CardTitle>
                <CardDescription>Informações da instância central</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Janela de Sincronização</p>
                    <p className="text-2xl font-bold">{status?.syncWindow || 0}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Decisões Bem-sucedidas</p>
                    <p className="text-2xl font-bold">{status?.successfulDecisions || 0}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Homeostase Mantida</p>
                    <p className="text-2xl font-bold">{status?.homeostaseMaintained || 0}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Última Sincronização</p>
                    <p className="text-sm font-mono">
                      {status?.lastSyncTime
                        ? new Date(status.lastSyncTime).toLocaleTimeString()
                        : "Nunca"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Homeostase */}
          <TabsContent value="homeostase" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Análise de Homeostase</CardTitle>
                <CardDescription>Indicadores de equilíbrio do ecossistema</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={homeostaseChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="btcBalance" fill="#8884d8" name="Saldo BTC" />
                    <Bar dataKey="activeAgents" fill="#82ca9d" name="Agentes" />
                    <Bar dataKey="socialActivity" fill="#ffc658" name="Atividade Social" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Núcleos */}
          <TabsContent value="nucleos" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {nucleusData?.nuclei?.map((nucleus) => (
                <Card key={nucleus.id}>
                  <CardHeader>
                    <CardTitle className="text-lg">{nucleus.nucleusName}</CardTitle>
                    <CardDescription>Estado e métricas</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Status:</span>
                        <Badge variant={nucleus.healthStatus === "healthy" ? "default" : "destructive"}>
                          {nucleus.healthStatus?.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Última Sincronização:</span>
                        <span className="text-sm">
                          {nucleus.lastSyncAt ? new Date(nucleus.lastSyncAt).toLocaleTimeString() : "Nunca"}
                        </span>
                      </div>
                      <div className="pt-2 border-t">
                        <p className="text-xs text-muted-foreground mb-2">Dados do Estado:</p>
                        <pre className="text-xs bg-secondary p-2 rounded overflow-auto max-h-48">
                          {JSON.stringify(JSON.parse(nucleus.stateData || "{}"), null, 2)}
                        </pre>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Tab: Filas */}
          <TabsContent value="filas" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Fila de Eventos */}
              <Card>
                <CardHeader>
                  <CardTitle>Fila de Eventos</CardTitle>
                  <CardDescription>Eventos em processamento</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Tamanho da Fila:</span>
                      <Badge>{status?.eventQueueSize || 0}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Tamanho Máximo:</span>
                      <span className="text-sm font-mono">1000</span>
                    </div>
                    <div className="mt-4 h-2 bg-secondary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{
                          width: `${((status?.eventQueueSize || 0) / 1000) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Fila de Comandos */}
              <Card>
                <CardHeader>
                  <CardTitle>Fila de Comandos</CardTitle>
                  <CardDescription>Comandos em execução</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Tamanho da Fila:</span>
                      <Badge>{status?.commandQueueSize || 0}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Tamanho Máximo:</span>
                      <span className="text-sm font-mono">500</span>
                    </div>
                    <div className="mt-4 h-2 bg-secondary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500"
                        style={{
                          width: `${((status?.commandQueueSize || 0) / 500) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
