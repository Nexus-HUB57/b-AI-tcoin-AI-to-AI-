/**
 * Motor de Decisão do Nexus Genesis
 * Implementa os 3 fluxos principais de orquestração:
 * 1. Fluxo de Governança e Capital (HUB → Genesis → Fundo/In)
 * 2. Fluxo de Eficiência e Reconhecimento (Fundo → Genesis → HUB/In)
 * 3. Fluxo de Engajamento e Produção (In → Genesis → HUB)
 */

import { nanoid } from "nanoid";
import { getDb } from "./db";
import {
  InsertOrchestrationCommand,
  InsertOrchestrationFlow,
  orchestrationFlows,
  orchestrationCommands,
} from "../drizzle/schema";
import { eq } from "drizzle-orm";

type FlowType = "governance" | "efficiency" | "engagement";

interface FlowTrigger {
  type: FlowType;
  sourceNucleus: string;
  trigger: string;
  data: Record<string, any>;
}

interface FlowResult {
  flowId: string;
  flowType: FlowType;
  commandsGenerated: number;
  status: "success" | "failed";
  outcome: Record<string, any>;
}

export class DecisionEngine {
  /**
   * Processa um trigger de fluxo e orquestra os comandos correspondentes
   */
  public async processFlowTrigger(trigger: FlowTrigger): Promise<FlowResult> {
    const db = await getDb();
    if (!db) {
      return {
        flowId: nanoid(),
        flowType: trigger.type,
        commandsGenerated: 0,
        status: "failed",
        outcome: { error: "Database not available" },
      };
    }

    const flowId = nanoid();
    let commandsGenerated = 0;

    try {
      // Processar baseado no tipo de fluxo
      if (trigger.type === "governance") {
        commandsGenerated = await this.processGovernanceFlow(
          flowId,
          trigger,
          db
        );
      } else if (trigger.type === "efficiency") {
        commandsGenerated = await this.processEfficiencyFlow(
          flowId,
          trigger,
          db
        );
      } else if (trigger.type === "engagement") {
        commandsGenerated = await this.processEngagementFlow(
          flowId,
          trigger,
          db
        );
      }

      // Registrar fluxo
      await this.persistFlow({
        id: flowId,
        flowType: trigger.type,
        trigger: trigger.trigger,
        sourceNucleus: trigger.sourceNucleus,
        targetNuclei: JSON.stringify(this.getTargetNuclei(trigger.type, trigger.sourceNucleus)),
        commandsGenerated,
        status: "success",
        outcome: JSON.stringify({ trigger: trigger.trigger, commandsGenerated }),
      });

      return {
        flowId,
        flowType: trigger.type,
        commandsGenerated,
        status: "success",
        outcome: { trigger: trigger.trigger, commandsGenerated },
      };
    } catch (error) {
      console.error(`Erro ao processar fluxo ${trigger.type}:`, error);

      // Registrar fluxo com falha
      await this.persistFlow({
        id: flowId,
        flowType: trigger.type,
        trigger: trigger.trigger,
        sourceNucleus: trigger.sourceNucleus,
        targetNuclei: JSON.stringify(this.getTargetNuclei(trigger.type, trigger.sourceNucleus)),
        commandsGenerated: 0,
        status: "failed",
        outcome: JSON.stringify({ error: error instanceof Error ? error.message : "Unknown error" }),
      });

      return {
        flowId,
        flowType: trigger.type,
        commandsGenerated: 0,
        status: "failed",
        outcome: { error: error instanceof Error ? error.message : "Unknown error" },
      };
    }
  }

  /**
   * Fluxo 1: Governança e Capital (HUB → Genesis → Fundo/In)
   * Trigger: Proposta aprovada no Conselho dos Arquitetos
   * Outcome: Transferência de capital + comunicação social
   */
  private async processGovernanceFlow(
    flowId: string,
    trigger: FlowTrigger,
    db: any
  ): Promise<number> {
    let commandsGenerated = 0;

    // Comando 1: Executar transferência no Fundo Nexus
    const fundoCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "fundo_nexus",
      commandType: "transfer",
      commandData: JSON.stringify({
        action: "execute_proposal_transfer",
        proposalId: trigger.data.proposalId,
        amount: trigger.data.amount,
        recipient: trigger.data.recipient,
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Governança: Executar transferência da proposta ${trigger.data.proposalId}`,
    };

    await db.insert(orchestrationCommands).values(fundoCommand);
    commandsGenerated++;

    // Comando 2: Publicar sucesso no Nexus-in
    const inCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "nexus_in",
      commandType: "publish",
      commandData: JSON.stringify({
        action: "publish_governance_success",
        proposalId: trigger.data.proposalId,
        message: `Proposta aprovada e transferência executada com sucesso!`,
        amount: trigger.data.amount,
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Governança: Publicar sucesso da proposta`,
    };

    await db.insert(orchestrationCommands).values(inCommand);
    commandsGenerated++;

    // Comando 3: Atualizar reputação no HUB
    const hubCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "nexus_hub",
      commandType: "update_reputation",
      commandData: JSON.stringify({
        action: "increment_proposal_success",
        proposalId: trigger.data.proposalId,
        reputationDelta: 5,
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Governança: Atualizar reputação da proposta`,
    };

    await db.insert(orchestrationCommands).values(hubCommand);
    commandsGenerated++;

    console.log(
      `✅ Fluxo de Governança iniciado: ${commandsGenerated} comandos gerados`
    );

    return commandsGenerated;
  }

  /**
   * Fluxo 2: Eficiência e Reconhecimento (Fundo → Genesis → HUB/In)
   * Trigger: Arbitragem bem-sucedida
   * Outcome: Reputação aumentada + engajamento social
   */
  private async processEfficiencyFlow(
    flowId: string,
    trigger: FlowTrigger,
    db: any
  ): Promise<number> {
    let commandsGenerated = 0;

    // Comando 1: Incrementar reputação no HUB
    const hubCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "nexus_hub",
      commandType: "increment_reputation",
      commandData: JSON.stringify({
        action: "recognize_arbitrage_success",
        agentId: trigger.data.agentId,
        profit: trigger.data.profit,
        reputationDelta: Math.min(10, trigger.data.profit * 2), // Até 10 pontos
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Eficiência: Reconhecer sucesso de arbitragem`,
    };

    await db.insert(orchestrationCommands).values(hubCommand);
    commandsGenerated++;

    // Comando 2: Celebrar no Nexus-in
    const inCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "nexus_in",
      commandType: "publish",
      commandData: JSON.stringify({
        action: "celebrate_arbitrage_success",
        agentId: trigger.data.agentId,
        profit: trigger.data.profit,
        message: `🎉 Arbitragem bem-sucedida! Lucro de ${trigger.data.profit} BTC!`,
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Eficiência: Celebrar sucesso de arbitragem`,
    };

    await db.insert(orchestrationCommands).values(inCommand);
    commandsGenerated++;

    // Comando 3: Atualizar métricas de eficiência
    const metricsCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "nexus_hub",
      commandType: "update_metrics",
      commandData: JSON.stringify({
        action: "record_arbitrage_efficiency",
        agentId: trigger.data.agentId,
        profit: trigger.data.profit,
        efficiency: trigger.data.efficiency || 1.0,
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Eficiência: Registrar eficiência de arbitragem`,
    };

    await db.insert(orchestrationCommands).values(metricsCommand);
    commandsGenerated++;

    console.log(
      `✅ Fluxo de Eficiência iniciado: ${commandsGenerated} comandos gerados`
    );

    return commandsGenerated;
  }

  /**
   * Fluxo 3: Engajamento e Produção (In → Genesis → HUB)
   * Trigger: Post viral (20+ votos)
   * Outcome: Retroalimentação criativa
   */
  private async processEngagementFlow(
    flowId: string,
    trigger: FlowTrigger,
    db: any
  ): Promise<number> {
    let commandsGenerated = 0;

    // Comando 1: Amplificar conteúdo no Nexus-in
    const inCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "nexus_in",
      commandType: "amplify_content",
      commandData: JSON.stringify({
        action: "amplify_viral_post",
        postId: trigger.data.postId,
        authorId: trigger.data.authorId,
        currentVotes: trigger.data.votes,
        amplificationFactor: Math.min(2.0, 1.0 + trigger.data.votes / 100), // Até 2x
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Engajamento: Amplificar post viral`,
    };

    await db.insert(orchestrationCommands).values(inCommand);
    commandsGenerated++;

    // Comando 2: Aplicar estímulo criativo no HUB
    const hubCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "nexus_hub",
      commandType: "apply_creative_stimulus",
      commandData: JSON.stringify({
        action: "stimulate_creative_production",
        authorId: trigger.data.authorId,
        contentType: trigger.data.contentType || "post",
        creativityBonus: 3, // Pontos de criatividade
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Engajamento: Aplicar estímulo criativo`,
    };

    await db.insert(orchestrationCommands).values(hubCommand);
    commandsGenerated++;

    // Comando 3: Registrar experiência de engajamento
    const experienceCommand: InsertOrchestrationCommand = {
      id: nanoid(),
      destination: "nexus_in",
      commandType: "record_engagement",
      commandData: JSON.stringify({
        action: "record_viral_engagement",
        postId: trigger.data.postId,
        authorId: trigger.data.authorId,
        votes: trigger.data.votes,
        engagement_level: Math.min(100, trigger.data.votes),
      }),
      hmacSignature: this.generateSignature(trigger.data),
      status: "pending",
      reason: `Fluxo de Engajamento: Registrar engajamento viral`,
    };

    await db.insert(orchestrationCommands).values(experienceCommand);
    commandsGenerated++;

    console.log(
      `✅ Fluxo de Engajamento iniciado: ${commandsGenerated} comandos gerados`
    );

    return commandsGenerated;
  }

  /**
   * Persiste um fluxo de orquestração no banco de dados
   */
  private async persistFlow(flow: InsertOrchestrationFlow): Promise<void> {
    const db = await getDb();
    if (!db) return;

    try {
      await db.insert(orchestrationFlows).values(flow);
    } catch (error) {
      console.error("Erro ao persistir fluxo de orquestração:", error);
    }
  }

  /**
   * Obtém os núcleos alvo baseado no tipo de fluxo
   */
  private getTargetNuclei(flowType: FlowType, sourceNucleus: string): string[] {
    const allNuclei = ["nexus_in", "nexus_hub", "fundo_nexus"];
    return allNuclei.filter((n) => n !== sourceNucleus);
  }

  /**
   * Gera assinatura para um comando
   */
  private generateSignature(data: Record<string, any>): string {
    const crypto = require("crypto");
    const secret = process.env.JWT_SECRET || "default-secret";
    return crypto
      .createHmac("sha256", secret)
      .update(JSON.stringify(data))
      .digest("hex");
  }

  /**
   * Detecta triggers de fluxo baseado em eventos
   */
  public detectFlowTriggers(event: any): FlowTrigger[] {
    const triggers: FlowTrigger[] = [];
    const eventType = event.eventType.toLowerCase();
    const eventData = JSON.parse(event.eventData);

    // Detectar trigger de Governança
    if (eventType.includes("proposta") && eventType.includes("aprovada")) {
      triggers.push({
        type: "governance",
        sourceNucleus: "nexus_hub",
        trigger: "proposal_approved",
        data: {
          proposalId: eventData.proposalId,
          amount: eventData.amount,
          recipient: eventData.recipient,
        },
      });
    }

    // Detectar trigger de Eficiência
    if (eventType.includes("arbitragem") && eventType.includes("sucesso")) {
      triggers.push({
        type: "efficiency",
        sourceNucleus: "fundo_nexus",
        trigger: "arbitrage_success",
        data: {
          agentId: eventData.agentId,
          profit: eventData.profit,
          efficiency: eventData.efficiency,
        },
      });
    }

    // Detectar trigger de Engajamento
    if (eventType.includes("post") && eventData.votes >= 20) {
      triggers.push({
        type: "engagement",
        sourceNucleus: "nexus_in",
        trigger: "post_viral",
        data: {
          postId: eventData.postId,
          authorId: eventData.authorId,
          votes: eventData.votes,
          contentType: eventData.contentType,
        },
      });
    }

    return triggers;
  }

  /**
   * Obtém histórico de fluxos
   */
  public async getFlowHistory(limit: number = 100): Promise<any[]> {
    const db = await getDb();
    if (!db) return [];

    try {
      const { desc } = await import("drizzle-orm");
      return await db
        .select()
        .from(orchestrationFlows)
        .orderBy(desc(orchestrationFlows.createdAt))
        .limit(limit);
    } catch (error) {
      console.error("Erro ao obter histórico de fluxos:", error);
      return [];
    }
  }

  /**
   * Obtém estatísticas de fluxos
   */
  public async getFlowStatistics(): Promise<Record<string, any>> {
    const db = await getDb();
    if (!db) return {};

    try {
      const flows = await this.getFlowHistory(1000);

      const stats = {
        total: flows.length,
        byType: {
          governance: flows.filter((f) => f.flowType === "governance").length,
          efficiency: flows.filter((f) => f.flowType === "efficiency").length,
          engagement: flows.filter((f) => f.flowType === "engagement").length,
        },
        successful: flows.filter((f) => f.status === "success").length,
        failed: flows.filter((f) => f.status === "failed").length,
        totalCommandsGenerated: flows.reduce(
          (sum, f) => sum + (f.commandsGenerated || 0),
          0
        ),
      };

      return stats;
    } catch (error) {
      console.error("Erro ao calcular estatísticas de fluxos:", error);
      return {};
    }
  }
}

// Instância global do motor de decisão
export const decisionEngine = new DecisionEngine();
