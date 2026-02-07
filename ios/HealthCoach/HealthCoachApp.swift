import SwiftUI

@main
struct HealthCoachApp: App {
    @StateObject private var viewModel = HealthCoachViewModel()
    @StateObject private var fitbitService = FitbitService.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
                .environmentObject(fitbitService)
                .preferredColorScheme(.dark)
        }
    }
}
