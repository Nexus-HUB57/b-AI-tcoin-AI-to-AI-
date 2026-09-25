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

// Mock settlement
vi.mock("./settlement.js", () => ({
  settlement: { settleTrade: vi.fn(async () => {}) },
}));

// Mock metrics
vi.mock("../metrics/registry.js", () => ({
  tradesTotal: { inc: vi.fn() },
}));

import { matchingEngine } from "./matchingEngine.js";
import { withTx } from "../db.js";

describe("MatchingEngine — match", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should return empty matches when no resting orders", async () => {
    const mockClient = {
      query: vi.fn()
        .mockResolvedValueOnce({ rows: [] }),  // No resting orders
    };
    vi.mocked(withTx).mockImplementationOnce(async (fn) => fn(mockClient));

    const newOrder = {
      id: "order-1",
      pair: "BAIT/USDC",
      side: "buy",
      type: "limit",
      price: 100,
      quantity: 10,
      filled: 0,
      agent_id: "a1",
    };

    const matches = await matchingEngine.match(newOrder);
    expect(matches).toEqual([]);
  });

  it("should cancel market order with no liquidity", async () => {
    const mockClient = {
      query: vi.fn()
        .mockResolvedValueOnce({ rows: [] })  // No resting orders
        .mockResolvedValueOnce({ rows: [] }),  // Cancel update
    };
    vi.mocked(withTx).mockImplementationOnce(async (fn) => fn(mockClient));

    const newOrder = {
      id: "order-2",
      pair: "BAIT/USDC",
      side: "buy",
      type: "market",
      price: null,
      quantity: 10,
      filled: 0,
      agent_id: "a1",
    };

    const matches = await matchingEngine.match(newOrder);
    expect(matches).toEqual([]);
    // The market order should be cancelled
    expect(mockClient.query).toHaveBeenCalledTimes(2);
  });
});
