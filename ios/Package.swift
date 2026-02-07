// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "HealthCoach",
    platforms: [
        .iOS(.v17),
    ],
    products: [
        .library(name: "HealthCoach", targets: ["HealthCoach"]),
    ],
    targets: [
        .target(
            name: "HealthCoach",
            path: "HealthCoach"
        ),
        .testTarget(
            name: "HealthCoachTests",
            dependencies: ["HealthCoach"],
            path: "HealthCoachTests"
        ),
    ]
)
