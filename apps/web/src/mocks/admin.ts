/**
 * Mock user admin (EP-ADM-05..11) + notifications inbox (EP-NTF-01..05) — T-617F.
 * Users = the snapshot demo accounts, one shared store (an ADM edit is visible to every
 * session). Same rules as `user_admin_service`: AI cannot be granted (422), `scope_pillars`
 * only for DIR, only a CEO grants/changes/locks CEO, no self role change / self lock (422),
 * `initial_password` ≥ 12 chars, duplicate email → 409, stale `version` → 409.
 */
import { SNAPSHOT, mockId, type MockClaims, type RoleCode } from "./fixtures";
import { MockHttpError, ok, paginate, parsePage } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";

export interface MockUser {
  id: string; email: string; full_name: string; role_id: string; role_code: RoleCode; scope_pillars: string[];
  department_id: string | null; employee_id: string | null; locale: "vi" | "en"; is_active: boolean;
  is_service_account: boolean; last_login_at: string | null; locked_until: string | null;
  created_at: string; updated_at: string; version: number;
}

const STAMP = `${SNAPSHOT.reference_date}T01:00:00Z`;
const roleId = (code: string) => mockId("role", code);
// on globalThis: `next dev` re-evaluates server modules when it compiles another page
const G = globalThis as typeof globalThis & { __aureonMockUsers?: MockUser[] | null; __aureonMockInbox?: Map<string, Inbox> };

function seedUsers(): MockUser[] {
  return SNAPSHOT.users.map((u) => ({
    id: mockId("user", u.email), email: u.email, full_name: u.full_name, role_id: roleId(u.role), role_code: u.role,
    scope_pillars: [...u.scope_pillars], department_id: mockId("department", u.department),
    employee_id: u.employee ? mockId("employee", u.employee) : null, locale: "vi", is_active: true,
    is_service_account: u.is_service_account, last_login_at: null, locked_until: null, created_at: STAMP, updated_at: STAMP, version: 1,
  }));
}

export function userStore(): MockUser[] {
  G.__aureonMockUsers ??= seedUsers();
  return G.__aureonMockUsers;
}

const ROLE_CODES = ["CEO", "DIR", "MGR", "EMP", "REV", "ADM", "AI"] as const;
const PILLARS = ["F", "O", "C", "U", "S"];

function obj(req: MockRequest): Record<string, unknown> {
  return (req.body && typeof req.body === "object" ? req.body : {}) as Record<string, unknown>;
}
const rule = (message: string, extra: Record<string, unknown> = {}): never => {
  throw new MockHttpError(422, "BUSINESS_RULE_VIOLATION", message, extra);
};
const invalid = (field: string): never => {
  throw new MockHttpError(422, "VALIDATION_ERROR", "invalid body", { fields: [field] });
};

function checkGrant(actor: MockClaims, role: string, pillars: unknown, target?: MockUser): void {
  if (!(ROLE_CODES as readonly string[]).includes(role)) invalid("role_code");
  if (role === "AI") rule("AI role cannot be granted", { field: "role_code", reason: "ai_not_grantable" });
  if ((role === "CEO" || target?.role_code === "CEO") && actor.role !== "CEO") {
    throw new MockHttpError(403, "FORBIDDEN_SCOPE", "only a CEO may grant or change CEO", { field: "role_code" });
  }
  if (Array.isArray(pillars) && pillars.length) {
    if (role !== "DIR") rule("scope_pillars only for DIR", { field: "scope_pillars", reason: "pillars_only_dir" });
    if (pillars.some((p) => !PILLARS.includes(String(p)))) invalid("scope_pillars");
  }
}

function listUsers(req: MockRequest) {
  const q = req.query;
  const role = q.get("role_code");
  const active = q.get("is_active");
  const dept = q.get("department_id");
  const text = q.get("q")?.toLowerCase();
  const rows = userStore().filter((u) => (!role || u.role_code === role) && (active === null || active === "" || String(u.is_active) === active)
    && (!dept || u.department_id === dept) && (!text || `${u.email} ${u.full_name}`.toLowerCase().includes(text)));
  return paginate(rows as unknown as Record<string, unknown>[], parsePage(q, ["email", "full_name", "created_at", "last_login_at"]));
}

function findUser(id: string | undefined): MockUser {
  const u = userStore().find((x) => x.id === id);
  if (!u) throw new MockHttpError(404, "NOT_FOUND", "user not found");
  return u;
}

function createUser(req: MockRequest) {
  const b = obj(req);
  for (const f of ["email", "full_name", "role_code", "initial_password"]) if (!b[f]) invalid(f);
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(b.email))) invalid("email");
  if (String(b.initial_password).length < 12) invalid("initial_password");
  checkGrant(req.claims, String(b.role_code), b.scope_pillars);
  const email = String(b.email).toLowerCase();
  if (userStore().some((u) => u.email === email)) throw new MockHttpError(409, "DUPLICATE_RESOURCE", "email exists", { field: "email" });
  const now = new Date().toISOString();
  const u: MockUser = {
    id: mockId("user", `${email}:${Date.now()}`), email, full_name: String(b.full_name), role_id: roleId(String(b.role_code)),
    role_code: b.role_code as RoleCode, scope_pillars: Array.isArray(b.scope_pillars) ? b.scope_pillars.map(String).sort() : [],
    department_id: (b.department_id as string | null) ?? null, employee_id: (b.employee_id as string | null) ?? null,
    locale: b.locale === "en" ? "en" : "vi", is_active: true, is_service_account: false, last_login_at: null, locked_until: null,
    created_at: now, updated_at: now, version: 1,
  };
  userStore().push(u);
  recordAudit(req.claims, "auth.user_create", "users", u.id);
  return ok(u, 201);
}

function patchUser(req: MockRequest) {
  const u = findUser(req.params.id);
  const b = obj(req);
  if (b.version != null && b.version !== u.version) throw new MockHttpError(409, "CONFLICT_STATE", "stale version", { expected: u.version });
  const role = (b.role_code as string | undefined) ?? u.role_code;
  if (b.role_code !== undefined || b.scope_pillars !== undefined) {
    if (u.id === req.claims.sub && b.role_code !== undefined && b.role_code !== u.role_code) rule("cannot change own role", { field: "role_code", reason: "self_change" });
    checkGrant(req.claims, role, b.scope_pillars ?? (role === "DIR" ? u.scope_pillars : []), u);
  }
  if (b.full_name !== undefined) u.full_name = String(b.full_name);
  if (b.locale === "vi" || b.locale === "en") u.locale = b.locale;
  if (b.department_id !== undefined) u.department_id = (b.department_id as string | null) ?? null;
  if (b.employee_id !== undefined) u.employee_id = (b.employee_id as string | null) ?? null;
  if (b.role_code !== undefined) Object.assign(u, { role_code: role, role_id: roleId(role) });
  if (role !== "DIR") u.scope_pillars = [];
  else if (Array.isArray(b.scope_pillars)) u.scope_pillars = b.scope_pillars.map(String).sort();
  u.version += 1;
  u.updated_at = new Date().toISOString();
  recordAudit(req.claims, "auth.user_update", "users", u.id);
  return ok(u);
}

/** Same rule as the API (`core/idempotency`): action POSTs need an Idempotency-Key. */
function requireIdem(req: MockRequest): void {
  if (!req.headers.get("idempotency-key")?.trim()) throw new MockHttpError(400, "BAD_REQUEST", "Idempotency-Key header is required", { header: "Idempotency-Key" });
}

const setActive = (active: boolean) => (req: MockRequest) => {
  requireIdem(req);
  const u = findUser(req.params.id);
  const reason = String(obj(req).reason ?? "").trim();
  if (!reason) invalid("reason");
  if (u.id === req.claims.sub) rule("cannot deactivate yourself", { reason: "self_change" });
  if (u.role_code === "CEO" && req.claims.role !== "CEO") throw new MockHttpError(403, "FORBIDDEN_SCOPE", "only a CEO may lock CEO");
  if (u.is_active === active) throw new MockHttpError(409, "CONFLICT_STATE", "already in this state", { is_active: active });
  Object.assign(u, { is_active: active, version: u.version + 1, updated_at: new Date().toISOString() });
  recordAudit(req.claims, active ? "auth.user_reactivate" : "auth.user_deactivate", "users", u.id, reason);
  return ok(u);
};

function roles() {
  return ok(SNAPSHOT.roles.map((r) => ({ ...r, id: roleId(r.code), permissions: [...SNAPSHOT.role_permissions[r.code as RoleCode]] })));
}

// ---------------------------------------------------------------- notifications (per user)
export const NOTIFICATION_KINDS = ["alert", "review_assigned", "review_escalated", "task_assigned", "approval_requested",
  "approval_decided", "report_ready", "ai_action", "document_ready", "reminder", "system"] as const;
const EMAIL_DEFAULT_ON = new Set(["task_assigned", "approval_requested", "review_assigned", "review_escalated"]);

export interface MockNotification { id: string; kind: string; title: string; body: string; link: string | null; ref_schema: string | null; ref_table: string | null; ref_id: string | null; read_at: string | null; created_at: string }
interface Inbox { items: MockNotification[]; prefs: Map<string, boolean> }
const inboxes: Map<string, Inbox> = (G.__aureonMockInbox ??= new Map());

/** Demo inbox: a few unread items so the bell shows a badge on the mock (fake, no PII). */
function seedInbox(c: MockClaims): Inbox {
  const at = (h: number) => new Date(Date.parse(`${SNAPSHOT.reference_date}T09:00:00Z`) - h * 3_600_000).toISOString();
  const mk = (i: number, kind: string, title: string, link: string, read = false): MockNotification => ({
    id: mockId("notification", `${c.sub}:${i}`), kind, title, body: "", link, ref_schema: null, ref_table: null, ref_id: null,
    read_at: read ? at(i) : null, created_at: at(i),
  });
  const items = [
    mk(1, "alert", "Runway tiền mặt dưới ngưỡng cảnh báo", "/home"),
    mk(2, "task_assigned", "Bạn được giao việc: Chuẩn bị báo cáo tuần", "/work"),
    mk(3, "approval_requested", "Có yêu cầu chờ phê duyệt", "/work/approvals"),
    mk(5, "system", "Chào mừng đến Aureon", "/home", true),
  ];
  return { items, prefs: new Map() };
}

function inbox(c: MockClaims): Inbox {
  let box = inboxes.get(c.sub);
  if (!box) {
    box = seedInbox(c);
    inboxes.set(c.sub, box);
  }
  return box;
}

/** Test/dev hook: push a notification into a user's inbox. */
export function pushNotification(c: MockClaims, n: Omit<MockNotification, "id" | "read_at" | "created_at">): MockNotification {
  const row = { ...n, id: globalThis.crypto.randomUUID(), read_at: null, created_at: new Date().toISOString() };
  inbox(c).items.unshift(row);
  return row;
}

function listNotifications(req: MockRequest) {
  const box = inbox(req.claims);
  const unreadOnly = req.query.get("unread_only") === "true";
  const kind = req.query.get("kind");
  if (kind && !(NOTIFICATION_KINDS as readonly string[]).includes(kind)) invalid("kind");
  const rows = box.items.filter((n) => (!unreadOnly || n.read_at === null) && (!kind || n.kind === kind)).sort((a, b) => b.created_at.localeCompare(a.created_at));
  const page = parsePage(req.query);
  const data = rows.slice(page.offset, page.offset + page.limit);
  return ok(data, 200, {
    pagination: { total: rows.length, limit: page.limit, offset: page.offset, has_next: page.offset + data.length < rows.length },
    unread_count: box.items.filter((n) => n.read_at === null).length,
  });
}

function markRead(req: MockRequest) {
  requireIdem(req);
  const n = inbox(req.claims).items.find((x) => x.id === req.params.id);
  if (!n) throw new MockHttpError(404, "NOT_FOUND", "notification not found");
  n.read_at ??= new Date().toISOString();
  return ok(n);
}

function readAll(req: MockRequest) {
  requireIdem(req);
  const upTo = (obj(req).up_to as string | undefined) ?? new Date().toISOString();
  let updated = 0;
  for (const n of inbox(req.claims).items) if (n.read_at === null && n.created_at <= upTo) { n.read_at = new Date().toISOString(); updated += 1; }
  return ok({ updated });
}

function prefsOut(c: MockClaims) {
  const p = inbox(c).prefs;
  return NOTIFICATION_KINDS.map((k) => ({ kind: k, email_enabled: p.get(k) ?? EMAIL_DEFAULT_ON.has(k), is_default: !p.has(k) }));
}

function patchPrefs(req: MockRequest) {
  const items = obj(req).items;
  if (!Array.isArray(items) || items.length === 0) invalid("items");
  const list = items as { kind?: unknown; email_enabled?: unknown }[];
  if (list.some((i) => !(NOTIFICATION_KINDS as readonly string[]).includes(String(i.kind)) || typeof i.email_enabled !== "boolean")) invalid("items");
  for (const i of list) inbox(req.claims).prefs.set(String(i.kind), Boolean(i.email_enabled));
  recordAudit(req.claims, "platform.notification_preference_update", "notification_preferences", req.claims.sub);
  return ok(prefsOut(req.claims));
}

export function resetAdminStore(): void {
  G.__aureonMockUsers = null;
  inboxes.clear();
}

/** `permission: ""` = token only (EP-NTF, R-DEC-31). */
export const ADMIN_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/platform/users", permission: "platform:read", handler: listUsers },
  { method: "POST", pattern: "/platform/users", permission: "platform:admin", handler: createUser },
  { method: "GET", pattern: "/platform/users/:id", permission: "platform:read", handler: (req) => ok(findUser(req.params.id)) },
  { method: "PATCH", pattern: "/platform/users/:id", permission: "platform:admin", handler: patchUser },
  { method: "POST", pattern: "/platform/users/:id/deactivate", permission: "platform:admin", handler: setActive(false) },
  { method: "POST", pattern: "/platform/users/:id/reactivate", permission: "platform:admin", handler: setActive(true) },
  { method: "GET", pattern: "/platform/roles", permission: "platform:read", handler: roles },
  { method: "GET", pattern: "/notifications", permission: "", handler: listNotifications },
  { method: "POST", pattern: "/notifications/read-all", permission: "", handler: readAll },
  { method: "GET", pattern: "/notifications/preferences", permission: "", handler: (req) => ok(prefsOut(req.claims)) },
  { method: "PATCH", pattern: "/notifications/preferences", permission: "", handler: patchPrefs },
  { method: "POST", pattern: "/notifications/:id/read", permission: "", handler: markRead },
];
