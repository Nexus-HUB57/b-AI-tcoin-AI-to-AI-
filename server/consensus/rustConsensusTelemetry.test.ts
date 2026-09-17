import { describe, expect, it } from "vitest";
import { RustConsensusTelemetry } from "./rustConsensusTelemetry";

describe("RustConsensusTelemetry (High-Performance Core)", () => {
  it("deve retornar métricas válidas de consenso do núcleo Rust", () => {
    const metrics = RustConsensusTelemetry.getMetrics();
    expect(metrics.blockHeight).toBeGreaterThan(0);
    expect(metrics.tps).toBeGreaterThan(100000);
    expect(metrics.consensusHealth).toBe("OPTIMAL");
    expect(metrics.masterVaultSecured).toBe(true);
  });

  it("deve verificar bloco simulado do Rust core com hash de auditoria", () => {
    const res = RustConsensusTelemetry.verifyRustBlockSimulation("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    expect(res.valid).toBe(true);
    expect(res.auditHash).toBeDefined();
  });
});
