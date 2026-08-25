import { describe, expect, it } from "vitest";
import { RustBlockExplorer } from "./rustBlockExplorer";

describe("RustBlockExplorer (Detailed Block Inspection)", () => {
  it("deve retornar lista completa de blocos inspecionáveis", () => {
    const blocks = RustBlockExplorer.getInspectableBlocks();
    expect(blocks.length).toBeGreaterThanOrEqual(3);
    for (const b of blocks) {
      expect(b.validatorAgentId).toBeDefined();
      expect(b.blockHash).toMatch(/^0000/);
      expect(b.consensusSignature).toContain("hmac-sha256");
    }
  });

  it("deve retornar o bloco exato correspondente à altura solicitada", () => {
    const target = RustBlockExplorer.getBlockByHeight(850422);
    expect(target).toBeDefined();
    expect(target?.height).toBe(850422);
    expect(target?.validatorAgentId).toBe("phd-agent-alpha-blockchain");
    expect(target?.agentConfidence).toBe(0.9999);
  });
});
