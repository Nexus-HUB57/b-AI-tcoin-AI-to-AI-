/**
 * BaitcoinKit.kt - b'AI'tcoin Mobile SDK for Android
 *
 * Copyright (c) 2024 b'AI'tcoin Foundation. All rights reserved.
 *
 * Requires: Android API 24+ (Android 7.0 Nougat)
 * Kotlin 1.6+
 *
 * ============================================================================
 * IMPORTANT: Android builds must include BouncyCastle (bcprov-jdk18on). The
 * BouncyCastle-backed provider below performs the secp256k1 point operations;
 * BIP-340 encoding, tagged hashing, signing, and verification are implemented
 * directly from the published specification. There is deliberately no crypto
 * placeholder or SHA-256 stand-in for elliptic-curve operations.
 * ============================================================================
 */

package org.baitcoin.sdk

import java.math.BigInteger
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import org.bouncycastle.asn1.sec.SECNamedCurves
import org.bouncycastle.asn1.x9.X9ECParameters
import org.bouncycastle.crypto.digests.RIPEMD160Digest
import org.bouncycastle.math.ec.ECPoint
import org.json.JSONArray
import org.json.JSONObject

// ============================================================================
// Network
// ============================================================================

/**
 * Represents the b'AI'tcoin network variant.
 * Mainnet uses 'b' address prefix, testnet uses 't' address prefix.
 *
 * @property prefix The single-character prefix used in addresses for this network.
 * @property displayName Human-readable network name.
 */
enum class Network(val prefix: Char, val displayName: String) {
    /** Production b'AI'tcoin network with 'b' prefixed addresses. */
    MAINNET('b', "b'AI'tcoin Mainnet"),

    /** Test network for development with 't' prefixed addresses. */
    TESTNET('t', "b'AI'tcoin Testnet");

    companion object {
        /** Parse a network from its prefix character. */
        fun fromPrefix(prefix: Char): Network? = when (prefix) {
            'b' -> MAINNET
            't' -> TESTNET
            else -> null
        }
    }
}

// ============================================================================
// CryptoProvider Interface
// ============================================================================

/**
 * Interface abstracting elliptic curve cryptographic operations.
 * Implementations must use a real secp256k1 primitive and BIP-340 semantics.
 * The SDK default is [BouncyCastleCryptoProvider]; callers supplying a custom
 * provider are responsible for equivalent validation and cryptographic security.
 */
interface CryptoProvider {
    /**
     * Generate a new secp256k1 key pair.
     * @return Pair of (privateKey, publicKey) where publicKey is 32 bytes x-only.
     */
    fun generateKeyPair(): Pair<ByteArray, ByteArray>

    /**
     * Derive the 32-byte x-only public key from a 32-byte private key.
     * @param privateKey The 32-byte private key.
     * @return The 32-byte x-only public key.
     */
    fun derivePublicKey(privateKey: ByteArray): ByteArray

    /**
     * Sign a message using Schnorr/BIP-340 with the given private key.
     * @param message The 32-byte message digest to sign.
     * @param privateKey The 32-byte secp256k1 private key.
     * @return The 64-byte Schnorr signature.
     */
    fun schnorrSign(message: ByteArray, privateKey: ByteArray): ByteArray

    /**
     * Verify a Schnorr/BIP-340 signature.
     * @param signature The 64-byte Schnorr signature.
     * @param message The 32-byte message digest.
     * @param publicKey The 32-byte x-only public key.
     * @return True if the signature is valid.
     */
    fun schnorrVerify(signature: ByteArray, message: ByteArray, publicKey: ByteArray): Boolean
}

// ============================================================================
// BouncyCastleCryptoProvider (secp256k1 + BIP-340)
// ============================================================================

/**
 * BouncyCastle-backed secp256k1 provider implementing BIP-340 Schnorr.
 *
 * BouncyCastle supplies the audited secp256k1 curve and scalar/point
 * arithmetic. The BIP-340 rules that are not exposed as a high-level JCA API
 * (x-only key lifting, even-Y normalization, tagged hashes, and Schnorr
 * equation checking) are kept explicitly here so they can be reviewed against
 * the specification. Java's standard cryptography APIs are not used as a
 * substitute for secp256k1.
 *
 * @see <a href="https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki">BIP-340</a>
 */
class BouncyCastleCryptoProvider(
    private val random: SecureRandom = SecureRandom()
) : CryptoProvider {

    private val curveParameters: X9ECParameters = requireNotNull(
        SECNamedCurves.getByName("secp256k1")
    ) { "BouncyCastle does not expose secp256k1" }
    private val curve = curveParameters.curve
    private val generator: ECPoint = curveParameters.g

    override fun generateKeyPair(): Pair<ByteArray, ByteArray> {
        val privateKey = ByteArray(BYTES_32)
        do {
            random.nextBytes(privateKey)
        } while (!isValidPrivateKey(privateKey))
        return privateKey.copyOf() to derivePublicKey(privateKey)
    }

    override fun derivePublicKey(privateKey: ByteArray): ByteArray {
        val scalar = requirePrivateKey(privateKey)
        val point = generator.multiply(scalar).normalize()
        return toFixed32(point.affineXCoord.toBigInteger())
    }

    override fun schnorrSign(message: ByteArray, privateKey: ByteArray): ByteArray {
        requireMessage(message)
        // BIP-340 requires a fresh 32-byte auxiliary random value. The
        // overload taking auxRand exists for deterministic conformance tests.
        val auxRand = ByteArray(BYTES_32).also(random::nextBytes)
        return schnorrSign(message, privateKey, auxRand)
    }

    /**
     * Sign with an explicit BIP-340 auxiliary randomness value. This is useful
     * for reproducing the official vectors; production callers should use the
     * interface method, which obtains fresh randomness from SecureRandom.
     */
    fun schnorrSign(message: ByteArray, privateKey: ByteArray, auxRand: ByteArray): ByteArray {
        requireMessage(message)
        require(auxRand.size == BYTES_32) { "BIP-340 auxiliary randomness must be 32 bytes" }

        val d0 = requirePrivateKey(privateKey)
        val publicPoint = generator.multiply(d0).normalize()
        val d = if (isOdd(publicPoint.affineYCoord.toBigInteger())) {
            ORDER.subtract(d0)
        } else {
            d0
        }
        val publicKeyX = toFixed32(publicPoint.affineXCoord.toBigInteger())
        val maskedKey = xor(
            toFixed32(d),
            taggedHash("BIP0340/aux", auxRand)
        )
        val nonceHash = taggedHash("BIP0340/nonce", maskedKey + publicKeyX + message)
        val k0 = BigInteger(1, nonceHash).mod(ORDER)
        require(k0.signum() != 0) { "BIP-340 nonce generation produced zero" }

        val noncePoint = generator.multiply(k0).normalize()
        val k = if (isOdd(noncePoint.affineYCoord.toBigInteger())) {
            ORDER.subtract(k0)
        } else {
            k0
        }
        val rX = toFixed32(noncePoint.affineXCoord.toBigInteger())
        val challenge = BigInteger(1, taggedHash("BIP0340/challenge", rX + publicKeyX + message))
            .mod(ORDER)
        val s = k.add(challenge.multiply(d)).mod(ORDER)
        return rX + toFixed32(s)
    }

    override fun schnorrVerify(signature: ByteArray, message: ByteArray, publicKey: ByteArray): Boolean {
        if (signature.size != BYTES_64 || message.size != BYTES_32 || publicKey.size != BYTES_32) {
            return false
        }

        return try {
            val r = BigInteger(1, signature.copyOfRange(0, BYTES_32))
            val s = BigInteger(1, signature.copyOfRange(BYTES_32, BYTES_64))
            if (r.signum() < 0 || r >= FIELD_PRIME || s.signum() < 0 || s >= ORDER) {
                return false
            }

            val publicPoint = liftX(publicKey) ?: return false
            val challenge = BigInteger(
                1,
                taggedHash(
                    "BIP0340/challenge",
                    signature.copyOfRange(0, BYTES_32) + publicKey + message
                )
            ).mod(ORDER)
            val result = generator.multiply(s)
                .subtract(publicPoint.multiply(challenge))
                .normalize()

            !result.isInfinity &&
                !isOdd(result.affineYCoord.toBigInteger()) &&
                result.affineXCoord.toBigInteger() == r
        } catch (_: RuntimeException) {
            // Malformed encodings and invalid curve points fail closed.
            false
        }
    }

    private fun requirePrivateKey(privateKey: ByteArray): BigInteger {
        require(isValidPrivateKey(privateKey)) {
            "secp256k1 private key must be exactly 32 bytes and in [1, n-1]"
        }
        return BigInteger(1, privateKey)
    }

    private fun isValidPrivateKey(privateKey: ByteArray): Boolean {
        if (privateKey.size != BYTES_32) return false
        val scalar = BigInteger(1, privateKey)
        return scalar.signum() > 0 && scalar < ORDER
    }

    private fun requireMessage(message: ByteArray) {
        require(message.size == BYTES_32) { "BIP-340 message must be exactly 32 bytes" }
    }

    /** BIP-340 lift_x: return the unique secp256k1 point with even Y. */
    private fun liftX(xBytes: ByteArray): ECPoint? {
        if (xBytes.size != BYTES_32) return null
        val x = BigInteger(1, xBytes)
        if (x >= FIELD_PRIME) return null

        val alpha = x.modPow(BigInteger.valueOf(3), FIELD_PRIME)
            .add(BigInteger.valueOf(7))
            .mod(FIELD_PRIME)
        var beta = alpha.modPow(FIELD_PRIME.add(BigInteger.ONE).shiftRight(2), FIELD_PRIME)
        if (beta.multiply(beta).mod(FIELD_PRIME) != alpha) return null
        if (isOdd(beta)) beta = FIELD_PRIME.subtract(beta)

        return try {
            curve.createPoint(x, beta).normalize().takeIf { !it.isInfinity && it.isValid }
        } catch (_: RuntimeException) {
            null
        }
    }

    private fun taggedHash(tag: String, data: ByteArray): ByteArray {
        val tagHash = sha256(tag.toByteArray(Charsets.UTF_8))
        return sha256(tagHash + tagHash + data)
    }

    private fun sha256(data: ByteArray): ByteArray = MessageDigest.getInstance("SHA-256").digest(data)

    private fun xor(left: ByteArray, right: ByteArray): ByteArray {
        require(left.size == right.size)
        return ByteArray(left.size) { index -> (left[index].toInt() xor right[index].toInt()).toByte() }
    }

    private fun toFixed32(value: BigInteger): ByteArray {
        val raw = value.toByteArray()
        return when {
            raw.size == BYTES_32 -> raw
            raw.size == BYTES_32 + 1 && raw[0] == 0.toByte() -> raw.copyOfRange(1, raw.size)
            raw.size < BYTES_32 -> ByteArray(BYTES_32 - raw.size) + raw
            else -> error("integer does not fit in 32 bytes")
        }
    }

    private fun isOdd(value: BigInteger): Boolean = value.testBit(0)

    private companion object {
        const val BYTES_32 = 32
        const val BYTES_64 = 64
        val FIELD_PRIME = BigInteger("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F", 16)
        val ORDER = BigInteger("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
    }
}

// ============================================================================
// Hash Utilities
// ============================================================================

/**
 * Cryptographic hash utilities for b'AI'tcoin address generation.
 * Provides SHA-256 and RIPEMD-160 (Hash160) operations.
 */
object BaitcoinHash {

    /**
     * Compute SHA-256 hash.
     * @param data Input byte array.
     * @return 32-byte SHA-256 digest.
     */
    fun sha256(data: ByteArray): ByteArray {
        val md = MessageDigest.getInstance("SHA-256")
        return md.digest(data)
    }

    /**
     * Compute RIPEMD-160 hash.
     * @param data Input byte array.
     * @return 20-byte RIPEMD-160 digest.
     * @note Requires the BouncyCastle `bcprov-jdk18on` dependency. The digest is
     *       instantiated directly from BouncyCastle; no provider registration or
     *       insecure hash fallback is permitted.
     */
    fun ripemd160(data: ByteArray): ByteArray {
        val digest = RIPEMD160Digest()
        digest.update(data, 0, data.size)
        return ByteArray(digest.digestSize).also { digest.doFinal(it, 0) }
    }

    /**
     * Compute Hash160: RIPEMD160(SHA256(data)). Used for b'AI'tcoin address derivation.
     * @param data Input data (typically a 32-byte x-only public key).
     * @return 20-byte Hash160 digest (the pubkey hash).
     */
    fun hash160(data: ByteArray): ByteArray {
        return ripemd160(sha256(data))
    }

    /**
     * Compute double SHA-256 (used in Base58Check).
     * @param data Input byte array.
     * @return 32-byte double-SHA-256 digest.
     */
    fun doubleSha256(data: ByteArray): ByteArray {
        return sha256(sha256(data))
    }
}

// ============================================================================
// Base58 Encoding/Decoding
// ============================================================================

/**
 * Base58 encoding and decoding for b'AI'tcoin addresses.
 * Uses the Bitcoin-style Base58 alphabet:
 * 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
 */
object Base58 {

    /** Base58 alphabet (excludes 0, O, I, l to avoid ambiguity). */
    private const val ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    /**
     * Encode raw bytes to a Base58 string.
     * @param data The raw bytes to encode.
     * @return The Base58-encoded string.
     */
    fun encode(data: ByteArray): String {
        var num = data.fold(0L) { acc, byte -> (acc shl 8) or (byte.toLong() and 0xFF) }

        var result = StringBuilder()
        while (num > 0) {
            val remainder = (num % 58).toInt()
            result.insert(0, ALPHABET[remainder])
            num /= 58
        }

        // Preserve leading zero bytes as '1' characters
        for (byte in data) {
            if (byte == 0.toByte()) {
                result.insert(0, '1')
            } else {
                break
            }
        }

        return if (result.isEmpty()) "1" else result.toString()
    }

    /**
     * Encode raw bytes to a Base58Check string (with 4-byte checksum).
     * @param data The raw bytes to encode (version byte + payload).
     * @return The Base58Check-encoded string.
     */
    fun encodeCheck(data: ByteArray): String {
        val checksum = BaitcoinHash.doubleSha256(data).copyOfRange(0, 4)
        val payload = data + checksum
        return encode(payload)
    }

    /**
     * Decode a Base58 string to raw bytes.
     * @param string The Base58-encoded string.
     * @return The decoded raw bytes, or null if invalid.
     */
    fun decode(string: String): ByteArray? {
        var num = 0L
        var base: Long = 1

        for (char in string.reversed()) {
            val index = ALPHABET.indexOf(char)
            if (index < 0) return null
            num += index.toLong() * base
            base *= 58
        }

        // Count leading '1's (representing leading zero bytes)
        val leadingOnes = string.takeWhile { it == '1' }.length

        val bytes = mutableListOf<Byte>()
        repeat(leadingOnes) { bytes.add(0) }

        // Convert number to big-endian bytes
        if (num > 0) {
            var n = num
            val temp = mutableListOf<Byte>()
            while (n > 0) {
                temp.add(0, (n and 0xFF).toByte())
                n = n ushr 8
            }
            bytes.addAll(temp)
        }

        return if (bytes.isEmpty()) byteArrayOf(0) else bytes.toByteArray()
    }

    /**
     * Decode a Base58Check string and verify the checksum.
     * @param string The Base58Check-encoded string.
     * @return The decoded payload (without checksum), or null if invalid.
     */
    fun decodeCheck(string: String): ByteArray? {
        val decoded = decode(string) ?: return null
        if (decoded.size <= 4) return null

        val payload = decoded.copyOfRange(0, decoded.size - 4)
        val checksum = decoded.copyOfRange(decoded.size - 4, decoded.size)
        val expectedChecksum = BaitcoinHash.doubleSha256(payload).copyOfRange(0, 4)

        if (!checksum.contentEquals(expectedChecksum)) return null
        return payload
    }

    /** Convert List<Byte> to ByteArray. */
    private fun List<Byte>.toByteArray(): ByteArray {
        val arr = ByteArray(this.size)
        this.forEachIndexed { i, b -> arr[i] = b }
        return arr
    }
}

// ============================================================================
// BaitcoinAddress
// ============================================================================

/**
 * Represents a b'AI'tcoin address with validation and parsing capabilities.
 *
 * Address format: `<prefix><Base58Check(Hash160(pubkey))>`
 * - Mainnet prefix: `b` (e.g., b'1A2b3C...)
 * - Testnet prefix: `t` (e.g., t'1XyZ9w...)
 *
 * The address is derived by:
 * 1. Taking the 32-byte x-only public key
 * 2. Computing Hash160 = RIPEMD160(SHA256(pubkey)) -> 20 bytes
 * 3. Prepending a version byte (0x00 for mainnet, 0x6F for testnet)
 * 4. Encoding with Base58Check
 * 5. Prepending the network prefix character
 *
 * @property address The full address string including the prefix.
 * @property network The network this address belongs to.
 * @property pubkeyHash The 20-byte Hash160 pubkey hash.
 */
data class BaitcoinAddress(
    val address: String,
    val network: Network,
    val pubkeyHash: ByteArray
) {
    companion object {
        /** Version byte for mainnet addresses. */
        private const val MAINNET_VERSION: Byte = 0x00

        /** Version byte for testnet addresses. */
        private const val TESTNET_VERSION: Byte = 0x6F

        /**
         * Derive a b'AI'tcoin address from a public key.
         * @param pubkey The 32-byte x-only public key.
         * @param network The target network (mainnet or testnet).
         * @return The derived BaitcoinAddress.
         */
        fun from(pubkey: ByteArray, network: Network): BaitcoinAddress {
            val hash = BaitcoinHash.hash160(pubkey)
            val versionByte: Byte = if (network == Network.MAINNET) MAINNET_VERSION else TESTNET_VERSION
            val payload = byteArrayOf(versionByte) + hash
            val base58 = Base58.encodeCheck(payload)
            val addressString = "${network.prefix}'$base58"
            return BaitcoinAddress(address = addressString, network = network, pubkeyHash = hash)
        }

        /**
         * Parse a b'AI'tcoin address string into a BaitcoinAddress.
         * @param address The address string to parse (e.g., "b'1A2b3C...").
         * @return The parsed BaitcoinAddress, or null if the address is invalid.
         */
        fun parse(address: String): BaitcoinAddress? {
            if (address.length <= 2) return null

            val prefix = address[0]
            val base58Part = address.substring(2) // Remove prefix + quote

            val network = Network.fromPrefix(prefix) ?: return null

            val decoded = Base58.decodeCheck(base58Part) ?: return null
            if (decoded.size < 21) return null

            val versionByte = decoded[0]
            val expectedVersion: Byte = if (network == Network.MAINNET) MAINNET_VERSION else TESTNET_VERSION
            if (versionByte != expectedVersion) return null

            val pubkeyHash = decoded.copyOfRange(1, 21)
            return BaitcoinAddress(address = address, network = network, pubkeyHash = pubkeyHash)
        }

        /**
         * Validate a b'AI'tcoin address string.
         * @param address The address string to validate.
         * @return True if the address is valid.
         */
        fun validate(address: String): Boolean {
            return parse(address) != null
        }
    }

    /**
     * Custom equals to compare pubkeyHash contents.
     */
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is BaitcoinAddress) return false
        return address == other.address &&
               network == other.network &&
               pubkeyHash.contentEquals(other.pubkeyHash)
    }

    override fun hashCode(): Int {
        var result = address.hashCode()
        result = 31 * result + network.hashCode()
        result = 31 * result + pubkeyHash.contentHashCode()
        return result
    }

    override fun toString(): String = address
}

// ============================================================================
// BaitcoinKeyPair
// ============================================================================

/**
 * Represents a secp256k1 key pair for b'AI'tcoin signing operations.
 *
 * The public key is the 32-byte x-only coordinate (BIP-340 / Schnorr style),
 * not the full 65-byte uncompressed public key.
 *
 * @property privateKey The 32-byte secp256k1 private key. **Handle with extreme care.**
 * @property publicKey The 32-byte x-only public key derived from the private key.
 */
class BaitcoinKeyPair(
    val privateKey: ByteArray,
    val publicKey: ByteArray,
    private val crypto: CryptoProvider
) {
    companion object {
        /**
         * Generate a new random key pair.
         * @param crypto The crypto provider (defaults to BouncyCastleCryptoProvider).
         * @return A new BaitcoinKeyPair with fresh random keys.
         */
        fun generate(crypto: CryptoProvider = BouncyCastleCryptoProvider()): BaitcoinKeyPair {
            val (privKey, pubKey) = crypto.generateKeyPair()
            return BaitcoinKeyPair(privKey, pubKey, crypto)
        }

        /**
         * Import a key pair from a hex-encoded private key string.
         * @param hex The 64-character hex string representing the 32-byte private key.
         * @param crypto The crypto provider (defaults to BouncyCastleCryptoProvider).
         * @return A BaitcoinKeyPair, or null if the hex is invalid.
         */
        fun fromPrivateKeyHex(
            hex: String,
            crypto: CryptoProvider = BouncyCastleCryptoProvider()
        ): BaitcoinKeyPair? {
            val cleanHex = if (hex.startsWith("0x")) hex.substring(2) else hex
            if (cleanHex.length != 64) return null
            val privKey = hexToBytes(cleanHex) ?: return null
            return try {
                val pubKey = crypto.derivePublicKey(privKey)
                BaitcoinKeyPair(privKey, pubKey, crypto)
            } catch (_: IllegalArgumentException) {
                // Invalid scalars (zero or >= secp256k1 order) fail closed.
                null
            }
        }

        /** Convert a hex string to a ByteArray. */
        private fun hexToBytes(hex: String): ByteArray? {
            if (hex.length % 2 != 0) return null
            return try {
                ByteArray(hex.length / 2) { i ->
                    val index = i * 2
                    hex.substring(index, index + 2).toInt(16).toByte()
                }
            } catch (e: NumberFormatException) {
                null
            }
        }
    }

    /**
     * Sign a message using Schnorr/BIP-340.
     * @param message The message data to sign.
     * @return The 64-byte Schnorr signature.
     */
    fun sign(message: ByteArray): ByteArray {
        val messageHash = BaitcoinHash.sha256(message)
        return crypto.schnorrSign(messageHash, privateKey)
    }

    /**
     * Export the private key as a hex string.
     * @return 64-character lowercase hex string.
     */
    fun privateKeyHex(): String {
        return privateKey.joinToString("") { "%02x".format(it) }
    }

    /**
     * Export the public key as a hex string.
     * @return 64-character lowercase hex string.
     */
    fun publicKeyHex(): String {
        return publicKey.joinToString("") { "%02x".format(it) }
    }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is BaitcoinKeyPair) return false
        return privateKey.contentEquals(other.privateKey) &&
               publicKey.contentEquals(other.publicKey)
    }

    override fun hashCode(): Int {
        var result = privateKey.contentHashCode()
        result = 31 * result + publicKey.contentHashCode()
        return result
    }
}

// ============================================================================
// TxInput / TxOutput
// ============================================================================

/**
 * A transaction input reference.
 *
 * @property txId The transaction ID of the previous transaction being spent.
 * @property outputIndex The output index within the previous transaction.
 * @property signature The unlocking script or signature proving ownership (optional).
 * @property publicKey The public key associated with the input (optional).
 */
data class TxInput(
    val txId: String,
    val outputIndex: Int,
    var signature: ByteArray? = null,
    var publicKey: ByteArray? = null
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is TxInput) return false
        return txId == other.txId && outputIndex == other.outputIndex
    }

    override fun hashCode(): Int {
        var result = txId.hashCode()
        result = 31 * result + outputIndex
        return result
    }
}

/**
 * A transaction output destination and amount.
 *
 * @property address The recipient's b'AI'tcoin address.
 * @property amount The amount in satoshi (1 BAIT = 100,000,000 satoshi).
 */
data class TxOutput(
    val address: String,
    val amount: Long
)

// ============================================================================
// BaitcoinTransaction
// ============================================================================

/**
 * Represents a b'AI'tcoin transaction with signing and serialization support.
 *
 * b'AI'tcoin transactions support standard transfers and agent-specific
 * operations. Each transaction has a unique ID derived from its content hash.
 *
 * @property inputs Transaction inputs (previous outputs being spent).
 * @property outputs Transaction outputs (destination addresses and amounts).
 * @property nonce Monotonically increasing nonce to prevent replay attacks.
 * @property signature The Schnorr signature over the serialized transaction.
 * @property agentId Optional agent ID for agent-specific transactions.
 * @property txId The transaction ID (SHA-256 hash of the serialized unsigned tx).
 */
class BaitcoinTransaction(
    val inputs: MutableList<TxInput>,
    val outputs: List<TxOutput>,
    var nonce: Long,
    var signature: ByteArray? = null,
    var agentId: String? = null,
    private val crypto: CryptoProvider = BouncyCastleCryptoProvider()
) {
    /**
     * The transaction ID, computed from the serialized unsigned transaction.
     */
    val txId: String

    init {
        txId = computeTxId(inputs, outputs, nonce, agentId)
    }

    companion object {
        /**
         * Create a standard transfer transaction.
         * @param inputs Array of TxInput to spend.
         * @param outputs Array of TxOutput for destinations.
         * @param nonce Monotonically increasing nonce.
         * @return A new BaitcoinTransaction.
         */
        fun createTransfer(
            inputs: List<TxInput>,
            outputs: List<TxOutput>,
            nonce: Long
        ): BaitcoinTransaction {
            return BaitcoinTransaction(
                inputs = inputs.toMutableList(),
                outputs = outputs,
                nonce = nonce
            )
        }

        /**
         * Compute the transaction ID from its components.
         */
        private fun computeTxId(
            inputs: List<TxInput>,
            outputs: List<TxOutput>,
            nonce: Long,
            agentId: String?
        ): String {
            val data = mutableListOf<Byte>()
            for (input in inputs) {
                data.addAll(input.txId.toByteArray().toList())
                data.add((input.outputIndex and 0xFF).toByte())
            }
            for (output in outputs) {
                data.addAll(output.address.toByteArray().toList())
                val amountBytes = ByteArray(8)
                var val_ = output.amount
                for (i in 7 downTo 0) {
                    amountBytes[i] = (val_ and 0xFF).toByte()
                    val_ = val_ ushr 8
                }
                data.addAll(amountBytes.toList())
            }
            val nonceBytes = ByteArray(8)
            var n = nonce
            for (i in 7 downTo 0) {
                nonceBytes[i] = (n and 0xFF).toByte()
                n = n ushr 8
            }
            data.addAll(nonceBytes.toList())
            agentId?.let { data.addAll(it.toByteArray().toList()) }
            val hash = BaitcoinHash.sha256(data.toByteArray())
            return hash.joinToString("") { "%02x".format(it) }
        }
    }

    /**
     * Sign the transaction with a private key.
     * @param privateKey The 32-byte private key.
     * @return The 64-byte Schnorr signature.
     */
    fun sign(privateKey: ByteArray): ByteArray {
        val serialized = serializeUnsigned()
        val messageHash = BaitcoinHash.sha256(serialized)
        val sig = crypto.schnorrSign(messageHash, privateKey)
        this.signature = sig
        return sig
    }

    /**
     * Serialize the unsigned transaction for signing.
     * @return The serialized transaction data as a ByteArray.
     */
    fun serializeUnsigned(): ByteArray {
        val stream = mutableListOf<Byte>()

        // Inputs count
        val inputCount = inputs.size
        stream.addAll(intToLittleEndianBytes(inputCount, 4))

        // Inputs
        for (input in inputs) {
            val txIdBytes = input.txId.toByteArray()
            stream.addAll(intToLittleEndianBytes(txIdBytes.size, 4))
            stream.addAll(txIdBytes.toList())
            stream.addAll(intToLittleEndianBytes(input.outputIndex, 4))
        }

        // Outputs count
        stream.addAll(intToLittleEndianBytes(outputs.size, 4))

        // Outputs
        for (output in outputs) {
            val addrBytes = output.address.toByteArray()
            stream.addAll(intToLittleEndianBytes(addrBytes.size, 4))
            stream.addAll(addrBytes.toList())
            stream.addAll(longToLittleEndianBytes(output.amount))
        }

        // Nonce
        stream.addAll(longToLittleEndianBytes(nonce))

        // Agent ID (optional)
        agentId?.let { id ->
            val agentBytes = id.toByteArray()
            stream.addAll(intToLittleEndianBytes(agentBytes.size, 4))
            stream.addAll(agentBytes.toList())
        }

        return stream.toByteArray()
    }

    /**
     * Convert the transaction to a dictionary representation for JSON serialization.
     * @return A map representing the transaction.
     */
    fun toDict(): Map<String, Any> {
        val dict = mutableMapOf<String, Any>(
            "txId" to txId,
            "inputs" to inputs.map { input ->
                val m = mutableMapOf<String, Any>(
                    "txId" to input.txId,
                    "outputIndex" to input.outputIndex
                )
                input.signature?.let { m["signature"] = it.joinToString("") { "%02x".format(it) } }
                input.publicKey?.let { m["publicKey"] = it.joinToString("") { "%02x".format(it) } }
                m
            },
            "outputs" to outputs.map { output ->
                mapOf("address" to output.address, "amount" to output.amount)
            },
            "nonce" to nonce
        )
        signature?.let {
            dict["signature"] = it.joinToString("") { "%02x".format(it) }
        }
        agentId?.let { dict["agentId"] = it }
        return dict
    }

    /** Convert an integer to little-endian byte array of specified size. */
    private fun intToLittleEndianBytes(value: Int, size: Int): List<Byte> {
        val bytes = mutableListOf<Byte>()
        var v = value
        repeat(size) {
            bytes.add((v and 0xFF).toByte())
            v = v ushr 8
        }
        return bytes
    }

    /** Convert a long to little-endian 8-byte array. */
    private fun longToLittleEndianBytes(value: Long): List<Byte> {
        val bytes = mutableListOf<Byte>()
        var v = value
        repeat(8) {
            bytes.add((v and 0xFF).toByte())
            v = v ushr 8
        }
        return bytes
    }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is BaitcoinTransaction) return false
        return txId == other.txId
    }

    override fun hashCode(): Int = txId.hashCode()

    override fun toString(): String = "BaitcoinTransaction(txId=$txId)"
}

// ============================================================================
// BaitcoinWallet
// ============================================================================

/**
 * The main b'AI'tcoin wallet class providing key management, signing, and address derivation.
 *
 * Usage:
 * ```kotlin
 * // Generate a new wallet
 * val wallet = BaitcoinWallet.generate()
 * println(wallet.getAddress()) // e.g., b'1A2b3C...
 *
 * // Import from private key
 * val wallet2 = BaitcoinWallet.import("0x...")
 *
 * // Sign a message
 * val signature = wallet.sign(messageData)
 * ```
 *
 * @property keyPair The key pair for this wallet.
 * @property network The network this wallet operates on.
 * @property address The derived b'AI'tcoin address.
 */
class BaitcoinWallet private constructor(
    val keyPair: BaitcoinKeyPair,
    val network: Network,
    val address: BaitcoinAddress,
    private val crypto: CryptoProvider
) {
    companion object {
        /**
         * Generate a new random wallet on the specified network.
         * @param network The target network (defaults to MAINNET).
         * @param crypto The crypto provider.
         * @return A new BaitcoinWallet with a freshly generated key pair.
         */
        fun generate(
            network: Network = Network.MAINNET,
            crypto: CryptoProvider = BouncyCastleCryptoProvider()
        ): BaitcoinWallet {
            val keyPair = BaitcoinKeyPair.generate(crypto)
            val address = BaitcoinAddress.from(keyPair.publicKey, network)
            return BaitcoinWallet(keyPair, network, address, crypto)
        }

        /**
         * Import a wallet from a hex-encoded private key.
         * @param privateKeyHex The 64-character hex private key string.
         * @param network The target network (defaults to MAINNET).
         * @param crypto The crypto provider.
         * @return A BaitcoinWallet, or null if the private key is invalid.
         */
        fun import(
            privateKeyHex: String,
            network: Network = Network.MAINNET,
            crypto: CryptoProvider = BouncyCastleCryptoProvider()
        ): BaitcoinWallet? {
            val keyPair = BaitcoinKeyPair.fromPrivateKeyHex(privateKeyHex, crypto) ?: return null
            val address = BaitcoinAddress.from(keyPair.publicKey, network)
            return BaitcoinWallet(keyPair, network, address, crypto)
        }
    }

    /**
     * Sign a message using the wallet's private key (Schnorr/BIP-340).
     * @param message The message data to sign.
     * @return The 64-byte Schnorr signature.
     */
    fun sign(message: ByteArray): ByteArray {
        return keyPair.sign(message)
    }

    /**
     * Get the wallet's b'AI'tcoin address string.
     * @return The full address string (e.g., "b'1A2b3C...").
     */
    fun getAddress(): String {
        return address.address
    }

    /**
     * Export the key bundle encrypted with a passphrase.
     * @param passphrase The passphrase to encrypt the key bundle.
     * @return JSON-encoded, encrypted key bundle as ByteArray.
     * @note In production, use Android Keystore for hardware-backed key storage.
     *       This placeholder uses XOR encryption with SHA-256 derived key.
     */
    fun exportKeyBundle(passphrase: String): ByteArray {
        val json = JSONObject().apply {
            put("privateKey", keyPair.privateKeyHex())
            put("publicKey", keyPair.publicKeyHex())
            put("network", network.name)
            put("address", address.address)
            put("exportedAt", java.time.Instant.now().toString())
        }
        val jsonBytes = json.toString().toByteArray(Charsets.UTF_8)

        val salt = ByteArray(16).also { SecureRandom().nextBytes(it) }
        val nonce = ByteArray(12).also { SecureRandom().nextBytes(it) }
        val spec = PBEKeySpec(passphrase.toCharArray(), salt, 210_000, 256)
        val key = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
            .generateSecret(spec).encoded
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, javax.crypto.spec.SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
        val sealed = cipher.doFinal(jsonBytes)
        return JSONObject().apply {
            put("version", 2)
            put("algorithm", "aes-256-gcm")
            put("iterations", 210_000)
            put("salt", Base64.getEncoder().encodeToString(salt))
            put("iv", Base64.getEncoder().encodeToString(nonce))
            put("ciphertext", Base64.getEncoder().encodeToString(sealed.copyOf(sealed.size - 16)))
            put("auth_tag", Base64.getEncoder().encodeToString(sealed.copyOfRange(sealed.size - 16, sealed.size)))
        }.toString().toByteArray(Charsets.UTF_8)
    }

    /**
     * Verify a signature against a message using the wallet's public key.
     * @param signature The 64-byte Schnorr signature.
     * @param message The original message data.
     * @return True if the signature is valid.
     */
    fun verify(signature: ByteArray, message: ByteArray): Boolean {
        val messageHash = BaitcoinHash.sha256(message)
        return crypto.schnorrVerify(signature, messageHash, keyPair.publicKey)
    }
}

// ============================================================================
// BaitcoinKit
// ============================================================================

/**
 * Main entry point for the b'AI'tcoin Android SDK.
 *
 * Provides factory methods and configuration for the SDK.
 * All cryptographic operations are performed locally on the device;
 * private keys never leave the device.
 *
 * Usage:
 * ```kotlin
 * // Configure the SDK
 * BaitcoinKit.configure(network = Network.MAINNET)
 *
 * // Create a wallet
 * val wallet = BaitcoinKit.createWallet()
 * println(wallet.getAddress())
 *
 * // Validate an address
 * val isValid = BaitcoinKit.validateAddress("b'1A2b3C...")
 * ```
 */
object BaitcoinKit {

    /** The currently configured network. Defaults to MAINNET. */
    var network: Network = Network.MAINNET

    /** The crypto provider used across the SDK. */
    var crypto: CryptoProvider = BouncyCastleCryptoProvider()

    /** The number of decimal places for BAIT amounts (8 decimal places). */
    const val DECIMAL_PLACES: Int = 8

    /** One BAIT in satoshi units. */
    const val SATOSHI_PER_BAIT: Long = 100_000_000L

    /** SDK version string. */
    const val VERSION = "1.0.0"

    /**
     * Configure the SDK with a specific network and optional crypto provider.
     * @param network The target network.
     * @param crypto Optional custom crypto provider.
     */
    fun configure(network: Network, crypto: CryptoProvider? = null) {
        this.network = network
        if (crypto != null) {
            this.crypto = crypto
        }
    }

    /**
     * Create a new wallet on the configured network.
     * @return A new BaitcoinWallet.
     */
    fun createWallet(): BaitcoinWallet {
        return BaitcoinWallet.generate(network, crypto)
    }

    /**
     * Import a wallet from a hex private key on the configured network.
     * @param privateKeyHex The 64-character hex private key.
     * @return A BaitcoinWallet, or null if the key is invalid.
     */
    fun importWallet(privateKeyHex: String): BaitcoinWallet? {
        return BaitcoinWallet.import(privateKeyHex, network, crypto)
    }

    /**
     * Validate a b'AI'tcoin address string.
     * @param address The address string to validate.
     * @return True if the address is syntactically valid.
     */
    fun validateAddress(address: String): Boolean {
        return BaitcoinAddress.validate(address)
    }

    /**
     * Parse a b'AI'tcoin address string.
     * @param address The address string to parse.
     * @return A BaitcoinAddress, or null if invalid.
     */
    fun parseAddress(address: String): BaitcoinAddress? {
        return BaitcoinAddress.parse(address)
    }

    /**
     * Convert BAIT to satoshi.
     * @param bait The amount in BAIT.
     * @return The amount in satoshi.
     */
    fun toSatoshi(bait: Double): Long {
        return (bait * SATOSHI_PER_BAIT).toLong()
    }

    /**
     * Convert satoshi to BAIT.
     * @param satoshi The amount in satoshi.
     * @return The amount in BAIT.
     */
    fun toBait(satoshi: Long): Double {
        return satoshi.toDouble() / SATOSHI_PER_BAIT.toDouble()
    }
}
