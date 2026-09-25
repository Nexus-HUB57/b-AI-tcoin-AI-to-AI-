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
  config: { x402: { mode: "local" } },
}));

import { x402Client } from "./x402Client.js";
import { query } from "../db.js";

describe("X402Client — createEscrow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should create escrow and payment records", async () => {
    vi.mocked(query)
      .mockResolvedValueOnce({ rows: [{ id: "escrow-1" }] })  // INSERT escrow
      .mockResolvedValueOnce({ rows: [] });  // INSERT payment

    const result = await x402Client.createEscrow({
      tradeId: "trade-1",
      buyerAgent: "buyer-1",
      sellerAgent: "seller-1",
      buyerAmount: 1000,
      sellerAmount: 500,
      pair: "BAIT/USDC",
    });

    expect(result.escrowId).toBe("escrow-1");
    expect(result.paymentRequiredId).toMatch(/^x402-/);
    expect(result.buyerPaymentRequest.amount).toBe(1000);
    expect(result.sellerPaymentRequest.amount).toBe(500);
  });
});

describe("X402Client — verify", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should reject unknown payment", async () => {
    vi.mocked(query).mockResolvedValueOnce({ rows: [] });

    const result = await x402Client.verify({ paymentRequiredId: "x402-unknown" });
    expect(result.valid).toBe(false);
    expect(result.reason).toBe("not_found");
  });

  it("should reject expired payment", async () => {
    const pastDate = new Date(Date.now() - 60000).toISOString();
    vi.mocked(query)
      .mockResolvedValueOnce({ rows: [{ id: "pay-1", expires_at: pastDate }] })
      .mockResolvedValueOnce({ rows: [] });

    const result = await x402Client.verify({ paymentRequiredId: "x402-expired" });
    expect(result.valid).toBe(false);
    expect(result.reason).toBe("expired");
  });

  it("should accept valid non-expired payment", async () => {
    const futureDate = new Date(Date.now() + 600000).toISOString();
    vi.mocked(query)
      .mockResolvedValueOnce({ rows: [{ id: "pay-1", expires_at: futureDate }] })
      .mockResolvedValueOnce({ rows: [] });

    const result = await x402Client.verify({ paymentRequiredId: "x402-valid" });
    expect(result.valid).toBe(true);
  });
});

describe("X402Client — health", () => {
  it("should return true in local mode", async () => {
    const result = await x402Client.health();
    expect(result).toBe(true);
  });
});
