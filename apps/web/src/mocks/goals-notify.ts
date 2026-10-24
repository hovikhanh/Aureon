/**
 * Mock consumer `execution.on_goal_alert` (R-DEC-59) — same recipients / texts as
 * `execution/events/consumers.py`: `execution.kpi_below_threshold` → KPI owner + MGR/DIR of the
 * exact department; `execution.okr_at_risk` → KR owner + Objective owner + MGR of the department.
 * Title / body carry codes and numbers only. Synchronous here (the API goes through the outbox).
 */
import { SNAPSHOT, claimsFor, mockId } from "./fixtures";
import { pushNotification } from "./admin";

function recipients(owners: string[], roles: string[], departmentId: string | null) {
  return SNAPSHOT.users.filter((u) => !u.is_service_account && (owners.includes(mockId("user", u.email))
    || (departmentId !== null && roles.includes(u.role) && mockId("department", u.department) === departmentId)));
}

const fmt = (n: number) => String(Math.round(n * 10_000) / 10_000);

function send(users: ReturnType<typeof recipients>, n: { title: string; body: string; link: string; refTable: "kpis" | "key_results"; refId: string }): void {
  for (const u of users) pushNotification(claimsFor(u), { kind: "alert", title: n.title, body: n.body, link: n.link, ref_schema: "execution", ref_table: n.refTable, ref_id: n.refId });
}

export function notifyKpiAlert(k: { id: string; code: string; owner_id: string; department_id: string | null }, e: { period_key: string; band: string; achievement_pct: number }): void {
  send(recipients([k.owner_id], ["MGR", "DIR"], k.department_id), { title: `KPI ${k.code} ${e.band} kỳ ${e.period_key}`, body: `${k.code}: đạt ${fmt(e.achievement_pct)}% kỳ ${e.period_key}`,
    link: `/goals/kpis/${k.id}`, refTable: "kpis", refId: k.id });
}

export function notifyKrAlert(kr: { id: string; owner_id: string }, o: { id: string; owner_id: string; period_key: string; department_id: string | null }, a: { progress: number; expected: number }): void {
  send(recipients([kr.owner_id, o.owner_id], ["MGR"], o.department_id), { title: `KR có rủi ro kỳ ${o.period_key}`, body: `Tiến độ ${fmt(a.progress)}% (kế hoạch ${fmt(a.expected)}%)`,
    link: `/goals/objectives/${o.id}?kr=${kr.id}`, refTable: "key_results", refId: kr.id });
}
