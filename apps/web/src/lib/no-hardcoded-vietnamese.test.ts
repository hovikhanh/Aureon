// @vitest-environment node
/**
 * TC-UI-005 — No hard-coded Vietnamese strings in apps/web/src.
 * Vietnamese copy must live in i18n message files (apps/web/messages/*), never in source.
 * Spec: docs/2.PRODUCT/06-UI-UX-SPEC.md §7.2, CLAUDE.md § Frontend.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const SRC_DIR = fileURLToPath(new URL("..", import.meta.url));
const SOURCE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx"];

// Vietnamese-specific letters (precomposed) and combining diacritics.
const VIETNAMESE_CHARS =
  /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\u0300-\u0309\u0323]/i;

function listSourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return listSourceFiles(full);
    return SOURCE_EXTENSIONS.some((ext) => name.endsWith(ext)) ? [full] : [];
  });
}

function stripComments(code: string): string {
  return code.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
}

export function findHardcodedVietnamese(files: string[]): string[] {
  const offenders: string[] = [];
  for (const file of files) {
    if (file.endsWith(".test.ts") || file.endsWith(".test.tsx")) continue;
    const lines = stripComments(readFileSync(file, "utf8")).split("\n");
    lines.forEach((line, index) => {
      if (VIETNAMESE_CHARS.test(line)) {
        offenders.push(`${relative(SRC_DIR, file)}:${index + 1}`);
      }
    });
  }
  return offenders;
}

describe("TC-UI-005 no hard-coded Vietnamese in src", () => {
  it("detector flags Vietnamese text", () => {
    expect(VIETNAMESE_CHARS.test("Đăng nhập")).toBe(true);
    expect(VIETNAMESE_CHARS.test("Login")).toBe(false);
  });

  it("source files contain no Vietnamese literals", () => {
    expect(findHardcodedVietnamese(listSourceFiles(SRC_DIR))).toEqual([]);
  });
});
