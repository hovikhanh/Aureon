/** U-07: a form field never shows its machine key, including every field of the seeded schemas. */
import { readFileSync, readdirSync } from "node:fs";
import { describe, expect, it } from "vitest";
import en from "../../../messages/en.json";
import vi from "../../../messages/vi.json";
import { fieldLabel } from "./field-label";

const flat = (o: Record<string, unknown>, p = ""): Record<string, string> =>
  Object.fromEntries(Object.entries(o).flatMap(([k, v]) => (typeof v === "object" && v ? Object.entries(flat(v as Record<string, unknown>, `${p}${k}.`)) : [[`${p}${k}`, String(v)]])));
const translator = (messages: object) => {
  const m = flat(messages as Record<string, unknown>);
  return Object.assign((k: string) => m[k] ?? k, { has: (k: string) => k in m });
};

/** Field names of the BE catalog (source of truth for the seeded ExtractionSchemas). */
function schemaFields(): string[] {
  const dir = new URL("../../../../api/src/app/modules/idp/services/", import.meta.url);
  const files = [new URL("schema_registry.py", dir), ...readdirSync(new URL("catalog/", dir)).filter((f) => f.endsWith(".py")).map((f) => new URL(`catalog/${f}`, dir))];
  const names = files.flatMap((f) => [...readFileSync(f, "utf8").matchAll(/(?:\bf\(\s*|"name":\s*)"([a-z][a-z0-9_]*)"/g)].map((m) => m[1]!));
  return [...new Set(names)];
}

describe("fieldLabel (U-07)", () => {
  const fields = schemaFields();

  it("finds the seeded schema fields (guards the regex above)", () => {
    expect(fields).toEqual(expect.arrayContaining(["seller_name", "subtotal", "vat_rate_pct", "vat_amount", "kpi_code"]));
  });

  it.each([["vi", vi], ["en", en]] as const)("%s: every seeded field has a real label, not a snake_case key", (_, messages) => {
    const t = translator(messages);
    for (const name of fields) {
      const label = fieldLabel(t, { name, label_key: `idp.field.${name}` });
      expect(label, name).not.toMatch(/_/);
      expect(label, name).not.toBe(name);
    }
  });

  it("prefers label_key, and humanises an unknown field added by Admin", () => {
    const t = translator({ a: { b: "Nhãn" }, capture: { field: { x: "Khác" } } });
    expect(fieldLabel(t, { name: "x", label_key: "a.b" })).toBe("Nhãn");
    expect(fieldLabel(t, { name: "x", label_key: "a.missing" })).toBe("Khác");
    expect(fieldLabel(t, { name: "contract_end_date" })).toBe("Contract end date");
  });
});
