import Foundation
import CryptoKit

// MARK: - Fitbit Service

@MainActor
final class FitbitService: ObservableObject {
    static let shared = FitbitService()

    // MARK: - Published State

    @Published var isConnected: Bool = false
    @Published var isAuthenticating: Bool = false
    @Published var lastSyncDate: Date?
    @Published var connectionError: String?

    // MARK: - OAuth2 PKCE Configuration

    private let clientId = "YOUR_FITBIT_CLIENT_ID"
    private let redirectURI = "healthcoach://fitbit/callback"
    private let authorizationEndpoint = URL(string: "https://www.fitbit.com/oauth2/authorize")!
    private let tokenEndpoint = URL(string: "https://api.fitbit.com/oauth2/token")!
    private let scopes = ["activity", "heartrate", "sleep", "profile"]

    private var accessToken: String?
    private var refreshToken: String?
    private var tokenExpiry: Date?
    private var codeVerifier: String?

    private let session = URLSession.shared

    // MARK: - OAuth2 PKCE Flow

    /// Generate the authorization URL for the OAuth2 PKCE flow.
    /// In a production app, this URL would be opened in ASWebAuthenticationSession.
    func generateAuthURL() -> URL? {
        let verifier = generateCodeVerifier()
        codeVerifier = verifier

        guard let challenge = generateCodeChallenge(from: verifier) else {
            return nil
        }

        var components = URLComponents(url: authorizationEndpoint, resolvingAgainstBaseURL: false)
        components?.queryItems = [
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "client_id", value: clientId),
            URLQueryItem(name: "redirect_uri", value: redirectURI),
            URLQueryItem(name: "scope", value: scopes.joined(separator: " ")),
            URLQueryItem(name: "code_challenge", value: challenge),
            URLQueryItem(name: "code_challenge_method", value: "S256")
        ]

        return components?.url
    }

    /// Handle the callback URL after authorization.
    func handleCallback(url: URL) async {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let code = components.queryItems?.first(where: { $0.name == "code" })?.value else {
            connectionError = "Invalid authorization callback."
            return
        }

        await exchangeCodeForToken(code: code)
    }

    /// Exchange the authorization code for access and refresh tokens.
    private func exchangeCodeForToken(code: String) async {
        guard let verifier = codeVerifier else {
            connectionError = "Missing code verifier."
            return
        }

        isAuthenticating = true

        var request = URLRequest(url: tokenEndpoint)
        request.httpMethod = "POST"
        request.addValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

        let bodyParams = [
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirectURI,
            "client_id": clientId,
            "code_verifier": verifier
        ]
        request.httpBody = bodyParams
            .map { "\($0.key)=\($0.value)" }
            .joined(separator: "&")
            .data(using: .utf8)

        do {
            let (data, _) = try await session.data(for: request)
            let tokenResponse = try JSONDecoder().decode(FitbitTokenResponse.self, from: data)

            accessToken = tokenResponse.accessToken
            refreshToken = tokenResponse.refreshToken
            tokenExpiry = Date().addingTimeInterval(TimeInterval(tokenResponse.expiresIn))
            isConnected = true
            lastSyncDate = Date()

            storeTokensInKeychain(access: tokenResponse.accessToken, refresh: tokenResponse.refreshToken)
        } catch {
            connectionError = "Failed to connect to Fitbit: \(error.localizedDescription)"
        }

        isAuthenticating = false
    }

    // MARK: - Data Fetching (Stubs)

    /// Fetch sleep data for a given date range.
    func fetchSleepData(startDate: Date, endDate: Date) async -> [SensorReading] {
        // Stub: return mock data
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"

        return (0..<7).map { dayOffset in
            SensorReading(
                type: .sleepScore,
                value: Double.random(in: 55...95),
                timestamp: Calendar.current.date(byAdding: .day, value: -dayOffset, to: Date()) ?? Date()
            )
        }
    }

    /// Fetch step count for today.
    func fetchSteps(date: Date = Date()) async -> SensorReading? {
        // Stub: return mock data
        return SensorReading(
            type: .steps,
            value: Double(Int.random(in: 3000...12000)),
            timestamp: date
        )
    }

    /// Fetch heart rate data for a given date.
    func fetchHeartRate(date: Date = Date()) async -> [SensorReading] {
        // Stub: return mock data
        return MockDataProvider.sampleHeartRateReadings(count: 20)
    }

    /// Fetch intraday heart rate for live mode.
    func fetchIntradayHeartRate(since: Date) async -> [SensorReading] {
        // Stub: return mock data
        return MockDataProvider.sampleHeartRateReadings(count: 5)
    }

    // MARK: - Token Management (Keychain Stubs)

    /// Store tokens securely in Keychain.
    /// In production, use Security framework's SecItemAdd.
    private func storeTokensInKeychain(access: String, refresh: String) {
        // Stub: In production, store using SecItemAdd
        // let query: [String: Any] = [
        //     kSecClass as String: kSecClassGenericPassword,
        //     kSecAttrAccount as String: "fitbit_access_token",
        //     kSecValueData as String: access.data(using: .utf8)!
        // ]
        // SecItemAdd(query as CFDictionary, nil)
    }

    /// Retrieve tokens from Keychain.
    func loadTokensFromKeychain() -> Bool {
        // Stub: In production, use SecItemCopyMatching
        return false
    }

    /// Remove tokens from Keychain on disconnect.
    func disconnect() {
        accessToken = nil
        refreshToken = nil
        tokenExpiry = nil
        isConnected = false
        lastSyncDate = nil
        // Stub: In production, use SecItemDelete
    }

    // MARK: - PKCE Helpers

    private func generateCodeVerifier() -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return Data(bytes)
            .base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    private func generateCodeChallenge(from verifier: String) -> String? {
        guard let data = verifier.data(using: .utf8) else { return nil }
        let hash = SHA256.hash(data: data)
        return Data(hash)
            .base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

// MARK: - Token Response

private struct FitbitTokenResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    let expiresIn: Int
    let tokenType: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
        case tokenType = "token_type"
    }
}
