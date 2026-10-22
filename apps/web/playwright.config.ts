import { defineConfig, devices } from "@playwright/test";

/** E2E against a running stack: API :4000 (seeded) + web :3000 (`pnpm build && pnpm start`). */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    locale: "vi-VN",
    timezoneId: "Asia/Ho_Chi_Minh",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: process.env.E2E_NO_SERVER
    ? undefined
    : { command: "pnpm start", url: "http://localhost:3000/login", reuseExistingServer: true, timeout: 120_000 },
});
