import { describe, expect, it } from "vitest";
import { MainnetZeroSimulationGuard } from "./mainnetZeroSimulationGuard";

describe("MainnetZeroSimulationGuard", () => {
  it("deve impor zero simulação e retornar status mainnet nativa", () => {
    expect(() => MainnetZeroSimulationGuard.enforceZeroSimulation()).not.toThrow();
    const status = MainnetZeroSimulationGuard.getGuardStatus();
    expect(status.network).toBe("BITCOIN_MAINNET_NATIVE");
    expect(status.simulationAllowed).toBe(false);
  });
});
