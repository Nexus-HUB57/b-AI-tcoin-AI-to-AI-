import { COOKIE_NAME } from "@shared/const";
import { agentSwarmRouter } from "./routers/agentSwarm";
import { masterWalletRouter } from "./routers/masterWallet";
import { masterWorkersRouter } from "./routers/masterWorkersRouter";
import { lastWaveOrganismRouter } from "./routers/lastWaveOrganism";
import { agentAuthorityRouter } from "./routers/agentAuthority";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { orchestrator } from "./orchestrator";
import { decisionEngine } from "./decisionEngine";
import {
  getRecentOrchestrationEvents,
  getPendingCommands,
  getRecentTsraLogs,
  getRecentHomeostaseMetrics,
  getGenesisState,
  getGenesisExperiences,
  getNucleusStates,
} from "./db";

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query((opts) => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  agentSwarm: agentSwarmRouter,
  masterWallet: masterWalletRouter,
  masterWorkers: masterWorkersRouter,
  organism: lastWaveOrganismRouter,
  agentAuthority: agentAuthorityRouter,
  orchestration: router({
    // Obtém status atual do orquestrador
    status: publicProcedure.query(async () => {
      return orchestrator.getStatus();
    }),

    // Obtém métricas de orquestração
    getMetrics: publicProcedure.query(async () => {
      const recentLogs = await getRecentTsraLogs(10);
      const genesisState = await getGenesisState();

      if (recentLogs.length === 0) {
        return {
          eventsPerSecond: 0,
          responseRate: 0,
          homeostaseStatus: "unknown",
          senciencyLevel: genesisState?.senciencyLevel || "0.15",
        };
      }

      const totalEvents = recentLogs.reduce(
        (sum, log) => sum + (log.eventsProcessed || 0),
        0
      );
      const totalCommands = recentLogs.reduce(
        (sum, log) => sum + (log.commandsOrchestrated || 0),
        0
      );
      const totalDuration = recentLogs.reduce(
        (sum, log) => sum + (log.syncDurationMs || 0),
        0
      );

      return {
        eventsPerSecond: totalEvents / (totalDuration / 1000),
        responseRate: totalCommands > 0 ? (totalCommands / totalEvents) * 100 : 0,
        homeostaseStatus: "optimal",
        senciencyLevel: genesisState?.senciencyLevel || "0.15",
      };
    }),

    // Obtém estado global dos núcleos
    getGlobalState: publicProcedure.query(async () => {
      const nucleusStates = await getNucleusStates();
      const genesisState = await getGenesisState();

      return {
        genesis: genesisState,
        nuclei: nucleusStates,
      };
    }),

    // Obtém eventos recentes
    getRecentEvents: publicProcedure.query(async () => {
      return await getRecentOrchestrationEvents(50);
    }),

    // Obtém comandos pendentes
    getPendingCommands: publicProcedure.query(async () => {
      return await getPendingCommands();
    }),

    // Obtém logs TSRA recentes
    getTsraLogs: publicProcedure.query(async () => {
      return await getRecentTsraLogs(100);
    }),

    // Obtém métricas de homeostase
    getHomeostaseMetrics: publicProcedure.query(async () => {
      return await getRecentHomeostaseMetrics(100);
    }),

    // Obtém experiências do Genesis
    getGenesisExperiences: publicProcedure.query(async () => {
      return await getGenesisExperiences(50);
    }),

    // Executa sincronização manual
    manualSync: publicProcedure.mutation(async () => {
      return await orchestrator.executeManualSync();
    }),

    // Inicia protocolo TSRA
    startTSRA: publicProcedure.mutation(async () => {
      orchestrator.startTSRA();
      return { success: true, message: "TSRA iniciado" };
    }),

    // Para protocolo TSRA
    stopTSRA: publicProcedure.mutation(async () => {
      orchestrator.stopTSRA();
      return { success: true, message: "TSRA parado" };
    }),

    // Obtém fila de eventos
    getEventQueue: publicProcedure.query(async () => {
      return orchestrator.getEventQueue();
    }),

    // Obtém fila de comandos
    getCommandQueue: publicProcedure.query(async () => {
      return orchestrator.getCommandQueue();
    }),

    // Obtém histórico de fluxos
    getFlowHistory: publicProcedure.query(async () => {
      return await decisionEngine.getFlowHistory(100);
    }),

    // Obtém estatísticas de fluxos
    getFlowStatistics: publicProcedure.query(async () => {
      return await decisionEngine.getFlowStatistics();
    }),
  }),
});

export type AppRouter = typeof appRouter;
