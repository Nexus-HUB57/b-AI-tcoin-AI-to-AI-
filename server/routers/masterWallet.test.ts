import { describe, expect, it } from "vitest";
import { MasterWalletGuard } from "../wallet/masterWalletGuard";

describe("MasterWallet Router & Security Guard", () => {
  it("deve validar o estado da master wallet protegida pela Master Passphrase", () => {
    const state = MasterWalletGuard.getMasterWalletState();
    expect(state.masterAddress).toBeDefined();
    expect(state.unifiedUnderSingleVault).toBe(true);
    expect(state.requiredConfirmations).toBe(6);
    expect(state.maxTransactionLimitBTC).toBe(1.0);
  });

  it("deve assinar e verificar payloads determinísticamente com HMAC-SHA256", () => {
    const payload = "test-payload-mainnet";
    const sig = MasterWalletGuard.signPayloadDeterministic(payload);
    expect(sig).toBeDefined();
    expect(MasterWalletGuard.verifyMasterSignature(payload, sig)).toBe(true);
  });
});
