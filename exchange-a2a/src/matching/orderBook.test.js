import { describe, it, expect, vi, beforeEach } from "vitest";
import crypto from "node:crypto";

// Mock db module
vi.mock("../db.js", () => ({
  query: vi.fn(),
  withTx: vi.fn(async (fn) => fn({
    query: vi.fn(),
  })),
}));

// Mock logger
vi.mock("../logger.js", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

// Mock reputation engine
vi.mock("../reputation/engine.js", () => ({
  reputation: {
    get: vi.fn(async () => ({ trust_tier: "gold" })),
  },
}));

// Mock matching engine
vi.mock("./matchingEngine.js", () => ({
  matchingEngine: {
    match: vi.fn(async () => []),
  },
}));

// Mock metrics
vi.mock("../metrics/registry.js", () => ({
  ordersTotal: { inc: vi.fn() },
  orderLatency: { observe: vi.fn() },
}));

import { orderBook } from "./orderBook.js";
import { query, withTx } from "../db.js";
import { matchingEngine } from "./matchingEngine.js";

describe("OrderBook — validatePair", () => {
  it("should reject empty pair", async () => {
    await expect(
      orderBook.place({ agentId: "a1", pair: "", side: "buy", quantity: 100, price: 50 })
    ).rejects.toThrow("pair obrigatório");
  });

  it("should reject invalid side", async () => {
    await expect(
      orderBook.place({ agentId: "a1", pair: "BAIT/USDC", side: "hold", quantity: 100, price: 50 })
    ).rejects.toThrow("side inválido");
  });

  it("should reject invalid type", async () => {
    await expect(
      orderBook.place({ agentId: "a1", pair: "BAIT/USDC", side: "buy", type: "stop", quantity: 100, price: 50 })
    ).rejects.toThrow("type inválido");
  });

  it("should reject limit order without price", async () => {
    await expect(
      orderBook.place({ agentId: "a1", pair: "BAIT/USDC", side: "buy", quantity: 100 })
    ).rejects.toThrow("limit requer price > 0");
  });

  it("should reject zero quantity", async () => {
    await expect(
      orderBook.place({ agentId: "a1", pair: "BAIT/USDC", side: "buy", quantity: 0, price: 50 })
    ).rejects.toThrow("quantity deve ser > 0");
  });

  it("should reject negative quantity", async () => {
    await expect(
      orderBook.place({ agentId: "a1", pair: "BAIT/USDC", side: "buy", quantity: -10, price: 50 })
    ).rejects.toThrow("quantity deve ser > 0");
  });
});

describe("OrderBook — place", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call withTx for atomic insert+match", async () => {
    const mockTxClient = {
      query: vi.fn()
        .mockResolvedValueOnce({ rows: [{ id: "order-1", agent_id: "a1", pair: "BAIT/USDC", side: "buy", type: "limit", price: 50, quantity: 100, filled: 0, status: "open" }] })
        .mockResolvedValueOnce({ rows: [] })
        .mockResolvedValueOnce({ rows: [] }),
    };
    vi.mocked(withTx).mockImplementationOnce(async (fn) => fn(mockTxClient));
    vi.mocked(query).mockResolvedValue({ rows: [{ status: "open", filled: 0 }] });

    const result = await orderBook.place({
      agentId: "a1",
      pair: "BAIT/USDC",
      side: "buy",
      type: "limit",
      price: 50,
      quantity: 100,
    });

    expect(withTx).toHaveBeenCalled();
    expect(result.orderId).toBeDefined();
  });
});

describe("OrderBook — cancel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should cancel an open order", async () => {
    vi.mocked(query).mockResolvedValueOnce({ rowCount: 1 });

    const result = await orderBook.cancel({ agentId: "a1", orderId: "order-1" });
    expect(result.status).toBe("cancelled");
  });

  it("should throw if order not cancelable", async () => {
    vi.mocked(query).mockResolvedValueOnce({ rowCount: 0 });

    await expect(
      orderBook.cancel({ agentId: "a1", orderId: "order-1" })
    ).rejects.toThrow("ordem não cancelável");
  });
});
