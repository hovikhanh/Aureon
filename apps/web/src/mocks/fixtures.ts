/**
 * Mock fixtures (T-604) — typed view over `seed_snapshot.json`, exported from the v3 seed by
 * `python -m app.seed.snapshot` (drift-checked BE-side). Never hand-edit numbers here.
 */
import snapshot from "./seed_snapshot.json";

export type RoleCode = "CEO" | "DIR" | "MGR" | "EMP" | "REV" | "ADM" | "AI";

export interface SnapshotUser {
  email: string;
  role: RoleCode;
  full_name: string;
  department: string;
  scope_pillars: string[];
  employee: string | null;
  is_service_account: boolean;
}

export interface SnapshotMetric {
  code: string;
  pillar: "F" | "O" | "C" | "U" | "S" | null;
  value: number | null;
  unit: string;
  status: "ok" | "warning" | "critical" | "no_data";
  period_key: string;
}

export const SNAPSHOT = snapshot as unknown as {
  reference_date: string;
  company: string;
  users: SnapshotUser[];
  departments: { code: string; name: string; head: string; teams: { code: string; name: string }[] }[];
  employees: { code: string; full_name: string; department: string; team: string | null; manager: string | null; status: string; hire_date: string }[];
  metrics: SnapshotMetric[];
  role_permissions: Record<RoleCode, string[]>;
  organization: { code: string; name: string; valid_from: string };
  assignments: { employee: string; department: string; team: string | null; manager: string | null; valid_from: string; valid_to: string | null }[];
  roles: { code: RoleCode; role_ref: string; name_vi: string; name_en: string; pillars: string[]; scope_rules: Record<string, string> }[];
};

/** Deterministic UUID-shaped id from a stable key (mock only — the API uses real UUIDs). */
export function mockId(kind: string, key: string): string {
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  for (const ch of `${kind}:${key}`) {
    const c = ch.codePointAt(0) ?? 0;
    h1 = Math.imul(h1 ^ c, 0x01000193) >>> 0;
    h2 = Math.imul(h2 ^ c, 0x5bd1e995) >>> 0;
  }
  const hex = (h1.toString(16).padStart(8, "0") + h2.toString(16).padStart(8, "0")).repeat(2);
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-8${hex.slice(17, 20)}-${hex.slice(20, 32)}`;
}

/** Human (loginable) demo accounts — the AI actor is a service account and cannot log in. */
export const MOCK_USERS = SNAPSHOT.users.filter((u) => !u.is_service_account);

export interface MockClaims {
  sub: string;
  email: string;
  name: string;
  role: RoleCode;
  permissions: string[];
  scope_pillars: string[];
  department_id: string;
  /** R-DEC-41 — `hr.employees.id` of the user (null for accounts without an employee). */
  employee_id: string | null;
}

/** Same claim set as the real RS256 JWT (CLAUDE §5.3, `core/security.py`). */
export function claimsFor(user: SnapshotUser): MockClaims {
  return {
    sub: mockId("user", user.email),
    email: user.email,
    name: user.full_name,
    role: user.role,
    permissions: [...SNAPSHOT.role_permissions[user.role]],
    scope_pillars: [...user.scope_pillars].sort(),
    department_id: mockId("department", user.department),
    employee_id: user.employee ? mockId("employee", user.employee) : null,
  };
}

/**
 * R-DEC-76 (resolved 2026-10-24): ADM gets `idp:read` + `idp:write` (scope `s`, HR_ROSTER only —
 * enforced BE-side) for SCR-63 / C5 org import. The BE permission matrix + snapshot export catch
 * up in M1.5; until the snapshot carries them, the mock overlays them here (idempotent).
 */
for (const p of ["idp:read", "idp:write"]) {
  const adm = SNAPSHOT.role_permissions.ADM;
  if (!adm.includes(p)) adm.push(p);
}
SNAPSHOT.role_permissions.ADM.sort();
