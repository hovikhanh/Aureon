import { humanizeKey } from "@/lib/humanize";
import type { FormField } from "./types";

type T = { (key: string): string; has: (key: string) => boolean };

/**
 * Display label of a schema field: `label_key` → `capture.field.*` → the review names
 * `idp.fieldName.*` (the invoice schema has no `label_key`) → humanised, never the raw `snake_case`.
 */
export function fieldLabel(t: T, f: Pick<FormField, "name"> & Partial<Pick<FormField, "label_key">>): string {
  for (const key of [f.label_key, `capture.field.${f.name}`, `idp.fieldName.${f.name}`]) if (key && t.has(key)) return t(key);
  return humanizeKey(f.name);
}
