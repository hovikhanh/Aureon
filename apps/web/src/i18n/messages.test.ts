// @vitest-environment node
/**
 * 06 §7.2 i18n: every translation key referenced in src/ exists in messages/vi.json,
 * and en.json mirrors vi.json's key structure ("cấu trúc key sẵn cho en").
 * Static scan: `useTranslations("ns")` / `getTranslations("ns")` bound to a variable,
 * then `var("key")` calls in the same file.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import en from "../../messages/en.json";
import vi from "../../messages/vi.json";

const SRC_DIR = fileURLToPath(new URL("..", import.meta.url));

type Messages = { [key: string]: string | Messages };

function flatten(messages: Messages, prefix = ""): string[] {
  return Object.entries(messages).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === "string" ? [path] : flatten(value, path);
  });
}

function listSourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return listSourceFiles(full);
    return /\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [full] : [];
  });
}

function usedKeys(): { key: string; file: string }[] {
  const used: { key: string; file: string }[] = [];
  for (const file of listSourceFiles(SRC_DIR)) {
    const code = readFileSync(file, "utf8");
    const bindings = code.matchAll(
      /(?:const|let)\s+(\w+)\s*=\s*(?:await\s+)?(?:useTranslations|getTranslations)\(\s*["']([\w.]+)["']\s*\)/g,
    );
    for (const [, variable, namespace] of bindings) {
      const calls = code.matchAll(new RegExp(`\\b${variable}\\(\\s*["']([\\w.]+)["']`, "g"));
      for (const [, key] of calls) {
        used.push({ key: `${namespace}.${key}`, file: relative(SRC_DIR, file) });
      }
    }
  }
  return used;
}

describe("i18n messages (06 §7.2)", () => {
  const viKeys = new Set(flatten(vi as Messages));

  it("finds translation usages in src (scanner sanity check)", () => {
    const keys = usedKeys().map((u) => u.key);
    expect(keys).toContain("home.heading");
    expect(keys).toContain("format.currencySuffix");
  });

  it("every key used in src exists in vi.json", () => {
    const missing = usedKeys().filter((u) => !viKeys.has(u.key));
    expect(missing).toEqual([]);
  });

  it("en.json has the same key structure as vi.json", () => {
    expect(flatten(en as Messages).sort()).toEqual([...viKeys].sort());
  });
});
