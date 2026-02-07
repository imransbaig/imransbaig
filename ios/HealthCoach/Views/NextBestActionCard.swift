import SwiftUI

struct NextBestActionCard: View {
    let action: NextBestAction
    let onTap: () -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isVisible: Bool = false
    @State private var isPressed: Bool = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: AppSpacing.lg) {
                // Action Icon
                ZStack {
                    Circle()
                        .fill(Color.hcPrimary.opacity(0.15))
                        .frame(width: 56, height: 56)

                    Image(systemName: action.actionType.iconName)
                        .font(.system(size: 24, weight: .semibold))
                        .foregroundColor(.hcPrimary)
                }

                // Content
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text(action.title)
                        .font(AppTypography.headline())
                        .foregroundColor(.hcTextPrimary)
                        .lineLimit(2)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility2)

                    Text(action.subtitle)
                        .font(AppTypography.subheadline())
                        .foregroundColor(.hcTextSecondary)
                        .lineLimit(3)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                }

                Spacer(minLength: 0)

                // Confidence Ring
                ConfidenceRing(confidence: action.confidence)
                    .frame(width: 40, height: 40)
            }
            .accentCardStyle(accentColor: .hcPrimary)
            .scaleEffect(isPressed ? 0.97 : 1.0)
        }
        .buttonStyle(PlainButtonStyle())
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in
                    withAnimation(.easeInOut(duration: 0.1)) {
                        isPressed = true
                    }
                }
                .onEnded { _ in
                    withAnimation(.easeInOut(duration: 0.1)) {
                        isPressed = false
                    }
                }
        )
        .opacity(isVisible ? 1 : 0)
        .offset(y: isVisible ? 0 : (reduceMotion ? 0 : 12))
        .onAppear {
            if reduceMotion {
                isVisible = true
            } else {
                withAnimation(.spring(response: 0.5, dampingFraction: 0.8).delay(0.1)) {
                    isVisible = true
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Recommended action: \(action.title). \(action.subtitle)")
        .accessibilityHint("Double tap to see why this action was recommended. Confidence level: \(Int(action.confidence * 100)) percent.")
        .accessibilityAddTraits(.isButton)
    }
}

// MARK: - Confidence Ring

struct ConfidenceRing: View {
    let confidence: Double

    var body: some View {
        ZStack {
            // Background ring
            Circle()
                .stroke(Color.hcTextTertiary.opacity(0.3), lineWidth: 3)

            // Confidence arc
            Circle()
                .trim(from: 0, to: CGFloat(confidence))
                .stroke(
                    confidenceColor,
                    style: StrokeStyle(lineWidth: 3, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))

            // Percentage text
            Text("\(Int(confidence * 100))")
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundColor(confidenceColor)
        }
        .accessibilityLabel("Confidence: \(Int(confidence * 100)) percent")
    }

    private var confidenceColor: Color {
        if confidence >= 0.8 {
            return .hcPrimary
        } else if confidence >= 0.6 {
            return .hcAmber
        } else {
            return .hcAlert
        }
    }
}

#Preview {
    ZStack {
        Color.hcBackground.ignoresSafeArea()
        NextBestActionCard(
            action: MockDataProvider.sampleNextAction(),
            onTap: {}
        )
        .padding()
    }
}
