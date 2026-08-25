import { NexusOrchestrator } from "./orchestrator";
import { DecisionEngine } from "./decisionEngine";
import { HomeostaseAnalyzer } from "./homeostaseAnalyzer";
import { getWebSocketManager } from "./websocket";

/**
 * WebSocket Orchestrator Integration
 * Integra o NexusOrchestrator com o WebSocket Manager
 * para emitir eventos em tempo real
 */
export class OrchestratorWebSocketBridge {
  private orchestrator: NexusOrchestrator;
  private decisionEngine: DecisionEngine;
  private homeostaseAnalyzer: HomeostaseAnalyzer;
  private wsManager = getWebSocketManager();
  private lastSyncWindow = 0;
  private lastEventQueueSize = 0;
  private lastCommandQueueSize = 0;

  constructor(
    orchestrator: NexusOrchestrator,
    decisionEngine: DecisionEngine,
    homeostaseAnalyzer: HomeostaseAnalyzer
  ) {
    this.orchestrator = orchestrator;
    this.decisionEngine = decisionEngine;
    this.homeostaseAnalyzer = homeostaseAnalyzer;
  }

  /**
   * Iniciar monitoramento de eventos
   */
  startMonitoring() {
    // Monitorar sincronização TSRA
    this.monitorTSRA();

    // Monitorar filas
    this.monitorQueues();

    // Monitorar homeostase
    this.monitorHomeostase();

    console.log("✅ WebSocket Bridge iniciado");
  }

  /**
   * Monitorar sincronização TSRA
   */
  private monitorTSRA() {
    setInterval(() => {
      const status = this.orchestrator.getStatus();

      // Detectar mudança de syncWindow
      if (status.syncWindow !== this.lastSyncWindow) {
        const lastSyncTime =
          status.lastSyncTime && typeof status.lastSyncTime === "object" && "getTime" in status.lastSyncTime
            ? (status.lastSyncTime as any).getTime()
            : typeof status.lastSyncTime === "number"
              ? status.lastSyncTime
              : 0;
        this.wsManager.emitSyncCompleted(
          status.syncWindow,
          Date.now() - lastSyncTime,
          status.eventsProcessed
        );
        this.lastSyncWindow = status.syncWindow;
      }

      // Monitorar evolução de senciência
      if (status.senciencyLevel > 0.15) {
        this.wsManager.emitGenesisEvolved(status.senciencyLevel, 0.01);
      }
    }, 1000);
  }

  /**
   * Monitorar filas
   */
  private monitorQueues() {
    setInterval(() => {
      const eventQueue = this.orchestrator.getEventQueue();
      const commandQueue = this.orchestrator.getCommandQueue();

      // Emitir atualização de fila de eventos se mudou
      if (eventQueue.size !== this.lastEventQueueSize) {
        this.wsManager.emitEventQueueUpdated(eventQueue.size, eventQueue.maxSize);
        this.lastEventQueueSize = eventQueue.size;

        // Emitir eventos recentes
        if (eventQueue.events.length > 0) {
          const recentEvent = eventQueue.events[eventQueue.events.length - 1];
          this.wsManager.emitEventReceived(
            (recentEvent as any).sourceNucleus || "unknown",
            (recentEvent as any).eventType || "unknown",
            (recentEvent as any).sentimentScore || 0
          );
        }
      }

      // Emitir atualização de fila de comandos se mudou
      if (commandQueue.size !== this.lastCommandQueueSize) {
        this.wsManager.emitCommandQueueUpdated(commandQueue.size, commandQueue.maxSize);
        this.lastCommandQueueSize = commandQueue.size;

        // Emitir comandos recentes
        if (commandQueue.commands.length > 0) {
          const recentCommand = commandQueue.commands[commandQueue.commands.length - 1];
          this.wsManager.emitCommandGenerated(
            (recentCommand as any).destination || "unknown",
            (recentCommand as any).commandType || "unknown"
          );
        }
      }
    }, 500);
  }

  /**
   * Monitorar homeostase
   */
  private monitorHomeostase() {
    setInterval(async () => {
      const metrics = await this.homeostaseAnalyzer.getHomeostaseHistory(1);

      if (metrics.length > 0) {
        const metric = metrics[0];

        // Emitir alerta se status crítico
        if (metric.equilibriumStatus === "critical") {
          const issues = metric.issues ? JSON.parse(metric.issues as any) : [];
          this.wsManager.emitHomeostaseAlert(
            metric.equilibriumStatus,
            issues,
            100 - (metric.activeAgents || 0) * 5 // Cálculo simples de risco
          );
        }
      }
    }, 2000);
  }

  /**
   * Emitir evento de fluxo acionado
   */
  emitFlowTriggered(flowType: string, sourceNucleus: string, trigger: string) {
    this.wsManager.emitFlowTriggered(flowType, sourceNucleus, trigger);
  }

  /**
   * Emitir evento de fluxo concluído
   */
  emitFlowCompleted(flowType: string, commandsGenerated: number, success: boolean) {
    this.wsManager.emitFlowCompleted(flowType, commandsGenerated, success);
  }

  /**
   * Emitir evento de comando executado
   */
  emitCommandExecuted(commandId: string, destination: string, success: boolean) {
    this.wsManager.emitCommandExecuted(commandId, destination, success);
  }

  /**
   * Emitir TSRA iniciado
   */
  emitTSRAStarted() {
    this.wsManager.emitTSRAStarted();
  }

  /**
   * Emitir TSRA parado
   */
  emitTSRAStopped() {
    this.wsManager.emitTSRAStopped();
  }

  /**
   * Parar monitoramento
   */
  stop() {
    console.log("⏹️ WebSocket Bridge parado");
  }
}

// Singleton
let bridge: OrchestratorWebSocketBridge | null = null;

export function getOrchestratorWebSocketBridge(
  orchestrator: NexusOrchestrator,
  decisionEngine: DecisionEngine,
  homeostaseAnalyzer: HomeostaseAnalyzer
): OrchestratorWebSocketBridge {
  if (!bridge) {
    bridge = new OrchestratorWebSocketBridge(orchestrator, decisionEngine, homeostaseAnalyzer);
  }
  return bridge;
}
