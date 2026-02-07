import SwiftUI

struct BreathingExerciseView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    // Configuration
    var totalDuration: TimeInterval = 120 // 2 minutes default

    // State
    @State private var isActive: Bool = false
    @State private var phase: BreathingPhase = .breatheIn
    @State private var circleScale: CGFloat = 0.5
    @State private var circleOpacity: Double = 0.4
    @State private var elapsedTime: TimeInterval = 0
    @State private var phaseTimer: Timer?
    @State private var tickTimer: Timer?
    @State private var cycleCount: Int = 0

    enum BreathingPhase: String {
        case breatheIn = "Breathe In"
        case hold = "Hold"
        case breatheOut = "Breathe Out"
        case ready = "Ready"
        case complete = "Complete"

        var duration: TimeInterval {
            switch self {
            case .breatheIn: return 4.0
            case .hold: return 4.0
            case .breatheOut: return 6.0
            case .ready: return 3.0
            case .complete: return 0
            }
        }

        var color: Color {
            switch self {
            case .breatheIn: return .hcPrimary
            case .hold: return .hcCalm
            case .breatheOut: return .hcPrimary.opacity(0.7)
            case .ready: return .hcTextTertiary
            case .complete: return .hcGreen
            }
        }
    }

    var body: some View {
        ZStack {
            Color.hcBackground.ignoresSafeArea()

            VStack(spacing: AppSpacing.xxxl) {
                // Close button
                HStack {
                    Spacer()
                    Button {
                        stopExercise()
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title2)
                            .foregroundColor(.hcTextTertiary)
                    }
                    .accessibilityLabel("Close breathing exercise")
                    .accessibilityHint("End the breathing exercise and return to the previous screen")
                }
                .padding(.horizontal, AppSpacing.xl)

                Spacer()

                // Phase Label
                VStack(spacing: AppSpacing.sm) {
                    Text(phase.rawValue)
                        .font(AppTypography.title())
                        .foregroundColor(phase.color)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility3)
                        .accessibilityAddTraits(.updatesFrequently)
                        .accessibilityLabel("Current phase: \(phase.rawValue)")

                    if phase != .complete && phase != .ready {
                        Text("Cycle \(cycleCount + 1)")
                            .font(AppTypography.footnote())
                            .foregroundColor(.hcTextTertiary)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                    }
                }

                // Breathing Circle
                breathingCircle

                // Timer
                timerDisplay

                Spacer()

                // Start / Complete Button
                controlButton
            }
            .padding(.bottom, AppSpacing.xxxl)
        }
    }

    // MARK: - Breathing Circle

    private var breathingCircle: some View {
        ZStack {
            // Outer glow ring
            Circle()
                .fill(phase.color.opacity(reduceMotion ? 0.05 : 0.08))
                .frame(width: 240, height: 240)
                .scaleEffect(reduceMotion ? 1.0 : circleScale * 1.3)

            // Middle ring
            Circle()
                .strokeBorder(phase.color.opacity(0.2), lineWidth: 1.5)
                .frame(width: 200, height: 200)
                .scaleEffect(reduceMotion ? 1.0 : circleScale * 1.1)

            // Main breathing circle
            Circle()
                .fill(
                    RadialGradient(
                        colors: [phase.color.opacity(0.5), phase.color.opacity(0.15)],
                        center: .center,
                        startRadius: 0,
                        endRadius: 80
                    )
                )
                .frame(width: 160, height: 160)
                .scaleEffect(reduceMotion ? 1.0 : circleScale)
                .opacity(reduceMotion ? circleOpacity : 1.0)
                .overlay(
                    Circle()
                        .strokeBorder(phase.color.opacity(0.6), lineWidth: 2)
                        .frame(width: 160, height: 160)
                        .scaleEffect(reduceMotion ? 1.0 : circleScale)
                )

            // Center dot
            Circle()
                .fill(phase.color)
                .frame(width: 12, height: 12)
        }
        .frame(width: 260, height: 260)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Breathing guide circle. \(phase.rawValue)")
        .accessibilityHint("The circle expands during inhale and contracts during exhale")
    }

    // MARK: - Timer Display

    private var timerDisplay: some View {
        VStack(spacing: AppSpacing.xs) {
            // Elapsed / remaining
            let remaining = max(0, totalDuration - elapsedTime)
            let minutes = Int(remaining) / 60
            let seconds = Int(remaining) % 60

            Text(String(format: "%d:%02d", minutes, seconds))
                .font(AppTypography.numericMedium())
                .foregroundColor(.hcTextSecondary)
                .monospacedDigit()
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)

            Text("remaining")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)

            // Progress bar
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.hcTextTertiary.opacity(0.15))
                        .frame(height: 4)

                    RoundedRectangle(cornerRadius: 2)
                        .fill(phase.color)
                        .frame(
                            width: geometry.size.width * CGFloat(min(elapsedTime / totalDuration, 1.0)),
                            height: 4
                        )
                }
            }
            .frame(height: 4)
            .padding(.horizontal, AppSpacing.xxxl)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Time remaining: \(Int(max(0, totalDuration - elapsedTime))) seconds")
    }

    // MARK: - Control Button

    private var controlButton: some View {
        Group {
            if phase == .complete {
                Button {
                    dismiss()
                } label: {
                    HStack(spacing: AppSpacing.sm) {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 18, weight: .semibold))
                        Text("Done")
                            .font(AppTypography.headline())
                    }
                    .foregroundColor(.hcBackground)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, AppSpacing.lg)
                    .background(
                        RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                            .fill(Color.hcGreen)
                    )
                }
                .accessibilityLabel("Done")
                .accessibilityHint("Close the breathing exercise")
            } else if !isActive {
                Button {
                    startExercise()
                } label: {
                    HStack(spacing: AppSpacing.sm) {
                        Image(systemName: "play.circle.fill")
                            .font(.system(size: 18, weight: .semibold))
                        Text("Begin")
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
                .accessibilityLabel("Begin breathing exercise")
                .accessibilityHint("Start a \(Int(totalDuration / 60))-minute guided breathing exercise")
            } else {
                Button {
                    stopExercise()
                } label: {
                    HStack(spacing: AppSpacing.sm) {
                        Image(systemName: "stop.circle.fill")
                            .font(.system(size: 18, weight: .semibold))
                        Text("Stop")
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
                .accessibilityLabel("Stop breathing exercise")
                .accessibilityHint("End the exercise early")
            }
        }
        .padding(.horizontal, AppSpacing.xxxl)
    }

    // MARK: - Exercise Control

    private func startExercise() {
        isActive = true
        elapsedTime = 0
        cycleCount = 0
        phase = .breatheIn

        // Start the tick timer for elapsed time
        tickTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
            Task { @MainActor in
                elapsedTime += 1.0
                if elapsedTime >= totalDuration {
                    completeExercise()
                }
            }
        }

        // Start the first phase
        animatePhase(.breatheIn)
        triggerHaptic()
    }

    private func stopExercise() {
        isActive = false
        phaseTimer?.invalidate()
        phaseTimer = nil
        tickTimer?.invalidate()
        tickTimer = nil
        phase = .ready

        // Reset circle
        if reduceMotion {
            circleOpacity = 0.4
        } else {
            withAnimation(.easeInOut(duration: 0.5)) {
                circleScale = 0.5
            }
        }
    }

    private func completeExercise() {
        isActive = false
        phase = .complete
        phaseTimer?.invalidate()
        phaseTimer = nil
        tickTimer?.invalidate()
        tickTimer = nil
        triggerHaptic()

        if reduceMotion {
            circleOpacity = 0.8
        } else {
            withAnimation(.easeInOut(duration: 0.5)) {
                circleScale = 1.0
            }
        }
    }

    private func animatePhase(_ newPhase: BreathingPhase) {
        guard isActive, newPhase != .complete else { return }

        phase = newPhase
        triggerHaptic()

        switch newPhase {
        case .breatheIn:
            if reduceMotion {
                withAnimation(.easeInOut(duration: newPhase.duration)) {
                    circleOpacity = 0.9
                }
            } else {
                withAnimation(.easeInOut(duration: newPhase.duration)) {
                    circleScale = 1.0
                }
            }
            scheduleNextPhase(.hold, after: newPhase.duration)

        case .hold:
            // No animation change during hold
            scheduleNextPhase(.breatheOut, after: newPhase.duration)

        case .breatheOut:
            if reduceMotion {
                withAnimation(.easeInOut(duration: newPhase.duration)) {
                    circleOpacity = 0.3
                }
            } else {
                withAnimation(.easeInOut(duration: newPhase.duration)) {
                    circleScale = 0.5
                }
            }
            scheduleNextPhase(.breatheIn, after: newPhase.duration)
            cycleCount += 1

        case .ready, .complete:
            break
        }
    }

    private func scheduleNextPhase(_ nextPhase: BreathingPhase, after delay: TimeInterval) {
        phaseTimer?.invalidate()
        phaseTimer = Timer.scheduledTimer(withTimeInterval: delay, repeats: false) { _ in
            Task { @MainActor in
                if isActive {
                    animatePhase(nextPhase)
                }
            }
        }
    }

    private func triggerHaptic() {
        let generator = UIImpactFeedbackGenerator(style: .soft)
        generator.prepare()
        generator.impactOccurred()
    }
}

#Preview {
    BreathingExerciseView()
}
