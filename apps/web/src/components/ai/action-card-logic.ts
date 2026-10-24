/**
 * ActionCard rules (06 §5.1, R-DEC-78) — pure, unit-tested: who may act, which fields render as money
 * (P04), which are editable on confirm, and the L1 "Tự làm" deep link.
 */
export interface CardAction {
  id?: string;
  action_name: string;
  autonomy_level: string;
  status?: string;
  on_behalf_of?: string;
  input_preview?: Record<string, unknown>;
  can_undo?: boolean;
}

/** L2 proposed + the viewer is the served user (ADM / another user only sees the card). */
export const canDecide = (a: CardAction, viewerId: string, permissions: string[]) =>
  a.autonomy_level === "L2" && a.status === "proposed" && !!a.id && a.on_behalf_of === viewerId && permissions.includes("ai:write");

const MONEY = /(amount|total|price|budget|revenue|cost)(_vnd)?$/;
export const isMoneyField = (key: string) => MONEY.test(key);
/** Plain text / date fields are editable; ids/codes/currency stay read-only. */
export const isEditable = (key: string, value: unknown) =>
  (typeof value === "string" || typeof value === "number") && !/(^|_)(id|currency|code)$/.test(key) && !/^(EMP|CLI|T)-/.test(String(value));

/** L1 "Tự làm" target: the screen where the user would do the action manually. */
export function selfServiceHref(actionName: string): string {
  const act = actionName.replace(/^ACT-/, "");
  if (/task/.test(act)) return "/work?new=1";
  if (/kpi|kr_checkin|objective/.test(act)) return "/goals";
  if (/invoice|expense|deal/.test(act)) return "/data";
  if (/decision|meeting/.test(act)) return "/meetings";
  return "/home";
}

/** Coerce edited strings back to the preview's original type (numbers stay numbers). */
export function diffEdits(original: Record<string, unknown>, edited: Record<string, string>): Record<string, unknown> | undefined {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(edited)) {
    const before = original[k];
    const next = typeof before === "number" ? Number(v.replace(/[^\d-]/g, "")) : v;
    if (next !== before) out[k] = next;
  }
  return Object.keys(out).length ? out : undefined;
}
