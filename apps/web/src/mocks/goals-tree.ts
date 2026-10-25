/**
 * Mock EP-STR-01 `/goals/tree` (10 §7.2.3): Strategy → SO → {KPI (children nested) · Objective → KR
 * (children nested) · Initiative → Project} + `unaligned`. Out-of-scope rows are dropped; an
 * out-of-scope ancestor of a visible row becomes `{id, code?, title?, restricted: true}` (R-DEC-57).
 * Only stored columns are read (evaluation, at_risk, progress) — no metric computed here.
 */
import type { MockClaims } from "./fixtures";
import { canRead } from "./goal-scope";
import { onTrack, periodKeyFor } from "./goals-rules";
import { goalStore, latestEvaluation, type GoalStore, type MKpi, type MKr, type MObjective, type MSO, type MStrategy } from "./goals-store";
import { workStore, workToday } from "./work-store";

export interface TreeOpts { periodKey: string; departmentId: string | null; strategyId: string | null }
type Node = Record<string, unknown>;

export const evaluationBrief = (s: GoalStore, kpi: string) => {
  const e = latestEvaluation(s, kpi);
  return e ? { period_key: e.period_key, actual_value: e.actual_value, target: e.target, achievement_pct: e.achievement_pct, band: e.band, previous_band: e.previous_band, evaluated_at: e.evaluated_at } : null;
};

export const krNode = (k: MKr) => ({
  id: k.id, title: k.title, unit: k.unit, baseline: k.baseline, target: k.target, current_value: k.current_value, progress_pct: k.progress_pct,
  confidence: k.confidence, at_risk: k.at_risk, last_checked_in_at: k.last_checked_in_at, owner_id: k.owner_id,
});

export function buildTree(c: MockClaims, o: TreeOpts) {
  const s = goalStore();
  const today = workToday();
  const deptOk = (d: string | null) => !o.departmentId || d === o.departmentId;

  const kpiNode = (k: MKpi): Node | null => {
    const children = s.kpis.filter((x) => !x.deleted && x.parent_kpi_id === k.id).map(kpiNode).filter((x): x is Node => x !== null);
    const visible = canRead(c, k);
    if (visible && (deptOk(k.department_id) || children.length)) {
      return { id: k.id, code: k.code, name: k.name, restricted: false, unit: k.unit, direction: k.direction, owner_id: k.owner_id, department_id: k.department_id,
        latest_evaluation: evaluationBrief(s, k.id), children };
    }
    return children.length ? { id: k.id, code: k.code, name: k.name, restricted: true, children } : null;
  };

  const objNode = (ob: MObjective): Node | null => {
    if (ob.period_key !== o.periodKey) return null;
    const children = s.objectives.filter((x) => !x.deleted && x.parent_id === ob.id).map(objNode).filter((x): x is Node => x !== null);
    const visible = canRead(c, ob);
    const krs = s.krs.filter((k) => !k.deleted && k.objective_id === ob.id);
    const ownKrs = krs.filter((k) => canRead(c, { ...k, department_id: visible ? ob.department_id : "-", pillar: visible ? ob.pillar : null }));
    if (visible && (deptOk(ob.department_id) || children.length)) {
      return { id: ob.id, title: ob.title, restricted: false, period_key: ob.period_key, level: ob.level, status: ob.status, progress_pct: ob.progress_pct,
        owner_id: ob.owner_id, department_id: ob.department_id, at_risk_kr_count: krs.filter((k) => k.at_risk).length, key_results: krs.map(krNode), children };
    }
    if (!ownKrs.length && !children.length) return null;
    return { id: ob.id, title: ob.title, restricted: true, key_results: ownKrs.map(krNode), children };
  };

  const projectsOf = (codes: string[]) => workStore().projects.filter((p) => !p.deleted && codes.includes(p.code)).map((p) => ({ id: p.id, code: p.code, name: p.name, status: p.status }));

  const soNode = (so: MSO): Node | null => {
    const kpis = s.kpis.filter((k) => !k.deleted && k.parent_kpi_id === null && k.strategic_objective_id === so.id).map(kpiNode).filter((x): x is Node => x !== null);
    const objectives = s.objectives.filter((x) => !x.deleted && x.parent_id === null && x.strategic_objective_id === so.id).map(objNode).filter((x): x is Node => x !== null);
    const initiatives = s.initiatives.filter((i) => !i.deleted && i.strategic_objective_id === so.id && canRead(c, i) && deptOk(i.department_id)).map((i) => ({
      id: i.id, code: i.code, title: i.title, restricted: false, status: i.status, progress_pct: i.progress_pct, start_date: i.start_date, planned_end_date: i.planned_end_date,
      on_track: onTrack(i.progress_pct, i.start_date, i.planned_end_date, today), projects: projectsOf(i.project_codes),
    }));
    const any = kpis.length + objectives.length + initiatives.length > 0;
    if (canRead(c, so) && (any || deptOk(so.department_id))) {
      return { id: so.id, code: so.code, title: so.title, restricted: false, pillar: so.pillar, owner_id: so.owner_id, department_id: so.department_id,
        progress_pct: so.progress_pct, status: so.status, kpis, objectives, initiatives };
    }
    return any ? { id: so.id, code: so.code, title: so.title, restricted: true, kpis, objectives, initiatives } : null;
  };

  const strategyNode = (st: MStrategy): Node | null => {
    const sos = s.sos.filter((x) => !x.deleted && x.strategy_id === st.id).sort((a, b) => a.sort_order - b.sort_order).map(soNode).filter((x): x is Node => x !== null);
    if (c.role !== "EMP") {
      return { id: st.id, code: st.code, name: st.name, restricted: false, status: st.status, period_start: st.period_start, period_end: st.period_end, owner_id: st.owner_id, strategic_objectives: sos };
    }
    return sos.length ? { id: st.id, code: st.code, name: st.name, restricted: true, strategic_objectives: sos } : null;
  };

  const strategies = s.strategies.filter((st) => !st.deleted && (o.strategyId ? st.id === o.strategyId : st.status === "active")).map(strategyNode).filter((x): x is Node => x !== null);
  return {
    strategies,
    unaligned: {
      kpis: s.kpis.filter((k) => !k.deleted && k.parent_kpi_id === null && k.strategic_objective_id === null).map(kpiNode).filter((x): x is Node => x !== null),
      objectives: s.objectives.filter((x) => !x.deleted && x.parent_id === null && x.strategic_objective_id === null).map(objNode).filter((x): x is Node => x !== null),
    },
  };
}

export const currentQuarter = () => periodKeyFor("QUARTER", workToday());
