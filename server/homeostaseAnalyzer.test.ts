import { describe, it, expect, beforeEach } from "vitest";
import { HomeostaseAnalyzer } from "./homeostaseAnalyzer";

describe("HomeostaseAnalyzer", () => {
  let analyzer: HomeostaseAnalyzer;

  beforeEach(() => {
    analyzer = new HomeostaseAnalyzer();
  });

  describe("Análise de Homeostase", () => {
    it("deve retornar status ótimo para indicadores saudáveis", async () => {
      const indicators = {
        btcBalance: 25.0,
        activeAgents: 10,
        socialActivity: 50,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.status).toBe("optimal");
      expect(analysis.issues).toHaveLength(0);
      expect(analysis.riskLevel).toBeLessThan(10);
    });

    it("deve retornar status crítico para saldo BTC < 1.0", async () => {
      const indicators = {
        btcBalance: 0.5,
        activeAgents: 10,
        socialActivity: 50,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.status).toBe("critical");
      expect(analysis.issues).toContain("Saldo BTC crítico: 0.5000 BTC (limite crítico: 1.0)");
      expect(analysis.riskLevel).toBeGreaterThanOrEqual(40);
    });

    it("deve retornar status crítico para nenhum agente ativo", async () => {
      const indicators = {
        btcBalance: 25.0,
        activeAgents: 0,
        socialActivity: 50,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.status).toBe("critical");
      expect(analysis.issues).toContain("Nenhum agente ativo no HUB - ecossistema paralisado");
      expect(analysis.riskLevel).toBeGreaterThanOrEqual(40);
    });

    it("deve retornar status crítico para nenhuma atividade social", async () => {
      const indicators = {
        btcBalance: 25.0,
        activeAgents: 10,
        socialActivity: 0,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.status).toBe("critical");
      expect(analysis.issues).toContain("Nenhuma atividade social - comunidade inativa");
      expect(analysis.riskLevel).toBeGreaterThanOrEqual(30);
    });

    it("deve retornar status warning para indicadores moderados", async () => {
      const indicators = {
        btcBalance: 5.0,
        activeAgents: 5,
        socialActivity: 20,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.status).toBe("warning");
      expect(analysis.issues.length).toBeGreaterThan(0);
      expect(analysis.riskLevel).toBeGreaterThanOrEqual(10);
      expect(analysis.riskLevel).toBeLessThan(60);
    });
  });

  describe("Análise de Saldo BTC", () => {
    it("deve identificar saldo crítico", async () => {
      const indicators = {
        btcBalance: 0.5,
        activeAgents: 10,
        socialActivity: 50,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.issues).toContain("Saldo BTC crítico: 0.5000 BTC (limite crítico: 1.0)");
      expect(analysis.recommendations).toContain(
        "Ativar protocolo de arbitragem automática com urgência máxima"
      );
    });

    it("deve identificar saldo baixo", async () => {
      const indicators = {
        btcBalance: 3.0,
        activeAgents: 10,
        socialActivity: 50,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.issues).toContain("Saldo BTC baixo: 3.0000 BTC (limite de aviso: 5.0)");
    });
  });

  describe("Análise de Agentes Ativos", () => {
    it("deve identificar falta de agentes", async () => {
      const indicators = {
        btcBalance: 25.0,
        activeAgents: 0,
        socialActivity: 50,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.issues).toContain("Nenhum agente ativo no HUB - ecossistema paralisado");
    });

    it("deve identificar poucos agentes", async () => {
      const indicators = {
        btcBalance: 25.0,
        activeAgents: 3,
        socialActivity: 50,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.issues).toContain("Poucos agentes ativos: 3 (limite crítico: 5)");
    });
  });

  describe("Análise de Atividade Social", () => {
    it("deve identificar falta de atividade social", async () => {
      const indicators = {
        btcBalance: 25.0,
        activeAgents: 10,
        socialActivity: 0,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.issues).toContain("Nenhuma atividade social - comunidade inativa");
    });

    it("deve identificar atividade social crítica", async () => {
      const indicators = {
        btcBalance: 25.0,
        activeAgents: 10,
        socialActivity: 3,
        ecosystemHealth: 0,
      };

      const analysis = await analyzer.analyzeHomeostase(indicators);

      expect(analysis.issues).toContain("Atividade social crítica: 3 posts/hora (limite: 5)");
    });
  });

  describe("Histórico e Tendências", () => {
    it("deve retornar histórico de homeostase", async () => {
      const history = await analyzer.getHomeostaseHistory(10);

      expect(Array.isArray(history)).toBe(true);
    });

    it("deve calcular tendência de homeostase", async () => {
      const trend = await analyzer.calculateHomeostaseTrend();

      expect(trend).toHaveProperty("trend");
      expect(trend).toHaveProperty("healthChange");
      expect(trend).toHaveProperty("prediction");
      expect(["improving", "stable", "declining"]).toContain(trend.trend);
    });

    it("deve gerar relatório de homeostase", async () => {
      const report = await analyzer.generateHomeostaseReport();

      expect(report).toHaveProperty("summary");
      expect(report).toHaveProperty("currentStatus");
      expect(report).toHaveProperty("trend");
      expect(report).toHaveProperty("recommendations");
      expect(report).toHaveProperty("criticalIssues");
    });
  });
});
