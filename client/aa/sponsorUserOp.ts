/**
 * Client helper: attach verifying-paymaster data to a UserOperation skeleton.
 * Does not hold private keys — asks backend /api/aa/sponsor then submits to bundler.
 */

export type UserOperationLike = {
  sender: string;
  nonce: string;
  initCode: string;
  callData: string;
  callGasLimit: string;
  verificationGasLimit: string;
  preVerificationGas: string;
  maxFeePerGas: string;
  maxPriorityFeePerGas: string;
  paymasterAndData: string;
  signature: string;
};

export async function requestPaymasterData(
  sponsorUrl: string,
  userOpHash: string,
  opts?: { validUntil?: number; validAfter?: number },
): Promise<string> {
  const res = await fetch(sponsorUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userOpHash,
      validUntil: opts?.validUntil,
      validAfter: opts?.validAfter,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`sponsor failed: ${res.status} ${text}`);
  }
  const json = (await res.json()) as { paymasterAndData: string };
  return json.paymasterAndData;
}

/**
 * Full soft flow (bundler-dependent):
 * 1) Build UserOp without pm data
 * 2) Get userOpHash from EntryPoint/bundler
 * 3) requestPaymasterData
 * 4) Sign UserOp with smart-account / owner
 * 5) eth_sendUserOperation
 */
export async function attachPaymaster(
  userOp: UserOperationLike,
  userOpHash: string,
  sponsorUrl: string,
): Promise<UserOperationLike> {
  const paymasterAndData = await requestPaymasterData(sponsorUrl, userOpHash);
  return { ...userOp, paymasterAndData };
}
