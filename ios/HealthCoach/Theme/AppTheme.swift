import SwiftUI

// MARK: - Color Palette

extension Color {
    // Primary palette
    static let hcBackground = Color(red: 0.102, green: 0.106, blue: 0.180)       // #1A1B2E
    static let hcBackgroundLight = Color(red: 0.137, green: 0.141, blue: 0.224)   // #232339
    static let hcSurface = Color(red: 0.157, green: 0.161, blue: 0.255)           // #282941
    static let hcPrimary = Color(red: 0.176, green: 0.831, blue: 0.749)           // #2DD4BF teal
    static let hcAlert = Color(red: 1.0, green: 0.420, blue: 0.420)              // #FF6B6B coral
    static let hcCalm = Color(red: 0.655, green: 0.545, blue: 0.980)             // #A78BFA lavender
    static let hcAmber = Color(red: 0.984, green: 0.749, blue: 0.286)            // #FBBF49 amber
    static let hcGreen = Color(red: 0.286, green: 0.851, blue: 0.467)            // #49D977 green

    // Semantic state colors
    static func stateColor(for state: UserState) -> Color {
        switch state {
        case .stressed: return .hcAlert
        case .calm: return .hcPrimary
        case .fatigued: return .hcAmber
        case .energized: return .hcGreen
        case .sleepDeprived: return .hcCalm
        }
    }

    // Text
    static let hcTextPrimary = Color.white
    static let hcTextSecondary = Color.white.opacity(0.7)
    static let hcTextTertiary = Color.white.opacity(0.45)

    // Card gradient
    static var hcCardGradient: LinearGradient {
        LinearGradient(
            gradient: Gradient(colors: [
                Color(red: 0.137, green: 0.141, blue: 0.224),
                Color(red: 0.118, green: 0.122, blue: 0.200)
            ]),
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

// MARK: - Typography

struct AppTypography {
    // Headers - rounded design for warm, non-clinical feel
    static func largeTitle() -> Font {
        .system(.largeTitle, design: .rounded, weight: .bold)
    }

    static func title() -> Font {
        .system(.title, design: .rounded, weight: .bold)
    }

    static func title2() -> Font {
        .system(.title2, design: .rounded, weight: .semibold)
    }

    static func title3() -> Font {
        .system(.title3, design: .rounded, weight: .semibold)
    }

    // Body
    static func headline() -> Font {
        .system(.headline, design: .rounded, weight: .semibold)
    }

    static func body() -> Font {
        .system(.body, design: .rounded, weight: .regular)
    }

    static func callout() -> Font {
        .system(.callout, design: .rounded, weight: .medium)
    }

    static func subheadline() -> Font {
        .system(.subheadline, design: .rounded, weight: .regular)
    }

    static func footnote() -> Font {
        .system(.footnote, design: .rounded, weight: .regular)
    }

    static func caption() -> Font {
        .system(.caption, design: .rounded, weight: .medium)
    }

    // Numeric displays (e.g., heart rate, timer)
    static func numericDisplay() -> Font {
        .system(size: 48, weight: .bold, design: .rounded)
    }

    static func numericLarge() -> Font {
        .system(size: 36, weight: .semibold, design: .rounded)
    }

    static func numericMedium() -> Font {
        .system(size: 24, weight: .semibold, design: .monospaced)
    }
}

// MARK: - Spacing

struct AppSpacing {
    static let xxs: CGFloat = 2
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 20
    static let xxl: CGFloat = 24
    static let xxxl: CGFloat = 32
    static let section: CGFloat = 40
}

// MARK: - Corner Radius

struct AppCornerRadius {
    static let small: CGFloat = 8
    static let medium: CGFloat = 12
    static let large: CGFloat = 16
    static let extraLarge: CGFloat = 24
    static let circular: CGFloat = 999
}

// MARK: - Shadow

struct AppShadow {
    static let cardShadowColor = Color.black.opacity(0.35)
    static let cardShadowRadius: CGFloat = 12
    static let cardShadowX: CGFloat = 0
    static let cardShadowY: CGFloat = 4

    static let subtleShadowColor = Color.black.opacity(0.2)
    static let subtleShadowRadius: CGFloat = 6
    static let subtleShadowY: CGFloat = 2
}
