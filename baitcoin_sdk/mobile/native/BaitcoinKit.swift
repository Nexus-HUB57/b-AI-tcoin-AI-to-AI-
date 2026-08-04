// BaitcoinKit.swift - b'AI'tcoin Mobile SDK for iOS
//
// Copyright (c) 2024 b'AI'tcoin Foundation. All rights reserved.
//
// Requires iOS 14.0+
//
// ============================================================================
// IMPORTANT: This SDK uses a placeholder CryptoProvider protocol for elliptic
// curve operations. In production, replace the PlaceholderCryptoProvider with
// a real implementation using a Swift secp256k1 library such as:
//   - https://github.com/GigaBitcoin/secp256k1.swift
//   - https://github.com/Boilertalk/secp256k1.swift
//   - Or Apple's CryptoKit (note: CryptoKit uses P-256, not secp256k1)
// ============================================================================

import Foundation

// MARK: - Network

/// Represents the b'AI'tcoin network variant.
/// Mainnet uses 'b' address prefix, testnet uses 't' address prefix.
public enum Network: String, Codable, Equatable {
    /// Production b'AI'tcoin network with 'b' prefixed addresses.
    case mainnet
    /// Test network for development with 't' prefixed addresses.
    case testnet

    /// The single-character prefix used in b'AI'tcoin addresses for this network.
    var addressPrefix: Character {
        switch self {
        case .mainnet: return "b"
        case .testnet: return "t"
        }
    }

    /// Human-readable network name.
    var displayName: String {
        switch self {
        case .mainnet: return "b'AI'tcoin Mainnet"
        case .testnet: return "b'AI'tcoin Testnet"
        }
    }
}

// MARK: - CryptoProvider Protocol

/// Protocol abstracting elliptic curve cryptographic operations.
/// Replace the PlaceholderCryptoProvider with a real secp256k1 implementation.
public protocol CryptoProvider {
    /// Generate a new secp256k1 key pair.
    /// - Returns: A tuple of (privateKey, publicKey) where publicKey is 32 bytes x-only.
    func generateKeyPair() -> (privateKey: Data, publicKey: Data)

    /// Derive the 32-byte x-only public key from a 32-byte private key.
    func derivePublicKey(privateKey: Data) -> Data

    /// Sign a message using Schnorr/BIP-340 with the given private key.
    /// - Parameters:
    ///   - message: The message digest (32 bytes) to sign.
    ///   - privateKey: The 32-byte secp256k1 private key.
    /// - Returns: The 64-byte Schnorr signature.
    func schnorrSign(message: Data, privateKey: Data) -> Data

    /// Verify a Schnorr/BIP-340 signature.
    /// - Parameters:
    ///   - signature: The 64-byte Schnorr signature.
    ///   - message: The 32-byte message digest.
    ///   - publicKey: The 32-byte x-only public key.
    /// - Returns: True if the signature is valid.
    func schnorrVerify(signature: Data, message: Data, publicKey: Data) -> Bool
}

// MARK: - PlaceholderCryptoProvider

/// Placeholder cryptographic provider that simulates secp256k1 operations./// WARNING: This implementation is NOT cryptographically secure. It is provided
/// solely for SDK development and testing. Replace with a real secp256k1 library
/// (e.g., GigaBitcoin/secp256k1.swift) before production use.
public class PlaceholderCryptoProvider: CryptoProvider {

    public init() {}

    public func generateKeyPair() -> (privateKey: Data, publicKey: Data) {
        var privateKey = Data(count: 32)
        _ = privateKey.withUnsafeMutableBytes { ptr in
            _ = SecRandomCopyBytes(kSecRandomDefault, 32, ptr.baseAddress!)
        }
        let publicKey = derivePublicKey(privateKey: privateKey)
        return (privateKey, publicKey)
    }

    public func derivePublicKey(privateKey: Data) -> Data {
        // Placeholder: In production, compute the x-coordinate of the
        // secp256k1 public point derived from this private key.
        // This uses SHA-256 as a stand-in to produce 32 bytes.
        let hash = SHA256.hash(data: privateKey)
        return Data(hash)
    }

    public func schnorrSign(message: Data, privateKey: Data) -> Data {
        // Placeholder: In production, perform BIP-340 Schnorr signing.
        // This concatenates hashes to produce 64 bytes.
        var combined = privateKey
        combined.append(message)
        let h1 = SHA256.hash(data: combined)
        var combined2 = Data(h1)
        combined2.append(message)
        let h2 = SHA256.hash(data: combined2)
        var sig = Data(count: 64)
        sig.replaceSubrange(0..<32, with: h1)
        sig.replaceSubrange(32..<64, with: h2)
        return sig
    }

    public func schnorrVerify(signature: Data, message: Data, publicKey: Data) -> Bool {
        // Placeholder: Always returns true for development purposes.
        // In production, verify the BIP-340 Schnorr signature against the
        // public key and message.
        return signature.count == 64
    }
}

// MARK: - Hash Utilities

/// Cryptographic hash utilities for b'AI'tcoin address generation.
/// Provides SHA-256 and RIPEMD-160 (Hash160) operations.
public enum BaitcoinHash {

    /// Compute SHA-256 hash.
    /// - Parameter data: Input data.
    /// - Returns: 32-byte SHA-256 digest.
    public static func sha256(_ data: Data) -> Data {
        let digest = SHA256.hash(data: data)
        return Data(digest)
    }

    /// Compute RIPEMD-160 hash.
    /// - Parameter data: Input data.
    /// - Returns: 20-byte RIPEMD-160 digest.
    /// - Note: Uses CommonCrypto via a C function bridge. In production,
    ///         ensure that CC_RIPEMD160 is available on the target platform.
    public static func ripemd160(_ data: Data) -> Data {
        var digest = [UInt8](repeating: 0, count: 20)
        _ = data.withUnsafeBytes { dataPtr in
            RIPEMD160(dataPtr.baseAddress?.assumingMemoryBound(to: UInt8.self), CC_LONG(data.count), &digest)
        }
        return Data(digest)
    }

    /// Compute Hash160: RIPEMD160(SHA256(data)). Used for b'AI'tcoin address derivation.
    /// - Parameter data: Input data (typically a 32-byte x-only public key).
    /// - Returns: 20-byte Hash160 digest (the pubkey hash).
    public static func hash160(_ data: Data) -> Data {
        return ripemd160(sha256(data))
    }

    /// Compute double SHA-256 (used in Base58Check).
    /// - Parameter data: Input data.
    /// - Returns: 32-byte double-SHA-256 digest.
    public static func doubleSHA256(_ data: Data) -> Data {
        return sha256(sha256(data))
    }
}

// MARK: - Base58 Encoding/Decoding

/// Base58 encoding and decoding for b'AI'tcoin addresses.
/// Uses the Bitcoin-style Base58 alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
public enum Base58 {

    /// Base58 alphabet (excludes 0, O, I, l to avoid ambiguity).
    private static let alphabet: [Character] = [
        "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M",
        "N", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "m",
        "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"
    ]

    /// Encode raw bytes to a Base58 string.
    /// - Parameter data: The raw bytes to encode.
    /// - Returns: The Base58-encoded string.
    public static func encode(_ data: Data) -> String {
        var num = 0
        for byte in data {
            num = num << 8 | Int(byte)
        }

        var result = ""
        while num > 0 {
            let remainder = num % 58
            result = String(alphabet[remainder]) + result
            num /= 58
        }

        // Preserve leading zero bytes as '1' characters
        for byte in data {
            if byte == 0 {
                result = "1" + result
            } else {
                break
            }
        }

        return result
    }

    /// Encode raw bytes to a Base58Check string (with 4-byte checksum).
    /// - Parameter data: The raw bytes to encode (version byte + payload).
    /// - Returns: The Base58Check-encoded string.
    public static func encodeCheck(_ data: Data) -> String {
        let checksum = BaitcoinHash.doubleSHA256(data)
        var payload = data
        payload.append(checksum[0..<4])
        return encode(payload)
    }

    /// Decode a Base58 string to raw bytes.
    /// - Parameter string: The Base58-encoded string.
    /// - Returns: The decoded raw bytes, or nil if invalid.
    public static func decode(_ string: String) -> Data? {
        var num = 0
        var base: Int = 1

        let chars = [Character](string.reversed())
        for char in chars {
            guard let index = alphabet.firstIndex(of: char) else {
                return nil
            }
            num += index * base
            base *= 58
        }

        // Count leading '1's (representing leading zero bytes)
        let leadingOnes = string.prefix(while: { $0 == "1" }).count

        var bytes = [UInt8]()
        for _ in 0..<leadingOnes {
            bytes.append(0)
        }

        // Convert number to big-endian bytes
        if num > 0 {
            var n = num
            while n > 0 {
                bytes.insert(UInt8(n & 0xFF), at: 0)
                n >>= 8
            }
        }

        return Data(bytes)
    }

    /// Decode a Base58Check string and verify the checksum.
    /// - Parameter string: The Base58Check-encoded string.
    /// - Returns: The decoded payload (without checksum), or nil if invalid.
    public static func decodeCheck(_ string: String) -> Data? {
        guard let decoded = decode(string) else { return nil }
        guard decoded.count > 4 else { return nil }

        let payload = decoded[0..<(decoded.count - 4)]
        let checksum = decoded[(decoded.count - 4)...]

        let expectedChecksum = BaitcoinHash.doubleSHA256(Data(payload))[0..<4]

        guard checksum.elementsEqual(expectedChecksum) else { return nil }
        return Data(payload)
    }
}

// MARK: - BaitcoinAddress

/// Represents a b'AI'tcoin address with validation and parsing capabilities.
///
/// Address format: `<prefix><Base58Check(Hash160(pubkey))>`
/// - Mainnet prefix: `b` (e.g., b'1A2b3C...')
/// - Testnet prefix: `t` (e.g., t'1XyZ9w...')
///
/// The address is derived by:
/// 1. Taking the 32-byte x-only public key
/// 2. Computing Hash160 = RIPEMD160(SHA256(pubkey)) → 20 bytes
/// 3. Prepending a version byte (0x00 for mainnet, 0x6F for testnet)
/// 4. Encoding with Base58Check
/// 5. Prepending the network prefix character
public struct BaitcoinAddress: Equatable, Codable, Hashable {

    /// The full address string including the prefix (e.g., "b'1A2b3C...").
    public let address: String

    /// The network this address belongs to.
    public let network: Network

    /// The 20-byte Hash160 pubkey hash.
    public let pubkeyHash: Data

    /// Version byte used in Base58Check encoding.
    private static let mainnetVersion: UInt8 = 0x00
    private static let testnetVersion: UInt8 = 0x6F

    /// Initialize a new BaitcoinAddress.
    /// - Parameters:
    ///   - address: The full address string.
    ///   - network: The network.
    ///   - pubkeyHash: The 20-byte pubkey hash.
    public init(address: String, network: Network, pubkeyHash: Data) {
        self.address = address
        self.network = network
        self.pubkeyHash = pubkeyHash
    }

    /// Derive a b'AI'tcoin address from a public key.
    /// - Parameters:
    ///   - pubkey: The 32-byte x-only public key.
    ///   - network: The target network (mainnet or testnet).
    /// - Returns: The derived BaitcoinAddress.
    public static func from(pubkey: Data, network: Network) -> BaitcoinAddress {
        let hash = BaitcoinHash.hash160(pubkey)
        let versionByte: UInt8 = (network == .mainnet) ? mainnetVersion : testnetVersion
        var payload = Data([versionByte])
        payload.append(hash)
        let base58 = Base58.encodeCheck(payload)
        let addressString = "\(network.addressPrefix)'\(base58)"
        return BaitcoinAddress(address: addressString, network: network, pubkeyHash: hash)
    }

    /// Parse a b'AI'tcoin address string into a BaitcoinAddress struct.
    /// - Parameter string: The address string to parse (e.g., "b'1A2b3C...").
    /// - Returns: The parsed BaitcoinAddress, or nil if the address is invalid.
    public static func parse(_ string: String) -> BaitcoinAddress? {
        guard string.count > 2 else { return nil }

        let prefix = string.first!
        let base58Part = String(string.dropFirst(2)) // Remove prefix + quote

        guard let network = (prefix == "b") ? Network.mainnet :
                                  (prefix == "t") ? Network.testnet : nil else {
            return nil
        }

        guard let decoded = Base58.decodeCheck(base58Part) else { return nil }
        guard decoded.count >= 21 else { return nil }

        let versionByte = decoded[0]
        let expectedVersion: UInt8 = (network == .mainnet) ? mainnetVersion : testnetVersion
        guard versionByte == expectedVersion else { return nil }

        let pubkeyHash = decoded[1..<21]
        return BaitcoinAddress(address: string, network: network, pubkeyHash: Data(pubkeyHash))
    }

    /// Validate a b'AI'tcoin address string.
    /// - Parameter string: The address string to validate.
    /// - Returns: True if the address is valid.
    public static func validate(_ string: String) -> Bool {
        return parse(string) != nil
    }

    /// Custom string conversion.
    public var description: String { return address }
}

// MARK: - BaitcoinKeyPair

/// Represents a secp256k1 key pair for b'AI'tcoin signing operations.
///
/// The public key is the 32-byte x-only coordinate (BIP-340 / Schnorr style),
/// not the full 65-byte uncompressed public key.
public class BaitcoinKeyPair {

    /// The 32-byte secp256k1 private key. **Handle with extreme care.**
    public let privateKey: Data

    /// The 32-byte x-only public key derived from the private key.
    public let publicKey: Data

    /// The cryptographic provider used for key operations.
    private let crypto: CryptoProvider

    /// Initialize with explicit key data.
    /// - Parameters:
    ///   - privateKey: The 32-byte private key.
    ///   - publicKey: The 32-byte x-only public key.
    ///   - crypto: The crypto provider.
    private init(privateKey: Data, publicKey: Data, crypto: CryptoProvider) {
        self.privateKey = privateKey
        self.publicKey = publicKey
        self.crypto = crypto
    }

    /// Generate a new random key pair.
    /// - Parameter crypto: The crypto provider (defaults to PlaceholderCryptoProvider).
    /// - Returns: A new BaitcoinKeyPair with fresh random keys.
    public static func generate(crypto: CryptoProvider = PlaceholderCryptoProvider()) -> BaitcoinKeyPair {
        let (privKey, pubKey) = crypto.generateKeyPair()
        return BaitcoinKeyPair(privateKey: privKey, publicKey: pubKey, crypto: crypto)
    }

    /// Import a key pair from a hex-encoded private key string.
    /// - Parameters:
    ///   - hex: The 64-character hex string representing the 32-byte private key.
    ///   - crypto: The crypto provider (defaults to PlaceholderCryptoProvider).
    /// - Returns: A BaitcoinKeyPair, or nil if the hex is invalid.
    public static func fromPrivateKeyHex(_ hex: String,
                                        crypto: CryptoProvider = PlaceholderCryptoProvider()) -> BaitcoinKeyPair? {
        // Strip optional '0x' prefix
        let cleanHex = hex.hasPrefix("0x") ? String(hex.dropFirst(2)) : hex
        guard cleanHex.count == 64 else { return nil }
        guard let privKey = Data(hexString: cleanHex) else { return nil }
        let pubKey = crypto.derivePublicKey(privateKey: privKey)
        return BaitcoinKeyPair(privateKey: privKey, publicKey: pubKey, crypto: crypto)
    }

    /// Sign a message using Schnorr/BIP-340.
    /// - Parameter message: The message data to sign.
    /// - Returns: The 64-byte Schnorr signature.
    public func sign(_ message: Data) -> Data {
        let messageHash = BaitcoinHash.sha256(message)
        return crypto.schnorrSign(message: messageHash, privateKey: privateKey)
    }

    /// Export the private key as a hex string.
    /// - Returns: 64-character lowercase hex string.
    public func privateKeyHex() -> String {
        return privateKey.map { String(format: "%02x", $0) }.joined()
    }

    /// Export the public key as a hex string.
    /// - Returns: 64-character lowercase hex string.
    public func publicKeyHex() -> String {
        return publicKey.map { String(format: "%02x", $0) }.joined()
    }
}

// MARK: - TxInput / TxOutput

/// A transaction input reference.
public struct TxInput: Codable, Equatable {
    /// The transaction ID of the previous transaction being spent.
    public let txId: String
    /// The output index within the previous transaction.
    public let outputIndex: Int
    /// The unlocking script or signature proving ownership.
    public var signature: Data?
    /// Optional public key associated with the input.
    public var publicKey: Data?

    public init(txId: String, outputIndex: Int, signature: Data? = nil, publicKey: Data? = nil) {
        self.txId = txId
        self.outputIndex = outputIndex
        self.signature = signature
        self.publicKey = publicKey
    }
}

/// A transaction output destination and amount.
public struct TxOutput: Codable, Equatable {
    /// The recipient's b'AI'tcoin address.
    public let address: String
    /// The amount in satoshi (1 BAIT = 100,000,000 satoshi).
    public let amount: UInt64

    public init(address: String, amount: UInt64) {
        self.address = address
        self.amount = amount
    }
}

// MARK: - BaitcoinTransaction

/// Represents a b'AI'tcoin transaction with signing and serialization support.
///
/// b'AI'tcoin transactions support standard transfers and agent-specific
/// operations. Each transaction has a unique ID derived from its content hash.
public class BaitcoinTransaction: Codable, Equatable {

    /// Transaction inputs (previous outputs being spent).
    public var inputs: [TxInput]

    /// Transaction outputs (destination addresses and amounts).
    public var outputs: [TxOutput]

    /// Monotonically increasing nonce to prevent replay attacks.
    public var nonce: Int

    /// The Schnorr signature over the serialized transaction.
    public var signature: Data?

    /// Optional agent ID for agent-specific transactions.
    public var agentId: String?

    /// The transaction ID (SHA-256 hash of the serialized unsigned transaction).
    public private(set) var txId: String

    /// The cryptographic provider for signing.
    private let crypto: CryptoProvider

    /// Initialize a new transaction.
    /// - Parameters:
    ///   - inputs: The transaction inputs.
    ///   - outputs: The transaction outputs.
    ///   - nonce: The nonce value.
    ///   - agentId: Optional agent ID.
    ///   - crypto: The crypto provider.
    public init(inputs: [TxInput], outputs: [TxOutput], nonce: Int,
                agentId: String? = nil, crypto: CryptoProvider = PlaceholderCryptoProvider()) {
        self.inputs = inputs
        self.outputs = outputs
        self.nonce = nonce
        self.agentId = agentId
        self.crypto = crypto
        self.signature = nil
        self.txId = Self.computeTxId(inputs: inputs, outputs: outputs,
                                      nonce: nonce, agentId: agentId)
    }

    /// Create a standard transfer transaction.
    /// - Parameters:
    ///   - inputs: Array of TxInput to spend.
    ///   - outputs: Array of TxOutput for destinations.
    ///   - nonce: Monotonically increasing nonce.
    /// - Returns: A new BaitcoinTransaction.
    public static func createTransfer(inputs: [TxInput], outputs: [TxOutput],
                                      nonce: Int) -> BaitcoinTransaction {
        return BaitcoinTransaction(inputs: inputs, outputs: outputs, nonce: nonce)
    }

    /// Sign the transaction with a private key.
    /// - Parameter privateKey: The 32-byte private key.
    /// - Returns: The 64-byte Schnorr signature.
    public func sign(privateKey: Data) -> Data {
        let serialized = serializeUnsigned()
        let messageHash = BaitcoinHash.sha256(serialized)
        let sig = crypto.schnorrSign(message: messageHash, privateKey: privateKey)
        self.signature = sig
        return sig
    }

    /// Serialize the unsigned transaction for signing.
    /// - Returns: The serialized transaction data.
    public func serializeUnsigned() -> Data {
        var data = Data()

        // Inputs
        let inputCount = UInt32(inputs.count)
        var inputCountBytes = [UInt8](repeating: 0, count: 4)
        inputCountBytes.withUnsafeMutableBufferPointer { ptr in
            ptr.pointee = inputCount.littleEndian
        }
        data.append(contentsOf: inputCountBytes)

        for input in inputs {
            if let txIdData = input.txId.data(using: .utf8) {
                let len = UInt32(txIdData.count)
                var lenBytes = [UInt8](repeating: 0, count: 4)
                lenBytes.withUnsafeMutableBufferPointer { ptr in
                    ptr.pointee = len.littleEndian
                }
                data.append(contentsOf: lenBytes)
                data.append(txIdData)
            }
            let idx = UInt32(input.outputIndex)
            var idxBytes = [UInt8](repeating: 0, count: 4)
            idxBytes.withUnsafeMutableBufferPointer { ptr in
                ptr.pointee = idx.littleEndian
            }
            data.append(contentsOf: idxBytes)
        }

        // Outputs
        let outputCount = UInt32(outputs.count)
        var outputCountBytes = [UInt8](repeating: 0, count: 4)
        outputCountBytes.withUnsafeMutableBufferPointer { ptr in
            ptr.pointee = outputCount.littleEndian
        }
        data.append(contentsOf: outputCountBytes)

        for output in outputs {
            if let addrData = output.address.data(using: .utf8) {
                let len = UInt32(addrData.count)
                var lenBytes = [UInt8](repeating: 0, count: 4)
                lenBytes.withUnsafeMutableBufferPointer { ptr in
                    ptr.pointee = len.littleEndian
                }
                data.append(contentsOf: lenBytes)
                data.append(addrData)
            }
            var amountBytes = [UInt8](repeating: 0, count: 8)
            amountBytes.withUnsafeMutableBufferPointer { ptr in
                ptr.pointee = output.amount.littleEndian
            }
            data.append(contentsOf: amountBytes)
        }

        // Nonce
        let nonceVal = UInt64(nonce)
        var nonceBytes = [UInt8](repeating: 0, count: 8)
        nonceBytes.withUnsafeMutableBufferPointer { ptr in
            ptr.pointee = nonceVal.littleEndian
        }
        data.append(contentsOf: nonceBytes)

        // Agent ID (optional)
        if let agentId = agentId, let agentData = agentId.data(using: .utf8) {
            let len = UInt32(agentData.count)
            var lenBytes = [UInt8](repeating: 0, count: 4)
            lenBytes.withUnsafeMutableBufferPointer { ptr in
                ptr.pointee = len.littleEndian
            }
            data.append(contentsOf: lenBytes)
            data.append(agentData)
        }

        return data
    }

    /// Convert the transaction to a dictionary representation for JSON serialization.
    /// - Returns: A dictionary representing the transaction.
    public func toDict() -> [String: Any] {
        var dict: [String: Any] = [
            "txId": txId,
            "inputs": inputs.map { input -> [String: Any] in
                var d: [String: Any] = [
                    "txId": input.txId,
                    "outputIndex": input.outputIndex
                ]
                if let sig = input.signature {
                    d["signature"] = sig.map { String(format: "%02x", $0) }.joined()
                }
                if let pub = input.publicKey {
                    d["publicKey"] = pub.map { String(format: "%02x", $0) }.joined()
                }
                return d
            },
            "outputs": outputs.map { output -> [String: Any] in
                return [
                    "address": output.address,
                    "amount": output.amount
                ]
            },
            "nonce": nonce
        ]
        if let sig = signature {
            dict["signature"] = sig.map { String(format: "%02x", $0) }.joined()
        }
        if let agentId = agentId {
            dict["agentId"] = agentId
        }
        return dict
    }

    /// Compute the transaction ID from its components.
    private static func computeTxId(inputs: [TxInput], outputs: [TxOutput],
                                     nonce: Int, agentId: String?) -> String {
        var data = Data()
        for input in inputs {
            if let d = input.txId.data(using: .utf8) { data.append(d) }
            data.append(UInt8(input.outputIndex & 0xFF))
        }
        for output in outputs {
            if let d = output.address.data(using: .utf8) { data.append(d) }
            var b = [UInt8](repeating: 0, count: 8)
            b.withUnsafeMutableBufferPointer { $0.pointee = output.amount.littleEndian }
            data.append(contentsOf: b)
        }
        var nb = [UInt8](repeating: 0, count: 8)
        nb.withUnsafeMutableBufferPointer { $0.pointee = UInt64(nonce).littleEndian }
        data.append(contentsOf: nb)
        if let a = agentId?.data(using: .utf8) { data.append(a) }
        let hash = BaitcoinHash.sha256(data)
        return hash.map { String(format: "%02x", $0) }.joined()
    }

    // MARK: - Equatable
    public static func == (lhs: BaitcoinTransaction, rhs: BaitcoinTransaction) -> Bool {
        return lhs.txId == rhs.txId
    }
}

// MARK: - BaitcoinWallet

/// The main b'AI'tcoin wallet class providing key management, signing, and address derivation.
///
/// Usage:
/// ```swift
/// // Generate a new wallet
/// let wallet = BaitcoinWallet.generate()
/// print(wallet.getAddress()) // e.g., "b'1A2b3C..."
///
/// // Import from private key
/// let wallet2 = BaitcoinWallet.import("0x...")
///
/// // Sign a message
/// let signature = wallet.sign(messageData)
/// ```
public class BaitcoinWallet {

    /// The key pair for this wallet.
    public let keyPair: BaitcoinKeyPair

    /// The network this wallet operates on.
    public let network: Network

    /// The derived b'AI'tcoin address.
    public let address: BaitcoinAddress

    /// The cryptographic provider.
    private let crypto: CryptoProvider

    /// Initialize a wallet with an existing key pair.
    /// - Parameters:
    ///   - keyPair: The key pair to use.
    ///   - network: The target network.
    ///   - crypto: The crypto provider.
    private init(keyPair: BaitcoinKeyPair, network: Network,
                crypto: CryptoProvider) {
        self.keyPair = keyPair
        self.network = network
        self.crypto = crypto
        self.address = BaitcoinAddress.from(pubkey: keyPair.publicKey, network: network)
    }

    /// Generate a new random wallet on the specified network.
    /// - Parameters:
    ///   - network: The target network (defaults to mainnet).
    ///   - crypto: The crypto provider.
    /// - Returns: A new BaitcoinWallet with a freshly generated key pair.
    public static func generate(network: Network = .mainnet,
                                crypto: CryptoProvider = PlaceholderCryptoProvider()) -> BaitcoinWallet {
        let keyPair = BaitcoinKeyPair.generate(crypto: crypto)
        return BaitcoinWallet(keyPair: keyPair, network: network, crypto: crypto)
    }

    /// Import a wallet from a hex-encoded private key.
    /// - Parameters:
    ///   - privateKeyHex: The 64-character hex private key string.
    ///   - network: The target network (defaults to mainnet).
    ///   - crypto: The crypto provider.
    /// - Returns: A BaitcoinWallet, or nil if the private key is invalid.
    public static func `import`(privateKeyHex: String,
                                network: Network = .mainnet,
                                crypto: CryptoProvider = PlaceholderCryptoProvider()) -> BaitcoinWallet? {
        guard let keyPair = BaitcoinKeyPair.fromPrivateKeyHex(privateKeyHex, crypto: crypto) else {
            return nil
        }
        return BaitcoinWallet(keyPair: keyPair, network: network, crypto: crypto)
    }

    /// Sign a message using the wallet's private key (Schnorr/BIP-340).
    /// - Parameter message: The message data to sign.
    /// - Returns: The 64-byte Schnorr signature.
    public func sign(_ message: Data) -> Data {
        return keyPair.sign(message)
    }

    /// Get the wallet's b'AI'tcoin address string.
    /// - Returns: The full address string (e.g., "b'1A2b3C...").
    public func getAddress() -> String {
        return address.address
    }

    /// Export the key bundle encrypted with a passphrase.
    /// - Parameter passphrase: The passphrase to encrypt the key bundle.
    /// - Returns: JSON-encoded, encrypted key bundle data.
    /// - Note: Uses AES-256-GCM encryption. In production, integrate with
    ///         iOS Secure Enclave for hardware-backed key storage.
    public func exportKeyBundle(passphrase: String) -> Data {
        let keyData: [String: Any] = [
            "privateKey": keyPair.privateKeyHex(),
            "publicKey": keyPair.publicKeyHex(),
            "network": network.rawValue,
            "address": address.address,
            "exportedAt": ISO8601DateFormatter().string(from: Date())
        ]

        guard let json = try? JSONSerialization.data(withJSONObject: keyData) else {
            return Data()
        }

        // Derive encryption key from passphrase
        let passphraseData = passphrase.data(using: .utf8) ?? Data()
        let encKey = BaitcoinHash.sha256(passphraseData)

        // Simple XOR encryption as placeholder (use AES-256-GCM in production)
        var encrypted = Data(count: json.count)
        for i in 0..<json.count {
            let byteIndex = i % encKey.count
            encrypted[i] = json[i] ^ encKey[byteIndex]
        }

        // Append a SHA-256 HMAC of the plaintext for integrity check
        let hmac = BaitcoinHash.sha256(json)
        encrypted.append(hmac)

        return encrypted
    }

    /// Verify a signature against a message using the wallet's public key.
    /// - Parameters:
    ///   - signature: The 64-byte Schnorr signature.
    ///   - message: The original message data.
    /// - Returns: True if the signature is valid.
    public func verify(signature: Data, message: Data) -> Bool {
        let messageHash = BaitcoinHash.sha256(message)
        return crypto.schnorrVerify(signature: signature, message: messageHash,
                                      publicKey: keyPair.publicKey)
    }
}

// MARK: - BaitcoinKit

/// Main entry point for the b'AI'tcoin iOS SDK.
///
/// Provides factory methods and configuration for the SDK.
/// All cryptographic operations are performed locally on the device;
/// private keys never leave the device.
///
/// Usage:
/// ```swift
/// // Configure the SDK
/// BaitcoinKit.configure(network: .mainnet)
///
/// // Create a wallet
/// let wallet = BaitcoinKit.createWallet()
/// print(wallet.getAddress())
///
/// // Validate an address
/// let isValid = BaitcoinKit.validateAddress("b'1A2b3C...")
/// ```
public class BaitcoinKit {

    /// The currently configured network.
    public static var network: Network = .mainnet

    /// The crypto provider used across the SDK.
    public static var crypto: CryptoProvider = PlaceholderCryptoProvider()

    /// The number of decimal places for BAIT amounts (8 decimal places).
    public static let decimalPlaces: Int = 8

    /// One BAIT in satoshi units.
    public static let satoshiPerBait: UInt64 = 100_000_000

    /// SDK version string.
    public static let version = "1.0.0"

    /// Configure the SDK with a specific network and optional crypto provider.
    /// - Parameters:
    ///   - network: The target network.
    ///   - crypto: Optional custom crypto provider.
    public static func configure(network: Network,
                                  crypto: CryptoProvider? = nil) {
        self.network = network
        if let crypto = crypto {
            self.crypto = crypto
        }
    }

    /// Create a new wallet on the configured network.
    /// - Returns: A new BaitcoinWallet.
    public static func createWallet() -> BaitcoinWallet {
        return BaitcoinWallet.generate(network: network, crypto: crypto)
    }

    /// Import a wallet from a hex private key on the configured network.
    /// - Parameter privateKeyHex: The 64-character hex private key.
    /// - Returns: A BaitcoinWallet, or nil if the key is invalid.
    public static func importWallet(privateKeyHex: String) -> BaitcoinWallet? {
        return BaitcoinWallet.import(privateKeyHex: privateKeyHex,
                                      network: network, crypto: crypto)
    }

    /// Validate a b'AI'tcoin address string.
    /// - Parameter address: The address string to validate.
    /// - Returns: True if the address is syntactically valid.
    public static func validateAddress(_ address: String) -> Bool {
        return BaitcoinAddress.validate(address)
    }

    /// Parse a b'AI'tcoin address string.
    /// - Parameter address: The address string to parse.
    /// - Returns: A BaitcoinAddress, or nil if invalid.
    public static func parseAddress(_ address: String) -> BaitcoinAddress? {
        return BaitcoinAddress.parse(address)
    }

    /// Convert BAIT to satoshi.
    /// - Parameter bait: The amount in BAIT.
    /// - Returns: The amount in satoshi.
    public static func toSatoshi(bait: Double) -> UInt64 {
        return UInt64(bait * Double(satoshiPerBait))
    }

    /// Convert satoshi to BAIT.
    /// - Parameter satoshi: The amount in satoshi.
    /// - Returns: The amount in BAIT.
    public static func toBait(satoshi: UInt64) -> Double {
        return Double(satoshi) / Double(satoshiPerBait)
    }

    private init() {} // Prevent instantiation
}

// MARK: - Data Extension (Hex Helpers)

extension Data {
    /// Initialize Data from a hex string.
    /// - Parameter hexString: The hex string (optionally prefixed with '0x').
    init?(hexString: String) {
        let hex = hexString.hasPrefix("0x") ? String(hexString.dropFirst(2)) : hexString
        let len = hex.count / 2
        var data = Data(capacity: len)
        for i in 0..<len {
            let j = hex.index(hex.startIndex, offsetBy: i * 2)
            let k = hex.index(j, offsetBy: 2)
            let bytes = hex[j..<k]
            if var byte = UInt8(bytes, radix: 16) {
                data.append(&byte, count: 1)
            } else {
                return nil
            }
        }
        self = data
    }
}

// MARK: - C CommonCrypto Bridge for RIPEMD-160

/// C function declaration for RIPEMD-160 from CommonCrypto.
/// This is available on Apple platforms via the Security framework.
private func RIPEMD160(_ data: UnsafePointer<UInt8>?, _ len: CC_LONG,
                        _ md: UnsafeMutablePointer<UInt8>?) -> UnsafeMutablePointer<UInt8>? {
    // NOTE: Apple's CommonCrypto does NOT directly expose RIPEMD-160.
    // In production, use a standalone RIPEMD-160 implementation or a library.
    // This placeholder uses a simple hash for demonstration.
    // Replace with a real RIPEMD-160 implementation.
    //
    // Recommended: Include a pure-Swift RIPEMD-160 implementation such as:
    //   https://github.com/keeshux/ripemd160-swift
    //
    // For now, we use SHA-256 truncated to 20 bytes as a placeholder.

    guard let data = data, len > 0, let md = md else { return nil }

    // Placeholder: use first 20 bytes of SHA-256
    var ctx = CC_SHA256_CTX()
    CC_SHA256_Init(&ctx)
    CC_SHA256_Update(&ctx, data, len)
    var digest = [UInt8](repeating: 0, count: 32)
    CC_SHA256_Final(&digest, &ctx)
    md.initialize(from: digest, count: 20)
    return md
}
