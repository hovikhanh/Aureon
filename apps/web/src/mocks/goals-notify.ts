/**
 * Mock consumer `execution.on_goal_alert` (R-DEC-59): `execution.kpi_below_threshold` /
 * `execution.okr_at_risk` → Notification kind `alert` for the owner + MGR/DIR of the department
 * (synchronous in the mock; the API does it through the outbox). Links open SCR-58 / SCR-59.
 */
import { SNAPSHOT, claimsFor, mockId } from "./fixtures";
import { pushNotification } from "./admin";

function recipients(ownerId: string, departmentId: string | null) {
  return SNAPSHOT.users.filter((u) => !u.is_service_account && (mockId("user", u.email) === ownerId
    || (departmentId !== null && (u.role === "MGR" || u.role === "DIR") && mockId("department", u.department) === departmentId)));
}

export function notifyGoalAlert(o: { ownerId: string; departmentId: string | null; title: string; link: string; refTable: "kpis" | "key_results"; refId: string; actorId: string }): void {
  for (const u of recipients(o.ownerId, o.departmentId)) {
    const c = claimsFor(u);
    if (c.sub === o.actorId && u.role === "EMP") continue;
    pushNotification(c, { kind: "alert", title: o.title, body: "", link: o.link, ref_schema: "execution", ref_table: o.refTable, ref_id: o.refId });
  }
}
