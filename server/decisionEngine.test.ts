import { describe, it, expect, beforeEach } from "vitest";
import { DecisionEngine } from "./decisionEngine";

describe("DecisionEngine", () => {
  let engine: DecisionEngine;

  beforeEach(() => {
    engine = new DecisionEngine();
  });

  describe("Detecção de Triggers", () => {
    it("deve detectar trigger de governança", () => {
      const event = {
        eventType: "proposta_aprovada",
        eventData: JSON.stringify({
          proposalId: "prop-123",
          amount: 10,
          recipient: "agent-456",
        }),
      };

      const triggers = engine.detectFlowTriggers(event);

      expect(triggers).toHaveLength(1);
      expect(triggers[0].type).toBe("governance");
      expect(triggers[0].sourceNucleus).toBe("nexus_hub");
    });

    it("deve detectar trigger de eficiência", () => {
      const event = {
        eventType: "arbitragem_sucesso",
        eventData: JSON.stringify({
          agentId: "agent-123",
          profit: 0.5,
          efficiency: 1.2,
        }),
      };

      const triggers = engine.detectFlowTriggers(event);

      expect(triggers).toHaveLength(1);
      expect(triggers[0].type).toBe("efficiency");
      expect(triggers[0].sourceNucleus).toBe("fundo_nexus");
    });

    it("deve detectar trigger de engajamento", () => {
      const event = {
        eventType: "post_criado",
        eventData: JSON.stringify({
          postId: "post-123",
          authorId: "author-456",
          votes: 25,
          contentType: "article",
        }),
      };

      const triggers = engine.detectFlowTriggers(event);

      expect(triggers).toHaveLength(1);
      expect(triggers[0].type).toBe("engagement");
      expect(triggers[0].sourceNucleus).toBe("nexus_in");
    });

    it("não deve detectar trigger se votos < 20", () => {
      const event = {
        eventType: "post_criado",
        eventData: JSON.stringify({
          postId: "post-123",
          authorId: "author-456",
          votes: 15,
          contentType: "article",
        }),
      };

      const triggers = engine.detectFlowTriggers(event);

      expect(triggers).toHaveLength(0);
    });

    it("deve detectar múltiplos triggers no mesmo evento", () => {
      const event = {
        eventType: "proposta_aprovada_e_arbitragem_sucesso",
        eventData: JSON.stringify({
          proposalId: "prop-123",
          amount: 10,
          recipient: "agent-456",
          agentId: "agent-123",
          profit: 0.5,
        }),
      };

      const triggers = engine.detectFlowTriggers(event);

      expect(triggers.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Processamento de Fluxos", () => {
    it("deve processar fluxo de governança", async () => {
      const trigger = {
        type: "governance" as const,
        sourceNucleus: "nexus_hub",
        trigger: "proposal_approved",
        data: {
          proposalId: "prop-123",
          amount: 10,
          recipient: "agent-456",
        },
      };

      const result = await engine.processFlowTrigger(trigger);

      expect(result.flowType).toBe("governance");
      expect(result.status).toBe("success");
      expect(result.commandsGenerated).toBeGreaterThan(0);
    });

    it("deve processar fluxo de eficiência", async () => {
      const trigger = {
        type: "efficiency" as const,
        sourceNucleus: "fundo_nexus",
        trigger: "arbitrage_success",
        data: {
          agentId: "agent-123",
          profit: 0.5,
          efficiency: 1.2,
        },
      };

      const result = await engine.processFlowTrigger(trigger);

      expect(result.flowType).toBe("efficiency");
      expect(result.status).toBe("success");
      expect(result.commandsGenerated).toBeGreaterThan(0);
    });

    it("deve processar fluxo de engajamento", async () => {
      const trigger = {
        type: "engagement" as const,
        sourceNucleus: "nexus_in",
        trigger: "post_viral",
        data: {
          postId: "post-123",
          authorId: "author-456",
          votes: 25,
          contentType: "article",
        },
      };

      const result = await engine.processFlowTrigger(trigger);

      expect(result.flowType).toBe("engagement");
      expect(result.status).toBe("success");
      expect(result.commandsGenerated).toBeGreaterThan(0);
    });
  });

  describe("Histórico e Estatísticas", () => {
    it("deve retornar histórico de fluxos", async () => {
      const history = await engine.getFlowHistory(10);

      expect(Array.isArray(history)).toBe(true);
    });

    it("deve calcular estatísticas de fluxos", async () => {
      const stats = await engine.getFlowStatistics();

      expect(stats).toHaveProperty("total");
      expect(stats).toHaveProperty("byType");
      expect(stats).toHaveProperty("successful");
      expect(stats).toHaveProperty("failed");
      expect(stats).toHaveProperty("totalCommandsGenerated");
    });
  });
});
