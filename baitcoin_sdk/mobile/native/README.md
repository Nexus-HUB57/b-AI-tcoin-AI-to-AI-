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

1. Copy `BaitcoinKit.swift` into your Xcode project.
2. In your target's **Build Phases**, ensure `Security.framework` is linked.
3. For production use, add a secp256k1 Swift package (e.g., [secp256k1.swift](https://github.com/GigaBitcoin/secp256k1.swift)) and implement the `CryptoProvider` protocol with it.

```bash
# Or add via Swift Package Manager (when published)
# File > Swift Packages > Add Package Dependency
```

### Android (Kotlin)

1. Copy `BaitcoinKit.kt` into your project's source set (e.g., `app/src/main/java/org/baitcoin/sdk/`).
2. Add BouncyCastle as a dependency for RIPEMD-160 support:

```groovy
// build.gradle (app)
implementation 'org.bouncycastle:bcprov-jdk18on:1.78'
```

3. Register the BouncyCastle provider in your Application class:

```kotlin
import java.security.Security
import org.bouncycastle.jce.provider.BouncyCastleProvider

class MyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Security.addProvider(BouncyCastleProvider())
    }
}
```

4. For production use, implement the `CryptoProvider` interface using BitcoinJ or BouncyCastle's secp256k1 operations.

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

3. **Replace placeholder crypto.** The `PlaceholderCryptoProvider` / `PlaceholderCryptoProvider` is for development only. It uses SHA-256 instead of secp256k1 and provides no real cryptographic security. Replace with a real secp256k1 library before any production deployment.

4. **Memory cleanup.** Private key data should be zeroed from memory as soon as possible after use. In Swift, use `mutableBytes` to clear bytes. In Kotlin, overwrite array elements with zeros.

5. **Passphrase strength.** The `exportKeyBundle` passphrase should be at least 16 characters with mixed case, numbers, and symbols. Consider using a dedicated password manager.

6. **Key bundle encryption.** The current `exportKeyBundle` uses XOR encryption as a placeholder. Production implementations should use AES-256-GCM with a proper key derivation function (PBKDF2, Argon2id, or scrypt).

## License

Copyright (c) 2024 b'AI'tcoin Foundation. All rights reserved.
