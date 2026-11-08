/** U-02: a hash of an id is never a display value. Fallbacks use a human label ("Phòng ban khác"). */
import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const SRC = fileURLToPath(new URL("..", import.meta.url));

/** Not a display of an entity id, or owned elsewhere. Do not add a screen here to silence the test. */
const ALLOWED = new Set([
  "features/goals/CheckInCard.tsx", // builds a DOM id prefix, never rendered
  "features/capture/admin/IncidentsTab.tsx", // Admin incident log: the document code is the reference
  "features/crm/SalesInsights.tsx", // owned by the funnel work (still open, see changes-fe.md)
]);

function sources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    return e.isDirectory() ? sources(p) : p.endsWith(".tsx") ? [p] : [];
  });
}

describe("no raw id on screen (U-02)", () => {
  it("guards the real tree", () => {
    expect(sources(join(SRC, "features")).length).toBeGreaterThan(100);
  });

  it("no component renders `id.slice(0, 8)`", () => {
    const hits = [...sources(join(SRC, "features")), ...sources(join(SRC, "components"))]
      .map((f) => [relative(SRC, f).replaceAll("\\", "/"), readFileSync(f, "utf8")] as const)
      .filter(([rel, text]) => !ALLOWED.has(rel) && /\.slice\(0,\s*8\)/.test(text))
      .map(([rel]) => rel);
    expect(hits).toEqual([]);
  });
});
