import SwiftUI

struct TodayView: View {
    @EnvironmentObject var viewModel: HealthCoachViewModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var showTrustPanel: Bool = false
    @State private var showCueLogger: Bool = false
    @State private var showBreathingExercise: Bool = false
    @State private var headerVisible: Bool = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppSpacing.xxl) {
                    // Greeting Header
                    greetingHeader

                    // State Indicator
                    stateIndicator

                    // Next Best Action Card
                    if let action = viewModel.nextAction {
                        VStack(alignment: .leading, spacing: AppSpacing.sm) {
                            Text("Recommended for You")
                                .font(AppTypography.caption())
                                .foregroundColor(.hcTextTertiary)
                                .textCase(.uppercase)
                                .padding(.horizontal, AppSpacing.xs)
                                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                                .accessibilityLabel("Recommended for you")

                            NextBestActionCard(action: action) {
                                showTrustPanel = true
                            }
                        }
                    }

                    // Quick Actions
                    quickActionsSection

                    // Recent Cues
                    if !viewModel.recentCues.isEmpty {
                        recentCuesSection
                    }

                    Spacer(minLength: AppSpacing.section)
                }
                .padding(.horizontal, AppSpacing.xl)
                .padding(.top, AppSpacing.lg)
            }
            .background(Color.hcBackground)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("Health Coach")
                        .font(AppTypography.headline())
                        .foregroundColor(.hcTextPrimary)
                }
            }
            .toolbarBackground(Color.hcBackground, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .refreshable {
                await viewModel.refreshAll()
            }
            .sheet(isPresented: $showTrustPanel) {
                if let action = viewModel.nextAction {
                    TrustPanelView(action: action) { wasHelpful in
                        viewModel.submitFeedback(actionId: action.id, wasHelpful: wasHelpful)
                    }
                    .presentationDetents([.large])
                    .presentationDragIndicator(.visible)
                }
            }
            .sheet(isPresented: $showCueLogger) {
                CueLoggerView { type, note in
                    viewModel.logCue(type: type, note: note)
                }
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
            }
            .fullScreenCover(isPresented: $showBreathingExercise) {
                BreathingExerciseView()
            }
        }
    }

    // MARK: - Greeting Header

    private var greetingHeader: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text(viewModel.greetingText)
                .font(AppTypography.largeTitle())
                .foregroundColor(.hcTextPrimary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility3)
                .accessibilityAddTraits(.isHeader)

            Text(viewModel.greetingSubtext)
                .font(AppTypography.body())
                .foregroundColor(.hcTextSecondary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)
        }
        .opacity(headerVisible ? 1 : 0)
        .offset(y: headerVisible ? 0 : (reduceMotion ? 0 : 8))
        .onAppear {
            if reduceMotion {
                headerVisible = true
            } else {
                withAnimation(.easeOut(duration: 0.5)) {
                    headerVisible = true
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(viewModel.greetingText). \(viewModel.greetingSubtext)")
    }

    // MARK: - State Indicator

    private var stateIndicator: some View {
        HStack(spacing: AppSpacing.md) {
            Circle()
                .fill(Color.stateColor(for: viewModel.currentState))
                .frame(width: 10, height: 10)

            Text("Current state: \(viewModel.currentState.displayName)")
                .font(AppTypography.subheadline())
                .foregroundColor(.hcTextSecondary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
        }
        .padding(.horizontal, AppSpacing.md)
        .padding(.vertical, AppSpacing.sm)
        .background(
            Capsule()
                .fill(Color.stateColor(for: viewModel.currentState).opacity(0.1))
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Your current state is \(viewModel.currentState.displayName)")
    }

    // MARK: - Quick Actions

    private var quickActionsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Quick Actions")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .textCase(.uppercase)
                .padding(.horizontal, AppSpacing.xs)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                .accessibilityAddTraits(.isHeader)

            VStack(spacing: AppSpacing.md) {
                // Downshift Now
                QuickActionButton(
                    title: "Downshift Now",
                    subtitle: "2-min breathing reset",
                    icon: "wind",
                    accentColor: .hcCalm
                ) {
                    showBreathingExercise = true
                }
                .accessibilityLabel("Downshift Now")
                .accessibilityHint("Start a quick 2-minute breathing exercise to help you relax")

                HStack(spacing: AppSpacing.md) {
                    // Log a Cue
                    QuickActionButton(
                        title: "Log a Cue",
                        subtitle: "Track what you feel",
                        icon: "plus.circle.fill",
                        accentColor: .hcAmber
                    ) {
                        showCueLogger = true
                    }
                    .accessibilityLabel("Log a Cue")
                    .accessibilityHint("Open the cue logger to record how you're feeling")

                    // Start Live Mode
                    QuickActionButton(
                        title: "Start Live Mode",
                        subtitle: "Real-time coaching",
                        icon: "waveform.path.ecg",
                        accentColor: .hcPrimary
                    ) {
                        viewModel.startLiveMode()
                    }
                    .accessibilityLabel("Start Live Mode")
                    .accessibilityHint("Begin a real-time coaching session with heart rate monitoring")
                }
            }
        }
    }

    // MARK: - Recent Cues

    private var recentCuesSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Recent Cues")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .textCase(.uppercase)
                .padding(.horizontal, AppSpacing.xs)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                .accessibilityAddTraits(.isHeader)

            ForEach(viewModel.recentCues.prefix(3)) { cue in
                HStack(spacing: AppSpacing.md) {
                    Image(systemName: cue.type.iconName)
                        .font(.system(size: 16, weight: .medium))
                        .foregroundColor(cueColor(for: cue.type))
                        .frame(width: 32, height: 32)
                        .background(cueColor(for: cue.type).opacity(0.12))
                        .clipShape(Circle())

                    VStack(alignment: .leading, spacing: AppSpacing.xxs) {
                        Text(cue.type.displayName)
                            .font(AppTypography.callout())
                            .foregroundColor(.hcTextPrimary)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility1)

                        if let note = cue.note {
                            Text(note)
                                .font(AppTypography.footnote())
                                .foregroundColor(.hcTextTertiary)
                                .lineLimit(1)
                                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                        }
                    }

                    Spacer()

                    Text(cue.timestamp, style: .relative)
                        .font(AppTypography.caption())
                        .foregroundColor(.hcTextTertiary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                }
                .subtleCardStyle()
                .accessibilityElement(children: .combine)
                .accessibilityLabel("\(cue.type.displayName) cue\(cue.note != nil ? ": \(cue.note!)" : ""), logged \(cue.timestamp, style: .relative) ago")
            }
        }
    }

    private func cueColor(for type: CueType) -> Color {
        switch type {
        case .stress: return .hcAlert
        case .pain: return .hcAmber
        case .moodLow: return .hcCalm
        case .moodHigh: return .hcGreen
        case .custom: return .hcPrimary
        }
    }
}

// MARK: - Quick Action Button

struct QuickActionButton: View {
    let title: String
    let subtitle: String
    let icon: String
    let accentColor: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: AppSpacing.md) {
                Image(systemName: icon)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundColor(accentColor)
                    .frame(width: 36, height: 36)

                VStack(alignment: .leading, spacing: AppSpacing.xxs) {
                    Text(title)
                        .font(AppTypography.callout())
                        .foregroundColor(.hcTextPrimary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility1)

                    Text(subtitle)
                        .font(AppTypography.footnote())
                        .foregroundColor(.hcTextTertiary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                }

                Spacer(minLength: 0)

                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.hcTextTertiary)
            }
            .cardStyle(padding: AppSpacing.md)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

#Preview {
    TodayView()
        .environmentObject(HealthCoachViewModel())
        .environmentObject(FitbitService.shared)
}
