import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const configDir = dirname(fileURLToPath(import.meta.url));

/**
 * Load the repo-root .env into process.env before the tests run, so `pnpm test:e2e` is
 * reproducible without a manual `set -a; source .env; set +a`. Pure Node fs (no new
 * dependency). Existing process.env values win, so CI / shell overrides still take priority.
 * The E2E login helper needs DEMO_*_PASSWORD; app URLs come from E2E_BASE_URL / API_URL.
 */
function loadRootEnv(): void {
  // apps/web/playwright.config.ts → repo root is two levels up.
  const envPath = resolve(configDir, "../../.env");
  let raw: string;
  try {
    raw = readFileSync(envPath, "utf8");
  } catch {
    // No .env (e.g. CI injects env directly) — nothing to load.
    return;
  }
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    if (!key || key in process.env) continue;
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    process.env[key] = value;
  }
}

loadRootEnv();

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  // The suite shares backend DB state and EP-02 login is rate-limited per (email, IP);
  // a single worker keeps runs deterministic.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
