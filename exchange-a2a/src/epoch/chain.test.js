import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock db module
vi.mock("../db.js", () => ({
  query: vi.fn(),
  withTx: vi.fn(),
}));

// Mock logger
vi.mock("../logger.js", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

// Mock config
vi.mock("../config.js", () => ({
  config: { epoch: { localPrivkeyHex: null, kmsKeyId: null } },
}));

// Mock ecdsaHybrid
vi.mock("./ecdsaHybrid.js", () => ({
  EcdsaHybridSigner: vi.fn().mockImplementation(() => ({
    init: vi.fn(async () => {}),
    sign: vi.fn(async (hash) => ({ signatureHex: "sig_" + hash.slice(0, 8), pubkeyHex: "pub123", kmsKeyId: null })),
    verify: vi.fn(() => true),
  })),
}));

// Mock metrics
vi.mock("../metrics/registry.js", () => ({
  epochHeight: { set: vi.fn() },
}));

import { epochChain } from "./chain.js";
import { query } from "../db.js";

describe("EpochChain — computeHash", () => {
  it("should produce deterministic SHA-256 hash", () => {
    const h1 = epochChain.computeHash({
      prevHash: "genesis",
      payload: { kind: "test" },
      timestamp: 1000,
    });
    const h2 = epochChain.computeHash({
      prevHash: "genesis",
      payload: { kind: "test" },
      timestamp: 1000,
    });
    expect(h1).toBe(h2);
    expect(h1).toHaveLength(64);  // SHA-256 hex
  });

  it("should produce different hash for different payload", () => {
    const h1 = epochChain.computeHash({
      prevHash: "genesis",
      payload: { kind: "test" },
      timestamp: 1000,
    });
    const h2 = epochChain.computeHash({
      prevHash: "genesis",
      payload: { kind: "other" },
      timestamp: 1000,
    });
    expect(h1).not.toBe(h2);
  });
});

describe("EpochChain — head", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should return null when no epochs exist", async () => {
    vi.mocked(query).mockResolvedValueOnce({ rows: [] });
    const head = await epochChain.head();
    expect(head).toBeNull();
  });

  it("should return latest epoch", async () => {
    const mockHead = { epoch: 42, epoch_hash: "abc123", prev_hash: "def456", payload: {}, created_at: "2026-01-01" };
    vi.mocked(query).mockResolvedValueOnce({ rows: [mockHead] });
    const head = await epochChain.head();
    expect(head).toEqual(mockHead);
  });
});
