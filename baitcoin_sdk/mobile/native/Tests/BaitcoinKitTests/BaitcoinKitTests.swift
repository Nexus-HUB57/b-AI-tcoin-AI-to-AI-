import XCTest
@testable import BaitcoinKit

final class BaitcoinKitTests: XCTestCase {
    func testProviderDerivesAndVerifiesBIP340Signature() throws {
        let provider = P256KCryptoProvider()
        let privateKey = Data(repeating: 1, count: 32)
        let message = Data(repeating: 2, count: 32)
        let publicKey = try provider.derivePublicKey(privateKey: privateKey)
        let signature = try provider.schnorrSign(message: message, privateKey: privateKey)

        XCTAssertEqual(publicKey.count, 32)
        XCTAssertEqual(signature.count, 64)
        XCTAssertTrue(provider.schnorrVerify(signature: signature, message: message, publicKey: publicKey))

        var alteredMessage = message
        alteredMessage[0] ^= 0x01
        XCTAssertFalse(provider.schnorrVerify(signature: signature, message: alteredMessage, publicKey: publicKey))
    }
}
