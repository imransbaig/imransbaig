import Foundation

// MARK: - User State

enum UserState: String, Codable, CaseIterable, Identifiable {
    case stressed
    case calm
    case fatigued
    case energized
    case sleepDeprived

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .stressed: return "Stressed"
        case .calm: return "Calm"
        case .fatigued: return "Fatigued"
        case .energized: return "Energized"
        case .sleepDeprived: return "Sleep Deprived"
        }
    }

    var emoji: String {
        switch self {
        case .stressed: return "😰"
        case .calm: return "😌"
        case .fatigued: return "😴"
        case .energized: return "⚡"
        case .sleepDeprived: return "🥱"
        }
    }
}

// MARK: - Sensor Reading

struct SensorReading: Codable, Identifiable {
    let id: UUID
    let type: SensorType
    let value: Double
    let timestamp: Date

    init(id: UUID = UUID(), type: SensorType, value: Double, timestamp: Date = Date()) {
        self.id = id
        self.type = type
        self.value = value
        self.timestamp = timestamp
    }
}

enum SensorType: String, Codable {
    case heartRate
    case hrv
    case skinTemperature
    case steps
    case sleepScore
    case bloodOxygen
}

// MARK: - Next Best Action

struct NextBestAction: Codable, Identifiable {
    let id: UUID
    let title: String
    let subtitle: String
    let actionType: ActionType
    let reasonTrace: ReasonTrace
    let confidence: Double

    init(
        id: UUID = UUID(),
        title: String,
        subtitle: String,
        actionType: ActionType,
        reasonTrace: ReasonTrace,
        confidence: Double = 0.85
    ) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.actionType = actionType
        self.reasonTrace = reasonTrace
        self.confidence = confidence
    }
}

enum ActionType: String, Codable {
    case breathingExercise
    case movement
    case hydration
    case rest
    case social
    case nutrition
    case sleep

    var iconName: String {
        switch self {
        case .breathingExercise: return "wind"
        case .movement: return "figure.walk"
        case .hydration: return "drop.fill"
        case .rest: return "bed.double.fill"
        case .social: return "person.2.fill"
        case .nutrition: return "leaf.fill"
        case .sleep: return "moon.fill"
        }
    }
}

// MARK: - Reason Trace

struct ReasonTrace: Codable, Identifiable {
    let traceId: UUID
    let timestamp: Date
    let trigger: String
    let signals: [String]
    let inference: String
    let action: String
    let explanation: String
    let confidence: Double

    var id: UUID { traceId }

    init(
        traceId: UUID = UUID(),
        timestamp: Date = Date(),
        trigger: String,
        signals: [String],
        inference: String,
        action: String,
        explanation: String,
        confidence: Double
    ) {
        self.traceId = traceId
        self.timestamp = timestamp
        self.trigger = trigger
        self.signals = signals
        self.inference = inference
        self.action = action
        self.explanation = explanation
        self.confidence = confidence
    }
}

// MARK: - Cue Type

enum CueType: String, Codable, CaseIterable, Identifiable {
    case stress
    case pain
    case moodLow
    case moodHigh
    case custom

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .stress: return "Stress"
        case .pain: return "Pain"
        case .moodLow: return "Low Mood"
        case .moodHigh: return "High Mood"
        case .custom: return "Custom"
        }
    }

    var iconName: String {
        switch self {
        case .stress: return "bolt.heart.fill"
        case .pain: return "bandage.fill"
        case .moodLow: return "cloud.rain.fill"
        case .moodHigh: return "sun.max.fill"
        case .custom: return "pencil.circle.fill"
        }
    }
}

// MARK: - Cue Entry

struct CueEntry: Codable, Identifiable {
    let id: UUID
    let type: CueType
    let note: String?
    let timestamp: Date

    init(id: UUID = UUID(), type: CueType, note: String? = nil, timestamp: Date = Date()) {
        self.id = id
        self.type = type
        self.note = note
        self.timestamp = timestamp
    }
}

// MARK: - Live Session

struct LiveSession: Codable, Identifiable {
    let id: UUID
    let startTime: Date
    var endTime: Date?
    var readings: [SensorReading]
    var interventions: [String]
    var currentState: UserState

    var duration: TimeInterval {
        let end = endTime ?? Date()
        return end.timeIntervalSince(startTime)
    }

    var isActive: Bool {
        endTime == nil
    }

    init(
        id: UUID = UUID(),
        startTime: Date = Date(),
        endTime: Date? = nil,
        readings: [SensorReading] = [],
        interventions: [String] = [],
        currentState: UserState = .calm
    ) {
        self.id = id
        self.startTime = startTime
        self.endTime = endTime
        self.readings = readings
        self.interventions = interventions
        self.currentState = currentState
    }
}

// MARK: - Feedback

struct ActionFeedback: Codable {
    let actionId: UUID
    let wasHelpful: Bool
    let timestamp: Date

    init(actionId: UUID, wasHelpful: Bool, timestamp: Date = Date()) {
        self.actionId = actionId
        self.wasHelpful = wasHelpful
        self.timestamp = timestamp
    }
}

// MARK: - Mock Data Provider

struct MockDataProvider {
    static func sampleReasonTrace() -> ReasonTrace {
        ReasonTrace(
            trigger: "Elevated resting heart rate detected",
            signals: [
                "Heart rate: 82 bpm (above your baseline of 68)",
                "HRV: 35ms (below your average of 52ms)",
                "Sleep score last night: 62/100",
                "No movement logged in 3 hours"
            ],
            inference: "Your body appears to be in a stress response, likely compounded by reduced sleep quality last night.",
            action: "A 2-minute breathing exercise can activate your parasympathetic nervous system and help restore balance.",
            explanation: "Your heart rate is higher than usual and your body's recovery signals are lower, which often happens after a tough night of sleep. A short breathing exercise is the quickest way to help your body reset.",
            confidence: 0.87
        )
    }

    static func sampleNextAction() -> NextBestAction {
        NextBestAction(
            title: "Take a Breathing Break",
            subtitle: "Your stress signals are elevated. A 2-minute reset can help.",
            actionType: .breathingExercise,
            reasonTrace: sampleReasonTrace(),
            confidence: 0.87
        )
    }

    static func sampleCues() -> [CueEntry] {
        [
            CueEntry(type: .stress, note: "Tight deadline at work", timestamp: Date().addingTimeInterval(-3600)),
            CueEntry(type: .moodLow, note: nil, timestamp: Date().addingTimeInterval(-7200)),
            CueEntry(type: .pain, note: "Headache after lunch", timestamp: Date().addingTimeInterval(-14400))
        ]
    }

    static func sampleHeartRateReadings(count: Int = 30) -> [SensorReading] {
        (0..<count).map { index in
            SensorReading(
                type: .heartRate,
                value: Double.random(in: 65...95),
                timestamp: Date().addingTimeInterval(-Double(count - index) * 10)
            )
        }
    }

    static func sampleStressTrend() -> [Double] {
        [0.6, 0.72, 0.55, 0.48, 0.63, 0.41, 0.38]
    }

    static func sampleSleepScores() -> [Double] {
        [72, 68, 81, 75, 62, 85, 78]
    }

    static var weekdayLabels: [String] {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEE"
        return (-6...0).map { offset in
            let date = Calendar.current.date(byAdding: .day, value: offset, to: Date())!
            return formatter.string(from: date)
        }
    }
}
