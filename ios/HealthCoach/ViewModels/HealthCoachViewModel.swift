import Foundation
import Combine
import SwiftUI

// MARK: - Health Coach View Model

@MainActor
final class HealthCoachViewModel: ObservableObject {

    // MARK: - Published Properties

    @Published var currentState: UserState = .calm
    @Published var nextAction: NextBestAction? = nil
    @Published var recentCues: [CueEntry] = []
    @Published var isLiveMode: Bool = false
    @Published var liveSession: LiveSession? = nil
    @Published var heartRateReadings: [SensorReading] = []
    @Published var currentHeartRate: Double = 72.0
    @Published var sessionElapsed: TimeInterval = 0
    @Published var stressTrend: [Double] = []
    @Published var sleepScores: [Double] = []
    @Published var isLoading: Bool = false
    @Published var feedbackSubmitted: Bool = false

    // MARK: - Private Properties

    private let apiClient = APIClient.shared
    private var livePollingTimer: Timer?
    private var sessionTimer: Timer?
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Initialization

    init() {
        loadMockData()
    }

    // MARK: - Data Loading

    func fetchState() async {
        isLoading = true
        let state = await apiClient.fetchCurrentState()
        currentState = state
        isLoading = false
    }

    func fetchNextAction() async {
        let action = await apiClient.fetchNextAction()
        nextAction = action
    }

    func fetchRecentCues() async {
        let cues = await apiClient.fetchRecentCues()
        recentCues = cues
    }

    func fetchInsights() async {
        async let trend = apiClient.fetchStressTrend()
        async let sleep = apiClient.fetchSleepScores()
        stressTrend = await trend
        sleepScores = await sleep
    }

    func refreshAll() async {
        isLoading = true
        async let _ = fetchState()
        async let _ = fetchNextAction()
        async let _ = fetchRecentCues()
        async let _ = fetchInsights()
        isLoading = false
    }

    // MARK: - Cue Logging

    func logCue(type: CueType, note: String?) {
        let entry = CueEntry(type: type, note: note?.isEmpty == true ? nil : note)
        recentCues.insert(entry, at: 0)

        Task {
            _ = await apiClient.logCue(entry: entry)
            // Refresh next action after logging a cue, as it may change recommendations
            await fetchNextAction()
        }
    }

    // MARK: - Live Mode

    func startLiveMode() {
        guard !isLiveMode else { return }

        isLiveMode = true
        let session = LiveSession(currentState: currentState)
        liveSession = session
        sessionElapsed = 0
        heartRateReadings = MockDataProvider.sampleHeartRateReadings(count: 10)
        currentHeartRate = heartRateReadings.last?.value ?? 72.0

        startSessionTimer()
        startLivePolling()

        Task {
            _ = await apiClient.startLiveSession()
        }
    }

    func endLiveMode() {
        isLiveMode = false
        stopSessionTimer()
        stopLivePolling()

        if let session = liveSession {
            Task {
                _ = await apiClient.endLiveSession(sessionId: session.id)
            }
        }

        liveSession = nil
    }

    // MARK: - Feedback

    func submitFeedback(actionId: UUID, wasHelpful: Bool) {
        let feedback = ActionFeedback(actionId: actionId, wasHelpful: wasHelpful)
        feedbackSubmitted = true

        Task {
            _ = await apiClient.submitFeedback(feedback)
            // Reset feedback state after a delay
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            feedbackSubmitted = false
        }
    }

    // MARK: - Greeting

    var greetingText: String {
        let hour = Calendar.current.component(.hour, from: Date())
        switch hour {
        case 5..<12:
            return "Good morning"
        case 12..<17:
            return "Good afternoon"
        case 17..<21:
            return "Good evening"
        default:
            return "Good night"
        }
    }

    var greetingSubtext: String {
        switch currentState {
        case .stressed:
            return "Let's find some calm together."
        case .calm:
            return "You're in a great place right now."
        case .fatigued:
            return "Your body could use some rest."
        case .energized:
            return "Great energy! Let's make the most of it."
        case .sleepDeprived:
            return "Rest is important. Let's take it easy today."
        }
    }

    // MARK: - Session Timer Formatting

    var formattedSessionTime: String {
        let minutes = Int(sessionElapsed) / 60
        let seconds = Int(sessionElapsed) % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    // MARK: - Private Methods

    private func loadMockData() {
        currentState = .stressed
        nextAction = MockDataProvider.sampleNextAction()
        recentCues = MockDataProvider.sampleCues()
        stressTrend = MockDataProvider.sampleStressTrend()
        sleepScores = MockDataProvider.sampleSleepScores()
        heartRateReadings = MockDataProvider.sampleHeartRateReadings()
        currentHeartRate = heartRateReadings.last?.value ?? 72.0
    }

    private func startSessionTimer() {
        sessionTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.sessionElapsed += 1.0
            }
        }
    }

    private func stopSessionTimer() {
        sessionTimer?.invalidate()
        sessionTimer = nil
    }

    private func startLivePolling() {
        livePollingTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.simulateLiveReading()
            }
        }
    }

    private func stopLivePolling() {
        livePollingTimer?.invalidate()
        livePollingTimer = nil
    }

    private func simulateLiveReading() {
        // Generate a realistic heart rate value that trends around the current value
        let delta = Double.random(in: -3...3)
        let newHR = max(55, min(120, currentHeartRate + delta))
        currentHeartRate = newHR

        let reading = SensorReading(type: .heartRate, value: newHR)
        heartRateReadings.append(reading)

        // Keep only last 60 readings
        if heartRateReadings.count > 60 {
            heartRateReadings.removeFirst()
        }

        // Update state based on heart rate
        if newHR > 90 {
            currentState = .stressed
        } else if newHR > 80 {
            currentState = .energized
        } else if newHR < 60 {
            currentState = .fatigued
        } else {
            currentState = .calm
        }

        liveSession?.currentState = currentState
        liveSession?.readings.append(reading)
    }
}
