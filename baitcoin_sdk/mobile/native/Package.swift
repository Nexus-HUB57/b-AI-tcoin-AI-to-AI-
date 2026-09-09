// swift-tools-version: 6.1

import PackageDescription

let package = Package(
    name: "BaitcoinKit",
    platforms: [
        .iOS(.v14)
    ],
    products: [
        .library(name: "BaitcoinKit", targets: ["BaitcoinKit"])
    ],
    dependencies: [
        // P256K wraps Bitcoin Core's libsecp256k1 and exposes BIP-340 Schnorr.
        .package(
            url: "https://github.com/21-DOT-DEV/swift-secp256k1.git",
            exact: "0.23.2"
        )
    ],
    targets: [
        .target(
            name: "BaitcoinKit",
            dependencies: [
                .product(name: "P256K", package: "swift-secp256k1")
            ],
            path: ".",
            exclude: ["Tests", "README.md", "BaitcoinKit.kt"],
            sources: ["BaitcoinKit.swift"]
        ),
        .testTarget(
            name: "BaitcoinKitTests",
            dependencies: ["BaitcoinKit"],
            path: "Tests/BaitcoinKitTests",
            resources: [.process("Fixtures")]
        )
    ]
)
