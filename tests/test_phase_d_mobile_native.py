"""Phase D: Mobile SDK Native - Content validation tests.

Since we cannot compile Swift or Kotlin in this environment, these tests
validate the structural completeness and cross-platform consistency of the
native SDK source files.
"""

import os
import unittest
import re


# Resolve paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWIFT_PATH = os.path.join(BASE_DIR, "baitcoin_sdk", "mobile", "native", "BaitcoinKit.swift")
KOTLIN_PATH = os.path.join(BASE_DIR, "baitcoin_sdk", "mobile", "native", "BaitcoinKit.kt")
README_PATH = os.path.join(BASE_DIR, "baitcoin_sdk", "mobile", "native", "README.md")


def _read(path):
    """Read file contents, raising an assertion if the file is missing."""
    assert os.path.isfile(path), f"File does not exist: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestSwiftSDKExists(unittest.TestCase):
    """Verify the Swift SDK file exists and contains required classes/structs."""

    def setUp(self):
        self.src = _read(SWIFT_PATH)

    def test_swift_file_exists(self):
        """BaitcoinKit.swift must exist and be non-empty."""
        self.assertTrue(os.path.isfile(SWIFT_PATH), "Swift SDK file is missing")
        self.assertGreater(len(self.src), 1000, "Swift SDK file seems too small")

    def test_swift_has_BaitcoinKit(self):
        """Swift file must contain the BaitcoinKit class (main entry point)."""
        self.assertIn("public class BaitcoinKit", self.src)
        self.assertIn("static func configure", self.src)
        self.assertIn("static func createWallet", self.src)
        self.assertIn("static func importWallet", self.src)
        self.assertIn("static func validateAddress", self.src)
        self.assertIn("static func parseAddress", self.src)
        self.assertIn("static func toSatoshi", self.src)
        self.assertIn("static func toBait", self.src)
        # Check constant values
        self.assertIn("satoshiPerBait", self.src)
        self.assertIn("100_000_000", self.src)
        self.assertIn("decimalPlaces", self.src)

    def test_swift_has_Wallet(self):
        """Swift file must contain BaitcoinWallet with required methods."""
        self.assertIn("public class BaitcoinWallet", self.src)
        self.assertIn("static func generate", self.src)
        self.assertIn("static func import", self.src)
        self.assertIn("func sign", self.src)
        self.assertIn("func getAddress", self.src)
        self.assertIn("func exportKeyBundle", self.src)

    def test_swift_has_Address(self):
        """Swift file must contain BaitcoinAddress with required static methods."""
        self.assertIn("public struct BaitcoinAddress", self.src)
        self.assertIn("static func from(pubkey: Data, network: Network)", self.src)
        self.assertIn("static func parse(_ string: String)", self.src)
        self.assertIn("static func validate(_ string: String)", self.src)
        self.assertIn("let address: String", self.src)
        self.assertIn("let network: Network", self.src)
        self.assertIn("let pubkeyHash: Data", self.src)

    def test_swift_has_Transaction(self):
        """Swift file must contain BaitcoinTransaction with required fields and methods."""
        self.assertIn("public class BaitcoinTransaction", self.src)
        self.assertIn("static func createTransfer", self.src)
        self.assertIn("func sign(privateKey: Data)", self.src)
        self.assertIn("func toDict", self.src)
        # Check required fields
        self.assertIn("var inputs", self.src)
        self.assertIn("var outputs", self.src)
        self.assertIn("var nonce", self.src)
        self.assertIn("var signature", self.src)
        self.assertIn("var agentId", self.src)
        self.assertIn("var txId", self.src)

    def test_swift_has_KeyPair(self):
        """Swift file must contain BaitcoinKeyPair with required methods."""
        self.assertIn("public class BaitcoinKeyPair", self.src)
        self.assertIn("static func generate", self.src)
        self.assertIn("static func fromPrivateKeyHex", self.src)
        self.assertIn("func sign", self.src)
        self.assertIn("let privateKey: Data", self.src)
        self.assertIn("let publicKey: Data", self.src)

    def test_swift_has_base58(self):
        """Swift file must contain Base58 encoding/decoding."""
        self.assertIn("enum Base58", self.src)
        self.assertIn("public static func encode", self.src)
        self.assertIn("public static func decode", self.src)
        self.assertIn("public static func encodeCheck", self.src)
        self.assertIn("public static func decodeCheck", self.src)
        # Check alphabet
        self.assertIn("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz", self.src)

    def test_swift_has_hash160(self):
        """Swift file must contain Hash160 (RIPEMD160 + SHA256) utilities."""
        self.assertIn("enum BaitcoinHash", self.src)
        self.assertIn("static func sha256", self.src)
        self.assertIn("static func ripemd160", self.src)
        self.assertIn("static func hash160", self.src)
        self.assertIn("static func doubleSHA256", self.src)

    def test_swift_has_Network(self):
        """Swift file must have Network enum with mainnet and testnet."""
        self.assertIn("public enum Network", self.src)
        self.assertIn("case mainnet", self.src)
        self.assertIn("case testnet", self.src)

    def test_swift_has_CryptoProvider(self):
        """Swift file must have a CryptoProvider protocol for pluggable crypto."""
        self.assertIn("public protocol CryptoProvider", self.src)
        self.assertIn("PlaceholderCryptoProvider", self.src)
        self.assertIn("func schnorrSign", self.src)
        self.assertIn("func schnorrVerify", self.src)
        self.assertIn("func generateKeyPair", self.src)
        self.assertIn("func derivePublicKey", self.src)

    def test_swift_has_documentation(self):
        """Swift file should contain documentation comments (/// style)."""
        doc_count = self.src.count("///")
        self.assertGreater(doc_count, 20, "Expected at least 20 documentation comment lines")

    def test_swift_has_TxInput_TxOutput(self):
        """Swift file must contain TxInput and TxOutput structs."""
        self.assertIn("public struct TxInput", self.src)
        self.assertIn("public struct TxOutput", self.src)
        self.assertIn("let address: String", self.src)
        self.assertIn("let amount: UInt64", self.src)


class TestKotlinSDKExists(unittest.TestCase):
    """Verify the Kotlin SDK file exists and contains required classes."""

    def setUp(self):
        self.src = _read(KOTLIN_PATH)

    def test_kotlin_file_exists(self):
        """BaitcoinKit.kt must exist and be non-empty."""
        self.assertTrue(os.path.isfile(KOTLIN_PATH), "Kotlin SDK file is missing")
        self.assertGreater(len(self.src), 1000, "Kotlin SDK file seems too small")

    def test_kotlin_has_package(self):
        """Kotlin file must declare the org.baitcoin.sdk package."""
        self.assertIn("package org.baitcoin.sdk", self.src)

    def test_kotlin_has_BaitcoinKit(self):
        """Kotlin file must contain the BaitcoinKit object (main entry point)."""
        self.assertIn("object BaitcoinKit", self.src)
        self.assertIn("fun configure", self.src)
        self.assertIn("fun createWallet", self.src)
        self.assertIn("fun importWallet", self.src)
        self.assertIn("fun validateAddress", self.src)
        self.assertIn("fun parseAddress", self.src)
        self.assertIn("fun toSatoshi", self.src)
        self.assertIn("fun toBait", self.src)
        # Check constants
        self.assertIn("SATOSHI_PER_BAIT", self.src)
        self.assertIn("100_000_000", self.src)
        self.assertIn("DECIMAL_PLACES", self.src)

    def test_kotlin_has_Wallet(self):
        """Kotlin file must contain BaitcoinWallet with required methods."""
        self.assertIn("class BaitcoinWallet", self.src)
        self.assertIn("fun generate", self.src)
        self.assertIn("fun import", self.src)
        self.assertIn("fun sign(message: ByteArray)", self.src)
        self.assertIn("fun getAddress", self.src)
        self.assertIn("fun exportKeyBundle", self.src)

    def test_kotlin_has_Address(self):
        """Kotlin file must contain BaitcoinAddress data class with companion methods."""
        self.assertIn("data class BaitcoinAddress", self.src)
        self.assertIn("fun from(pubkey: ByteArray, network: Network)", self.src)
        self.assertIn("fun parse(address: String)", self.src)
        self.assertIn("fun validate(address: String)", self.src)
        self.assertIn("val address: String", self.src)
        self.assertIn("val network: Network", self.src)
        self.assertIn("val pubkeyHash: ByteArray", self.src)

    def test_kotlin_has_Transaction(self):
        """Kotlin file must contain BaitcoinTransaction with required fields and methods."""
        self.assertIn("class BaitcoinTransaction", self.src)
        self.assertIn("fun createTransfer", self.src)
        self.assertIn("fun sign(privateKey: ByteArray)", self.src)
        self.assertIn("fun toDict", self.src)
        # Check required fields
        self.assertIn("val inputs", self.src)
        self.assertIn("val outputs", self.src)
        self.assertIn("var nonce", self.src)
        self.assertIn("var signature", self.src)
        self.assertIn("var agentId", self.src)
        self.assertIn("val txId", self.src)

    def test_kotlin_has_KeyPair(self):
        """Kotlin file must contain BaitcoinKeyPair with required methods."""
        self.assertIn("class BaitcoinKeyPair", self.src)
        self.assertIn("fun generate", self.src)
        self.assertIn("fun fromPrivateKeyHex", self.src)
        self.assertIn("fun sign", self.src)
        self.assertIn("val privateKey: ByteArray", self.src)
        self.assertIn("val publicKey: ByteArray", self.src)

    def test_kotlin_has_Base58(self):
        """Kotlin file must contain Base58 encoding/decoding."""
        self.assertIn("object Base58", self.src)
        self.assertIn("fun encode", self.src)
        self.assertIn("fun decode", self.src)
        self.assertIn("fun encodeCheck", self.src)
        self.assertIn("fun decodeCheck", self.src)
        # Check alphabet
        self.assertIn("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz", self.src)

    def test_kotlin_has_hash160(self):
        """Kotlin file must contain Hash160 (RIPEMD160 + SHA256) utilities."""
        self.assertIn("object BaitcoinHash", self.src)
        self.assertIn("fun sha256", self.src)
        self.assertIn("fun ripemd160", self.src)
        self.assertIn("fun hash160", self.src)
        self.assertIn("fun doubleSha256", self.src)

    def test_kotlin_has_Network(self):
        """Kotlin file must have Network enum class with MAINNET and TESTNET."""
        self.assertIn("enum class Network", self.src)
        self.assertIn("MAINNET", self.src)
        self.assertIn("TESTNET", self.src)

    def test_kotlin_has_CryptoProvider(self):
        """Kotlin file must have a CryptoProvider interface for pluggable crypto."""
        self.assertIn("interface CryptoProvider", self.src)
        self.assertIn("class PlaceholderCryptoProvider", self.src)
        self.assertIn("fun schnorrSign", self.src)
        self.assertIn("fun schnorrVerify", self.src)
        self.assertIn("fun generateKeyPair", self.src)
        self.assertIn("fun derivePublicKey", self.src)

    def test_kotlin_has_documentation(self):
        """Kotlin file should contain documentation comments (/** */ style)."""
        doc_count = self.src.count("/**")
        self.assertGreater(doc_count, 15, "Expected at least 15 KDoc comment blocks")

    def test_kotlin_has_TxInput_TxOutput(self):
        """Kotlin file must contain TxInput and TxOutput data classes."""
        self.assertIn("data class TxInput", self.src)
        self.assertIn("data class TxOutput", self.src)
        self.assertIn("val address: String", self.src)
        self.assertIn("val amount: Long", self.src)


class TestSDKConsistency(unittest.TestCase):
    """Verify that both SDKs implement consistent address formats, key sizes, and transaction fields."""

    def setUp(self):
        self.swift = _read(SWIFT_PATH)
        self.kotlin = _read(KOTLIN_PATH)

    def test_address_format_matches(self):
        """Both SDKs must use b' for mainnet and t' for testnet address prefixes."""
        # Swift: mainnet prefix 'b', testnet prefix 't'
        self.assertIn("return \"b\"", self.swift)
        self.assertIn("return \"t\"", self.swift)
        # Swift: address string construction uses prefix + quote
        self.assertIn("network.addressPrefix)", self.swift)

        # Kotlin: MAINNET prefix 'b', TESTNET prefix 't'
        self.assertIn("MAINNET('b'", self.kotlin)
        self.assertIn("TESTNET('t'", self.kotlin)
        # Kotlin: address string construction uses prefix + quote
        self.assertIn("network.prefix}", self.kotlin)

    def test_key_size_32_bytes(self):
        """Both SDKs must use 32-byte (64-char hex) x-only public keys."""
        # Swift: 32 bytes for private and public keys
        self.assertIn("32 bytes x-only", self.swift)
        self.assertIn("Data(count: 32)", self.swift)  # Key generation uses 32 bytes
        # Swift: hex validation checks for 64 chars
        self.assertIn("cleanHex.count == 64", self.swift)

        # Kotlin: 32 bytes for private and public keys
        self.assertIn("32 bytes x-only", self.kotlin)
        self.assertIn("ByteArray(32)", self.kotlin)  # Key generation uses 32 bytes
        # Kotlin: hex validation checks for 64 chars
        self.assertIn("cleanHex.length != 64", self.kotlin)

    def test_transaction_fields_match(self):
        """Both SDKs must have the same transaction fields: inputs, outputs, nonce, signature, agentId, txId."""
        required_fields = ["inputs", "outputs", "nonce", "signature", "agentId", "txId"]
        for field in required_fields:
            self.assertIn(field, self.swift, f"Swift missing transaction field: {field}")
            self.assertIn(field, self.kotlin, f"Kotlin missing transaction field: {field}")

        # Both should have createTransfer and sign
        self.assertIn("createTransfer", self.swift)
        self.assertIn("createTransfer", self.kotlin)
        self.assertIn("toDict", self.swift)
        self.assertIn("toDict", self.kotlin)

    def test_network_enum_matches(self):
        """Both SDKs must have mainnet and testnet network variants."""
        # Swift
        self.assertIn("case mainnet", self.swift)
        self.assertIn("case testnet", self.swift)

        # Kotlin
        self.assertIn("MAINNET", self.kotlin)
        self.assertIn("TESTNET", self.kotlin)

    def test_satoshi_per_bait_matches(self):
        """Both SDKs must use 100,000,000 satoshi per BAIT (8 decimal places)."""
        # Swift
        self.assertIn("100_000_000", self.swift)
        self.assertIn("decimalPlaces", self.swift)

        # Kotlin
        self.assertIn("100_000_000", self.kotlin)
        self.assertIn("DECIMAL_PLACES", self.kotlin)

    def test_base58_alphabet_matches(self):
        """Both SDKs must use the same Bitcoin-style Base58 alphabet."""
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        self.assertIn(alphabet, self.swift)
        self.assertIn(alphabet, self.kotlin)

    def test_address_version_bytes(self):
        """Both SDKs must use the same version bytes: 0x00 mainnet, 0x6F testnet."""
        self.assertIn("0x00", self.swift)
        self.assertIn("0x6F", self.swift)
        self.assertIn("0x00", self.kotlin)
        self.assertIn("0x6F", self.kotlin)

    def test_hash160_consistency(self):
        """Both SDKs must implement Hash160 as RIPEMD160(SHA256(data))."""
        self.assertIn("ripemd160(sha256", self.swift)
        self.assertIn("ripemd160(sha256", self.kotlin)

    def test_both_have_schnorr_placeholder(self):
        """Both SDKs must note that the placeholder crypto needs replacement."""
        self.assertIn("PlaceholderCryptoProvider", self.swift)
        self.assertIn("PlaceholderCryptoProvider", self.kotlin)
        self.assertIn("placeholder", self.swift.lower())
        self.assertIn("placeholder", self.kotlin.lower())


class TestNativeReadme(unittest.TestCase):
    """Verify the native SDKs README exists and has required sections."""

    def setUp(self):
        self.readme = _read(README_PATH)

    def test_readme_exists(self):
        """README.md must exist in the native SDK directory."""
        self.assertTrue(os.path.isfile(README_PATH), "README.md is missing")
        self.assertGreater(len(self.readme), 500, "README.md seems too short")

    def test_readme_has_installation(self):
        """README must contain installation instructions for both platforms."""
        self.assertIn("Installation", self.readme, "README missing Installation section")
        # iOS installation
        self.assertIn("iOS", self.readme)
        self.assertIn("Xcode", self.readme)
        # Android installation
        self.assertIn("Android", self.readme)
        self.assertIn("BouncyCastle", self.readme)

    def test_readme_has_quick_start(self):
        """README must contain quick start code examples for both platforms."""
        self.assertIn("Quick Start", self.readme, "README missing Quick Start section")
        # Swift example
        self.assertIn("BaitcoinKit.createWallet", self.readme)
        self.assertIn("wallet.sign", self.readme)
        self.assertIn("wallet.getAddress", self.readme)
        # Kotlin example
        self.assertIn("BaitcoinKit.createWallet()", self.readme)
        self.assertIn("wallet.sign(", self.readme)

    def test_readme_has_security_notes(self):
        """README must contain security notes."""
        self.assertIn("Security Notes", self.readme, "README missing Security Notes section")
        self.assertIn("Secure Enclave", self.readme)
        self.assertIn("Android Keystore", self.readme)
        self.assertIn("private key", self.readme.lower())
        self.assertIn("never leave", self.readme.lower())

    def test_readme_has_address_format(self):
        """README must document the address format."""
        self.assertIn("Address Format", self.readme, "README missing Address Format section")
        self.assertIn("b'", self.readme)
        self.assertIn("t'", self.readme)
        self.assertIn("mainnet", self.readme.lower())
        self.assertIn("testnet", self.readme.lower())
        self.assertIn("Base58Check", self.readme)
        self.assertIn("Hash160", self.readme)

    def test_readme_has_api_reference(self):
        """README must have an API reference table."""
        self.assertIn("API Reference", self.readme, "README missing API Reference section")
        # Check some key APIs are mentioned
        self.assertIn("BaitcoinKit", self.readme)
        self.assertIn("BaitcoinWallet", self.readme)
        self.assertIn("BaitcoinAddress", self.readme)
        self.assertIn("BaitcoinKeyPair", self.readme)
        self.assertIn("BaitcoinTransaction", self.readme)

    def test_readme_has_overview(self):
        """README must have an overview table with platform info."""
        self.assertIn("Overview", self.readme, "README missing Overview section")
        self.assertIn("iOS 14", self.readme)
        self.assertIn("API 24", self.readme)
        self.assertIn("Swift", self.readme)
        self.assertIn("Kotlin", self.readme)

    def test_readme_has_8_decimals(self):
        """README must document 8 decimal places / 100M satoshi per BAIT."""
        self.assertIn("8 decimal", self.readme)
        self.assertIn("100,000,000", self.readme)


if __name__ == "__main__":
    unittest.main()
