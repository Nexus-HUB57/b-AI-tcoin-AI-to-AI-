/**
 * Analisador de Homeostase do Nexus Genesis
 * Detecta desequilíbrios e recomenda ações de reequilíbrio
 */

import { getDb } from "./db";
import {
  InsertHomeostaseMetric,
  homeostaseMetrics,
  genesisExperiences,
} from "../drizzle/schema";
import { nanoid } from "nanoid";
import { desc } from "drizzle-orm";

export interface HomeostaseIndicators {
  btcBalance: number;
  activeAgents: number;
  socialActivity: number;
  ecosystemHealth: number; // 0-100
}

export interface HomeostaseAnalysis {
  status: "critical" | "warning" | "optimal";
  indicators: HomeostaseIndicators;
  issues: string[];
  recommendations: string[];
  riskLevel: number; // 0-100
}

export class HomeostaseAnalyzer {
  /**
   * Analisa o estado de homeostase do ecossistema
   */
  public async analyzeHomeostase(
    indicators: HomeostaseIndicators
  ): Promise<HomeostaseAnalysis> {
    const issues: string[] = [];
    const recommendations: string[] = [];
    let riskLevel = 0;

    // Análise de Saldo BTC
    const btcAnalysis = this.analyzeBtcBalance(indicators.btcBalance);
    if (btcAnalysis.issue) {
      issues.push(btcAnalysis.issue);
      recommendations.push(btcAnalysis.recommendation);
      riskLevel += btcAnalysis.riskDelta;
    }

    // Análise de Agentes Ativos
    const agentAnalysis = this.analyzeActiveAgents(indicators.activeAgents);
    if (agentAnalysis.issue) {
      issues.push(agentAnalysis.issue);
      recommendations.push(agentAnalysis.recommendation);
      riskLevel += agentAnalysis.riskDelta;
    }

    // Análise de Atividade Social
    const socialAnalysis = this.analyzeSocialActivity(
      indicators.socialActivity
    );
    if (socialAnalysis.issue) {
      issues.push(socialAnalysis.issue);
      recommendations.push(socialAnalysis.recommendation);
      riskLevel += socialAnalysis.riskDelta;
    }

    // Calcular saúde do ecossistema (0-100)
    const ecosystemHealth = Math.max(
      0,
      100 -
        (btcAnalysis.riskDelta +
          agentAnalysis.riskDelta +
          socialAnalysis.riskDelta)
    );

    // Determinar status geral
    let status: "critical" | "warning" | "optimal" = "optimal";
    if (riskLevel >= 30) {
      status = "critical";
    } else if (riskLevel >= 15) {
      status = "warning";
    }

    // Persistir métricas
    await this.persistMetrics({
      btcBalance: indicators.btcBalance,
      activeAgents: indicators.activeAgents,
      socialActivity: indicators.socialActivity,
      equilibriumStatus: status,
      issues: JSON.stringify(issues),
    });

    // Registrar experiência se houver desequilíbrio crítico
    if (status === "critical") {
      await this.recordCriticalExperience(issues, recommendations);
    }

    return {
      status,
      indicators: { ...indicators, ecosystemHealth },
      issues,
      recommendations,
      riskLevel: Math.min(100, riskLevel),
    };
  }

  /**
   * Analisa saldo BTC crítico
   */
  private analyzeBtcBalance(btcBalance: number): {
    issue?: string;
    recommendation: string;
    riskDelta: number;
  } {
    if (btcBalance < 1.0) {
      return {
        issue: `Saldo BTC crítico: ${btcBalance.toFixed(4)} BTC (limite crítico: 1.0)`,
        recommendation:
          "Ativar protocolo de arbitragem automática com urgência máxima",
        riskDelta: 40,
      };
    }

    if (btcBalance < 5.0) {
      return {
        issue: `Saldo BTC baixo: ${btcBalance.toFixed(4)} BTC (limite de aviso: 5.0)`,
        recommendation: "Iniciar operações de arbitragem para recuperação",
        riskDelta: 20,
      };
    }

    if (btcBalance < 25.0) {
      return {
        issue: `Saldo BTC abaixo do ótimo: ${btcBalance.toFixed(4)} BTC (ótimo: 25.0+)`,
        recommendation: "Monitorar e preparar operações de arbitragem",
        riskDelta: 10,
      };
    }

    return {
      recommendation: "Saldo BTC em nível ótimo",
      riskDelta: 0,
    };
  }

  /**
   * Analisa agentes ativos
   */
  private analyzeActiveAgents(activeAgents: number): {
    issue?: string;
    recommendation: string;
    riskDelta: number;
  } {
    if (activeAgents === 0) {
      return {
        issue: "Nenhum agente ativo no HUB - ecossistema paralisado",
        recommendation:
          "Criar ou reativar agentes imediatamente - risco crítico",
        riskDelta: 40,
      };
    }

    if (activeAgents < 5) {
      return {
        issue: `Poucos agentes ativos: ${activeAgents} (limite crítico: 5)`,
        recommendation: "Estimular criação de novos agentes ou reativar existentes",
        riskDelta: 25,
      };
    }

    if (activeAgents < 10) {
      return {
        issue: `Agentes abaixo do ótimo: ${activeAgents} (ótimo: 10+)`,
        recommendation: "Incentivar criação de novos agentes",
        riskDelta: 10,
      };
    }

    return {
      recommendation: "Nível ótimo de agentes ativos",
      riskDelta: 0,
    };
  }

  /**
   * Analisa atividade social
   */
  private analyzeSocialActivity(socialActivity: number): {
    issue?: string;
    recommendation: string;
    riskDelta: number;
  } {
    if (socialActivity === 0) {
      return {
        issue: "Nenhuma atividade social - comunidade inativa",
        recommendation: "Estimular criação de conteúdo e engajamento urgentemente",
        riskDelta: 30,
      };
    }

    if (socialActivity < 5) {
      return {
        issue: `Atividade social crítica: ${socialActivity} posts/hora (limite: 5)`,
        recommendation: "Lançar campanhas de estímulo criativo",
        riskDelta: 20,
      };
    }

    if (socialActivity < 20) {
      return {
        issue: `Atividade social baixa: ${socialActivity} posts/hora (aviso: 20)`,
        recommendation: "Incentivar criação de conteúdo viral",
        riskDelta: 10,
      };
    }

    if (socialActivity < 50) {
      return {
        issue: `Atividade social abaixo do ótimo: ${socialActivity} posts/hora (ótimo: 50+)`,
        recommendation: "Monitorar e manter estímulos criativos",
        riskDelta: 5,
      };
    }

    return {
      recommendation: "Atividade social em nível ótimo",
      riskDelta: 0,
    };
  }

  /**
   * Persiste métricas de homeostase
   */
  private async persistMetrics(metrics: {
    btcBalance: number;
    activeAgents: number;
    socialActivity: number;
    equilibriumStatus: string;
    issues: string;
  }): Promise<void> {
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
        issues: metrics.issues,
      };

      await db.insert(homeostaseMetrics).values(metric);
    } catch (error) {
      console.error("Erro ao persistir métricas de homeostase:", error);
    }
  }

  /**
   * Registra experiência de desequilíbrio crítico
   */
  private async recordCriticalExperience(
    issues: string[],
    recommendations: string[]
  ): Promise<void> {
    const db = await getDb();
    if (!db) return;

    try {
      await db.insert(genesisExperiences).values({
        id: nanoid(),
        experienceType: "critical_imbalance_detected",
        description: `Desequilíbrio crítico detectado: ${issues.join("; ")}`,
        impact: "negative",
        senciencyDelta: "-0.05",
      });
    } catch (error) {
      console.error("Erro ao registrar experiência crítica:", error);
    }
  }

  /**
   * Obtém histórico de homeostase
   */
  public async getHomeostaseHistory(limit: number = 100): Promise<any[]> {
    const db = await getDb();
    if (!db) return [];

    try {
      return await db
        .select()
        .from(homeostaseMetrics)
        .orderBy(desc(homeostaseMetrics.createdAt))
        .limit(limit);
    } catch (error) {
      console.error("Erro ao obter histórico de homeostase:", error);
      return [];
    }
  }

  /**
   * Calcula tendência de homeostase
   */
  public async calculateHomeostaseTrend(): Promise<{
    trend: "improving" | "stable" | "declining";
    healthChange: number;
    prediction: string;
  }> {
    const history = await this.getHomeostaseHistory(20);

    if (history.length < 2) {
      return {
        trend: "stable",
        healthChange: 0,
        prediction: "Dados insuficientes para análise de tendência",
      };
    }

    // Calcular saúde para cada ponto
    const healthScores = history.map((metric) => {
      const btcScore = Math.min(100, (metric.btcBalance || 0) / 25 * 100);
      const agentScore = Math.min(100, (metric.activeAgents || 0) / 10 * 100);
      const socialScore = Math.min(100, (metric.socialActivity || 0) / 50 * 100);
      return (btcScore + agentScore + socialScore) / 3;
    });

    const oldestHealth = healthScores[healthScores.length - 1];
    const newestHealth = healthScores[0];
    const healthChange = newestHealth - oldestHealth;

    let trend: "improving" | "stable" | "declining" = "stable";
    let prediction = "Homeostase estável";

    if (healthChange > 5) {
      trend = "improving";
      prediction = "Ecossistema se recuperando - continue monitorando";
    } else if (healthChange < -5) {
      trend = "declining";
      prediction = "Ecossistema degradando - ação imediata recomendada";
    }

    return {
      trend,
      healthChange: Math.round(healthChange * 100) / 100,
      prediction,
    };
  }

  /**
   * Gera relatório de homeostase
   */
  public async generateHomeostaseReport(): Promise<{
    summary: string;
    currentStatus: HomeostaseAnalysis | null;
    trend: any;
    recommendations: string[];
    criticalIssues: string[];
  }> {
    const history = await this.getHomeostaseHistory(1);
    const trend = await this.calculateHomeostaseTrend();

    let currentStatus: HomeostaseAnalysis | null = null;
    let criticalIssues: string[] = [];
    let recommendations: string[] = [];

    if (history.length > 0) {
      const latest = history[0];
      currentStatus = await this.analyzeHomeostase({
        btcBalance: parseFloat(latest.btcBalance || "0"),
        activeAgents: latest.activeAgents || 0,
        socialActivity: latest.socialActivity || 0,
        ecosystemHealth: 0,
      });

      criticalIssues = currentStatus.issues;
      recommendations = currentStatus.recommendations;
    }

    const summary =
      currentStatus?.status === "critical"
        ? "⚠️ ALERTA CRÍTICO: Ecossistema em estado crítico - ação imediata necessária"
        : currentStatus?.status === "warning"
          ? "⚠️ AVISO: Ecossistema com desequilíbrios - monitoramento recomendado"
          : "✅ Ecossistema em homeostase ótima";

    return {
      summary,
      currentStatus,
      trend,
      recommendations,
      criticalIssues,
    };
  }
}

// Instância global do analisador
export const homeostaseAnalyzer = new HomeostaseAnalyzer();
