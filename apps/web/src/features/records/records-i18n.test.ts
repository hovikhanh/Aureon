/** TC-M7-01 (unit) — every field / column / enum value / action of the record specs has a vi + en label. */
import { readdirSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import vi from "../../../messages/vi.json";
import en from "../../../messages/en.json";
import { RESOURCES } from "./specs";

type Tree = Record<string, unknown>;
const has = (tree: Tree, path: string) => path.split(".").reduce<unknown>((o, k) => (o as Tree | undefined)?.[k], tree) !== undefined;

describe("records i18n", () => {
  const keys = new Set<string>();
  for (const r of RESOURCES) {
    keys.add(`records.resource.${r.key}`);
    for (const c of r.columns) keys.add(`records.field.${c.name}`);
    for (const f of [...r.fields, ...(r.actions ?? []).flatMap((a) => a.fields)]) {
      keys.add(`records.field.${f.name}`);
      for (const o of f.options ?? []) if (f.type === "select" || f.type === "multi") keys.add(`records.enum.${f.name}.${o}`);
    }
    for (const c of r.columns) if (c.type === "enum") for (const f of r.fields.filter((x) => x.name === c.name)) for (const o of f.options ?? []) keys.add(`records.enum.${c.name}.${o}`);
    for (const a of r.actions ?? []) keys.add(`records.action.${r.key}.${a.key}`);
  }
  it.each(["vi", "en"] as const)("%s has every label", (lang) => {
    const tree = (lang === "vi" ? vi : en) as Tree;
    expect([...keys].filter((k) => !has(tree, k))).toEqual([]);
  });
});

describe("records sort (U-10)", () => {
  /** `page_params(...)` whitelist of a list endpoint, read from the routers: an unlisted field is a 4xx. */
  const whitelist = (domain: string, path: string) => {
    const dir = new URL(`../../../../api/src/app/modules/${domain}/routes/`, import.meta.url);
    // a router may carry a prefix (`EnvelopeRouter(prefix="/work")` → `@router.get("/projects")`)
    const decorator = (src: string) => {
      const prefix = /Router\(prefix="([^"]*)"/.exec(src)?.[1] ?? "";
      return `@router.get("${path.startsWith(prefix) ? path.slice(prefix.length) : path}"`;
    };
    const src = readdirSync(dir).filter((f) => f.endsWith(".py")).map((f) => readFileSync(new URL(f, dir), "utf8")).find((s) => s.includes(decorator(s)))!;
    const route = src.indexOf(decorator(src));
    return [...src.slice(route).match(/page_params\(([^)]*)\)/)![1]!.matchAll(/"(\w+)"/g)].map((m) => m[1]!);
  };

  it.each(RESOURCES.map((r) => [r.key, r] as const))("%s sorts only on its columns, within the API whitelist", (_, r) => {
    const columns = r.columns.map((c) => c.name);
    const allowed = whitelist(r.domain, r.path);
    expect(allowed).toContain(r.sortBy);
    for (const f of r.sortable ?? []) {
      expect(columns).toContain(f);
      expect(allowed).toContain(f);
    }
    expect(r.sortable?.length).toBeGreaterThan(0);
  });
});
