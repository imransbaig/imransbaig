import SwiftUI

struct InsightsView: View {
    @EnvironmentObject var viewModel: HealthCoachViewModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var contentVisible: Bool = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppSpacing.xxl) {
                    // 7-Day Stress Trend
                    stressTrendSection

                    // Sleep Quality Summary
                    sleepQualitySection

                    // Action Effectiveness
                    actionEffectivenessSection

                    Spacer(minLength: AppSpacing.section)
                }
                .padding(.horizontal, AppSpacing.xl)
                .padding(.top, AppSpacing.lg)
                .opacity(contentVisible ? 1 : 0)
                .onAppear {
                    if reduceMotion {
                        contentVisible = true
                    } else {
                        withAnimation(.easeOut(duration: 0.4)) {
                            contentVisible = true
                        }
                    }
                }
            }
            .background(Color.hcBackground)
            .navigationTitle("Insights")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(Color.hcBackground, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }

    // MARK: - Stress Trend

    private var stressTrendSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                VStack(alignment: .leading, spacing: AppSpacing.xxs) {
                    Text("7-Day Stress Trend")
                        .font(AppTypography.headline())
                        .foregroundColor(.hcTextPrimary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility2)
                        .accessibilityAddTraits(.isHeader)

                    Text("Lower is better")
                        .font(AppTypography.footnote())
                        .foregroundColor(.hcTextTertiary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                }

                Spacer()

                trendIndicator
            }

            // Bar chart
            stressBarChart
                .frame(height: 120)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(stressTrendAccessibilityLabel)
        }
        .cardStyle()
    }

    private var trendIndicator: some View {
        let trend = viewModel.stressTrend
        let isImproving = (trend.last ?? 0) < (trend.first ?? 0)

        return HStack(spacing: AppSpacing.xs) {
            Image(systemName: isImproving ? "arrow.down.right" : "arrow.up.right")
                .font(.system(size: 12, weight: .bold))

            Text(isImproving ? "Improving" : "Elevated")
                .font(AppTypography.caption())
        }
        .foregroundColor(isImproving ? .hcPrimary : .hcAlert)
        .padding(.horizontal, AppSpacing.md)
        .padding(.vertical, AppSpacing.xs)
        .background(
            Capsule()
                .fill((isImproving ? Color.hcPrimary : Color.hcAlert).opacity(0.12))
        )
        .accessibilityLabel("Stress trend is \(isImproving ? "improving" : "elevated")")
    }

    private var stressBarChart: some View {
        let data = viewModel.stressTrend
        let labels = MockDataProvider.weekdayLabels

        return GeometryReader { geometry in
            HStack(alignment: .bottom, spacing: AppSpacing.sm) {
                ForEach(Array(zip(data.indices, data)), id: \.0) { index, value in
                    VStack(spacing: AppSpacing.xs) {
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .fill(barColor(for: value))
                            .frame(
                                width: (geometry.size.width - CGFloat(data.count - 1) * AppSpacing.sm) / CGFloat(data.count),
                                height: max(8, geometry.size.height * 0.75 * CGFloat(value))
                            )

                        Text(index < labels.count ? labels[index] : "")
                            .font(.system(size: 10, weight: .medium, design: .rounded))
                            .foregroundColor(.hcTextTertiary)
                    }
                }
            }
        }
    }

    private func barColor(for value: Double) -> Color {
        if value > 0.7 { return .hcAlert }
        if value > 0.5 { return .hcAmber }
        return .hcPrimary
    }

    private var stressTrendAccessibilityLabel: String {
        let labels = MockDataProvider.weekdayLabels
        let data = viewModel.stressTrend
        let descriptions = zip(labels, data).map { day, value in
            "\(day): \(Int(value * 100)) percent"
        }
        return "7-day stress trend. \(descriptions.joined(separator: ", "))"
    }

    // MARK: - Sleep Quality

    private var sleepQualitySection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Sleep Quality")
                .font(AppTypography.headline())
                .foregroundColor(.hcTextPrimary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)
                .accessibilityAddTraits(.isHeader)

            sleepChart
                .frame(height: 100)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(sleepAccessibilityLabel)

            // Summary stats
            HStack(spacing: AppSpacing.xl) {
                sleepStatItem(
                    label: "Average",
                    value: "\(Int(viewModel.sleepScores.reduce(0, +) / max(Double(viewModel.sleepScores.count), 1)))",
                    unit: "/100"
                )

                sleepStatItem(
                    label: "Best Night",
                    value: "\(Int(viewModel.sleepScores.max() ?? 0))",
                    unit: "/100"
                )

                sleepStatItem(
                    label: "Trend",
                    value: sleepTrendDirection,
                    unit: ""
                )
            }
        }
        .cardStyle()
    }

    private var sleepChart: some View {
        let data = viewModel.sleepScores
        let labels = MockDataProvider.weekdayLabels

        return GeometryReader { geometry in
            let minVal = (data.min() ?? 0) - 10
            let maxVal = (data.max() ?? 100) + 10
            let range = maxVal - minVal
            let stepWidth = geometry.size.width / CGFloat(max(data.count - 1, 1))

            ZStack {
                // Area fill
                Path { path in
                    for (index, value) in data.enumerated() {
                        let x = CGFloat(index) * stepWidth
                        let y = geometry.size.height * (1 - CGFloat((value - minVal) / range))

                        if index == 0 {
                            path.move(to: CGPoint(x: x, y: y))
                        } else {
                            path.addLine(to: CGPoint(x: x, y: y))
                        }
                    }
                    path.addLine(to: CGPoint(x: CGFloat(data.count - 1) * stepWidth, y: geometry.size.height))
                    path.addLine(to: CGPoint(x: 0, y: geometry.size.height))
                    path.closeSubpath()
                }
                .fill(
                    LinearGradient(
                        colors: [Color.hcCalm.opacity(0.3), Color.hcCalm.opacity(0.05)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )

                // Line
                Path { path in
                    for (index, value) in data.enumerated() {
                        let x = CGFloat(index) * stepWidth
                        let y = geometry.size.height * (1 - CGFloat((value - minVal) / range))

                        if index == 0 {
                            path.move(to: CGPoint(x: x, y: y))
                        } else {
                            path.addLine(to: CGPoint(x: x, y: y))
                        }
                    }
                }
                .stroke(Color.hcCalm, style: StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))

                // Day labels
                ForEach(Array(labels.enumerated()), id: \.offset) { index, label in
                    Text(label)
                        .font(.system(size: 10, weight: .medium, design: .rounded))
                        .foregroundColor(.hcTextTertiary)
                        .position(
                            x: CGFloat(index) * stepWidth,
                            y: geometry.size.height + 14
                        )
                }
            }
        }
        .padding(.bottom, AppSpacing.xl)
    }

    private func sleepStatItem(label: String, value: String, unit: String) -> some View {
        VStack(spacing: AppSpacing.xxs) {
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text(value)
                    .font(AppTypography.title3())
                    .foregroundColor(.hcCalm)

                Text(unit)
                    .font(AppTypography.caption())
                    .foregroundColor(.hcTextTertiary)
            }

            Text(label)
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
        }
        .frame(maxWidth: .infinity)
        .dynamicTypeSize(...DynamicTypeSize.accessibility1)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(label): \(value)\(unit)")
    }

    private var sleepTrendDirection: String {
        let scores = viewModel.sleepScores
        guard scores.count >= 2 else { return "--" }
        let recent = scores.suffix(3).reduce(0, +) / 3.0
        let earlier = scores.prefix(3).reduce(0, +) / 3.0
        if recent > earlier + 2 { return "Up" }
        if recent < earlier - 2 { return "Down" }
        return "Stable"
    }

    private var sleepAccessibilityLabel: String {
        let labels = MockDataProvider.weekdayLabels
        let data = viewModel.sleepScores
        let descriptions = zip(labels, data).map { day, value in
            "\(day): \(Int(value)) out of 100"
        }
        return "Sleep quality over 7 days. \(descriptions.joined(separator: ", "))"
    }

    // MARK: - Action Effectiveness

    private var actionEffectivenessSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Action Effectiveness")
                .font(AppTypography.headline())
                .foregroundColor(.hcTextPrimary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)
                .accessibilityAddTraits(.isHeader)

            Text("How well your recent actions worked")
                .font(AppTypography.footnote())
                .foregroundColor(.hcTextTertiary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)

            VStack(spacing: AppSpacing.md) {
                effectivenessRow(action: "Breathing Exercises", score: 0.88, count: 12)
                effectivenessRow(action: "Movement Breaks", score: 0.74, count: 8)
                effectivenessRow(action: "Hydration Reminders", score: 0.62, count: 15)
                effectivenessRow(action: "Rest Suggestions", score: 0.81, count: 6)
            }
        }
        .cardStyle()
    }

    private func effectivenessRow(action: String, score: Double, count: Int) -> some View {
        VStack(spacing: AppSpacing.sm) {
            HStack {
                Text(action)
                    .font(AppTypography.callout())
                    .foregroundColor(.hcTextPrimary)
                    .dynamicTypeSize(...DynamicTypeSize.accessibility1)

                Spacer()

                Text("\(Int(score * 100))%")
                    .font(AppTypography.callout())
                    .foregroundColor(effectivenessColor(score))
                    .dynamicTypeSize(...DynamicTypeSize.accessibility1)
            }

            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 3)
                        .fill(Color.hcTextTertiary.opacity(0.15))
                        .frame(height: 6)

                    RoundedRectangle(cornerRadius: 3)
                        .fill(effectivenessColor(score))
                        .frame(width: geometry.size.width * CGFloat(score), height: 6)
                }
            }
            .frame(height: 6)

            HStack {
                Text("\(count) times used")
                    .font(AppTypography.caption())
                    .foregroundColor(.hcTextTertiary)
                    .dynamicTypeSize(...DynamicTypeSize.accessibility1)

                Spacer()
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(action): \(Int(score * 100)) percent effective, used \(count) times")
    }

    private func effectivenessColor(_ score: Double) -> Color {
        if score >= 0.8 { return .hcPrimary }
        if score >= 0.6 { return .hcAmber }
        return .hcAlert
    }
}

#Preview {
    InsightsView()
        .environmentObject(HealthCoachViewModel())
        .environmentObject(FitbitService.shared)
}
