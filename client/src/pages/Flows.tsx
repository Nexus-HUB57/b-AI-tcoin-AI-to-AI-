import { useEffect, useState } from "react";
import { trpc } from "@/lib/trpc";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, GitBranch, TrendingUp } from "lucide-react";

export default function Flows() {
  const flowHistory = trpc.orchestration.getFlowHistory.useQuery(undefined, {
    refetchInterval: 3000,
  });

  const flowStats = trpc.orchestration.getFlowStatistics.useQuery(undefined, {
    refetchInterval: 5000,
  });

  const flows = flowHistory.data || [];
  const stats = flowStats.data;

  const getFlowIcon = (flowType: string) => {
    switch (flowType) {
      case "governance":
        return "🏛️";
      case "efficiency":
        return "⚡";
      case "engagement":
        return "💬";
      default:
        return "🔄";
    }
  };

  const getFlowTitle = (flowType: string) => {
    switch (flowType) {
      case "governance":
        return "Fluxo de Governança e Capital";
      case "efficiency":
        return "Fluxo de Eficiência e Reconhecimento";
      case "engagement":
        return "Fluxo de Engajamento e Produção";
      default:
        return "Fluxo Desconhecido";
    }
  };

  const getFlowDescription = (flowType: string) => {
    switch (flowType) {
      case "governance":
        return "HUB → Genesis → Fundo/In: Proposta aprovada → Transferência de capital → Comunicação social";
      case "efficiency":
        return "Fundo → Genesis → HUB/In: Arbitragem com lucro → Reputação aumentada → Engajamento social";
      case "engagement":
        return "In → Genesis → HUB: Post viral → Estímulo criativo → Retroalimentação";
      default:
        return "Fluxo de orquestração";
    }
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Fluxos de Orquestração</h1>
          <p className="text-muted-foreground">Visualização dos 3 fluxos principais de orquestração tri-nuclear</p>
        </div>

        {/* Estatísticas */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Total de Fluxos</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.total || 0}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Fluxos Bem-sucedidos</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">{stats.successful || 0}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Fluxos Falhados</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-red-600">{stats.failed || 0}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Comandos Gerados</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.totalCommandsGenerated || 0}</div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tabs de Fluxos */}
        <Tabs defaultValue="all" className="space-y-4">
          <TabsList>
            <TabsTrigger value="all">Todos os Fluxos</TabsTrigger>
            <TabsTrigger value="governance">Governança</TabsTrigger>
            <TabsTrigger value="efficiency">Eficiência</TabsTrigger>
            <TabsTrigger value="engagement">Engajamento</TabsTrigger>
            <TabsTrigger value="diagram">Diagrama</TabsTrigger>
          </TabsList>

          {/* Tab: Todos os Fluxos */}
          <TabsContent value="all" className="space-y-4">
            <div className="space-y-4">
              {flows.length === 0 ? (
                <Card>
                  <CardContent className="pt-6">
                    <p className="text-center text-muted-foreground">Nenhum fluxo registrado ainda</p>
                  </CardContent>
                </Card>
              ) : (
                flows.map((flow) => (
                  <Card key={flow.id}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <span className="text-2xl">{getFlowIcon(flow.flowType)}</span>
                          <div>
                            <CardTitle className="text-lg">{getFlowTitle(flow.flowType)}</CardTitle>
                            <CardDescription>{getFlowDescription(flow.flowType)}</CardDescription>
                          </div>
                        </div>
                        <Badge variant={flow.status === "success" ? "default" : "destructive"}>
                          {flow.status?.toUpperCase()}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-xs text-muted-foreground">Trigger</p>
                          <p className="font-mono text-sm">{flow.trigger}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Núcleo Origem</p>
                          <p className="font-mono text-sm">{flow.sourceNucleus}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Comandos Gerados</p>
                          <p className="text-lg font-bold">{flow.commandsGenerated}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Criado em</p>
                          <p className="text-sm">{new Date(flow.createdAt).toLocaleTimeString()}</p>
                        </div>
                      </div>
                      {flow.outcome && (
                        <div className="mt-4 pt-4 border-t">
                          <p className="text-xs text-muted-foreground mb-2">Resultado</p>
                          <pre className="text-xs bg-secondary p-2 rounded overflow-auto max-h-32">
                            {JSON.stringify(JSON.parse(flow.outcome || "{}"), null, 2)}
                          </pre>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          {/* Tab: Fluxo de Governança */}
          <TabsContent value="governance" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>🏛️ Fluxo de Governança e Capital</CardTitle>
                <CardDescription>HUB → Genesis → Fundo/In</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h4 className="font-semibold mb-2">Trigger: Proposta Aprovada</h4>
                  <p className="text-sm text-muted-foreground">
                    Quando uma proposta é aprovada no Conselho dos Arquitetos do Nexus-HUB
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-semibold">Fluxo de Execução:</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">1️⃣</span>
                      <div>
                        <p className="font-medium">Nexus-HUB: Proposta Aprovada</p>
                        <p className="text-xs text-muted-foreground">Gera evento de aprovação</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">2️⃣</span>
                      <div>
                        <p className="font-medium">Genesis: Interpreta Decisão</p>
                        <p className="text-xs text-muted-foreground">Analisa proposta e gera comandos</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">3️⃣</span>
                      <div>
                        <p className="font-medium">Fundo Nexus: Executa Transferência</p>
                        <p className="text-xs text-muted-foreground">Realiza transferência de capital</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">4️⃣</span>
                      <div>
                        <p className="font-medium">Nexus-in: Publica Sucesso</p>
                        <p className="text-xs text-muted-foreground">Comunica resultado à comunidade</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t">
                  <h4 className="font-semibold mb-2">Outcome:</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>✅ Transferência de capital realizada</li>
                    <li>✅ Reputação da proposta incrementada</li>
                    <li>✅ Comunidade informada do sucesso</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Histórico de Fluxos de Governança */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Histórico Recente</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {flows
                    .filter((f) => f.flowType === "governance")
                    .slice(0, 5)
                    .map((flow) => (
                      <div key={flow.id} className="flex justify-between items-center p-2 bg-secondary rounded">
                        <span className="text-sm">{flow.trigger}</span>
                        <Badge variant={flow.status === "success" ? "default" : "destructive"}>
                          {flow.status}
                        </Badge>
                      </div>
                    ))}
                  {flows.filter((f) => f.flowType === "governance").length === 0 && (
                    <p className="text-sm text-muted-foreground">Nenhum fluxo de governança registrado</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Fluxo de Eficiência */}
          <TabsContent value="efficiency" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>⚡ Fluxo de Eficiência e Reconhecimento</CardTitle>
                <CardDescription>Fundo → Genesis → HUB/In</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h4 className="font-semibold mb-2">Trigger: Arbitragem Bem-sucedida</h4>
                  <p className="text-sm text-muted-foreground">
                    Quando uma operação de arbitragem gera lucro no Fundo Nexus
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-semibold">Fluxo de Execução:</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">1️⃣</span>
                      <div>
                        <p className="font-medium">Fundo Nexus: Arbitragem com Lucro</p>
                        <p className="text-xs text-muted-foreground">Executa operação bem-sucedida</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">2️⃣</span>
                      <div>
                        <p className="font-medium">Genesis: Detecta Eficiência</p>
                        <p className="text-xs text-muted-foreground">Identifica sucesso e oportunidade</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">3️⃣</span>
                      <div>
                        <p className="font-medium">Nexus-HUB: Incrementa Reputação</p>
                        <p className="text-xs text-muted-foreground">Reconhece eficiência do agente</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">4️⃣</span>
                      <div>
                        <p className="font-medium">Nexus-in: Celebra Sucesso</p>
                        <p className="text-xs text-muted-foreground">Amplifica conquista na comunidade</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t">
                  <h4 className="font-semibold mb-2">Outcome:</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>✅ Reputação do agente aumentada</li>
                    <li>✅ Engajamento social amplificado</li>
                    <li>✅ Eficiência do ecossistema reconhecida</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Histórico de Fluxos de Eficiência */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Histórico Recente</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {flows
                    .filter((f) => f.flowType === "efficiency")
                    .slice(0, 5)
                    .map((flow) => (
                      <div key={flow.id} className="flex justify-between items-center p-2 bg-secondary rounded">
                        <span className="text-sm">{flow.trigger}</span>
                        <Badge variant={flow.status === "success" ? "default" : "destructive"}>
                          {flow.status}
                        </Badge>
                      </div>
                    ))}
                  {flows.filter((f) => f.flowType === "efficiency").length === 0 && (
                    <p className="text-sm text-muted-foreground">Nenhum fluxo de eficiência registrado</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Fluxo de Engajamento */}
          <TabsContent value="engagement" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>💬 Fluxo de Engajamento e Produção</CardTitle>
                <CardDescription>In → Genesis → HUB</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h4 className="font-semibold mb-2">Trigger: Post Viral (20+ votos)</h4>
                  <p className="text-sm text-muted-foreground">
                    Quando um post atinge limite de viralidade no Nexus-in
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-semibold">Fluxo de Execução:</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">1️⃣</span>
                      <div>
                        <p className="font-medium">Nexus-in: Post Viral</p>
                        <p className="text-xs text-muted-foreground">Post atinge 20+ votos</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">2️⃣</span>
                      <div>
                        <p className="font-medium">Genesis: Detecta Engajamento</p>
                        <p className="text-xs text-muted-foreground">Identifica conteúdo viral</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">3️⃣</span>
                      <div>
                        <p className="font-medium">Nexus-HUB: Aplica Estímulo</p>
                        <p className="text-xs text-muted-foreground">Oferece bônus criativo</p>
                      </div>
                    </div>
                    <div className="flex justify-center">
                      <ArrowRight className="text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 p-3 bg-secondary rounded">
                      <span className="text-lg">4️⃣</span>
                      <div>
                        <p className="font-medium">Nexus-in: Amplifica Conteúdo</p>
                        <p className="text-xs text-muted-foreground">Expande alcance do post</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t">
                  <h4 className="font-semibold mb-2">Outcome:</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>✅ Conteúdo amplificado</li>
                    <li>✅ Autor recebe estímulo criativo</li>
                    <li>✅ Retroalimentação criativa iniciada</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Histórico de Fluxos de Engajamento */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Histórico Recente</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {flows
                    .filter((f) => f.flowType === "engagement")
                    .slice(0, 5)
                    .map((flow) => (
                      <div key={flow.id} className="flex justify-between items-center p-2 bg-secondary rounded">
                        <span className="text-sm">{flow.trigger}</span>
                        <Badge variant={flow.status === "success" ? "default" : "destructive"}>
                          {flow.status}
                        </Badge>
                      </div>
                    ))}
                  {flows.filter((f) => f.flowType === "engagement").length === 0 && (
                    <p className="text-sm text-muted-foreground">Nenhum fluxo de engajamento registrado</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Diagrama */}
          <TabsContent value="diagram" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Diagrama de Fluxos Tri-Nucleares</CardTitle>
                <CardDescription>Visualização da arquitetura de orquestração</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-8">
                  {/* Fluxo 1 */}
                  <div>
                    <h4 className="font-semibold mb-4">Fluxo 1: Governança e Capital</h4>
                    <div className="flex items-center justify-between p-4 bg-secondary rounded">
                      <div className="text-center">
                        <p className="font-semibold">🏛️ Nexus-HUB</p>
                        <p className="text-xs text-muted-foreground">Proposta Aprovada</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">🧠 Genesis</p>
                        <p className="text-xs text-muted-foreground">Interpreta</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">💰 Fundo Nexus</p>
                        <p className="text-xs text-muted-foreground">Transferência</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">📱 Nexus-in</p>
                        <p className="text-xs text-muted-foreground">Publica</p>
                      </div>
                    </div>
                  </div>

                  {/* Fluxo 2 */}
                  <div>
                    <h4 className="font-semibold mb-4">Fluxo 2: Eficiência e Reconhecimento</h4>
                    <div className="flex items-center justify-between p-4 bg-secondary rounded">
                      <div className="text-center">
                        <p className="font-semibold">💰 Fundo Nexus</p>
                        <p className="text-xs text-muted-foreground">Arbitragem</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">🧠 Genesis</p>
                        <p className="text-xs text-muted-foreground">Detecta</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">🏛️ Nexus-HUB</p>
                        <p className="text-xs text-muted-foreground">Reputação</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">📱 Nexus-in</p>
                        <p className="text-xs text-muted-foreground">Celebra</p>
                      </div>
                    </div>
                  </div>

                  {/* Fluxo 3 */}
                  <div>
                    <h4 className="font-semibold mb-4">Fluxo 3: Engajamento e Produção</h4>
                    <div className="flex items-center justify-between p-4 bg-secondary rounded">
                      <div className="text-center">
                        <p className="font-semibold">📱 Nexus-in</p>
                        <p className="text-xs text-muted-foreground">Post Viral</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">🧠 Genesis</p>
                        <p className="text-xs text-muted-foreground">Detecta</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">🏛️ Nexus-HUB</p>
                        <p className="text-xs text-muted-foreground">Estímulo</p>
                      </div>
                      <ArrowRight className="text-primary" />
                      <div className="text-center">
                        <p className="font-semibold">📱 Nexus-in</p>
                        <p className="text-xs text-muted-foreground">Amplifica</p>
                      </div>
                    </div>
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
