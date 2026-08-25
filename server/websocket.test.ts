import { describe, it, expect, beforeEach, vi } from "vitest";
import { WebSocketManager, WebSocketEventType } from "./websocket";
import { NexusOrchestrator } from "./orchestrator";
import { DecisionEngine } from "./decisionEngine";
import { HomeostaseAnalyzer } from "./homeostaseAnalyzer";

describe("WebSocketManager", () => {
  let wsManager: WebSocketManager;
  let orchestrator: NexusOrchestrator;
  let decisionEngine: DecisionEngine;
  let homeostaseAnalyzer: HomeostaseAnalyzer;

  beforeEach(() => {
    wsManager = new WebSocketManager();
    orchestrator = new NexusOrchestrator();
    decisionEngine = new DecisionEngine();
    homeostaseAnalyzer = new HomeostaseAnalyzer();
  });

  describe("Inicialização", () => {
    it("deve criar instância de WebSocketManager", () => {
      expect(wsManager).toBeDefined();
    });

    it("deve ter métodos de emissão de eventos", () => {
      expect(wsManager.broadcast).toBeDefined();
      expect(wsManager.emitSyncCompleted).toBeDefined();
      expect(wsManager.emitEventReceived).toBeDefined();
      expect(wsManager.emitCommandGenerated).toBeDefined();
      expect(wsManager.emitFlowTriggered).toBeDefined();
      expect(wsManager.emitHomeostaseAlert).toBeDefined();
    });
  });

  describe("Emissão de Eventos", () => {
    it("deve emitir evento de sincronização iniciada", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitSyncStarted();

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.SYNC_STARTED,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            status: "iniciado",
          }),
        })
      );
    });

    it("deve emitir evento de sincronização concluída", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitSyncCompleted(1, 500, 10);

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.SYNC_COMPLETED,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            syncWindow: 1,
            duration: 500,
            eventsProcessed: 10,
            status: "concluído",
          }),
        })
      );
    });

    it("deve emitir evento recebido", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitEventReceived("nexus_hub", "proposta_aprovada", 0.8);

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.EVENT_RECEIVED,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            sourceNucleus: "nexus_hub",
            eventType: "proposta_aprovada",
            sentiment: 0.8,
          }),
          metadata: expect.objectContaining({
            sourceNucleus: "nexus_hub",
            severity: "info",
          }),
        })
      );
    });

    it("deve emitir evento de comando gerado", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitCommandGenerated("fundo_nexus", "transfer", "governance");

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.COMMAND_GENERATED,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            destination: "fundo_nexus",
            commandType: "transfer",
            flowType: "governance",
            status: "gerado",
          }),
        })
      );
    });

    it("deve emitir evento de fluxo acionado", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitFlowTriggered("governance", "nexus_hub", "proposal_approved");

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.FLOW_TRIGGERED,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            flowType: "governance",
            sourceNucleus: "nexus_hub",
            trigger: "proposal_approved",
            status: "acionado",
          }),
          metadata: expect.objectContaining({
            flowType: "governance",
            sourceNucleus: "nexus_hub",
          }),
        })
      );
    });

    it("deve emitir alerta de homeostase", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitHomeostaseAlert("critical", ["Saldo BTC crítico"], 85);

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.HOMEOSTASE_ALERT,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            status: "critical",
            issues: ["Saldo BTC crítico"],
            riskLevel: 85,
          }),
          metadata: expect.objectContaining({
            severity: "critical",
          }),
        })
      );
    });

    it("deve emitir evolução de senciência", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitGenesisEvolved(0.35, 0.05);

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.GENESIS_EVOLVED,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            senciencyLevel: 0.35,
            delta: 0.05,
            status: "evoluído",
          }),
        })
      );
    });

    it("deve emitir TSRA iniciado", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitTSRAStarted();

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.TSRA_STARTED,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            status: "iniciado",
          }),
        })
      );
    });

    it("deve emitir TSRA parado", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitTSRAStopped();

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.TSRA_STOPPED,
        expect.objectContaining({
          timestamp: expect.any(Number),
          data: expect.objectContaining({
            status: "parado",
          }),
        })
      );
    });
  });

  describe("Gerenciamento de Clientes", () => {
    it("deve retornar número de clientes conectados", () => {
      const count = wsManager.getConnectedClientsCount();
      expect(count).toBe(0);
    });
  });

  describe("Severidade de Eventos", () => {
    it("deve atribuir severidade correta para eventos negativos", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitEventReceived("nexus_hub", "erro", -0.8);

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.EVENT_RECEIVED,
        expect.objectContaining({
          metadata: expect.objectContaining({
            severity: "critical",
          }),
        })
      );
    });

    it("deve atribuir severidade correta para eventos neutros", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitEventReceived("nexus_hub", "neutro", -0.2);

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.EVENT_RECEIVED,
        expect.objectContaining({
          metadata: expect.objectContaining({
            severity: "warning",
          }),
        })
      );
    });

    it("deve atribuir severidade correta para eventos positivos", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitEventReceived("nexus_hub", "sucesso", 0.8);

      expect(spy).toHaveBeenCalledWith(
        WebSocketEventType.EVENT_RECEIVED,
        expect.objectContaining({
          metadata: expect.objectContaining({
            severity: "info",
          }),
        })
      );
    });
  });

  describe("Payload Structure", () => {
    it("deve incluir timestamp em todos os payloads", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitSyncCompleted(1, 500, 10);

      const call = spy.mock.calls[0];
      expect(call[1].timestamp).toBeDefined();
      expect(typeof call[1].timestamp).toBe("number");
      expect(call[1].timestamp).toBeGreaterThan(0);
    });

    it("deve incluir data em todos os payloads", () => {
      const spy = vi.spyOn(wsManager, "broadcast");

      wsManager.emitEventReceived("nexus_hub", "teste", 0);

      const call = spy.mock.calls[0];
      expect(call[1].data).toBeDefined();
      expect(typeof call[1].data).toBe("object");
    });
  });
});
