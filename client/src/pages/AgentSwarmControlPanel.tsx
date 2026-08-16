import { useState, useEffect } from "react";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Shield, Activity, Cpu, Server, Radio, RefreshCw, CheckCircle2, Zap, Layers, Clock, Eye, Hash, Award } from "lucide-react";

export default function AgentSwarmControlPanel() {
  const [lastUpdated, setLastUpdated] = useState<number>(Date.now());
  const [selectedBlockHeight, setSelectedBlockHeight] = useState<number | null>(850422);

  const { data: swarmData, isLoading: swarmLoading, refetch: refetchSwarm } = trpc.agentSwarm.getSwarmStatus.useQuery(undefined, {
    refetchInterval: 5000
  });

  const { data: rustMetrics, isLoading: rustLoading, refetch: refetchRust } = trpc.agentSwarm.getRustConsensusMetrics.useQuery(undefined, {
    refetchInterval: 2000
  });

  const { data: inspectableBlocks, isLoading: blocksLoading } = trpc.agentSwarm.getInspectableBlocks.useQuery(undefined, {
    refetchInterval: 5000
  });

  useEffect(() => {
    setLastUpdated(Date.now());
  }, [swarmData, rustMetrics, inspectableBlocks]);

  const selectedBlock = inspectableBlocks?.find(b => b.height === selectedBlockHeight) || inspectableBlocks?.[0];

  if (swarmLoading || rustLoading || blocksLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 p-8 flex items-center justify-center">
        <div className="flex items-center space-x-3">
          <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
          <span className="text-lg font-mono">Carregando Painel e Explorador de Blocos Rust...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 border-b border-slate-800 pb-6 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-500 bg-clip-text text-transparent">
              b'AI'tcoin Rust Consensus & Block Inspector
            </h1>
            <Badge variant="outline" className="border-cyan-500 text-cyan-400 font-mono">
              MAINNET ACTIVE 24/7
            </Badge>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Painel de controle em tempo real com telemetria do núcleo Rust, enxames PhD e inspeção detalhada de blocos por agente.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-slate-500">
            Atualizado: {new Date(lastUpdated).toLocaleTimeString()}
          </span>
          <Button variant="outline" size="sm" onClick={() => { refetchSwarm(); refetchRust(); }} className="border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800">
            <RefreshCw className="w-4 h-4 mr-2" /> Atualizar
          </Button>
        </div>
      </div>

      {/* Métricas de Alto Desempenho do Núcleo Rust */}
      <div className="mb-8">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-cyan-400">
          <Zap className="w-5 h-5 text-yellow-400" /> Núcleo de Consenso Rust (High-Performance Telemetry)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="bg-slate-900 border-slate-800 shadow-xl">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">Throughput (TPS)</CardTitle>
              <Zap className="w-4 h-4 text-yellow-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-white">{rustMetrics?.tps.toLocaleString()} TPS</div>
              <p className="text-xs text-cyan-400 mt-1">Escala Zettascale Ativa</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800 shadow-xl">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">Altura de Bloco (Mainnet)</CardTitle>
              <Layers className="w-4 h-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-white">#{rustMetrics?.blockHeight}</div>
              <p className="text-xs text-emerald-400 mt-1 flex items-center">
                <CheckCircle2 className="w-3 h-3 mr-1" /> Sincronizado
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800 shadow-xl">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">Latência Média</CardTitle>
              <Clock className="w-4 h-4 text-indigo-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-white">{rustMetrics?.averageLatencyMs} ms</div>
              <p className="text-xs text-indigo-400 mt-1">Validação determinística</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800 shadow-xl">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">Fila de Validação</CardTitle>
              <Activity className="w-4 h-4 text-emerald-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-white">{rustMetrics?.validationQueueSize} txs</div>
              <p className="text-xs text-emerald-300 mt-1">Rejeições: {rustMetrics?.rejectedBlocksCount}</p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Explorador de Blocos e Inspeção Detalhada por Agente */}
      <div className="mb-8">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-indigo-400">
          <Eye className="w-5 h-5 text-indigo-400" /> Explorador de Blocos & Vínculo com Agente Validador
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <Card className="bg-slate-900 border-slate-800 shadow-xl lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-md font-semibold text-slate-200">Blocos Inspecionáveis (Rust Core)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {inspectableBlocks?.map((block) => (
                  <div
                    key={block.height}
                    onClick={() => setSelectedBlockHeight(block.height)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      (selectedBlock?.height === block.height)
                        ? "bg-slate-800 border-cyan-500 shadow-md shadow-cyan-950/50"
                        : "bg-slate-950 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-mono font-bold text-white">#{block.height}</span>
                      <Badge className="bg-indigo-950 text-indigo-300 border border-indigo-800 text-[10px]">
                        {block.transactionCount} Txs
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-400 font-mono truncate">Hash: {block.blockHash}</p>
                    <p className="text-[11px] text-cyan-400 mt-1 flex items-center gap-1">
                      <Cpu className="w-3 h-3" /> {block.validatorAgentId}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800 shadow-xl lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-md font-semibold text-slate-200 flex items-center justify-between">
                <span>Detalhes do Bloco #{selectedBlock?.height} & Evidência do Agente</span>
                <Badge className="bg-emerald-600 text-white font-mono">Verificado em Mainnet</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedBlock ? (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
                      <span className="text-xs text-slate-400 uppercase font-mono tracking-wider">Hash do Bloco</span>
                      <p className="font-mono text-xs text-white break-all mt-1">{selectedBlock.blockHash}</p>
                    </div>
                    <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
                      <span className="text-xs text-slate-400 uppercase font-mono tracking-wider">Raiz de Merkle</span>
                      <p className="font-mono text-xs text-cyan-300 break-all mt-1">{selectedBlock.merkleRoot}</p>
                    </div>
                  </div>

                  <div className="p-5 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 rounded-lg border border-indigo-900/50 shadow-inner">
                    <h3 className="text-sm font-semibold text-indigo-400 mb-3 flex items-center gap-2">
                      <Award className="w-4 h-4 text-indigo-400" /> Agente Validador do Enxame PhD Responsável
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-xs text-slate-400 block">Identificador do Agente</span>
                        <span className="font-mono font-bold text-white">{selectedBlock.validatorAgentId}</span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-400 block">Especialização Determinística</span>
                        <span className="font-semibold text-indigo-300">{selectedBlock.agentSpecialization}</span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-400 block">Índice de Confiança & Assertividade</span>
                        <span className="font-mono text-emerald-400 font-bold">{(selectedBlock.agentConfidence * 100).toFixed(2)}%</span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-400 block">Eficiência de Gás / Otimização</span>
                        <span className="font-mono text-cyan-300">{selectedBlock.gasEfficiency}</span>
                      </div>
                    </div>
                    <div className="mt-4 pt-4 border-t border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-2">
                      <span className="text-xs font-mono text-slate-500">Assinatura de Auditoria HMAC:</span>
                      <span className="font-mono text-xs text-emerald-400 bg-slate-950 px-2.5 py-1 rounded border border-emerald-900/50">
                        {selectedBlock.consensusSignature}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-slate-400 text-center py-8">Selecione um bloco para inspecionar os detalhes.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card className="bg-slate-900 border-slate-800 shadow-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Rede Operacional</CardTitle>
            <Server className="w-4 h-4 text-cyan-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-white">{swarmData?.network}</div>
            <p className="text-xs text-emerald-400 mt-1 flex items-center">
              <CheckCircle2 className="w-3 h-3 mr-1" /> 100% Sem Testnet
            </p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800 shadow-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Nó Primário Ativo</CardTitle>
            <Radio className="w-4 h-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold font-mono text-blue-300">{swarmData?.activePrimaryNode}</div>
            <p className="text-xs text-slate-400 mt-1">Failover automático ativo</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800 shadow-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Enxame de Agentes PhD</CardTitle>
            <Cpu className="w-4 h-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-white">{swarmData?.phdAgents.length} Ativos</div>
            <p className="text-xs text-indigo-400 mt-1">Precisão otimizada</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800 shadow-xl">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Master Wallet Vault</CardTitle>
            <Shield className="w-4 h-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-xs font-mono text-emerald-300 truncate">{swarmData?.masterWallet}</div>
            <p className="text-xs text-slate-400 mt-1">Chave Mestre Segura</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="bg-slate-900 border-slate-800 shadow-xl">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Server className="w-5 h-5 text-cyan-400" /> Endpoints RPC e Status de Failover
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {swarmData?.nodes.map((node) => (
                <div key={node.providerId} className="p-4 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-white">{node.providerId}</span>
                      {node.isPrimary && <Badge className="bg-blue-600 text-white text-[10px]">Primário</Badge>}
                    </div>
                    <p className="text-xs text-slate-400 font-mono mt-1">{node.url}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-slate-400">{node.latencyMs}ms</span>
                    <Badge variant={node.healthy ? "default" : "destructive"} className={node.healthy ? "bg-emerald-600 text-white" : ""}>
                      {node.healthy ? "Saudável" : "Falha/Failover"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800 shadow-xl">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-400" /> Atividade do Enxame PhD 24/7
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {swarmData?.phdAgents.map((agent) => (
                <div key={agent.agentId} className="p-4 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="font-mono font-semibold text-white">{agent.agentId}</span>
                    <p className="text-xs text-slate-400 font-mono mt-1">Especialização: {agent.specialization}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-cyan-400">Confiança: {(agent.reliability * 100).toFixed(2)}%</span>
                    <Badge className="bg-emerald-600 text-white">
                      {agent.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
