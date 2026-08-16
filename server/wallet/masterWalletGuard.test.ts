import { describe, expect, it } from "vitest";
import { MasterWalletGuard } from "./masterWalletGuard";

describe("MasterWalletGuard (Unified Master Wallet)", () => {
  it("deve unificar endereços sob a Master Wallet protegida pela Master Key", () => {
    const state = MasterWalletGuard.getMasterWalletState();
    expect(state.unifiedUnderSingleVault).toBe(true);
    expect(state.passphraseSecured).toBe(true);
    expect(state.requiredConfirmations).toBe(6);
    expect(state.maxTransactionLimitBTC).toBe(1.0);
  });

  it("deve assinar e verificar payloads deterministicamente com a Master Key", () => {
    const payload = "transfer:0.5BTC:to_reserve";
    const sig = MasterWalletGuard.signPayloadDeterministic(payload);
    expect(sig).toBeDefined();

    const isValid = MasterWalletGuard.verifyMasterSignature(payload, sig);
    expect(isValid).toBe(true);
  });
});
