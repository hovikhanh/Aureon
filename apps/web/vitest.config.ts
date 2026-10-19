import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
    testTimeout: 15000,
    // Bound worker parallelism: with 26 jsdom suites the default fork count starves the
    // event loop on constrained CI/dev machines, making fireEvent/waitFor timing flaky
    // (random unrelated tests fail ~1/4 runs). Capping forks keeps the suite deterministic.
    pool: "forks",
    poolOptions: { forks: { minForks: 1, maxForks: 2 } },
  },
});
