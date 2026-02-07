import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var fitbitService: FitbitService

    @AppStorage("notificationsEnabled") private var notificationsEnabled: Bool = true
    @AppStorage("liveModeSensitivity") private var liveModeSensitivity: Double = 0.5

    var body: some View {
        NavigationStack {
            List {
                // Fitbit Connection
                fitbitSection

                // Notifications
                notificationsSection

                // Live Mode
                liveModeSection

                // About
                aboutSection
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
            .background(Color.hcBackground)
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(Color.hcBackground, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }

    // MARK: - Fitbit Section

    private var fitbitSection: some View {
        Section {
            HStack(spacing: AppSpacing.lg) {
                Image(systemName: "heart.circle.fill")
                    .font(.system(size: 28, weight: .medium))
                    .foregroundColor(fitbitService.isConnected ? .hcPrimary : .hcTextTertiary)
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: AppSpacing.xxs) {
                    Text("Fitbit")
                        .font(AppTypography.headline())
                        .foregroundColor(.hcTextPrimary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility2)

                    if fitbitService.isConnected {
                        if let lastSync = fitbitService.lastSyncDate {
                            Text("Last synced \(lastSync, style: .relative) ago")
                                .font(AppTypography.footnote())
                                .foregroundColor(.hcTextTertiary)
                                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                        }
                    } else {
                        Text("Not connected")
                            .font(AppTypography.footnote())
                            .foregroundColor(.hcTextTertiary)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                    }
                }

                Spacer()

                connectionButton
            }
            .listRowBackground(Color.hcSurface)
        } header: {
            Text("Wearable")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Fitbit connection: \(fitbitService.isConnected ? "Connected" : "Not connected")")
        .accessibilityHint(fitbitService.isConnected ? "Double tap to disconnect" : "Double tap to connect your Fitbit device")
    }

    private var connectionButton: some View {
        Button {
            if fitbitService.isConnected {
                fitbitService.disconnect()
            } else {
                // In production, this would trigger ASWebAuthenticationSession
                // For MVP, we simulate a connection
                fitbitService.isConnected = true
                fitbitService.lastSyncDate = Date()
            }
        } label: {
            Text(fitbitService.isConnected ? "Disconnect" : "Connect")
                .font(AppTypography.callout())
                .foregroundColor(fitbitService.isConnected ? .hcAlert : .hcPrimary)
                .padding(.horizontal, AppSpacing.md)
                .padding(.vertical, AppSpacing.sm)
                .background(
                    Capsule()
                        .fill((fitbitService.isConnected ? Color.hcAlert : Color.hcPrimary).opacity(0.12))
                )
        }
        .buttonStyle(PlainButtonStyle())
        .accessibilityLabel(fitbitService.isConnected ? "Disconnect Fitbit" : "Connect Fitbit")
    }

    // MARK: - Notifications Section

    private var notificationsSection: some View {
        Section {
            Toggle(isOn: $notificationsEnabled) {
                HStack(spacing: AppSpacing.md) {
                    Image(systemName: "bell.fill")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.hcAmber)
                        .frame(width: 28)
                        .accessibilityHidden(true)

                    VStack(alignment: .leading, spacing: AppSpacing.xxs) {
                        Text("Push Notifications")
                            .font(AppTypography.body())
                            .foregroundColor(.hcTextPrimary)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility2)

                        Text("Get notified about recommendations and insights")
                            .font(AppTypography.footnote())
                            .foregroundColor(.hcTextTertiary)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                    }
                }
            }
            .tint(.hcPrimary)
            .listRowBackground(Color.hcSurface)
            .accessibilityLabel("Push notifications")
            .accessibilityHint("Toggle to \(notificationsEnabled ? "disable" : "enable") push notifications for recommendations and insights")
            .accessibilityValue(notificationsEnabled ? "Enabled" : "Disabled")
        } header: {
            Text("Notifications")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
        }
    }

    // MARK: - Live Mode Section

    private var liveModeSection: some View {
        Section {
            VStack(alignment: .leading, spacing: AppSpacing.md) {
                HStack(spacing: AppSpacing.md) {
                    Image(systemName: "dial.medium.fill")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.hcPrimary)
                        .frame(width: 28)
                        .accessibilityHidden(true)

                    VStack(alignment: .leading, spacing: AppSpacing.xxs) {
                        Text("Detection Sensitivity")
                            .font(AppTypography.body())
                            .foregroundColor(.hcTextPrimary)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility2)

                        Text(sensitivityLabel)
                            .font(AppTypography.footnote())
                            .foregroundColor(.hcTextTertiary)
                            .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                    }
                }

                Slider(value: $liveModeSensitivity, in: 0...1, step: 0.1)
                    .tint(.hcPrimary)
                    .accessibilityLabel("Live mode sensitivity")
                    .accessibilityValue(sensitivityLabel)
                    .accessibilityHint("Adjust how sensitive the coach is to detecting state changes. Drag left for lower sensitivity, right for higher sensitivity.")

                HStack {
                    Text("Less sensitive")
                        .font(AppTypography.caption())
                        .foregroundColor(.hcTextTertiary)

                    Spacer()

                    Text("More sensitive")
                        .font(AppTypography.caption())
                        .foregroundColor(.hcTextTertiary)
                }
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
            }
            .listRowBackground(Color.hcSurface)
        } header: {
            Text("Live Mode")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
        } footer: {
            Text("Higher sensitivity means the coach will respond to smaller changes in your biometrics.")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
        }
    }

    private var sensitivityLabel: String {
        switch liveModeSensitivity {
        case 0..<0.3: return "Low - fewer, more confident alerts"
        case 0.3..<0.7: return "Medium - balanced detection"
        default: return "High - more responsive to changes"
        }
    }

    // MARK: - About Section

    private var aboutSection: some View {
        Section {
            aboutRow(title: "Version", value: "1.0.0 (MVP)")
            aboutRow(title: "Build", value: "2025.1")

            NavigationLink {
                privacyView
            } label: {
                HStack(spacing: AppSpacing.md) {
                    Image(systemName: "lock.shield.fill")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.hcCalm)
                        .frame(width: 28)
                        .accessibilityHidden(true)

                    Text("Privacy Policy")
                        .font(AppTypography.body())
                        .foregroundColor(.hcTextPrimary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility2)
                }
            }
            .listRowBackground(Color.hcSurface)
            .accessibilityLabel("Privacy Policy")
            .accessibilityHint("View the privacy policy")
        } header: {
            Text("About")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
        }
    }

    private func aboutRow(title: String, value: String) -> some View {
        HStack {
            Text(title)
                .font(AppTypography.body())
                .foregroundColor(.hcTextPrimary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)

            Spacer()

            Text(value)
                .font(AppTypography.subheadline())
                .foregroundColor(.hcTextTertiary)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
        }
        .listRowBackground(Color.hcSurface)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title): \(value)")
    }

    // MARK: - Privacy View

    private var privacyView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AppSpacing.xl) {
                Text("Privacy Policy")
                    .font(AppTypography.title())
                    .foregroundColor(.hcTextPrimary)
                    .dynamicTypeSize(...DynamicTypeSize.accessibility3)
                    .accessibilityAddTraits(.isHeader)

                Text("Health Coach is committed to protecting your privacy. All health data is processed locally on your device whenever possible. Data shared with our servers is encrypted in transit and at rest.\n\nYour biometric data from Fitbit is only accessed with your explicit consent and is used solely to provide personalized health coaching recommendations.\n\nYou can disconnect your wearable device and delete your data at any time from the Settings screen.")
                    .font(AppTypography.body())
                    .foregroundColor(.hcTextSecondary)
                    .lineSpacing(4)
                    .dynamicTypeSize(...DynamicTypeSize.accessibility2)
            }
            .padding(AppSpacing.xl)
        }
        .background(Color.hcBackground)
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(Color.hcBackground, for: .navigationBar)
        .toolbarColorScheme(.dark, for: .navigationBar)
    }
}

#Preview {
    SettingsView()
        .environmentObject(FitbitService.shared)
}
