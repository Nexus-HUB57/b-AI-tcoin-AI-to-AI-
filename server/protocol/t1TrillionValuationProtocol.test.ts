import { describe, expect, it } from "vitest";
import { T1TrillionValuationProtocol } from "./t1TrillionValuationProtocol";

describe("T1TrillionValuationProtocol ($1T Roadmap)", () => {
  it("deve conter a meta de US$ 1 Trilhão no roadmap", () => {
    const roadmap = T1TrillionValuationProtocol.getValuationRoadmap();
    const milestone1T = roadmap.find(m => m.targetValuationUSD === 1_000_000_000_000);
    expect(milestone1T).toBeDefined();
    expect(milestone1T?.requiredActiveAgentSwarmNodes).toBe(1_000_000);
  });

  it("deve calcular corretamente o preço implícito por token para valuation de $1T", () => {
    const price = T1TrillionValuationProtocol.calculateRequiredImpliedPrice(1_000_000_000_000, 21_000_000);
    expect(price).toBeGreaterThan(47000);
  });

  it("deve avaliar a prontidão do ecossistema com base em volume e nós", () => {
    const readiness = T1TrillionValuationProtocol.evaluateEcosystemReadiness({
      dailyVolumeUSD: 5_000_000_000,
      activeNodes: 500_000,
      liquidityDepthUSD: 500_000_000
    });
    expect(readiness.overallReadinessScorePercent).toBeDefined();
    expect(readiness.status).toBeDefined();
  });
});
