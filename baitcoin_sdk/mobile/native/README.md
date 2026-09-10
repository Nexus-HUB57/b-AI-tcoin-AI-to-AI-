# b'AI'tcoin Native Mobile SDKs

Native SDKs for integrating b'AI'tcoin wallet functionality into iOS and Android applications.

## Overview

| Platform | File | Minimum Version | Language |
|----------|------|-----------------|----------|
| iOS | `BaitcoinKit.swift` | iOS 14.0+ | Swift 5.5+ |
| Android | `BaitcoinKit.kt` | Android API 24+ (7.0) | Kotlin 1.6+ |

Both SDKs implement:
- **Schnorr/BIP-340** signatures on secp256k1
- **Hash160 + Base58Check** addresses with `b'` prefix (mainnet) / `t'` prefix (testnet)
- **8 decimal places** (1 BAIT = 100,000,000 satoshi)
- Local-only key generation and signing (no server-side crypto)

## Installation

### iOS (Swift)

1. Add this directory as a Swift Package or copy the package manifest and
   `BaitcoinKit.swift` into your Xcode project.
2. Resolve the pinned `swift-secp256k1` dependency (`P256K` 0.23.2).
3. In your target's **Build Phases**, ensure `Security.framework` and
   `CommonCrypto` are available. Do not replace `P256KCryptoProvider` with
   CryptoKit P-256: P-256 is not secp256k1 and is not BIP-340 compatible.

```bash
# Or add the local Package.swift through Xcode's Swift Package dependencies.
```

### Android (Kotlin)

1. Copy `BaitcoinKit.kt` into your project's source set (e.g., `app/src/main/java/org/baitcoin/sdk/`).
2. Add the pinned BouncyCastle dependency. It supplies the audited secp256k1
   curve arithmetic and RIPEMD-160 implementation used by the SDK:

```groovy
// app/build.gradle
implementation 'org.bouncycastle:bcprov-jdk18on:1.78'
```

For Kotlin DSL use:

```kotlin
// app/build.gradle.kts
implementation("org.bouncycastle:bcprov-jdk18on:1.78")
```

No JCA provider registration is required: `BouncyCastleCryptoProvider` calls
BouncyCastle's secp256k1 and RIPEMD-160 primitives directly. The provider
performs x-only public-key derivation, private-key range checks, and BIP-340
Schnorr signing and verification. Java's standard cryptography APIs are not a
secp256k1 implementation and are not used as one.

## Quick Start

### iOS (Swift)

```swift
import Foundation

// Configure for mainnet (default)
BaitcoinKit.configure(network: .mainnet)

// Generate a new wallet
let wallet = BaitcoinKit.createWallet()
print("Address: \(wallet.getAddress())")  // e.g., b'1A2b3C...

// Sign a message
let message = "Hello b'AI'tcoin".data(using: .utf8)!
let signature = wallet.sign(message)
print("Signature: \(signature.map { String(format: "%02x", $0) }.joined())")

// Import from private key
let imported = BaitcoinKit.importWallet(privateKeyHex: "0xabcdef...")
if let imported = imported {
    print("Imported address: \(imported.getAddress())")
}

// Validate an address
let isValid = BaitcoinKit.validateAddress("b'1A2b3C...")
print("Valid: \(isValid)")

// Create a transaction
let input = TxInput(txId: "prevtxid", outputIndex: 0)
let output = TxOutput(address: "b'recipientaddr", amount: 50_000_000) // 0.5 BAIT
let tx = BaitcoinTransaction.createTransfer(inputs: [input], outputs: [output], nonce: 1)
let txSig = tx.sign(privateKey: wallet.keyPair.privateKey)
print("TX ID: \(tx.txId)")

// Convert units
let satoshi = BaitcoinKit.toSatoshi(bait: 1.5)  // 150_000_000
let bait = BaitcoinKit.toBait(satoshi: 150_000_000)  // 1.5
```

### Android (Kotlin)

```kotlin
import org.baitcoin.sdk.*

// Configure for mainnet (default)
BaitcoinKit.configure(network = Network.MAINNET)

// Generate a new wallet
val wallet = BaitcoinKit.createWallet()
println("Address: ${wallet.getAddress()}")  // e.g., b'1A2b3C...

// Sign a message
val message = "Hello b'AI'tcoin".toByteArray(Charsets.UTF_8)
val signature = wallet.sign(message)
println("Signature: ${signature.joinToString("") { "%02x".format(it) }}")

// Import from private key
val imported = BaitcoinKit.importWallet(privateKeyHex = "0xabcdef...")
if (imported != null) {
    println("Imported address: ${imported.getAddress()}")
}

// Validate an address
val isValid = BaitcoinKit.validateAddress("b'1A2b3C...")
println("Valid: $isValid")

// Create a transaction
val input = TxInput(txId = "prevtxid", outputIndex = 0)
val output = TxOutput(address = "b'recipientaddr", amount = 50_000_000) // 0.5 BAIT
val tx = BaitcoinTransaction.createTransfer(inputs = listOf(input), outputs = listOf(output), nonce = 1)
val txSig = tx.sign(wallet.keyPair.privateKey)
println("TX ID: ${tx.txId}")

// Convert units
val satoshi = BaitcoinKit.toSatoshi(1.5)  // 150_000_000
val bait = BaitcoinKit.toBait(150_000_000L)  // 1.5
```

## API Reference

### BaitcoinKit (Entry Point)

| Method / Property | Swift | Kotlin | Description |
|---|---|---|---|
| `configure(network:crypto:)` | `BaitcoinKit.configure(...)` | `BaitcoinKit.configure(...)` | Set network and optional crypto provider |
| `createWallet()` | `BaitcoinKit.createWallet()` | `BaitcoinKit.createWallet()` | Generate new wallet |
| `importWallet(privateKeyHex:)` | `BaitcoinKit.importWallet(...)` | `BaitcoinKit.importWallet(...)` | Import from hex private key |
| `validateAddress(_:)` | `BaitcoinKit.validateAddress(...)` | `BaitcoinKit.validateAddress(...)` | Validate address string |
| `parseAddress(_:)` | `BaitcoinKit.parseAddress(...)` | `BaitcoinKit.parseAddress(...)` | Parse address to struct |
| `toSatoshi(bait:)` | `BaitcoinKit.toSatoshi(...)` | `BaitcoinKit.toSatoshi(...)` | Convert BAIT to satoshi |
| `toBait(satoshi:)` | `BaitcoinKit.toBait(...)` | `BaitcoinKit.toBait(...)` | Convert satoshi to BAIT |

### BaitcoinWallet

| Method / Property | Description |
|---|---|
| `generate(network:crypto:)` | Create a new random wallet (static) |
| `import(privateKeyHex:network:crypto:)` | Import wallet from hex key (static) |
| `sign(message:) -> Data/ByteArray` | Schnorr/BIP-340 sign a message |
| `getAddress() -> String` | Get the wallet's address string |
| `exportKeyBundle(passphrase:) -> Data/ByteArray` | Export encrypted key bundle |
| `verify(signature:message:) -> Bool` | Verify a signature |

### BaitcoinAddress

| Method / Property | Description |
|---|---|
| `from(pubkey:network:)` | Derive address from public key (static) |
| `parse(_:)` | Parse address string (static) |
| `validate(_:)` | Validate address string (static) |
| `address` | Full address string (e.g., `b'1A2b3C...`) |
| `network` | Network (mainnet/testnet) |
| `pubkeyHash` | 20-byte Hash160 of public key |

### BaitcoinKeyPair

| Method / Property | Description |
|---|---|
| `generate(crypto:)` | Create new random key pair (static) |
| `fromPrivateKeyHex(_:crypto:)` | Import from hex private key (static) |
| `sign(_:) -> Data/ByteArray` | Schnorr sign a message |
| `privateKeyHex() -> String` | Export private key as hex |
| `publicKeyHex() -> String` | Export public key as hex |
| `privateKey` | 32-byte private key bytes |
| `publicKey` | 32-byte x-only public key bytes |

### BaitcoinTransaction

| Method / Property | Description |
|---|---|
| `createTransfer(inputs:outputs:nonce:)` | Create a transfer transaction (static) |
| `sign(privateKey:) -> Data/ByteArray` | Sign the transaction |
| `toDict() -> [String: Any] / Map<String, Any>` | Serialize to dictionary |
| `serializeUnsigned() -> Data/ByteArray` | Serialize unsigned tx bytes |
| `txId` | Transaction ID (hex) |
| `inputs` | List of transaction inputs |
| `outputs` | List of transaction outputs |
| `nonce` | Replay-prevention nonce |
| `signature` | Schnorr signature (after signing) |
| `agentId` | Optional agent ID |

## Address Format

b'AI'tcoin addresses use a prefixed Base58Check encoding of the Hash160 of the public key.

```
Format:  <prefix>'<Base58Check(version + Hash160(pubkey))>

Mainnet: b'<Base58Check(0x00 + RIPEMD160(SHA256(pubkey)))>
Testnet: t'<Base58Check(0x6F + RIPEMD160(SHA256(pubkey)))>

Example:  b'1A2b3C4d5E6f7G8h9J0k
          t'9Z8y7X6w5V4u3T2s1R0q
```

The public key used is the 32-byte **x-only** coordinate (BIP-340 style), not the full compressed or uncompressed public key.

## Security Notes

1. **Private keys never leave the device.** All cryptographic operations are performed locally. The SDK never transmits private keys to any server.

2. **Use hardware-backed storage.**
   - **iOS**: Integrate with Apple's [Secure Enclave](https://developer.apple.com/documentation/security/certificate_key_and_trust_services/keys/protecting_keys_with_the_secure_enclave) for private key storage via `SecKeyCreateRandomKey` with `kSecAttrTokenIDSecureEnclave`.
   - **Android**: Use the [Android Keystore](https://developer.android.com/training/articles/keystore) system for hardware-backed key storage. The `exportKeyBundle` method provides a software fallback but should not be used as the primary storage mechanism in production.

3. **Use the real Android provider.** The Android SDK defaults to
   `BouncyCastleCryptoProvider`, backed by the documented
   `org.bouncycastle:bcprov-jdk18on:1.78` dependency. There is no functional
   placeholder provider or SHA-256 stand-in for secp256k1 operations; invalid
   private keys, malformed x-only keys, and invalid BIP-340 signatures fail
   closed.

4. **Memory cleanup.** Private key data should be zeroed from memory as soon as possible after use. In Swift, use `mutableBytes` to clear bytes. In Kotlin, overwrite array elements with zeros.

5. **Passphrase strength.** The `exportKeyBundle` passphrase should be at least 16 characters with mixed case, numbers, and symbols. Consider using a dedicated password manager.

6. **Key bundle encryption.** `exportKeyBundle` uses AES-256-GCM with a
   PBKDF2-HMAC-SHA256-derived 256-bit key, a random 12-byte nonce, and a
   128-bit authentication tag. The Android and Python envelopes are versioned;
   native interoperability still requires execution in the target toolchains.

## License

Copyright (c) 2024 b'AI'tcoin Foundation. All rights reserved.
