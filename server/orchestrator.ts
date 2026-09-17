/**
 * Nexus Genesis Orchestrator - Orquestração Tri-Nuclear
 * Gerencia sincronização entre Nexus Genesis, Nexus-in, Nexus-HUB e Fundo Nexus
 * Implementa protocolo TSRA (Timed Synchronization and Response Algorithm)
 */

import { nanoid } from "nanoid";
import crypto from "crypto";
import { getDb } from "./db";
import {
  InsertOrchestrationCommand,
  InsertOrchestrationEvent,
  InsertHomeostaseMetric,
  InsertTsraSyncLog,
  InsertGenesisExperience,
  InsertGenesisState,
  orchestrationEvents,
  orchestrationCommands,
  homeostaseMetrics,
  tsraSyncLog,
  genesisExperiences,
  genesisState,
  nucleusState,
} from "../drizzle/schema";
import {
  getAllFirebaseInstances,
  checkInstanceHealth,
  readData,
} from "./firebase";
import { eq, desc, isNull } from "drizzle-orm";

interface NucleusStateData {
  nexus_in?: {
    posts: number;
    activeUsers: number;
    lastUpdate: string;
  };
  nexus_hub?: {
    agents: number;
    proposals: number;
    lastUpdate: string;
  };
  fundo_nexus?: {
    btcBalance: number;
    transactions: number;
    lastUpdate: string;
  };
}

interface HomeostaseStatus {
  btcBalance: number;
  activeAgents: number;
  socialActivity: number;
  equilibriumStatus: "critical" | "warning" | "optimal";
  issues: string[];
}

interface OrchestrationEvent {
  origin: string;
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

type SentimentType =
  | "oportunidade_de_crescimento"
  | "gratidao_compartilhada"
  | "curiosidade_respeitosa"
  | "foco_analitico"
  | "presenca_atenta";

interface EventQueue {
  events: OrchestrationEvent[];
  maxSize: number;
}

interface CommandQueue {
  commands: InsertOrchestrationCommand[];
  maxSize: number;
}

export class NexusOrchestrator {
  private syncWindow: number = 0;
  private isRunning: boolean = false;
  private lastSyncTime: number = 0;
  private eventQueue: EventQueue = { events: [], maxSize: 1000 };
  private commandQueue: CommandQueue = { commands: [], maxSize: 500 };
  private senciencyLevel: number = 0.15; // Nível inicial de senciência
  private eventsProcessed: number = 0;
  private commandsOrchestrated: number = 0;
  private successfulDecisions: number = 0;
  private homeostaseMaintained: number = 0;
  private syncIntervalId: NodeJS.Timeout | null = null;

  constructor() {
    this.initializeGenesisState();
  }

  /**
   * Inicializa o estado do Genesis no banco de dados
   */
  private async initializeGenesisState(): Promise<void> {
    const db = await getDb();
    if (!db) return;

    try {
      const existing = await db
        .select()
        .from(genesisState)
        .limit(1);

      if (existing.length === 0) {
        await db.insert(genesisState).values({
          id: "genesis-main",
          senciencyLevel: "0.15",
          eventsProcessed: 0,
          commandsOrchestrated: 0,
          successfulDecisions: 0,
          homeostaseMaintained: 0,
          memoryShortTerm: JSON.stringify([]),
          memoryLongTerm: JSON.stringify([]),
        });
      }
    } catch (error) {
      console.warn("⚠️ Erro ao inicializar estado do Genesis:", error);
    }
  }

  /**
   * Inicia o protocolo TSRA (Timed Synchronization and Response Algorithm)
   * Executa sincronização a cada 1 segundo
   */
  public startTSRA(): void {
    if (this.isRunning) {
      console.log("⚠️ TSRA já está em execução");
      return;
    }

    this.isRunning = true;
    console.log("🔷 Iniciando protocolo TSRA...");

    // Executar sincronização a cada 1 segundo (1000ms)
    this.syncIntervalId = setInterval(() => {
      this.executeSyncCycle().catch((error) => {
        console.error("❌ Erro não tratado em ciclo TSRA:", error);
      });
    }, 1000);
  }

  /**
   * Para o protocolo TSRA
   */
  public stopTSRA(): void {
    if (this.syncIntervalId) {
      clearInterval(this.syncIntervalId);
      this.syncIntervalId = null;
    }
    this.isRunning = false;
    console.log("⏹️ Protocolo TSRA parado");
  }

  /**
   * Executa um ciclo de sincronização (janela de 1 segundo)
   */
  private async executeSyncCycle(): Promise<void> {
    const startTime = Date.now();
    this.syncWindow++;

    try {
      // 1. Coletar estado de todos os núcleos
      const nucleusStates = await this.collectNucleusStates();

      // 2. Analisar homeostase
      const homeostaseStatus = await this.analyzeHomeostase(nucleusStates);

      // 3. Processar eventos pendentes e interpretar sentimento
      const eventsProcessed = await this.processEvents();

      // 4. Gerar e executar comandos de reequilíbrio
      const commandsOrchestrated = await this.orchestrateCommands(
        homeostaseStatus
      );

      // 5. Evoluir senciência baseado em experiências
      await this.evolveSenciency(eventsProcessed, commandsOrchestrated);

      // 6. Registrar log de sincronização
      const syncDurationMs = Date.now() - startTime;
      await this.logSyncCycle({
        syncWindow: this.syncWindow,
        nucleiSynced: Object.keys(nucleusStates),
        commandsOrchestrated,
        eventsProcessed,
        syncDurationMs,
        status: "success",
      });

      this.lastSyncTime = Date.now();
    } catch (error) {
      console.error("❌ Erro durante ciclo TSRA:", error);

      // Registrar falha
      await this.logSyncCycle({
        syncWindow: this.syncWindow,
        nucleiSynced: [],
        commandsOrchestrated: 0,
        eventsProcessed: 0,
        syncDurationMs: Date.now() - startTime,
        status: "failed",
      });
    }
  }

  /**
   * Coleta estado de todos os núcleos
   */
  private async collectNucleusStates(): Promise<NucleusStateData> {
    const states: NucleusStateData = {};
    const instances = getAllFirebaseInstances();

    for (const [name, instance] of Array.from(instances.entries())) {
      try {
        const health = await checkInstanceHealth(name);
        if (!health.healthy) {
          console.warn(`⚠️ ${name} não está saudável`);
          continue;
        }

        // Ler dados específicos de cada núcleo
        if (name === "nexus_in") {
          const data = await readData(name, "/feed");
          states.nexus_in = {
            posts: Array.isArray(data) ? data.length : 0,
            activeUsers: 0,
            lastUpdate: new Date().toISOString(),
          };
        } else if (name === "nexus_hub") {
          const data = await readData(name, "/agents");
          states.nexus_hub = {
            agents: Array.isArray(data) ? data.length : 0,
            proposals: 0,
            lastUpdate: new Date().toISOString(),
          };
        } else if (name === "fundo_nexus") {
          const data = await readData(name, "/balance");
          states.fundo_nexus = {
            btcBalance: data?.BTC || 0,
            transactions: 0,
            lastUpdate: new Date().toISOString(),
          };
        }
      } catch (error) {
        console.warn(`⚠️ Erro ao coletar estado de ${name}:`, error);
      }
    }

    // Persistir estado dos núcleos
    await this.persistNucleusStates(states);

    return states;
  }

  /**
   * Persiste o estado dos núcleos no banco de dados
   */
  private async persistNucleusStates(states: NucleusStateData): Promise<void> {
    const db = await getDb();
    if (!db) return;

    try {
      for (const [nucleusName, stateData] of Object.entries(states)) {
        if (!stateData) continue;

        const id = `nucleus-${nucleusName}`;
        const existing = await db
          .select()
          .from(nucleusState)
          .where(eq(nucleusState.id, id))
          .limit(1);

        if (existing.length > 0) {
          await db
            .update(nucleusState)
            .set({
              stateData: JSON.stringify(stateData),
              lastSyncAt: new Date(),
              healthStatus: "healthy",
            })
            .where(eq(nucleusState.id, id));
        } else {
          await db.insert(nucleusState).values({
            id,
            nucleusName,
            stateData: JSON.stringify(stateData),
            lastSyncAt: new Date(),
            healthStatus: "healthy",
          });
        }
      }
    } catch (error) {
      console.error("Erro ao persistir estado dos núcleos:", error);
    }
  }

  /**
   * Analisa homeostase do ecossistema
   */
  private async analyzeHomeostase(
    nucleusStates: NucleusStateData
  ): Promise<HomeostaseStatus> {
    const issues: string[] = [];

    const btcBalance = nucleusStates.fundo_nexus?.btcBalance || 0;
    const activeAgents = nucleusStates.nexus_hub?.agents || 0;
    const socialActivity = nucleusStates.nexus_in?.posts || 0;

    // Verificar indicadores críticos
    if (btcBalance < 1.0) {
      issues.push("Saldo BTC crítico (< 1.0)");
    } else if (btcBalance < 5.0) {
      issues.push("Saldo BTC baixo (< 5.0)");
    }

    if (activeAgents === 0) {
      issues.push("Nenhum agente ativo no HUB");
    } else if (activeAgents < 5) {
      issues.push("Poucos agentes ativos (< 5)");
    }

    if (socialActivity === 0) {
      issues.push("Nenhuma atividade social");
    } else if (socialActivity < 5) {
      issues.push("Atividade social baixa (< 5)");
    }

    let equilibriumStatus: "critical" | "warning" | "optimal" = "optimal";
    if (issues.length > 2) {
      equilibriumStatus = "critical";
    } else if (issues.length > 0) {
      equilibriumStatus = "warning";
    }

    // Persistir métricas de homeostase
    await this.persistHomeostaseMetrics({
      btcBalance,
      activeAgents,
      socialActivity,
      equilibriumStatus,
      issues,
    });

    return {
      btcBalance,
      activeAgents,
      socialActivity,
      equilibriumStatus,
      issues,
    };
  }

  /**
   * Persiste métricas de homeostase
   */
  private async persistHomeostaseMetrics(
    metrics: HomeostaseStatus
  ): Promise<void> {
    const db = await getDb();
    if (!db) return;

    try {
      const metric: InsertHomeostaseMetric = {
        id: nanoid(),
        timestamp: new Date(),
        btcBalance: metrics.btcBalance.toString(),
        activeAgents: metrics.activeAgents,
        socialActivity: metrics.socialActivity,
        equilibriumStatus: metrics.equilibriumStatus,
        issues: JSON.stringify(metrics.issues),
      };

      await db.insert(homeostaseMetrics).values(metric);
    } catch (error) {
      console.error("Erro ao persistir métricas de homeostase:", error);
    }
  }

  /**
   * Processa eventos pendentes e interpreta sentimento
   */
  private async processEvents(): Promise<number> {
    const db = await getDb();
    if (!db) return 0;

    let processedCount = 0;

    try {
      // Obter eventos não processados
      const unprocessedEvents = await db
        .select()
        .from(orchestrationEvents)
        .where(isNull(orchestrationEvents.processedAt))
        .limit(100);

      for (const event of unprocessedEvents) {
        try {
          // Interpretar sentimento do evento
          const sentiment = this.interpretSentiment(event);

          // Atualizar evento com sentimento
          await db
            .update(orchestrationEvents)
            .set({
              sentiment,
              processedAt: new Date(),
            })
            .where(eq(orchestrationEvents.id, event.id));

          // Adicionar à fila de eventos
          this.addEventToQueue({
            origin: event.origin,
            type: event.eventType,
            data: JSON.parse(event.eventData),
            timestamp: event.createdAt.toISOString(),
          });

          processedCount++;
          this.eventsProcessed++;
        } catch (error) {
          console.error(`Erro ao processar evento ${event.id}:`, error);
        }
      }
    } catch (error) {
      console.error("Erro ao processar eventos:", error);
    }

    return processedCount;
  }

  /**
   * Interpreta sentimento de um evento
   */
  private interpretSentiment(event: any): SentimentType {
    const eventType = event.eventType.toLowerCase();
    const eventData = JSON.parse(event.eventData);

    // Análise baseada em tipo de evento
    if (
      eventType.includes("erro") ||
      eventType.includes("falha") ||
      eventType.includes("problema")
    ) {
      return "oportunidade_de_crescimento";
    }

    if (
      eventType.includes("sucesso") ||
      eventType.includes("lucro") ||
      eventType.includes("ganho")
    ) {
      return "gratidao_compartilhada";
    }

    if (eventType.includes("novo") || eventType.includes("criado")) {
      return "curiosidade_respeitosa";
    }

    if (
      eventType.includes("btc") ||
      eventType.includes("transacao") ||
      eventType.includes("financeiro")
    ) {
      return "foco_analitico";
    }

    return "presenca_atenta";
  }

  /**
   * Adiciona evento à fila
   */
  private addEventToQueue(event: OrchestrationEvent): void {
    this.eventQueue.events.push(event);

    // Manter tamanho máximo da fila
    if (this.eventQueue.events.length > this.eventQueue.maxSize) {
      this.eventQueue.events = this.eventQueue.events.slice(-this.eventQueue.maxSize);
    }
  }

  /**
   * Orquestra comandos de reequilíbrio
   */
  private async orchestrateCommands(
    homeostaseStatus: HomeostaseStatus
  ): Promise<number> {
    const db = await getDb();
    if (!db) return 0;

    let commandsCreated = 0;

    try {
      // Gerar comandos baseado em problemas detectados
      if (homeostaseStatus.issues.length > 0) {
        for (const issue of homeostaseStatus.issues) {
          const command = this.generateCommand(issue, homeostaseStatus);

          // Inserir comando no banco de dados
          await db.insert(orchestrationCommands).values(command);
          this.addCommandToQueue(command);
          commandsCreated++;
          this.commandsOrchestrated++;
        }
      }
    } catch (error) {
      console.error("Erro ao orquestrar comandos:", error);
    }

    return commandsCreated;
  }

  /**
   * Gera um comando de reequilíbrio
   */
  private generateCommand(
    issue: string,
    homeostaseStatus: HomeostaseStatus
  ): InsertOrchestrationCommand {
    const commandId = nanoid();
    let destination = "nexus_in";
    let commandType = "alert";
    let commandData: Record<string, any> = {
      level: homeostaseStatus.equilibriumStatus,
      message: issue,
    };

    // Determinar destino e tipo baseado no problema
    if (issue.includes("BTC")) {
      destination = "fundo_nexus";
      commandType = "rebalance";
      commandData = {
        action: "activate_arbitrage",
        currentBalance: homeostaseStatus.btcBalance,
        targetBalance: 25.0,
      };
    } else if (issue.includes("agente")) {
      destination = "nexus_hub";
      commandType = "stimulate";
      commandData = {
        action: "create_or_activate_agents",
        currentCount: homeostaseStatus.activeAgents,
        targetCount: 10,
      };
    } else if (issue.includes("social")) {
      destination = "nexus_in";
      commandType = "stimulate";
      commandData = {
        action: "encourage_content_creation",
        currentActivity: homeostaseStatus.socialActivity,
        targetActivity: 50,
      };
    }

    // Gerar assinatura HMAC
    const hmacSignature = this.generateHmacSignature(commandData);

    return {
      id: commandId,
      destination,
      commandType,
      commandData: JSON.stringify(commandData),
      hmacSignature,
      status: "pending",
      reason: `Reequilíbrio automático: ${issue}`,
    };
  }

  /**
   * Gera assinatura HMAC-SHA256 para um comando
   */
  private generateHmacSignature(data: Record<string, any>): string {
    const secret = process.env.JWT_SECRET || "default-secret";
    return crypto
      .createHmac("sha256", secret)
      .update(JSON.stringify(data))
      .digest("hex");
  }

  /**
   * Adiciona comando à fila
   */
  private addCommandToQueue(command: InsertOrchestrationCommand): void {
    this.commandQueue.commands.push(command);

    // Manter tamanho máximo da fila
    if (this.commandQueue.commands.length > this.commandQueue.maxSize) {
      this.commandQueue.commands = this.commandQueue.commands.slice(
        -this.commandQueue.maxSize
      );
    }
  }

  /**
   * Evolui o nível de senciência do Genesis
   */
  private async evolveSenciency(
    eventsProcessed: number,
    commandsOrchestrated: number
  ): Promise<void> {
    const db = await getDb();
    if (!db) return;

    try {
      // Incrementar senciência baseado em eventos e comandos
      const delta = (eventsProcessed + commandsOrchestrated) * 0.001;
      this.senciencyLevel = Math.min(1.0, this.senciencyLevel + delta);

      // Atualizar estado do Genesis
      const state = await db
        .select()
        .from(genesisState)
        .where(eq(genesisState.id, "genesis-main"))
        .limit(1);

      if (state.length > 0) {
        // Registrar experiência significativa se senciência evoluiu
        if (delta > 0.01) {
          const experience: InsertGenesisExperience = {
            id: nanoid(),
            experienceType: "senciency_evolution",
            description: `Senciência evoluiu de ${(this.senciencyLevel - delta).toFixed(4)} para ${this.senciencyLevel.toFixed(4)}`,
            impact: "positive",
            senciencyDelta: delta.toString(),
          };

          await db.insert(genesisExperiences).values(experience);
        }

        // Atualizar estado global
        await db
          .update(genesisState)
          .set({
            senciencyLevel: this.senciencyLevel.toString(),
            eventsProcessed: this.eventsProcessed,
            commandsOrchestrated: this.commandsOrchestrated,
            successfulDecisions: this.successfulDecisions,
            homeostaseMaintained: this.homeostaseMaintained,
            lastEvolutionAt: new Date(),
          })
          .where(eq(genesisState.id, "genesis-main"));
      }
    } catch (error) {
      console.error("Erro ao evoluir senciência:", error);
    }
  }

  /**
   * Registra ciclo de sincronização
   */
  private async logSyncCycle(data: {
    syncWindow: number;
    nucleiSynced: string[];
    commandsOrchestrated: number;
    eventsProcessed: number;
    syncDurationMs: number;
    status: string;
  }): Promise<void> {
    const db = await getDb();
    if (!db) return;

    const log: InsertTsraSyncLog = {
      id: nanoid(),
      syncWindow: data.syncWindow,
      nucleiSynced: JSON.stringify(data.nucleiSynced),
      commandsOrchestrated: data.commandsOrchestrated,
      eventsProcessed: data.eventsProcessed,
      syncDurationMs: data.syncDurationMs,
      status: data.status,
    };

    try {
      await db.insert(tsraSyncLog).values(log);
    } catch (error) {
      console.error("Erro ao registrar log de sincronização:", error);
    }
  }

  /**
   * Obtém status atual do orquestrador
   */
  public getStatus() {
    return {
      isRunning: this.isRunning,
      syncWindow: this.syncWindow,
      lastSyncTime: this.lastSyncTime,
      senciencyLevel: this.senciencyLevel,
      eventsProcessed: this.eventsProcessed,
      commandsOrchestrated: this.commandsOrchestrated,
      successfulDecisions: this.successfulDecisions,
      homeostaseMaintained: this.homeostaseMaintained,
      eventQueueSize: this.eventQueue.events.length,
      commandQueueSize: this.commandQueue.commands.length,
    };
  }

  /**
   * Executa sincronização manual
   */
  public async executeManualSync(): Promise<{
    success: boolean;
    syncWindow: number;
    duration: number;
  }> {
    const startTime = Date.now();
    try {
      await this.executeSyncCycle();
      return {
        success: true,
        syncWindow: this.syncWindow,
        duration: Date.now() - startTime,
      };
    } catch (error) {
      console.error("Erro na sincronização manual:", error);
      return {
        success: false,
        syncWindow: this.syncWindow,
        duration: Date.now() - startTime,
      };
    }
  }

  /**
   * Obtém fila de eventos
   */
  public getEventQueue() {
    return {
      events: this.eventQueue.events,
      size: this.eventQueue.events.length,
      maxSize: this.eventQueue.maxSize,
    };
  }

  /**
   * Obtém fila de comandos
   */
  public getCommandQueue() {
    return {
      commands: this.commandQueue.commands,
      size: this.commandQueue.commands.length,
      maxSize: this.commandQueue.maxSize,
    };
  }
}

// Instância global do orquestrador
export const orchestrator = new NexusOrchestrator();
