import { describe, expect, it } from "vitest";
import { LastWaveAlgorithmicEngine } from "./lastWaveAlgorithmicEngine";

describe("LastWaveAlgorithmicEngine (Neural-Symbolic Consensus)", () => {
  it("deve avaliar a entropia do consenso e retornar prova neural-symbolic válida", () => {
    const proof = LastWaveAlgorithmicEngine.evaluateConsensusEntropy(850422, 2450);
    expect(proof.entropyScore).toBeGreaterThan(0.80);
    expect(proof.neuralConfidence).toBeGreaterThan(0.99);
    expect(proof.symbolicValidity).toBe(true);
    expect(proof.auditSignature).toBeDefined();
  });

  it("deve retornar status operacional de última onda", () => {
    const status = LastWaveAlgorithmicEngine.getEngineStatus();
    expect(status.algorithmTier).toBe("LAST_WAVE_NEURAL_SYMBOLIC_HYBRID");
    expect(status.masterVaultSecured).toBe(true);
  });
});
