import XCTest
@testable import HealthCoach

/// Tests for HealthCoach data models and view model logic.
final class HealthCoachTests: XCTestCase {

    // MARK: - Model Tests

    func testReasonTraceDecoding() throws {
        let json = """
        {
            "traceId": "abc-123",
            "timestamp": "2024-03-15T14:00:00Z",
            "trigger": "elevated_hr_sedentary",
            "signals": {"heart_rate_bpm": 92, "activity_level": "sedentary"},
            "inference": "stress_likely",
            "action": "breathing_exercise_2min",
            "explanation": "Your heart rate was elevated while sedentary; a 2-minute reset usually helps.",
            "confidence": 0.78
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let trace = try decoder.decode(ReasonTrace.self, from: json)

        XCTAssertEqual(trace.traceId, "abc-123")
        XCTAssertEqual(trace.trigger, "elevated_hr_sedentary")
        XCTAssertEqual(trace.action, "breathing_exercise_2min")
        XCTAssertEqual(trace.confidence, 0.78, accuracy: 0.01)
        XCTAssertTrue(trace.explanation.contains("heart rate"))
    }

    func testUserStateRawValues() {
        XCTAssertEqual(UserState.stressed.rawValue, "stressed")
        XCTAssertEqual(UserState.calm.rawValue, "calm")
        XCTAssertEqual(UserState.fatigued.rawValue, "fatigued")
        XCTAssertEqual(UserState.energized.rawValue, "energized")
        XCTAssertEqual(UserState.sleepDeprived.rawValue, "sleep_deprived")
    }

    func testCueTypeValues() {
        XCTAssertEqual(CueType.allCases.count, 5)
        XCTAssertTrue(CueType.allCases.contains(.stress))
        XCTAssertTrue(CueType.allCases.contains(.custom))
    }

    func testNextBestActionInit() {
        let trace = ReasonTrace(
            traceId: "test-1",
            timestamp: "2024-03-15T14:00:00Z",
            trigger: "test",
            signals: ["hr": 90],
            inference: "stressed",
            action: "breathe",
            explanation: "Test explanation",
            confidence: 0.7
        )
        let action = NextBestAction(
            id: "action-1",
            title: "Take a Breath",
            subtitle: "2-minute guided breathing",
            actionType: "breathing_exercise_2min",
            reasonTrace: trace
        )
        XCTAssertEqual(action.title, "Take a Breath")
        XCTAssertEqual(action.reasonTrace.confidence, 0.7, accuracy: 0.01)
    }

    // MARK: - ViewModel Tests

    func testViewModelInitialState() {
        let vm = HealthCoachViewModel()
        XCTAssertFalse(vm.isLiveMode)
        XCTAssertNotNil(vm.currentState)
    }

    func testViewModelStartLiveMode() {
        let vm = HealthCoachViewModel()
        vm.startLiveMode()
        XCTAssertTrue(vm.isLiveMode)
    }

    func testViewModelEndLiveMode() {
        let vm = HealthCoachViewModel()
        vm.startLiveMode()
        vm.endLiveMode()
        XCTAssertFalse(vm.isLiveMode)
    }

    func testViewModelLogCue() {
        let vm = HealthCoachViewModel()
        let initialCount = vm.recentCues.count
        vm.logCue(type: .stress, note: "Test stress cue")
        XCTAssertEqual(vm.recentCues.count, initialCount + 1)
        XCTAssertEqual(vm.recentCues.last?.cueType, .stress)
    }

    // MARK: - State Color Tests

    func testUserStateColors() {
        // Verify each state has a distinct display name
        let states = UserState.allCases
        let names = Set(states.map { $0.displayName })
        XCTAssertEqual(names.count, states.count, "Each state should have a unique display name")
    }
}
