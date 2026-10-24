import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import TestProject

private let serverURL = URL(string: "http://127.0.0.1")!

private actor TokenStore {
    var calls = 0
    func token() -> String {
        calls += 1
        return "token-\(calls)"
    }
}

struct AuthenticationBehaviorTests {
    private func intercept(
        _ authentication: Authentication,
        operationID: String,
        authorization: String? = nil,
        apiKey: String? = nil
    ) async throws {
        let middleware = AuthenticationMiddleware(authentication: authentication)
        _ = try await middleware.intercept(
            HTTPRequest(method: .get, scheme: "http", authority: "127.0.0.1", path: "/"),
            body: nil,
            baseURL: serverURL,
            operationID: operationID
        ) { request, body, url in
            #expect(request.headerFields[.authorization] == authorization)
            #expect(request.headerFields[HTTPField.Name("x-api-key")!] == apiKey)
            #expect(body == nil)
            #expect(url == serverURL)
            return (HTTPResponse(status: .ok), nil)
        }
    }

    @Test func credentialsFollowOperationRequirements() async throws {
        try await intercept(.bearer("token"), operationID: "bearer", authorization: "Bearer token")
        try await intercept(.bearer("token"), operationID: "publicEndpoint")
        try await intercept(.bearer("token"), operationID: "get/publicWithoutID")
        try await intercept(.apiKey("key"), operationID: "key", apiKey: "key")
        try await intercept(.apiKey("key"), operationID: "alternative", apiKey: "key")
        try await intercept(.none, operationID: "optionalAuth")
        try await intercept(
            .credentials(["BearerAuth": .init("token"), "Key": .init("key")]),
            operationID: "combined", authorization: "Bearer token", apiKey: "key"
        )
    }

    @Test func missingCredentialsAndUnsupportedSchemesFailBeforeSending() async throws {
        for (operation, authentication) in [
            ("bearer", Authentication.none),
            ("combined", .bearer("token")),
            ("unsupported", .credentials(["OAuth": .init("not-supported")])),
        ] {
            do {
                try await intercept(authentication, operationID: operation)
                Issue.record("Expected an authentication error")
            } catch AuthenticationError.unsatisfiedSecurityRequirements(let operationID) {
                #expect(operationID == operation)
            }
        }
    }

    @Test func tokenProviderRunsPerAuthenticatedRequest() async throws {
        let store = TokenStore()
        let authentication = Authentication.bearer { await store.token() }
        try await intercept(authentication, operationID: "publicEndpoint")
        try await intercept(authentication, operationID: "bearer", authorization: "Bearer token-1")
        try await intercept(authentication, operationID: "bearer", authorization: "Bearer token-2")
        #expect(await store.calls == 2)
    }

    @Test func providerErrorsPropagate() async throws {
        enum TokenError: Error { case unavailable }
        do {
            try await intercept(.bearer { throw TokenError.unavailable }, operationID: "bearer")
            Issue.record("Expected token provider error")
        } catch TokenError.unavailable {}
    }
}
