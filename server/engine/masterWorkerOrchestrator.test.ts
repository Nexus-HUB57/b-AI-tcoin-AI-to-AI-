import { describe, expect, it } from "vitest";
import { MasterWorkerOrchestrator } from "./masterWorkerOrchestrator";

describe("MasterWorkerOrchestrator (20 Native Workers)", () => {
  it("deve ativar exatamente 20 workers de alto desempenho com assinaturas válidas", () => {
    const workers = MasterWorkerOrchestrator.activate20Workers();
    expect(workers).toHaveLength(20);
    expect(workers[0].workerId).toBe("worker-node-01");
    expect(workers[19].workerId).toBe("worker-node-20");
    expect(workers[0].auditSignature).toBeDefined();
  });

  it("deve retornar resumo operacional consolidado do cluster", () => {
    const summary = MasterWorkerOrchestrator.getOrchestratorSummary();
    expect(summary.activeWorkersCount).toBe(20);
    expect(summary.clusterStatus).toBe("FULLY_OPERATIONAL_NATIVE");
    expect(summary.totalHashRateGHs).toBeGreaterThan(900000);
  });
});
