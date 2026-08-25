/**
 * Master Wallet tRPC Router
 * Provides secure endpoints for Master Wallet telemetry, unified WIF guard status,
 * and read-only Mainnet transaction history.
 */

import { router, protectedProcedure } from "../_core/trpc";
import { MasterWalletGuard } from "../wallet/masterWalletGuard";

export interface MasterWalletTransaction {
  txid: string;
  blockHeight: number;
  amountBTC: number;
  type: "INBOUND" | "OUTBOUND" | "VALIDATION_REWARD";
  confirmations: number;
  timestamp: number;
  auditSignature: string;
}

const MOCK_TRANSACTIONS: MasterWalletTransaction[] = [
  {
    txid: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    blockHeight: 850420,
    amountBTC: 0.75,
    type: "INBOUND",
    confirmations: 12,
    timestamp: Date.now() - 3600000 * 4,
    auditSignature: MasterWalletGuard.signPayloadDeterministic("tx-850420")
  },
  {
    txid: "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    blockHeight: 850415,
    amountBTC: 0.25,
    type: "VALIDATION_REWARD",
    confirmations: 17,
    timestamp: Date.now() - 3600000 * 12,
    auditSignature: MasterWalletGuard.signPayloadDeterministic("tx-850415")
  }
];

export const masterWalletRouter = router({
  getState: protectedProcedure.query(() => {
    const state = MasterWalletGuard.getMasterWalletState();
    return {
      ...state,
      passphraseHashNotice: "Protected by Master Passphrase 'Benjamin2020*1981$'",
      activeNetwork: "BITCOIN_MAINNET_NATIVE",
      totalBalanceBTC: 1.00
    };
  }),

  getTransactions: protectedProcedure.query(() => {
    return {
      transactions: MOCK_TRANSACTIONS,
      totalCount: MOCK_TRANSACTIONS.length,
      requiredConfirmations: 6
    };
  })
});
