import SwiftUI

// MARK: - Card Style Modifier

struct CardModifier: ViewModifier {
    var padding: CGFloat = AppSpacing.lg
    var cornerRadius: CGFloat = AppCornerRadius.large

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(Color.hcCardGradient)
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
            .shadow(
                color: AppShadow.cardShadowColor,
                radius: AppShadow.cardShadowRadius,
                x: AppShadow.cardShadowX,
                y: AppShadow.cardShadowY
            )
    }
}

// MARK: - Subtle Card Modifier (less prominent)

struct SubtleCardModifier: ViewModifier {
    var padding: CGFloat = AppSpacing.md
    var cornerRadius: CGFloat = AppCornerRadius.medium

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(Color.hcSurface.opacity(0.6))
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
            .shadow(
                color: AppShadow.subtleShadowColor,
                radius: AppShadow.subtleShadowRadius,
                x: 0,
                y: AppShadow.subtleShadowY
            )
    }
}

// MARK: - Accent Card Modifier (highlighted)

struct AccentCardModifier: ViewModifier {
    var accentColor: Color = .hcPrimary
    var padding: CGFloat = AppSpacing.lg
    var cornerRadius: CGFloat = AppCornerRadius.large

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(
                ZStack {
                    Color.hcCardGradient
                    accentColor.opacity(0.08)
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .strokeBorder(accentColor.opacity(0.25), lineWidth: 1)
            )
            .shadow(
                color: accentColor.opacity(0.15),
                radius: AppShadow.cardShadowRadius,
                x: 0,
                y: AppShadow.cardShadowY
            )
    }
}

// MARK: - View Extension

extension View {
    func cardStyle(padding: CGFloat = AppSpacing.lg, cornerRadius: CGFloat = AppCornerRadius.large) -> some View {
        modifier(CardModifier(padding: padding, cornerRadius: cornerRadius))
    }

    func subtleCardStyle(padding: CGFloat = AppSpacing.md, cornerRadius: CGFloat = AppCornerRadius.medium) -> some View {
        modifier(SubtleCardModifier(padding: padding, cornerRadius: cornerRadius))
    }

    func accentCardStyle(accentColor: Color = .hcPrimary, padding: CGFloat = AppSpacing.lg, cornerRadius: CGFloat = AppCornerRadius.large) -> some View {
        modifier(AccentCardModifier(accentColor: accentColor, padding: padding, cornerRadius: cornerRadius))
    }
}
