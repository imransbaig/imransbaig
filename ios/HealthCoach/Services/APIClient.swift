import Foundation

// MARK: - API Client

actor APIClient {
    static let shared = APIClient()

    private var baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(baseURL: URL = URL(string: "http://localhost:8000/api/v1")!) {
        self.baseURL = baseURL

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 15
        config.timeoutIntervalForResource = 30
        self.session = URLSession(configuration: config)

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601

        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
    }

    // MARK: - Configuration

    func updateBaseURL(_ url: URL) {
        self.baseURL = url
    }

    // MARK: - State Endpoints

    func fetchCurrentState(userId: String = "default") async -> UserState {
        do {
            let state: UserState = try await get(path: "/users/\(userId)/state")
            return state
        } catch {
            return MockDataProvider.sampleNextAction().reasonTrace.confidence > 0.5 ? .stressed : .calm
        }
    }

    func fetchNextAction(userId: String = "default") async -> NextBestAction {
        do {
            let action: NextBestAction = try await get(path: "/users/\(userId)/next-action")
            return action
        } catch {
            return MockDataProvider.sampleNextAction()
        }
    }

    // MARK: - Cue Endpoints

    func logCue(entry: CueEntry, userId: String = "default") async -> Bool {
        do {
            let _: CueEntry = try await post(path: "/users/\(userId)/cues", body: entry)
            return true
        } catch {
            return false
        }
    }

    func fetchRecentCues(userId: String = "default") async -> [CueEntry] {
        do {
            let cues: [CueEntry] = try await get(path: "/users/\(userId)/cues")
            return cues
        } catch {
            return MockDataProvider.sampleCues()
        }
    }

    // MARK: - Live Mode Endpoints

    func startLiveSession(userId: String = "default") async -> LiveSession? {
        do {
            let session: LiveSession = try await post(path: "/users/\(userId)/live/start", body: EmptyBody())
            return session
        } catch {
            return LiveSession()
        }
    }

    func endLiveSession(sessionId: UUID, userId: String = "default") async -> LiveSession? {
        do {
            let session: LiveSession = try await post(
                path: "/users/\(userId)/live/\(sessionId.uuidString)/end",
                body: EmptyBody()
            )
            return session
        } catch {
            return nil
        }
    }

    func fetchLiveReadings(sessionId: UUID, userId: String = "default") async -> [SensorReading] {
        do {
            let readings: [SensorReading] = try await get(
                path: "/users/\(userId)/live/\(sessionId.uuidString)/readings"
            )
            return readings
        } catch {
            return MockDataProvider.sampleHeartRateReadings(count: 5)
        }
    }

    // MARK: - Feedback

    func submitFeedback(_ feedback: ActionFeedback, userId: String = "default") async -> Bool {
        do {
            let _: ActionFeedback = try await post(path: "/users/\(userId)/feedback", body: feedback)
            return true
        } catch {
            return false
        }
    }

    // MARK: - Insights

    func fetchStressTrend(userId: String = "default", days: Int = 7) async -> [Double] {
        do {
            let trend: [Double] = try await get(path: "/users/\(userId)/insights/stress?days=\(days)")
            return trend
        } catch {
            return MockDataProvider.sampleStressTrend()
        }
    }

    func fetchSleepScores(userId: String = "default", days: Int = 7) async -> [Double] {
        do {
            let scores: [Double] = try await get(path: "/users/\(userId)/insights/sleep?days=\(days)")
            return scores
        } catch {
            return MockDataProvider.sampleSleepScores()
        }
    }

    // MARK: - Generic Network Methods

    private func get<T: Decodable>(path: String) async throws -> T {
        let url = baseURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.addValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await session.data(for: request)
        try validateResponse(response)
        return try decoder.decode(T.self, from: data)
    }

    private func post<T: Decodable, B: Encodable>(path: String, body: B) async throws -> T {
        let url = baseURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.addValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = try encoder.encode(body)

        let (data, response) = try await session.data(for: request)
        try validateResponse(response)
        return try decoder.decode(T.self, from: data)
    }

    private func validateResponse(_ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(statusCode: httpResponse.statusCode)
        }
    }
}

// MARK: - Supporting Types

private struct EmptyBody: Encodable {}

enum APIError: LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int)
    case decodingError(Error)
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid server response."
        case .httpError(let code):
            return "Server returned error code \(code)."
        case .decodingError(let error):
            return "Failed to parse response: \(error.localizedDescription)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}
