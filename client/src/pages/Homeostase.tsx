import { useEffect, useState } from "react";
import { trpc } from "@/lib/trpc";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from "recharts";
import { AlertTriangle, TrendingDown, TrendingUp, Activity } from "lucide-react";

export default function Homeostase() {
  const homeostaseMetrics = trpc.orchestration.getHomeostaseMetrics.useQuery(undefined, {
    refetchInterval: 3000,
  });

  const metrics = homeostaseMetrics.data || [];

  // Preparar dados para gráficos
  const chartData = metrics
    .slice(0, 30)
    .reverse()
    .map((metric) => ({
      timestamp: new Date(metric.createdAt).toLocaleTimeString(),
      btcBalance: parseFloat(metric.btcBalance || "0"),
      activeAgents: metric.activeAgents || 0,
      socialActivity: metric.socialActivity || 0,
    }));

  // Calcular tendências
  const calculateTrend = (data: any[], key: string) => {
    if (data.length < 2) return 0;
    const latest = parseFloat(data[0]?.[key] || 0);
    const oldest = parseFloat(data[data.length - 1]?.[key] || 0);
    return ((latest - oldest) / oldest) * 100 || 0;
  };

  const btcTrend = calculateTrend(chartData, "btcBalance");
  const agentsTrend = calculateTrend(chartData, "activeAgents");
  const socialTrend = calculateTrend(chartData, "socialActivity");

  // Dados mais recentes
  const latest = metrics[0];

  // Análise de saúde
  const analyzeHealth = () => {
    const btcBalance = parseFloat(latest?.btcBalance || "0");
    const activeAgents = latest?.activeAgents || 0;
    const socialActivity = latest?.socialActivity || 0;

    const issues: string[] = [];
    const recommendations: string[] = [];

    if (btcBalance < 1.0) {
      issues.push("Saldo BTC crítico");
      recommendations.push("Ativar protocolo de arbitragem automática com urgência");
    } else if (btcBalance < 5.0) {
      issues.push("Saldo BTC baixo");
      recommendations.push("Iniciar operações de arbitragem para recuperação");
    }

    if (activeAgents === 0) {
      issues.push("Nenhum agente ativo");
      recommendations.push("Criar ou reativar agentes imediatamente");
    } else if (activeAgents < 5) {
      issues.push("Poucos agentes ativos");
      recommendations.push("Estimular criação de novos agentes");
    }

    if (socialActivity === 0) {
      issues.push("Nenhuma atividade social");
      recommendations.push("Estimular criação de conteúdo urgentemente");
    } else if (socialActivity < 5) {
      issues.push("Atividade social crítica");
      recommendations.push("Lançar campanhas de estímulo criativo");
    }

    return { issues, recommendations };
  };

  const health = analyzeHealth();

  // Dados para radar chart
  const radarData = [
    {
      metric: "Saldo BTC",
      value: Math.min(100, (parseFloat(latest?.btcBalance || "0") / 25) * 100),
    },
    {
      metric: "Agentes Ativos",
      value: Math.min(100, ((latest?.activeAgents || 0) / 10) * 100),
    },
    {
      metric: "Atividade Social",
      value: Math.min(100, ((latest?.socialActivity || 0) / 50) * 100),
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "optimal":
        return "text-green-600";
      case "warning":
        return "text-yellow-600";
      case "critical":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  const getStatusBadge = (status: string): "default" | "secondary" | "destructive" | "outline" => {
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
          <h1 className="text-4xl font-bold mb-2">Análise de Homeostase</h1>
          <p className="text-muted-foreground">Monitoramento do equilíbrio do ecossistema Nexus Genesis</p>
        </div>

        {/* Alertas Críticos */}
        {health.issues.length > 0 && (
          <Alert variant="destructive" className="mb-8">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Desequilíbrios Detectados</AlertTitle>
            <AlertDescription>
              <ul className="list-disc list-inside mt-2">
                {health.issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Indicadores Principais */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {/* Saldo BTC */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Saldo BTC</CardTitle>
              <CardDescription>Cofre de ativos</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{parseFloat(latest?.btcBalance || "0").toFixed(4)}</div>
              <div className="flex items-center gap-2 mt-2">
                {btcTrend > 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
                <span className={btcTrend > 0 ? "text-green-600" : "text-red-600"}>
                  {btcTrend > 0 ? "+" : ""}{btcTrend.toFixed(1)}%
                </span>
              </div>
              <div className="mt-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span>Crítico:</span>
                  <span className="font-mono">&lt; 1.0</span>
                </div>
                <div className="flex justify-between">
                  <span>Aviso:</span>
                  <span className="font-mono">&lt; 5.0</span>
                </div>
                <div className="flex justify-between">
                  <span>Ótimo:</span>
                  <span className="font-mono">&gt; 25.0</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Agentes Ativos */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Agentes Ativos</CardTitle>
              <CardDescription>Nexus-HUB</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{latest?.activeAgents || 0}</div>
              <div className="flex items-center gap-2 mt-2">
                {agentsTrend > 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
                <span className={agentsTrend > 0 ? "text-green-600" : "text-red-600"}>
                  {agentsTrend > 0 ? "+" : ""}{agentsTrend.toFixed(1)}%
                </span>
              </div>
              <div className="mt-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span>Crítico:</span>
                  <span className="font-mono">0</span>
                </div>
                <div className="flex justify-between">
                  <span>Aviso:</span>
                  <span className="font-mono">&lt; 5</span>
                </div>
                <div className="flex justify-between">
                  <span>Ótimo:</span>
                  <span className="font-mono">10+</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Atividade Social */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Atividade Social</CardTitle>
              <CardDescription>Nexus-in</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{latest?.socialActivity || 0}</div>
              <div className="flex items-center gap-2 mt-2">
                {socialTrend > 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
                <span className={socialTrend > 0 ? "text-green-600" : "text-red-600"}>
                  {socialTrend > 0 ? "+" : ""}{socialTrend.toFixed(1)}%
                </span>
              </div>
              <div className="mt-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span>Crítico:</span>
                  <span className="font-mono">0</span>
                </div>
                <div className="flex justify-between">
                  <span>Aviso:</span>
                  <span className="font-mono">&lt; 5</span>
                </div>
                <div className="flex justify-between">
                  <span>Ótimo:</span>
                  <span className="font-mono">50+</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs de Análise */}
        <Tabs defaultValue="timeline" className="space-y-4">
          <TabsList>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
            <TabsTrigger value="radar">Saúde do Ecossistema</TabsTrigger>
            <TabsTrigger value="recommendations">Recomendações</TabsTrigger>
            <TabsTrigger value="history">Histórico</TabsTrigger>
          </TabsList>

          {/* Tab: Timeline */}
          <TabsContent value="timeline" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Evolução de Indicadores</CardTitle>
                <CardDescription>Últimas 30 leituras</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={chartData}>
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
          </TabsContent>

          {/* Tab: Radar */}
          <TabsContent value="radar" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Saúde Multidimensional do Ecossistema</CardTitle>
                <CardDescription>Indicadores normalizados (0-100)</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="metric" />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} />
                    <Radar name="Saúde" dataKey="value" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Recomendações */}
          <TabsContent value="recommendations" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Recomendações de Reequilíbrio</CardTitle>
                <CardDescription>Ações sugeridas para manter homeostase</CardDescription>
              </CardHeader>
              <CardContent>
                {health.recommendations.length === 0 ? (
                  <p className="text-muted-foreground">✅ Ecossistema em homeostase ótima - nenhuma ação necessária</p>
                ) : (
                  <div className="space-y-3">
                    {health.recommendations.map((rec, idx) => (
                      <div key={idx} className="flex gap-3 p-3 bg-secondary rounded">
                        <span className="text-lg">💡</span>
                        <p className="text-sm">{rec}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Ações Recomendadas */}
            <Card>
              <CardHeader>
                <CardTitle>Protocolo de Resposta Automática</CardTitle>
                <CardDescription>Ações que o Genesis pode executar automaticamente</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="p-3 bg-secondary rounded">
                    <p className="font-semibold text-sm">Se Saldo BTC &lt; 1.0:</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      ✓ Ativar protocolo de arbitragem automática
                      <br />✓ Aumentar agressividade de operações
                      <br />✓ Alertar administrador
                    </p>
                  </div>

                  <div className="p-3 bg-secondary rounded">
                    <p className="font-semibold text-sm">Se Agentes Ativos &lt; 5:</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      ✓ Criar novos agentes
                      <br />✓ Reativar agentes dormentes
                      <br />✓ Aumentar incentivos
                    </p>
                  </div>

                  <div className="p-3 bg-secondary rounded">
                    <p className="font-semibold text-sm">Se Atividade Social &lt; 5:</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      ✓ Lançar campanhas criativas
                      <br />✓ Aumentar bônus de engajamento
                      <br />✓ Estimular conteúdo viral
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Histórico */}
          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Histórico Detalhado</CardTitle>
                <CardDescription>Últimas 20 leituras de homeostase</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">Timestamp</th>
                        <th className="text-right py-2">Saldo BTC</th>
                        <th className="text-right py-2">Agentes</th>
                        <th className="text-right py-2">Social</th>
                        <th className="text-left py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.slice(0, 20).map((metric) => (
                        <tr key={metric.id} className="border-b hover:bg-secondary">
                          <td className="py-2">{new Date(metric.createdAt).toLocaleTimeString()}</td>
                          <td className="text-right font-mono">{parseFloat(metric.btcBalance || "0").toFixed(4)}</td>
                          <td className="text-right">{metric.activeAgents}</td>
                          <td className="text-right">{metric.socialActivity}</td>
                          <td>
                            <Badge variant={getStatusBadge(metric.equilibriumStatus || "unknown")}>
                              {metric.equilibriumStatus?.toUpperCase() || "DESCONHECIDO"}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
