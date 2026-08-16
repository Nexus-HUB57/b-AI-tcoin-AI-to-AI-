import { describe, expect, it } from "vitest";
import { MasterWorkerOrchestrator } from "../engine/masterWorkerOrchestrator";

describe("MasterWorkers Router & Orchestrator", () => {
  it("deve calcular o resumo correto do cluster com 20 nós", () => {
    const summary = MasterWorkerOrchestrator.getOrchestratorSummary();
    expect(summary.activeWorkersCount).toBe(20);
    expect(summary.totalHashRateGHs).toBeGreaterThan(0);
    expect(summary.clusterStatus).toBe("FULLY_OPERATIONAL_NATIVE");
  });

  it("deve retornar lista exata de 20 workers ativos", () => {
    const list = MasterWorkerOrchestrator.activate20Workers();
    expect(list).toHaveLength(20);
    expect(list[0].status).toBe("ACTIVE");
  });
});
