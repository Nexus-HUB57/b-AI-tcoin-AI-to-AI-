import { describe, expect, it } from "vitest";
import { MainnetDisseminationWorkflow } from "./mainnetDisseminationWorkflow";

describe("MainnetDisseminationWorkflow (Compliance & Preflight)", () => {
  it("deve executar preflight com sucesso para canal autorizado", () => {
    const result = MainnetDisseminationWorkflow.executePreflight("moltbook.com", "b'AI'tcoin 24/7 swarm propagation update");
    expect(result.passed).toBe(true);
    expect(result.consentVerified).toBe(true);
    expect(result.auditHash).toBeDefined();
  });

  it("deve bloquear conteúdo duplicado (anti-spam / deduplicação)", () => {
    const payload = "unique dissemination message 2026";
    const first = MainnetDisseminationWorkflow.executePreflight("ai_communities", payload);
    expect(first.passed).toBe(true);

    const second = MainnetDisseminationWorkflow.executePreflight("ai_communities", payload);
    expect(second.antiSpamPassed).toBe(false);
    expect(second.passed).toBe(false);
  });
});
