import { defineConfig, devices } from "@playwright/test";
import { MOCK_LOGIN_PASSWORD, MOCK_PORT } from "./e2e/support/mock";

/**
 * Two projects (T-606, R-DEC-25):
 *  - `mock`: no backend — Playwright starts `next dev` with `API_MODE=mock` (BFF serves
 *    `src/mocks`, fixtures = seed_snapshot.json). Runs only tests tagged `@mock`; every PR.
 *  - `real`: the seeded stack — API :4000 + web :3000 (`pnpm build && pnpm start`, or the
 *    compose `web` service). Runs every test except `@mock-only`.
 * Only the web servers of the selected projects are started (`--project=mock|real`).
 */
const MOCK_URL = `http://localhost:${MOCK_PORT}`;
const REAL_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";

function selectedProjects(argv: readonly string[]): Set<string> {
  const out = new Set<string>();
  argv.forEach((a, i) => {
    if (a.startsWith("--project=")) out.add(a.slice("--project=".length));
    else if (a === "--project" && argv[i + 1]) out.add(argv[i + 1] as string);
  });
  return out.size ? out : new Set(["mock", "real"]);
}

const wanted = selectedProjects(process.argv);
const desktop = { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } };

const servers = [
  wanted.has("mock") && {
    // run next directly (not via pnpm exec) so Playwright stops the whole server on exit
    command: `node node_modules/next/dist/bin/next dev --port ${MOCK_PORT}`,
    url: `${MOCK_URL}/login`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: {
      API_MODE: "mock",
      DEMO_MODE: "true",
      MOCK_LOGIN_PASSWORD,
      NEXTAUTH_URL: MOCK_URL,
      NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET ?? "e2e-mock-only-nextauth-secret",
    },
  },
  wanted.has("real") && !process.env.E2E_NO_SERVER && {
    command: "pnpm start",
    url: `${REAL_URL}/login`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
].filter((s): s is Exclude<typeof s, false> => Boolean(s));

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { trace: "retain-on-failure", locale: "vi-VN", timezoneId: "Asia/Ho_Chi_Minh" },
  projects: [
    // first hit of each route compiles on demand under `next dev` → longer budget
    { name: "mock", grep: /@mock/, timeout: 120_000, use: { ...desktop, baseURL: MOCK_URL } },
    { name: "real", grepInvert: /@mock-only/, use: { ...desktop, baseURL: REAL_URL } },
  ],
  webServer: servers,
});
