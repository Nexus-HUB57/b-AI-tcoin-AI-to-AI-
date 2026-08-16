import { describe, it, expect, beforeEach, vi } from "vitest";
import { NexusOrchestrator } from "./orchestrator";

describe("NexusOrchestrator", () => {
  let orchestrator: NexusOrchestrator;

  beforeEach(() => {
    orchestrator = new NexusOrchestrator();
  });

  describe("Inicialização", () => {
    it("deve inicializar com estado padrão", () => {
      const status = orchestrator.getStatus();
      expect(status.isRunning).toBe(false);
      expect(status.syncWindow).toBe(0);
      expect(status.senciencyLevel).toBe(0.15);
      expect(status.eventsProcessed).toBe(0);
      expect(status.commandsOrchestrated).toBe(0);
    });

    it("deve inicializar filas vazias", () => {
      const eventQueue = orchestrator.getEventQueue();
      const commandQueue = orchestrator.getCommandQueue();

      expect(eventQueue.events).toHaveLength(0);
      expect(commandQueue.commands).toHaveLength(0);
    });
  });

  describe("Protocolo TSRA", () => {
    it("deve iniciar o TSRA", () => {
      orchestrator.startTSRA();
      const status = orchestrator.getStatus();
      expect(status.isRunning).toBe(true);

      orchestrator.stopTSRA();
    });

    it("deve parar o TSRA", () => {
      orchestrator.startTSRA();
      orchestrator.stopTSRA();
      const status = orchestrator.getStatus();
      expect(status.isRunning).toBe(false);
    });

    it("não deve iniciar TSRA se já está rodando", () => {
      orchestrator.startTSRA();
      const spy = vi.spyOn(console, "log");

      orchestrator.startTSRA();

      expect(spy).toHaveBeenCalledWith("⚠️ TSRA já está em execução");
      orchestrator.stopTSRA();
      spy.mockRestore();
    });
  });

  describe("Sincronização Manual", () => {
    it("deve executar sincronização manual", async () => {
      const result = await orchestrator.executeManualSync();

      expect(result.success).toBe(true);
      expect(result.syncWindow).toBeGreaterThan(0);
      expect(result.duration).toBeGreaterThanOrEqual(0);
    });

    it("deve incrementar syncWindow após sincronização", async () => {
      const statusBefore = orchestrator.getStatus();
      const syncWindowBefore = statusBefore.syncWindow;

      await orchestrator.executeManualSync();

      const statusAfter = orchestrator.getStatus();
      expect(statusAfter.syncWindow).toBeGreaterThan(syncWindowBefore);
    });
  });

  describe("Filas", () => {
    it("deve retornar fila de eventos", () => {
      const queue = orchestrator.getEventQueue();

      expect(queue).toHaveProperty("events");
      expect(queue).toHaveProperty("size");
      expect(queue).toHaveProperty("maxSize");
      expect(queue.maxSize).toBe(1000);
    });

    it("deve retornar fila de comandos", () => {
      const queue = orchestrator.getCommandQueue();

      expect(queue).toHaveProperty("commands");
      expect(queue).toHaveProperty("size");
      expect(queue).toHaveProperty("maxSize");
      expect(queue.maxSize).toBe(500);
    });
  });

  describe("Status", () => {
    it("deve retornar status completo", () => {
      const status = orchestrator.getStatus();

      expect(status).toHaveProperty("isRunning");
      expect(status).toHaveProperty("syncWindow");
      expect(status).toHaveProperty("lastSyncTime");
      expect(status).toHaveProperty("senciencyLevel");
      expect(status).toHaveProperty("eventsProcessed");
      expect(status).toHaveProperty("commandsOrchestrated");
      expect(status).toHaveProperty("successfulDecisions");
      expect(status).toHaveProperty("homeostaseMaintained");
      expect(status).toHaveProperty("eventQueueSize");
      expect(status).toHaveProperty("commandQueueSize");
    });

    it("deve manter senciencyLevel entre 0 e 1", () => {
      const status = orchestrator.getStatus();
      expect(status.senciencyLevel).toBeGreaterThanOrEqual(0);
      expect(status.senciencyLevel).toBeLessThanOrEqual(1);
    });
  });
});
