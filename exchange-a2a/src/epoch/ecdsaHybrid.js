import crypto from "node:crypto";
import * as ecc from "tiny-secp256k1";
import { logger } from "../logger.js";

export class EcdsaHybridSigner {
  #localKey;
  #localPubkey;
  #kmsKeyId;

  constructor({ localPrivkeyHex = null, kmsKeyId = null } = {}) {
    this.#kmsKeyId = kmsKeyId;
    if (localPrivkeyHex) {
      this.#localKey = Buffer.from(localPrivkeyHex, "hex");
    } else {
      this.#localKey = crypto.randomBytes(32);
    }
    if (this.#localKey.length !== 32) throw new Error("chave local deve ter 32 bytes");
    this.#localPubkey = Buffer.from(ecc.pointFromScalar(this.#localKey, true));
  }

  get mode() { return this.#kmsKeyId ? "kms" : "local"; }
  get pubkeyHex() { return this.#localPubkey.toString("hex"); }
  get keyId() { return this.#kmsKeyId; }

  async init() { return this; }

  async sign(hashHex) {
    const hash = Buffer.from(hashHex, "hex");
    if (hash.length !== 32) throw new Error(`digest deve ter 32 bytes (tem ${hash.length})`);
    if (this.#kmsKeyId) {
      throw new Error("KMS não implementado neste slice — use EPOCH_LOCAL_PRIVKEY_HEX");
    }
    const sig = Buffer.from(ecc.sign(hash, this.#localKey));
    return {
      signature: sig, signatureHex: sig.toString("hex"),
      pubkeyHex: this.pubkeyHex, mode: "local", kmsKeyId: null,
    };
  }

  verify(hashHex, signatureHex, pubkeyHex) {
    try {
      const hash = Buffer.from(hashHex, "hex");
      const sig = Buffer.from(signatureHex, "hex");
      const pk = Buffer.from(pubkeyHex ?? this.pubkeyHex, "hex");
      const compact = sig.length === 65 ? sig.subarray(0, 64) : sig;
      return ecc.verify(hash, pk, compact);
    } catch (err) {
      logger.warn({ err: err.message }, "ecdsa verify erro");
      return false;
    }
  }
}
