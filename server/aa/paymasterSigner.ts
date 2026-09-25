/**
 * Off-chain verifying-paymaster signer (ERC-4337).
 *
 * Env:
 *   PAYMASTER_SIGNER_KEY  — hex private key (ops only; never user KEYSTORE_*)
 *   PAYMASTER_ADDRESS     — deployed BAITVerifyingPaymaster
 *   CHAIN_ID              — e.g. 1 | 11155111
 *
 * Signs: keccak256(abi.encode(userOpHash, validUntil, validAfter, paymaster, chainId))
 * then personal_sign (EIP-191) to match OpenZeppelin MessageHashUtils.toEthSignedMessageHash.
 */

import { keccak256, AbiCoder, SigningKey, Signature, getBytes, hexlify, solidityPacked } from "ethers";

const coder = AbiCoder.defaultAbiCoder();

export type SponsorRequest = {
  userOpHash: string;
  validUntil: number; // unix seconds
  validAfter?: number;
};

export type SponsorResult = {
  paymasterAndData: string;
  validUntil: number;
  validAfter: number;
  signature: string;
};

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing env ${name}`);
  return v;
}

export function getPaymasterHash(
  userOpHash: string,
  validUntil: number,
  validAfter: number,
  paymaster: string,
  chainId: number,
): string {
  return keccak256(
    coder.encode(
      ["bytes32", "uint48", "uint48", "address", "uint256"],
      [userOpHash, validUntil, validAfter, paymaster, chainId],
    ),
  );
}

/** EIP-191 eth signed message hash of a 32-byte digest */
export function toEthSignedMessageHash(digest: string): string {
  return keccak256(
    solidityPacked(["string", "bytes32"], [`\x19Ethereum Signed Message:\n32`, digest]),
  );
}

export function signPaymasterApproval(req: SponsorRequest): SponsorResult {
  const keyHex = requireEnv("PAYMASTER_SIGNER_KEY");
  const paymaster = requireEnv("PAYMASTER_ADDRESS");
  const chainId = Number(process.env.CHAIN_ID || "1");
  const validAfter = req.validAfter ?? 0;
  const validUntil = req.validUntil;

  const digest = getPaymasterHash(req.userOpHash, validUntil, validAfter, paymaster, chainId);
  const ethHash = toEthSignedMessageHash(digest);
  const signingKey = new SigningKey(keyHex.startsWith("0x") ? keyHex : `0x${keyHex}`);
  const sig = Signature.from(signingKey.sign(getBytes(ethHash)));
  const signature = sig.serialized; // 0x r||s||v

  // pack: paymaster (20) || validUntil (6) || validAfter (6) || signature (65)
  const untilHex = validUntil.toString(16).padStart(12, "0");
  const afterHex = validAfter.toString(16).padStart(12, "0");
  const paymasterAndData = hexlify(
    solidityPacked(
      ["address", "uint48", "uint48", "bytes"],
      [paymaster, validUntil, validAfter, signature],
    ),
  );

  // solidtyPacked already correct; keep untilHex for debug
  void untilHex;
  void afterHex;

  return { paymasterAndData, validUntil, validAfter, signature };
}

/** Express/Fastify-style handler sketch */
export async function sponsorHandler(body: {
  userOpHash: string;
  validUntil?: number;
  validAfter?: number;
}): Promise<SponsorResult> {
  const now = Math.floor(Date.now() / 1000);
  const validUntil = body.validUntil ?? now + 300; // 5 min
  if (validUntil < now) throw new Error("validUntil in the past");
  if (validUntil > now + 3600) throw new Error("validUntil too far (>1h)");
  return signPaymasterApproval({
    userOpHash: body.userOpHash,
    validUntil,
    validAfter: body.validAfter ?? 0,
  });
}
