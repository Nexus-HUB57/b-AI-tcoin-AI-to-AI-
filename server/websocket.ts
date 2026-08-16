import { Server as HTTPServer } from "http";
import { Server as SocketIOServer, Socket } from "socket.io";
import { NexusOrchestrator } from "./orchestrator";
import { DecisionEngine } from "./decisionEngine";
import { HomeostaseAnalyzer } from "./homeostaseAnalyzer";

/**
 * WebSocket Event Types
 */
export enum WebSocketEventType {
  // Sincronização TSRA
  SYNC_STARTED = "sync:started",
  SYNC_COMPLETED = "sync:completed",
  SYNC_FAILED = "sync:failed",

  // Eventos
  EVENT_RECEIVED = "event:received",
  EVENT_PROCESSED = "event:processed",
  EVENT_QUEUE_UPDATED = "event:queue:updated",

  // Comandos
  COMMAND_GENERATED = "command:generated",
  COMMAND_EXECUTED = "command:executed",
  COMMAND_QUEUE_UPDATED = "command:queue:updated",

  // Fluxos
  FLOW_TRIGGERED = "flow:triggered",
  FLOW_COMPLETED = "flow:completed",
  FLOW_FAILED = "flow:failed",

  // Homeostase
  HOMEOSTASE_UPDATED = "homeostase:updated",
  HOMEOSTASE_ALERT = "homeostase:alert",

  // Genesis
  GENESIS_EVOLVED = "genesis:evolved",
  GENESIS_EXPERIENCE = "genesis:experience",

  // Status
  STATUS_UPDATED = "status:updated",
  NUCLEUS_STATUS_CHANGED = "nucleus:status:changed",

  // Controle
  TSRA_STARTED = "tsra:started",
  TSRA_STOPPED = "tsra:stopped",
}

/**
 * WebSocket Payload Types
 */
export interface WebSocketPayload {
  timestamp: number;
  data: any;
  metadata?: {
    sourceNucleus?: string;
    flowType?: string;
    severity?: "info" | "warning" | "critical";
  };
}

/**
 * WebSocket Manager
 */
export class WebSocketManager {
  private io: SocketIOServer | null = null;
  private orchestrator: NexusOrchestrator | null = null;
  private decisionEngine: DecisionEngine | null = null;
  private homeostaseAnalyzer: HomeostaseAnalyzer | null = null;
  private connectedClients: Map<string, Socket> = new Map();
  private eventEmitters: Map<string, Function> = new Map();

  /**
   * Inicializar WebSocket Manager
   */
  initialize(
    httpServer: HTTPServer,
    orchestrator: NexusOrchestrator,
    decisionEngine: DecisionEngine,
    homeostaseAnalyzer: HomeostaseAnalyzer
  ) {
    this.orchestrator = orchestrator;
    this.decisionEngine = decisionEngine;
    this.homeostaseAnalyzer = homeostaseAnalyzer;

    // Criar servidor Socket.IO
    this.io = new SocketIOServer(httpServer, {
      cors: {
        origin: "*",
        methods: ["GET", "POST"],
      },
      transports: ["websocket", "polling"],
      pingInterval: 25000,
      pingTimeout: 60000,
    });

    // Configurar handlers de conexão
    this.setupConnectionHandlers();

    // Iniciar emissores de eventos
    this.startEventEmitters();

    console.log("✅ WebSocket Manager inicializado");
  }

  /**
   * Configurar handlers de conexão
   */
  private setupConnectionHandlers() {
    if (!this.io) return;

    this.io.on("connection", (socket: Socket) => {
      const clientId = socket.id;
      this.connectedClients.set(clientId, socket);

      console.log(`🔌 Cliente conectado: ${clientId} (Total: ${this.connectedClients.size})`);

      // Enviar status inicial
      socket.emit(WebSocketEventType.STATUS_UPDATED, {
        timestamp: Date.now(),
        data: this.orchestrator?.getStatus(),
      });

      // Handler de desconexão
      socket.on("disconnect", () => {
        this.connectedClients.delete(clientId);
        console.log(`🔌 Cliente desconectado: ${clientId} (Total: ${this.connectedClients.size})`);
      });

      // Handler de erro
      socket.on("error", (error: any) => {
        console.error(`❌ Erro WebSocket (${clientId}):`, error);
      });

      // Handler customizado de ping (keep-alive)
      socket.on("client:ping", () => {
        socket.emit("server:pong", { timestamp: Date.now() });
      });
    });
  }

  /**
   * Iniciar emissores de eventos
   */
  private startEventEmitters() {
    // Emitir status a cada 500ms
    const statusEmitter = setInterval(() => {
      if (this.orchestrator) {
        this.broadcast(WebSocketEventType.STATUS_UPDATED, {
          timestamp: Date.now(),
          data: this.orchestrator.getStatus(),
        });
      }
    }, 500);

    this.eventEmitters.set("status", () => clearInterval(statusEmitter));

    // Emitir métricas de homeostase a cada 2s
    const homeostaseEmitter = setInterval(async () => {
      if (this.homeostaseAnalyzer) {
        const metrics = await this.homeostaseAnalyzer.getHomeostaseHistory(1);
        if (metrics.length > 0) {
          this.broadcast(WebSocketEventType.HOMEOSTASE_UPDATED, {
            timestamp: Date.now(),
            data: metrics[0],
          });
        }
      }
    }, 2000);

    this.eventEmitters.set("homeostase", () => clearInterval(homeostaseEmitter));
  }

  /**
   * Broadcast para todos os clientes conectados
   */
  broadcast(event: WebSocketEventType | string, payload: WebSocketPayload) {
    if (!this.io) return;

    this.io.emit(event, payload);
  }

  /**
   * Enviar para cliente específico
   */
  sendToClient(clientId: string, event: WebSocketEventType | string, payload: WebSocketPayload) {
    const socket = this.connectedClients.get(clientId);
    if (socket) {
      socket.emit(event, payload);
    }
  }

  /**
   * Emitir evento de sincronização iniciada
   */
  emitSyncStarted(syncWindow: number) {
    this.broadcast(WebSocketEventType.SYNC_STARTED, {
      timestamp: Date.now(),
      data: {
        syncWindow,
        status: "iniciado",
      },
    });
  }

  /**
   * Emitir evento de sincronização concluída
   */
  emitSyncCompleted(syncWindow: number, duration: number, eventsProcessed: number) {
    this.broadcast(WebSocketEventType.SYNC_COMPLETED, {
      timestamp: Date.now(),
      data: {
        syncWindow,
        duration,
        eventsProcessed,
        status: "concluído",
      },
    });
  }

  /**
   * Emitir evento recebido
   */
  emitEventReceived(sourceNucleus: string, eventType: string, sentiment: number) {
    this.broadcast(WebSocketEventType.EVENT_RECEIVED, {
      timestamp: Date.now(),
      data: {
        sourceNucleus,
        eventType,
        sentiment,
      },
      metadata: {
        sourceNucleus,
        severity: sentiment < -0.5 ? "critical" : sentiment < 0 ? "warning" : "info",
      },
    });
  }

  /**
   * Emitir evento processado
   */
  emitEventProcessed(eventId: string, sourceNucleus: string) {
    this.broadcast(WebSocketEventType.EVENT_PROCESSED, {
      timestamp: Date.now(),
      data: {
        eventId,
        sourceNucleus,
        status: "processado",
      },
    });
  }

  /**
   * Emitir fila de eventos atualizada
   */
  emitEventQueueUpdated(queueSize: number, maxSize: number) {
    this.broadcast(WebSocketEventType.EVENT_QUEUE_UPDATED, {
      timestamp: Date.now(),
      data: {
        queueSize,
        maxSize,
        percentage: (queueSize / maxSize) * 100,
      },
    });
  }

  /**
   * Emitir comando gerado
   */
  emitCommandGenerated(
    destination: string,
    commandType: string,
    flowType?: string
  ) {
    this.broadcast(WebSocketEventType.COMMAND_GENERATED, {
      timestamp: Date.now(),
      data: {
        destination,
        commandType,
        flowType,
        status: "gerado",
      },
      metadata: {
        flowType,
      },
    });
  }

  /**
   * Emitir comando executado
   */
  emitCommandExecuted(commandId: string, destination: string, success: boolean) {
    this.broadcast(WebSocketEventType.COMMAND_EXECUTED, {
      timestamp: Date.now(),
      data: {
        commandId,
        destination,
        success,
        status: success ? "executado" : "falhou",
      },
      metadata: {
        severity: success ? "info" : "warning",
      },
    });
  }

  /**
   * Emitir fila de comandos atualizada
   */
  emitCommandQueueUpdated(queueSize: number, maxSize: number) {
    this.broadcast(WebSocketEventType.COMMAND_QUEUE_UPDATED, {
      timestamp: Date.now(),
      data: {
        queueSize,
        maxSize,
        percentage: (queueSize / maxSize) * 100,
      },
    });
  }

  /**
   * Emitir fluxo acionado
   */
  emitFlowTriggered(flowType: string, sourceNucleus: string, trigger: string) {
    this.broadcast(WebSocketEventType.FLOW_TRIGGERED, {
      timestamp: Date.now(),
      data: {
        flowType,
        sourceNucleus,
        trigger,
        status: "acionado",
      },
      metadata: {
        flowType,
        sourceNucleus,
      },
    });
  }

  /**
   * Emitir fluxo concluído
   */
  emitFlowCompleted(flowType: string, commandsGenerated: number, success: boolean) {
    this.broadcast(WebSocketEventType.FLOW_COMPLETED, {
      timestamp: Date.now(),
      data: {
        flowType,
        commandsGenerated,
        success,
        status: success ? "concluído" : "falhou",
      },
      metadata: {
        flowType,
        severity: success ? "info" : "warning",
      },
    });
  }

  /**
   * Emitir alerta de homeostase
   */
  emitHomeostaseAlert(status: string, issues: string[], riskLevel: number) {
    this.broadcast(WebSocketEventType.HOMEOSTASE_ALERT, {
      timestamp: Date.now(),
      data: {
        status,
        issues,
        riskLevel,
      },
      metadata: {
        severity:
          status === "critical" ? "critical" : status === "warning" ? "warning" : "info",
      },
    });
  }

  /**
   * Emitir evolução de senciência
   */
  emitGenesisEvolved(senciencyLevel: number, delta: number) {
    this.broadcast(WebSocketEventType.GENESIS_EVOLVED, {
      timestamp: Date.now(),
      data: {
        senciencyLevel,
        delta,
        status: "evoluído",
      },
    });
  }

  /**
   * Emitir experiência do Genesis
   */
  emitGenesisExperience(experienceType: string, impact: string, delta: number) {
    this.broadcast(WebSocketEventType.GENESIS_EXPERIENCE, {
      timestamp: Date.now(),
      data: {
        experienceType,
        impact,
        delta,
      },
    });
  }

  /**
   * Emitir TSRA iniciado
   */
  emitTSRAStarted() {
    this.broadcast(WebSocketEventType.TSRA_STARTED, {
      timestamp: Date.now(),
      data: {
        status: "iniciado",
      },
    });
  }

  /**
   * Emitir TSRA parado
   */
  emitTSRAStopped() {
    this.broadcast(WebSocketEventType.TSRA_STOPPED, {
      timestamp: Date.now(),
      data: {
        status: "parado",
      },
    });
  }

  /**
   * Obter número de clientes conectados
   */
  getConnectedClientsCount(): number {
    return this.connectedClients.size;
  }

  /**
   * Parar WebSocket Manager
   */
  stop() {
    // Limpar emissores
    this.eventEmitters.forEach((cleanup) => cleanup());
    this.eventEmitters.clear();

    // Desconectar todos os clientes
    if (this.io) {
      this.io.disconnectSockets();
      this.io.close();
    }

    this.connectedClients.clear();
    console.log("⏹️ WebSocket Manager parado");
  }
}

// Singleton
let wsManager: WebSocketManager | null = null;

export function getWebSocketManager(): WebSocketManager {
  if (!wsManager) {
    wsManager = new WebSocketManager();
  }
  return wsManager;
}
