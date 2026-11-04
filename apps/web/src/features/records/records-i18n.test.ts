/** TC-M7-01 (unit) — every field / column / enum value / action of the record specs has a vi + en label. */
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
      for (const o of f.options ?? []) if (f.type === "select") keys.add(`records.enum.${f.name}.${o}`);
    }
    for (const c of r.columns) if (c.type === "enum") for (const f of r.fields.filter((x) => x.name === c.name)) for (const o of f.options ?? []) keys.add(`records.enum.${c.name}.${o}`);
    for (const a of r.actions ?? []) keys.add(`records.action.${r.key}.${a.key}`);
  }
  it.each(["vi", "en"] as const)("%s has every label", (lang) => {
    const tree = (lang === "vi" ? vi : en) as Tree;
    expect([...keys].filter((k) => !has(tree, k))).toEqual([]);
  });
});
