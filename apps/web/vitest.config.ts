import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
    // T-1021 / R-DEC-150 — 14 §1.3 asks for measured FE coverage of `features/` + `lib/`.
    // Unit tests cover the pure logic modules (`*.ts`); React components (`*.tsx`) are covered
    // by Playwright (e2e/), which this provider cannot see, so they are excluded here instead
    // of dragging the number down and making the threshold meaningless.
    coverage: {
      provider: "v8",
      reporter: ["text-summary", "json-summary", "lcov"],
      reportsDirectory: "../../var/coverage/web",
      include: ["src/features/**/*.ts", "src/lib/**/*.ts"],
      exclude: [
        "**/*.test.ts",
        "**/*.d.ts",
        "src/**/mocks/**",
        // TanStack Query hooks: thin `useQuery`/`useMutation` wrappers that need a React
        // renderer, exercised end-to-end by Playwright (e2e/) instead of here.
        "src/**/use-*.ts",
      ],
      thresholds: { lines: 70, functions: 70, statements: 70, branches: 70 },
    },
  },
});
