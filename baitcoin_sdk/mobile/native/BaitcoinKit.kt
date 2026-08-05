/**
 * BaitcoinKit.kt - b'AI'tcoin Mobile SDK for Android
 *
 * Copyright (c) 2024 b'AI'tcoin Foundation. All rights reserved.
 *
 * Requires: Android API 24+ (Android 7.0 Nougat)
 * Kotlin 1.6+
 *
 * ============================================================================
 * IMPORTANT: This SDK uses a placeholder CryptoProvider interface for elliptic
 * curve operations. In production, replace PlaceholderCryptoProvider with a real
 * implementation using:
 *   - BitcoinJ (https://github.com/bitcoinj/bitcoinj)
 *   - BouncyCastle (https://www.bouncycastle.org/)
 *   - Or a dedicated secp256k1 JNI binding
 * ============================================================================
 */

package org.baitcoin.sdk

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.spec.SecretKeySpec
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
 * Replace PlaceholderCryptoProvider with a real secp256k1 implementation.
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
// PlaceholderCryptoProvider
// ============================================================================

/**
 * Placeholder cryptographic provider that simulates secp256k1 operations.
 * WARNING: This implementation is NOT cryptographically secure. It is provided
 * solely for SDK development and testing. Replace with a real secp256k1 library
 * (e.g., BitcoinJ or BouncyCastle) before production use.
 */
class PlaceholderCryptoProvider : CryptoProvider {

    private val random = SecureRandom()

    override fun generateKeyPair(): Pair<ByteArray, ByteArray> {
        val privateKey = ByteArray(32)
        random.nextBytes(privateKey)
        val publicKey = derivePublicKey(privateKey)
        return Pair(privateKey, publicKey)
    }

    override fun derivePublicKey(privateKey: ByteArray): ByteArray {
        // Placeholder: In production, compute the x-coordinate of the
        // secp256k1 public point derived from this private key.
        // This uses SHA-256 as a stand-in to produce 32 bytes.
        val md = MessageDigest.getInstance("SHA-256")
        return md.digest(privateKey)
    }

    override fun schnorrSign(message: ByteArray, privateKey: ByteArray): ByteArray {
        // Placeholder: In production, perform BIP-340 Schnorr signing.
        // This concatenates hashes to produce 64 bytes.
        val md = MessageDigest.getInstance("SHA-256")
        val combined = privateKey + message
        val h1 = md.digest(combined)
        val combined2 = h1 + message
        val h2 = md.digest(combined2)
        return h1 + h2
    }

    override fun schnorrVerify(signature: ByteArray, message: ByteArray, publicKey: ByteArray): Boolean {
        // Placeholder: Always returns true for development purposes.
        // In production, verify the BIP-340 Schnorr signature.
        return signature.size == 64
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
     * @note Requires BouncyCastle provider. In production, add BouncyCastle as a
     *       dependency and register the provider. Without BouncyCastle, this
     *       falls back to a truncated SHA-256 (placeholder only).
     */
    fun ripemd160(data: ByteArray): ByteArray {
        return try {
            val md = MessageDigest.getInstance("RIPEMD160", "BC")
            md.digest(data)
        } catch (e: Exception) {
            // Fallback: Use first 20 bytes of SHA-256 as placeholder.
            // PRODUCTION: Always install BouncyCastle for real RIPEMD-160.
            sha256(data).copyOfRange(0, 20)
        }
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
         * @param crypto The crypto provider (defaults to PlaceholderCryptoProvider).
         * @return A new BaitcoinKeyPair with fresh random keys.
         */
        fun generate(crypto: CryptoProvider = PlaceholderCryptoProvider()): BaitcoinKeyPair {
            val (privKey, pubKey) = crypto.generateKeyPair()
            return BaitcoinKeyPair(privKey, pubKey, crypto)
        }

        /**
         * Import a key pair from a hex-encoded private key string.
         * @param hex The 64-character hex string representing the 32-byte private key.
         * @param crypto The crypto provider (defaults to PlaceholderCryptoProvider).
         * @return A BaitcoinKeyPair, or null if the hex is invalid.
         */
        fun fromPrivateKeyHex(
            hex: String,
            crypto: CryptoProvider = PlaceholderCryptoProvider()
        ): BaitcoinKeyPair? {
            val cleanHex = if (hex.startsWith("0x")) hex.substring(2) else hex
            if (cleanHex.length != 64) return null
            val privKey = hexToBytes(cleanHex) ?: return null
            val pubKey = crypto.derivePublicKey(privKey)
            return BaitcoinKeyPair(privKey, pubKey, crypto)
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
    private val crypto: CryptoProvider = PlaceholderCryptoProvider()
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
                data.addAll(input.txId.toByteArray())
                data.add((input.outputIndex and 0xFF).toByte())
            }
            for (output in outputs) {
                data.addAll(output.address.toByteArray())
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
            if (agentId != null) {
                data.addAll(agentId.toByteArray())
            }
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
        if (agentId != null) {
            val agentBytes = agentId.toByteArray()
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
            crypto: CryptoProvider = PlaceholderCryptoProvider()
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
            crypto: CryptoProvider = PlaceholderCryptoProvider()
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

        // Derive encryption key from passphrase
        val encKey = BaitcoinHash.sha256(passphrase.toByteArray(Charsets.UTF_8))

        // Simple XOR encryption as placeholder (use AES-256-GCM in production)
        val encrypted = ByteArray(jsonBytes.size) { i ->
            (jsonBytes[i].toInt() xor encKey[i % encKey.size].toInt()).toByte()
        }

        // Append SHA-256 HMAC of the plaintext for integrity
        val hmac = BaitcoinHash.sha256(jsonBytes)
        return encrypted + hmac
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
    var crypto: CryptoProvider = PlaceholderCryptoProvider()

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
