import { describe, expect, it } from "vitest";
import { MainnetExecutionEngine } from "./mainnetExecutionEngine";

describe("MainnetExecutionEngine (No Simulation, Native Mainnet)", () => {
  it("deve operar exclusivamente em Bitcoin Mainnet sem simulação", () => {
    const status = MainnetExecutionEngine.getSystemStatus();
    expect(status.network).toContain("Mainnet");
    expect(status.simulationAllowed).toBe(false);
  });

  it("deve gerenciar failover automático entre nós primário e fallback", () => {
    const initialPrimary = MainnetExecutionEngine.getActiveNode().providerId;
    expect(initialPrimary).toBe("primary-rpc-node");

    MainnetExecutionEngine.reportNodeFailure("primary-rpc-node");
    const newPrimary = MainnetExecutionEngine.getActiveNode().providerId;
    expect(newPrimary).toBe("fallback-rpc-node");
  });

  it("deve validar criptografia WIF com a passphrase mestre", () => {
    const isValid = MainnetExecutionEngine.verifyMasterWIFEncryption("X0pHPC6zmMI9+Nb/QCP9mji0FxGfC1IHM+x/nGhf+Sb9SttJecDhxZp00k9bpKT6rk7gZGWRp3aJ6K3qxIU10o7eqfztkGeG2OuJFxXLs1M=");
    expect(isValid).toBe(true);
  });
});
