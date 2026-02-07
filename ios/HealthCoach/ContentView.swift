import SwiftUI

struct ContentView: View {
    @EnvironmentObject var viewModel: HealthCoachViewModel
    @State private var selectedTab: Tab = .today

    enum Tab: String, CaseIterable {
        case today = "Today"
        case liveMode = "Live Mode"
        case insights = "Insights"
        case settings = "Settings"

        var iconName: String {
            switch self {
            case .today: return "sun.max.fill"
            case .liveMode: return "waveform.path.ecg"
            case .insights: return "chart.bar.fill"
            case .settings: return "gearshape.fill"
            }
        }
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            TodayView()
                .tabItem {
                    Label(Tab.today.rawValue, systemImage: Tab.today.iconName)
                }
                .tag(Tab.today)
                .accessibilityLabel("Today tab")
                .accessibilityHint("View your daily health summary and recommended actions")

            LiveModeView()
                .tabItem {
                    Label(Tab.liveMode.rawValue, systemImage: Tab.liveMode.iconName)
                }
                .tag(Tab.liveMode)
                .accessibilityLabel("Live Mode tab")
                .accessibilityHint("Start a real-time coaching session")

            InsightsView()
                .tabItem {
                    Label(Tab.insights.rawValue, systemImage: Tab.insights.iconName)
                }
                .tag(Tab.insights)
                .accessibilityLabel("Insights tab")
                .accessibilityHint("View your health trends and patterns")

            SettingsView()
                .tabItem {
                    Label(Tab.settings.rawValue, systemImage: Tab.settings.iconName)
                }
                .tag(Tab.settings)
                .accessibilityLabel("Settings tab")
                .accessibilityHint("Configure app preferences and connections")
        }
        .tint(.hcPrimary)
        .onAppear {
            configureTabBarAppearance()
        }
    }

    private func configureTabBarAppearance() {
        let appearance = UITabBarAppearance()
        appearance.configureWithOpaqueBackground()
        appearance.backgroundColor = UIColor(Color.hcBackground)

        let itemAppearance = UITabBarItemAppearance()
        itemAppearance.normal.iconColor = UIColor(Color.hcTextTertiary)
        itemAppearance.normal.titleTextAttributes = [.foregroundColor: UIColor(Color.hcTextTertiary)]
        itemAppearance.selected.iconColor = UIColor(Color.hcPrimary)
        itemAppearance.selected.titleTextAttributes = [.foregroundColor: UIColor(Color.hcPrimary)]

        appearance.stackedLayoutAppearance = itemAppearance
        appearance.inlineLayoutAppearance = itemAppearance
        appearance.compactInlineLayoutAppearance = itemAppearance

        UITabBar.appearance().standardAppearance = appearance
        UITabBar.appearance().scrollEdgeAppearance = appearance
    }
}

#Preview {
    ContentView()
        .environmentObject(HealthCoachViewModel())
        .environmentObject(FitbitService.shared)
}
