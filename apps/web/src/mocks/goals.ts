/**
 * Mock D07–D10 goals routes (T-626F..T-628F, 10 §7.2.3): EP-STR-01..22, EP-KPI-01..10,
 * EP-OKR-01..11, EP-PRF-01..06 — scope R-DEC-57 (`goal-scope.ts`), envelope / 400 / 403 / 404 /
 * 409 / 422 like the API.
 */
import type { Route } from "./router";
import { STRATEGY_ROUTES } from "./goals-strategy";
import { KPI_ROUTES } from "./goals-kpi";
import { OKR_ROUTES } from "./goals-okr";

export const GOALS_ROUTES: readonly Route[] = [...STRATEGY_ROUTES, ...KPI_ROUTES, ...OKR_ROUTES];
export { resetGoalStore } from "./goals-store";
