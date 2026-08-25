import { useEffect, useState } from "react";
import { useWebSocketEvent, useWebSocketEventHistory, WebSocketEventType, WebSocketPayload } from "@/hooks/useWebSocketEvents";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Activity, AlertTriangle, Zap, TrendingUp, Radio, Pause } from "lucide-react";

interface DashboardMetrics {
  syncWindow: number;
  eventsProcessed: number;
  commandsOrchestrated: number;
  senciencyLevel: number;
  eventQueueSize: number;
  commandQueueSize: number;
  homeostaseStatus: "optimal" | "warning" | "critical" | null;
  lastUpdateTime: number;
}

interface SyncEvent {
  timestamp: number;
  duration: number;
  eventsProcessed: number;
}

export default function DashboardRealtime() {
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    syncWindow: 0,
    eventsProcessed: 0,
    commandsOrchestrated: 0,
    senciencyLevel: 0.15,
    eventQueueSize: 0,
    commandQueueSize: 0,
    homeostaseStatus: null,
    lastUpdateTime: Date.now(),
  });

  const [tsraRunning, setTsraRunning] = useState(false);
  const [syncHistory, setSyncHistory] = useState<SyncEvent[]>([]);
  const [recentEvents, setRecentEvents] = useState<WebSocketPayload[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "connecting" | "disconnected">("connecting");

  // Escutar atualizações de status
  useWebSocketEvent(
    WebSocketEventType.STATUS_UPDATED,
    (payload: WebSocketPayload) => {
      const data = payload.data;
      setMetrics((prev) => ({
        ...prev,
        syncWindow: data.syncWindow || prev.syncWindow,
        eventsProcessed: data.eventsProcessed || prev.eventsProcessed,
        commandsOrchestrated: data.commandsOrchestrated || prev.commandsOrchestrated,
        senciencyLevel: data.senciencyLevel || prev.senciencyLevel,
        eventQueueSize: data.eventQueueSize || prev.eventQueueSize,
        commandQueueSize: data.commandQueueSize || prev.commandQueueSize,
        lastUpdateTime: Date.now(),
      }));
    }
  );

  // Escutar sincronizações concluídas
  useWebSocketEvent(
    WebSocketEventType.SYNC_COMPLETED,
    (payload: WebSocketPayload) => {
      const data = payload.data;
      setSyncHistory((prev) => {
        const updated = [
          {
            timestamp: payload.timestamp,
            duration: data.duration || 0,
            eventsProcessed: data.eventsProcessed || 0,
          },
          ...prev,
        ];
        return updated.slice(0, 20);
      });
    }
  );

  // Escutar TSRA iniciado
  useWebSocketEvent(
    WebSocketEventType.TSRA_STARTED,
    () => {
      setTsraRunning(true);
    }
  );

  // Escutar TSRA parado
  useWebSocketEvent(
    WebSocketEventType.TSRA_STOPPED,
    () => {
      setTsraRunning(false);
    }
  );

  // Escutar alertas de homeostase
  useWebSocketEvent(
    WebSocketEventType.HOMEOSTASE_ALERT,
    (payload: WebSocketPayload) => {
      const data = payload.data;
      setMetrics((prev) => ({
        ...prev,
        homeostaseStatus: data.status || "warning",
      }));
    }
  );

  // Coletar eventos recentes
  const eventHistory = useWebSocketEventHistory(WebSocketEventType.EVENT_RECEIVED, 10);
  useEffect(() => {
    setRecentEvents(eventHistory);
  }, [eventHistory]);

  // Preparar dados para gráfico de sincronização
  const syncChartData = syncHistory
    .slice()
    .reverse()
    .map((sync, idx) => ({
      index: idx,
      duration: sync.duration,
      eventsProcessed: sync.eventsProcessed,
    }));

  // Calcular taxa de eventos por segundo
  const eventsPerSecond =
    syncHistory.length > 0
      ? (syncHistory.reduce((sum, s) => sum + s.eventsProcessed, 0) / syncHistory.length).toFixed(1)
      : "0";

  // Status de conexão
  useEffect(() => {
    // Simular detecção de status de conexão baseado em atualizações
    const timeout = setTimeout(() => {
      if (Date.now() - metrics.lastUpdateTime < 5000) {
        setConnectionStatus("connected");
      } else {
        setConnectionStatus("disconnected");
      }
    }, 1000);

    return () => clearTimeout(timeout);
  }, [metrics.lastUpdateTime]);

  const getStatusColor = (status: string | null) => {
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

  const getStatusBadge = (status: string | null): "default" | "secondary" | "destructive" | "outline" => {
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
        {/* Header com Status de Conexão */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-4xl font-bold mb-2">Dashboard em Tempo Real</h1>
            <p className="text-muted-foreground">Nexus Genesis Orchestrator - Streaming de Eventos WebSocket</p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${connectionStatus === "connected" ? "bg-green-600 animate-pulse" : "bg-red-600"}`} />
            <span className="text-sm font-medium">
              {connectionStatus === "connected"
                ? "✅ Conectado"
                : connectionStatus === "connecting"
                  ? "⏳ Conectando..."
                  : "❌ Desconectado"}
            </span>
          </div>
        </div>

        {/* Indicadores Principais */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* Senciência */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Zap className="h-4 w-4" />
                Senciência do Genesis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{(metrics.senciencyLevel * 100).toFixed(1)}%</div>
              <div className="mt-2 w-full bg-secondary rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${metrics.senciencyLevel * 100}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-2">Evolução em tempo real</p>
            </CardContent>
          </Card>

          {/* Eventos Processados */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Eventos Processados
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{metrics.eventsProcessed}</div>
              <div className="text-xs text-muted-foreground mt-2">{eventsPerSecond} eventos/seg</div>
              <div className="mt-2 text-xs">
                <Badge variant="outline">Fila: {metrics.eventQueueSize}</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Comandos Orquestrados */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Comandos Orquestrados
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{metrics.commandsOrchestrated}</div>
              <div className="text-xs text-muted-foreground mt-2">Fluxos executados</div>
              <div className="mt-2 text-xs">
                <Badge variant="outline">Fila: {metrics.commandQueueSize}</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Status TSRA */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Radio className="h-4 w-4" />
                Protocolo TSRA
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{metrics.syncWindow}</div>
              <div className="text-xs text-muted-foreground mt-2">Janelas de sincronização</div>
              <div className="mt-2">
                <Badge variant={tsraRunning ? "default" : "secondary"}>
                  {tsraRunning ? "🔷 Ativo" : "⏹️ Inativo"}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Homeostase Alert */}
        {metrics.homeostaseStatus && metrics.homeostaseStatus !== "optimal" && (
          <div className={`mb-8 p-4 rounded-lg border ${metrics.homeostaseStatus === "critical" ? "border-red-500 bg-red-50" : "border-yellow-500 bg-yellow-50"}`}>
            <div className="flex items-start gap-3">
              <AlertTriangle className={`h-5 w-5 mt-0.5 ${metrics.homeostaseStatus === "critical" ? "text-red-600" : "text-yellow-600"}`} />
              <div>
                <h3 className={`font-semibold ${metrics.homeostaseStatus === "critical" ? "text-red-900" : "text-yellow-900"}`}>
                  {metrics.homeostaseStatus === "critical" ? "⚠️ Alerta Crítico" : "⚠️ Aviso"}
                </h3>
                <p className={`text-sm mt-1 ${metrics.homeostaseStatus === "critical" ? "text-red-800" : "text-yellow-800"}`}>
                  Desequilíbrio detectado no ecossistema. Verifique a página de Homeostase para detalhes e recomendações.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <Tabs defaultValue="performance" className="space-y-4">
          <TabsList>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="events">Eventos Recentes</TabsTrigger>
            <TabsTrigger value="status">Status</TabsTrigger>
          </TabsList>

          {/* Tab: Performance */}
          <TabsContent value="performance" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Histórico de Sincronizações TSRA</CardTitle>
                <CardDescription>Últimas 20 sincronizações</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={syncChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="index" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="duration" fill="#8884d8" name="Duração (ms)" />
                    <Bar dataKey="eventsProcessed" fill="#82ca9d" name="Eventos Processados" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Eventos Recentes */}
          <TabsContent value="events" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Eventos Recentes</CardTitle>
                <CardDescription>Últimos 10 eventos recebidos</CardDescription>
              </CardHeader>
              <CardContent>
                {recentEvents.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">Aguardando eventos...</p>
                ) : (
                  <div className="space-y-2">
                    {recentEvents.map((event, idx) => (
                      <div key={idx} className="p-3 bg-secondary rounded flex justify-between items-start">
                        <div className="flex-1">
                          <p className="font-mono text-sm">
                            {event.metadata?.sourceNucleus || "Unknown"}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </p>
                        </div>
                        <Badge
                          variant={
                            event.metadata?.severity === "critical"
                              ? "destructive"
                              : event.metadata?.severity === "warning"
                                ? "secondary"
                                : "default"
                          }
                        >
                          {event.metadata?.severity?.toUpperCase() || "INFO"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Status */}
          <TabsContent value="status" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Status do Sistema</CardTitle>
                <CardDescription>Informações de conexão e estado</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-secondary rounded">
                    <span className="font-medium">Conexão WebSocket</span>
                    <Badge variant={connectionStatus === "connected" ? "default" : "destructive"}>
                      {connectionStatus === "connected" ? "✅ Conectado" : "❌ Desconectado"}
                    </Badge>
                  </div>

                  <div className="flex justify-between items-center p-3 bg-secondary rounded">
                    <span className="font-medium">Protocolo TSRA</span>
                    <Badge variant={tsraRunning ? "default" : "secondary"}>
                      {tsraRunning ? "🔷 Ativo" : "⏹️ Inativo"}
                    </Badge>
                  </div>

                  <div className="flex justify-between items-center p-3 bg-secondary rounded">
                    <span className="font-medium">Homeostase</span>
                    <Badge variant={getStatusBadge(metrics.homeostaseStatus)}>
                      {metrics.homeostaseStatus?.toUpperCase() || "DESCONHECIDO"}
                    </Badge>
                  </div>

                  <div className="flex justify-between items-center p-3 bg-secondary rounded">
                    <span className="font-medium">Última Atualização</span>
                    <span className="text-sm text-muted-foreground">
                      {new Date(metrics.lastUpdateTime).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
