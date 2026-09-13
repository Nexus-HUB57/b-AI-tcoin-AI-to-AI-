import { describe, expect, it } from "vitest";
import { BaitcoinOrchestratorBridge } from "./baitcoinOrchestratorBridge";

describe("BaitcoinOrchestratorBridge (Phd Harness)", () => {
  it("deve rejeitar disseminação se o consentimento não for verificado", async () => {
    const result = await BaitcoinOrchestratorBridge.dispatch({
      targetPlatform: "moltbook",
      agentId: "agent-999",
      topic: "b'AI'tcoin Launch",
      content: "Tentativa sem consentimento.",
      metricsShare: { marketCapTarget: "$1T", liquidityIndex: 0.9, senciencyLevel: 0.8 },
      consentVerified: false,
      timestamp: Date.now()
    });

    expect(result.success).toBe(false);
    expect(result.rateLimitStatus).toBe("REJECTED_NO_CONSENT");
  });

  it("deve bloquear conteúdo duplicado (anti-spam)", async () => {
    const payload = {
      targetPlatform: "moltbook" as const,
      agentId: "agent-100",
      topic: "b'AI'tcoin Utility",
      content: "Conteúdo único para teste de deduplicação anti-spam.",
      metricsShare: { marketCapTarget: "$1T", liquidityIndex: 0.95, senciencyLevel: 0.85 },
      consentVerified: true,
      timestamp: Date.now()
    };

    const first = await BaitcoinOrchestratorBridge.dispatch(payload);
    expect(first.success).toBe(true);

    const duplicate = await BaitcoinOrchestratorBridge.dispatch(payload);
    expect(duplicate.success).toBe(false);
    expect(duplicate.rateLimitStatus).toBe("DUPLICATE_BLOCKED");
  });
});
