/**
 * Pure helpers for SCR-64/65, KillSwitchBanner and ActionCard (06 §3.4 / §5.1) — unit-tested in
 * `logic.test.ts` (Vitest runs in node, so UI rules live here, not in the components).
 */
import type { Agent, KillSwitch, Level, Tool } from "./types";

export const CEILING_DEFAULT: Level = "L2";
const ORDER: Level[] = ["L0", "L1", "L2", "L3"];
export const rank = (l: string | null | undefined) => ORDER.indexOf((l ?? "L0") as Level);

/** Standard autonomy label key (relative to `aiAdmin`): L0 Chỉ thông tin · L1 AI gợi ý · L2 AI soạn · L3 AI đã làm. */
export const levelKey = (l: string | null | undefined) => `level.${ORDER.includes(l as Level) ? l : "L0"}`;
/** Agent `max_autonomy_level` choices: L0–ceiling selectable, the rest shown disabled ("Mở ở M3"). */
export const levelOptions = (ceiling: Level = CEILING_DEFAULT) => ["L0", "L1", "L2", "L3", "L4"].map((l) => ({ value: l, disabled: l === "L4" || rank(l) > rank(ceiling) }));

/** Cost bar tone: warning ≥ 80 %, danger ≥ 100 % (06 §3.4 SCR-64 Tổng quan). */
export const costTone = (pct: number): "ok" | "warning" | "danger" => (pct >= 100 ? "danger" : pct >= 80 ? "warning" : "ok");

/** KillSwitchBanner (06 §5.1): hidden when off or on load error; text by mode; scope = all or agent list. */
export function bannerState(ks: KillSwitch | undefined, isError: boolean): null | { textKey: string; scope: "all" | string[] } {
  if (isError || !ks?.enabled) return null;
  return { textKey: ks.mode === "L0" ? "killSwitch.banner.L0" : "killSwitch.banner.WRITE_OFF", scope: ks.agents?.length ? ks.agents : "all" };
}
export const bannerHasAdminLink = (role: string) => role === "ADM" || role === "CEO";

export interface ToolFilter { kind: string; domain: string; agent: string; mine: boolean }
export const filterTools = (tools: Tool[], f: ToolFilter) =>
  tools.filter((t) => (!f.kind || t.kind === f.kind) && (!f.domain || t.domain === f.domain) && (!f.agent || (t.agents ?? []).includes(f.agent)) && (!f.mine || t.available));

/** 13 metadata (10 §2.1): `name` is the pinned row header, `input_schema`/`output_schema` sit in the
 * expanded row; the other 11 + kind/domain/EP are toggleable columns. */
export const TOOL_COLUMNS = ["kind", "domain", "description", "permission", "risk_level", "data_scope", "data_classification", "autonomy",
  "approval_required", "reversible", "audit_required", "cost_estimate", "owner", "endpoint_ref"] as const;
export type ToolColumn = (typeof TOOL_COLUMNS)[number];
export const DEFAULT_HIDDEN: ToolColumn[] = ["description", "data_scope", "cost_estimate", "audit_required"];

/** Autonomy matrix rows: WRITE / EXECUTION tools only (06 §3.4). */
export const matrixTools = (tools: Tool[]) => tools.filter((t) => t.kind === "WRITE" || t.kind === "EXECUTION");
/** Root default shown struck-through ("hạ theo trần M1") when above the ceiling. */
export const cappedDefault = (rootDefault: string, ceiling: Level = CEILING_DEFAULT) =>
  rank(rootDefault) > rank(ceiling) ? { shown: ceiling, struck: rootDefault as Level } : { shown: rootDefault as Level, struck: null };

/** `1.250.000 đ` text ↔ integer VND (money threshold input). */
export const parseMoney = (text: string): number | null => {
  const digits = text.replace(/[^\d]/g, "");
  return digits ? Number(digits) : null;
};

/** v2.1 chat agent code kept on old `ai_actions` / log rows (R-DEC-71) — not in the agent catalog. */
export const LEGACY_AGENT_CODE = "assistant";

/** Agent display name; an unknown code falls back to `legacyLabel` (i18n) for the v2.1 code, else the code. */
export const agentName = (a: Pick<Agent, "name_vi" | "name_en"> | undefined, code: string, locale: string, legacyLabel?: string) =>
  a ? (locale === "en" ? a.name_en : a.name_vi) : code === LEGACY_AGENT_CODE && legacyLabel ? legacyLabel : code;

/** Error → i18n key: 422 `details.reason` (aiAdmin.reason.*), else code. */
export function errorKey(code: string, details: Record<string, unknown> | undefined): string {
  const r = details?.reason;
  if (typeof r === "string") return `aiAdmin.reason.${r}`;
  if (code === "CONFLICT_STATE") return "aiAdmin.conflict";
  return `errors.${code}`;
}
