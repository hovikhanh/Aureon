/**
 * Project `mock` (T-606): fixed login password accepted by the in-process mock (`MOCK_LOGIN_PASSWORD`).
 * Not a secret — the mock never reaches the API and `API_MODE=mock` is refused in production.
 */
export const MOCK_LOGIN_PASSWORD = "mock-demo-pass";
export const MOCK_PORT = Number(process.env.E2E_MOCK_PORT ?? 3100);
