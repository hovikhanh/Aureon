// @vitest-environment node
/**
 * 06 §6.2/§6.3 + CLAUDE.md: the AI color token must differ from `--primary`.
 * Parses the real stylesheet so a token edit that collapses them fails CI.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const css = readFileSync(fileURLToPath(new URL("./globals.css", import.meta.url)), "utf8");

function rootTokens(source: string): Map<string, string> {
  const withoutComments = source.replace(/\/\*[\s\S]*?\*\//g, "");
  const root = /:root\s*\{([^}]*)\}/.exec(withoutComments);
  if (!root) throw new Error(":root block not found in globals.css");
  const tokens = new Map<string, string>();
  for (const match of root[1].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    tokens.set(match[1], match[2].trim().toLowerCase());
  }
  return tokens;
}

/** Follow `var(--x)` references inside :root to a concrete value. */
function resolve(tokens: Map<string, string>, name: string, depth = 0): string {
  const value = tokens.get(name);
  if (value === undefined) throw new Error(`token ${name} is not defined`);
  const ref = /^var\((--[\w-]+)\)$/.exec(value);
  if (ref && depth < 10) return resolve(tokens, ref[1], depth + 1);
  return value;
}

describe("design tokens (06 §6)", () => {
  const tokens = rootTokens(css);

  it("defines every §6.2 color token", () => {
    for (const name of ["--primary", "--ai", "--ai-muted", "--status-ok", "--status-warn", "--status-critical", "--neutral-500"]) {
      expect(tokens.has(name), name).toBe(true);
    }
  });

  it("--ai differs from --primary (and their muted/foreground pairs are not reused)", () => {
    expect(resolve(tokens, "--ai")).not.toBe(resolve(tokens, "--primary"));
    expect(resolve(tokens, "--ai-muted")).not.toBe(resolve(tokens, "--primary"));
    expect(tokens.get("--ai")).not.toMatch(/var\(--primary/);
  });

  it("AI color is not one of the metric status colors (§6.2)", () => {
    const ai = resolve(tokens, "--ai");
    for (const status of ["--status-ok", "--status-warn", "--status-critical"]) {
      expect(ai).not.toBe(resolve(tokens, status));
    }
  });

  it("exposes Tailwind color utilities for primary and ai", () => {
    expect(css).toMatch(/--color-primary:\s*var\(--primary\)/);
    expect(css).toMatch(/--color-ai:\s*var\(--ai\)/);
  });
});
