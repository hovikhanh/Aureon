/** M1.6 AI Control Center DTOs (10 §7.2.5) — re-exported from the generated OpenAPI types. */
import type { Api } from "@aureon/shared-types";

export type Level = "L0" | "L1" | "L2" | "L3";
export type Tool = Api.ToolOut;
export type Agent = Api.AIAgentOut;
export type Policy = Api.AutonomyPolicyOut;
export type PolicyDefault = { tool_name: string; action_name: string | null; default_level: Level; max_level: Level };
export type KillSwitch = Api.KillSwitchOut;
export type AiAction = Api.AIActionOut;
export type CostSummary = Api.CostSummaryOut;
export type ToolCallLog = Api.ToolCallLogOut;
export type ModelCallLog = Api.ModelCallLogOut;

/** Viewer of the admin screens (from the session — display only, the API enforces). */
export interface Viewer {
  id: string;
  role: string;
  permissions: string[];
}
