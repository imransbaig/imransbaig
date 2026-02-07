import SwiftUI

struct LiveModeView: View {
    @EnvironmentObject var viewModel: HealthCoachViewModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var breathingScale: CGFloat = 1.0
    @State private var breathingOpacity: Double = 0.3
    @State private var pulseAnimation: Bool = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.hcBackground.ignoresSafeArea()

                if viewModel.isLiveMode {
                    activeSessionView
                } else {
                    inactiveView
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    HStack(spacing: AppSpacing.sm) {
                        if viewModel.isLiveMode {
                            Circle()
                                .fill(Color.hcAlert)
                                .frame(width: 8, height: 8)
                                .opacity(pulseAnimation ? 0.4 : 1.0)
                                .onAppear {
                                    if !reduceMotion {
                                        withAnimation(.easeInOut(duration: 1.0).repeatForever()) {
                                            pulseAnimation = true
                                        }
                                    }
                                }
                        }
                        Text("Live Mode")
                            .font(AppTypography.headline())
                            .foregroundColor(.hcTextPrimary)
                    }
                }
            }
            .toolbarBackground(Color.hcBackground, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }

    // MARK: - Active Session

    private var activeSessionView: some View {
        ScrollView {
            VStack(spacing: AppSpacing.xxl) {
                // Session Timer
                sessionTimerSection

                // Heart Rate Display
                heartRateSection

                // State Indicator
                currentStateSection

                // Breathing Circle
                breathingCircleSection

                // Active Intervention
                activeInterventionCard

                // End Session
                endSessionButton

                Spacer(minLength: AppSpacing.section)
            }
            .padding(.horizontal, AppSpacing.xl)
            .padding(.top, AppSpacing.lg)
        }
    }

    // MARK: - Session Timer

    private var sessionTimerSection: some View {
        VStack(spacing: AppSpacing.xs) {
            Text("Session Duration")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .textCase(.uppercase)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)

            Text(viewModel.formattedSessionTime)
                .font(AppTypography.numericMedium())
                .foregroundColor(.hcTextPrimary)
                .monospacedDigit()
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Session duration: \(viewModel.formattedSessionTime)")
    }

    // MARK: - Heart Rate

    private var heartRateSection: some View {
        VStack(spacing: AppSpacing.md) {
            HStack(alignment: .firstTextBaseline, spacing: AppSpacing.xs) {
                Text("\(Int(viewModel.currentHeartRate))")
                    .font(AppTypography.numericDisplay())
                    .foregroundColor(.hcAlert)
                    .monospacedDigit()
                    .dynamicTypeSize(...DynamicTypeSize.accessibility3)

                Text("BPM")
                    .font(AppTypography.subheadline())
                    .foregroundColor(.hcTextTertiary)
                    .dynamicTypeSize(...DynamicTypeSize.accessibility1)
            }

            // Mini heart rate chart
            heartRateChart
        }
        .cardStyle()
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Heart rate: \(Int(viewModel.currentHeartRate)) beats per minute")
        .accessibilityHint("Real-time heart rate from your wearable sensor")
    }

    private var heartRateChart: some View {
        GeometryReader { geometry in
            let readings = viewModel.heartRateReadings.suffix(30)
            let minHR = (readings.map(\.value).min() ?? 60) - 5
            let maxHR = (readings.map(\.value).max() ?? 100) + 5
            let range = maxHR - minHR
            let stepWidth = geometry.size.width / CGFloat(max(readings.count - 1, 1))

            Path { path in
                for (index, reading) in readings.enumerated() {
                    let x = CGFloat(index) * stepWidth
                    let y = geometry.size.height * (1 - CGFloat((reading.value - minHR) / range))

                    if index == 0 {
                        path.move(to: CGPoint(x: x, y: y))
                    } else {
                        path.addLine(to: CGPoint(x: x, y: y))
                    }
                }
            }
            .stroke(
                LinearGradient(
                    colors: [.hcAlert.opacity(0.6), .hcAlert],
                    startPoint: .leading,
                    endPoint: .trailing
                ),
                style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round)
            )
        }
        .frame(height: 60)
        .accessibilityHidden(true)
    }

    // MARK: - Current State

    private var currentStateSection: some View {
        HStack(spacing: AppSpacing.md) {
            Circle()
                .fill(Color.stateColor(for: viewModel.currentState))
                .frame(width: 14, height: 14)

            Text(viewModel.currentState.displayName)
                .font(AppTypography.title3())
                .foregroundColor(.hcTextPrimary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)

            Spacer()

            Text(viewModel.currentState.emoji)
                .font(.title2)
        }
        .subtleCardStyle()
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Current detected state: \(viewModel.currentState.displayName)")
    }

    // MARK: - Breathing Circle

    private var breathingCircleSection: some View {
        VStack(spacing: AppSpacing.md) {
            Text("Sync Your Breath")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .textCase(.uppercase)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)

            ZStack {
                // Outer glow
                Circle()
                    .fill(Color.hcPrimary.opacity(reduceMotion ? 0.08 : breathingOpacity * 0.3))
                    .frame(width: 140, height: 140)
                    .scaleEffect(reduceMotion ? 1.0 : breathingScale * 1.2)

                // Main circle
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [Color.hcPrimary.opacity(0.4), Color.hcPrimary.opacity(0.15)],
                            center: .center,
                            startRadius: 0,
                            endRadius: 60
                        )
                    )
                    .frame(width: 120, height: 120)
                    .scaleEffect(reduceMotion ? 1.0 : breathingScale)
                    .opacity(reduceMotion ? breathingOpacity : 1.0)
                    .overlay(
                        Circle()
                            .strokeBorder(Color.hcPrimary.opacity(0.5), lineWidth: 2)
                            .scaleEffect(reduceMotion ? 1.0 : breathingScale)
                    )
            }
            .onAppear {
                startBreathingAnimation()
            }
            .accessibilityLabel("Breathing guide circle")
            .accessibilityHint("Follow the expanding and contracting circle to sync your breathing")
        }
    }

    // MARK: - Active Intervention

    private var activeInterventionCard: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text("Active Suggestion")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .textCase(.uppercase)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)

            if let action = viewModel.nextAction {
                HStack(spacing: AppSpacing.md) {
                    Image(systemName: action.actionType.iconName)
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundColor(.hcPrimary)
                        .frame(width: 40, height: 40)
                        .background(Color.hcPrimary.opacity(0.12))
                        .clipShape(Circle())

                    VStack(alignment: .leading, spacing: AppSpacing.xxs) {
                        Text(action.title)
                            .font(AppTypography.callout())
                            .foregroundColor(.hcTextPrimary)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility1)

                        Text(action.subtitle)
                            .font(AppTypography.footnote())
                            .foregroundColor(.hcTextSecondary)
                            .lineLimit(2)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                    }

                    Spacer()
                }
                .accentCardStyle(accentColor: .hcPrimary)
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Active suggestion: \(action.title). \(action.subtitle)")
            }
        }
    }

    // MARK: - End Session Button

    private var endSessionButton: some View {
        Button {
            viewModel.endLiveMode()
        } label: {
            HStack(spacing: AppSpacing.sm) {
                Image(systemName: "stop.circle.fill")
                    .font(.system(size: 18, weight: .semibold))
                Text("End Session")
                    .font(AppTypography.headline())
            }
            .foregroundColor(.hcAlert)
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppSpacing.lg)
            .background(
                RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                    .fill(Color.hcAlert.opacity(0.12))
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                    .strokeBorder(Color.hcAlert.opacity(0.3), lineWidth: 1)
            )
        }
        .accessibilityLabel("End live mode session")
        .accessibilityHint("Stop the current real-time coaching session")
    }

    // MARK: - Inactive View

    private var inactiveView: some View {
        VStack(spacing: AppSpacing.xxxl) {
            Spacer()

            VStack(spacing: AppSpacing.xl) {
                Image(systemName: "waveform.path.ecg")
                    .font(.system(size: 56, weight: .light))
                    .foregroundColor(.hcPrimary.opacity(0.6))
                    .accessibilityHidden(true)

                VStack(spacing: AppSpacing.sm) {
                    Text("Live Mode")
                        .font(AppTypography.title())
                        .foregroundColor(.hcTextPrimary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility3)

                    Text("Get real-time coaching based on\nyour biometric signals.")
                        .font(AppTypography.body())
                        .foregroundColor(.hcTextSecondary)
                        .multilineTextAlignment(.center)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility2)
                }
            }

            Button {
                viewModel.startLiveMode()
            } label: {
                HStack(spacing: AppSpacing.sm) {
                    Image(systemName: "play.circle.fill")
                        .font(.system(size: 20, weight: .semibold))
                    Text("Start Session")
                        .font(AppTypography.headline())
                }
                .foregroundColor(.hcBackground)
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppSpacing.lg)
                .background(
                    RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                        .fill(Color.hcPrimary)
                )
            }
            .padding(.horizontal, AppSpacing.xxxl)
            .accessibilityLabel("Start live mode session")
            .accessibilityHint("Begin real-time coaching with heart rate monitoring and active interventions")

            Spacer()
        }
    }

    // MARK: - Animation

    private func startBreathingAnimation() {
        guard !reduceMotion else {
            // For reduce motion: use opacity changes only
            withAnimation(.easeInOut(duration: 4.0).repeatForever(autoreverses: true)) {
                breathingOpacity = 0.8
            }
            return
        }

        withAnimation(.easeInOut(duration: 4.0).repeatForever(autoreverses: true)) {
            breathingScale = 1.25
            breathingOpacity = 0.7
        }
    }
}

#Preview {
    LiveModeView()
        .environmentObject(HealthCoachViewModel())
        .environmentObject(FitbitService.shared)
}
