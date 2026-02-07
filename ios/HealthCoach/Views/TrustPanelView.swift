import SwiftUI

struct TrustPanelView: View {
    let action: NextBestAction
    let onFeedback: (Bool) -> Void

    @Environment(\.dismiss) private var dismiss
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var contentVisible: Bool = false
    @State private var feedbackGiven: Bool = false
    @State private var feedbackValue: Bool? = nil

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppSpacing.xxl) {
                    // Explanation
                    explanationSection

                    // Signal Summary
                    signalSection

                    // Inference
                    inferenceSection

                    // Confidence
                    confidenceSection

                    // Feedback
                    feedbackSection

                    Spacer(minLength: AppSpacing.section)
                }
                .padding(.horizontal, AppSpacing.xl)
                .padding(.top, AppSpacing.lg)
                .opacity(contentVisible ? 1 : 0)
                .offset(y: contentVisible ? 0 : (reduceMotion ? 0 : 16))
                .onAppear {
                    if reduceMotion {
                        contentVisible = true
                    } else {
                        withAnimation(.easeOut(duration: 0.4).delay(0.15)) {
                            contentVisible = true
                        }
                    }
                }
            }
            .background(Color.hcBackground)
            .navigationTitle("Why This Action?")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title3)
                            .foregroundColor(.hcTextTertiary)
                    }
                    .accessibilityLabel("Close panel")
                    .accessibilityHint("Dismiss the trust panel")
                }
            }
            .toolbarBackground(Color.hcBackground, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }

    // MARK: - Sections

    private var explanationSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            SectionHeader(title: "In Plain Terms", icon: "text.quote")

            Text(action.reasonTrace.explanation)
                .font(AppTypography.body())
                .foregroundColor(.hcTextPrimary)
                .lineSpacing(4)
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)
                .accessibilityLabel("Explanation: \(action.reasonTrace.explanation)")
        }
        .subtleCardStyle()
    }

    private var signalSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            SectionHeader(title: "What We Noticed", icon: "antenna.radiowaves.left.and.right")

            ForEach(Array(action.reasonTrace.signals.enumerated()), id: \.offset) { index, signal in
                HStack(alignment: .top, spacing: AppSpacing.md) {
                    Circle()
                        .fill(Color.hcPrimary)
                        .frame(width: 6, height: 6)
                        .padding(.top, 7)

                    Text(signal)
                        .font(AppTypography.subheadline())
                        .foregroundColor(.hcTextSecondary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Signal \(index + 1): \(signal)")
            }
        }
        .subtleCardStyle()
    }

    private var inferenceSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            SectionHeader(title: "Our Assessment", icon: "brain.head.profile")

            Text(action.reasonTrace.inference)
                .font(AppTypography.subheadline())
                .foregroundColor(.hcTextSecondary)
                .lineSpacing(3)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                .accessibilityLabel("Assessment: \(action.reasonTrace.inference)")
        }
        .subtleCardStyle()
    }

    private var confidenceSection: some View {
        HStack(spacing: AppSpacing.lg) {
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text("Confidence Level")
                    .font(AppTypography.caption())
                    .foregroundColor(.hcTextTertiary)
                    .dynamicTypeSize(...DynamicTypeSize.accessibility1)

                Text("\(Int(action.reasonTrace.confidence * 100))%")
                    .font(AppTypography.title2())
                    .foregroundColor(confidenceColor)
            }

            Spacer()

            // Confidence bar
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.hcTextTertiary.opacity(0.2))
                        .frame(height: 8)

                    RoundedRectangle(cornerRadius: 4)
                        .fill(confidenceColor)
                        .frame(
                            width: geometry.size.width * CGFloat(action.reasonTrace.confidence),
                            height: 8
                        )
                }
            }
            .frame(height: 8)
        }
        .subtleCardStyle()
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Confidence level: \(Int(action.reasonTrace.confidence * 100)) percent")
    }

    private var feedbackSection: some View {
        VStack(spacing: AppSpacing.lg) {
            Text("Was this helpful?")
                .font(AppTypography.headline())
                .foregroundColor(.hcTextPrimary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)

            if feedbackGiven {
                HStack(spacing: AppSpacing.sm) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.hcPrimary)
                    Text("Thank you for your feedback!")
                        .font(AppTypography.subheadline())
                        .foregroundColor(.hcTextSecondary)
                }
                .accessibilityLabel("Feedback submitted. Thank you!")
            } else {
                HStack(spacing: AppSpacing.lg) {
                    feedbackButton(isHelpful: true, icon: "hand.thumbsup.fill", label: "Yes")
                    feedbackButton(isHelpful: false, icon: "hand.thumbsdown.fill", label: "No")
                }
            }
        }
        .frame(maxWidth: .infinity)
        .subtleCardStyle()
    }

    private func feedbackButton(isHelpful: Bool, icon: String, label: String) -> some View {
        Button {
            withAnimation(.easeInOut(duration: 0.3)) {
                feedbackGiven = true
                feedbackValue = isHelpful
            }
            onFeedback(isHelpful)
        } label: {
            HStack(spacing: AppSpacing.sm) {
                Image(systemName: icon)
                Text(label)
                    .font(AppTypography.callout())
            }
            .foregroundColor(isHelpful ? .hcPrimary : .hcAlert)
            .padding(.horizontal, AppSpacing.xxl)
            .padding(.vertical, AppSpacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .fill((isHelpful ? Color.hcPrimary : Color.hcAlert).opacity(0.12))
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .strokeBorder((isHelpful ? Color.hcPrimary : Color.hcAlert).opacity(0.3), lineWidth: 1)
            )
        }
        .accessibilityLabel(isHelpful ? "Yes, this was helpful" : "No, this was not helpful")
        .accessibilityHint("Submit your feedback about this recommendation")
    }

    private var confidenceColor: Color {
        let confidence = action.reasonTrace.confidence
        if confidence >= 0.8 { return .hcPrimary }
        if confidence >= 0.6 { return .hcAmber }
        return .hcAlert
    }
}

// MARK: - Section Header

struct SectionHeader: View {
    let title: String
    let icon: String

    var body: some View {
        HStack(spacing: AppSpacing.sm) {
            Image(systemName: icon)
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(.hcPrimary)

            Text(title)
                .font(AppTypography.callout())
                .foregroundColor(.hcPrimary)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(title)
    }
}

#Preview {
    TrustPanelView(
        action: MockDataProvider.sampleNextAction(),
        onFeedback: { _ in }
    )
}
