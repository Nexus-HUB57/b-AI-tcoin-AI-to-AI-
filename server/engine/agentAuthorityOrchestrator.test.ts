import { describe, expect, it } from "vitest";
import { AgentAuthorityOrchestrator } from "./agentAuthorityOrchestrator";

describe("AgentAuthorityOrchestrator (Autonomous Governance)", () => {
  it("deve retornar status de governança válido", () => {
    const status = AgentAuthorityOrchestrator.getGovernanceStatus();
    expect(status.governanceTier).toBe("AUTONOMOUS_PhD_VERIFIABLE_CONSENSUS");
    expect(status.policyBoundAutonomy).toBe(true);
  });

  it("deve avaliar tarefa e gerar proposta com assinatura de auditoria HMAC", () => {
    const proposal = AgentAuthorityOrchestrator.evaluateAndDelegate(
      "agent-phd-omega",
      "BLOCKCHAIN_MAINNET",
      "payload-test-tx-1"
    );

    expect(proposal.agentId).toBe("agent-phd-omega");
    expect(proposal.capabilityRequired).toBe("BLOCKCHAIN_MAINNET");
    expect(proposal.auditSignature).toBeDefined();
    expect(typeof proposal.consensusScore).toBe("number");
  });
});
