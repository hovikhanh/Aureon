/** TanStack Query keys — one query per widget (CLAUDE §5.8). */
export const qk = {
  pillar: (domain: string, period: string) => ["pillar", domain, period] as const,
  alerts: () => ["alerts"] as const,
  conversations: () => ["ai", "conversations"] as const,
  messages: (id: string) => ["ai", "messages", id] as const,
  reviewQueue: (params: Record<string, unknown>) => ["idp", "review-queue", params] as const,
  reviewDetail: (id: string) => ["idp", "review", id] as const,
  employees: (params: Record<string, unknown>) => ["hr", "employees", params] as const,
  auditLogs: (params: Record<string, unknown>) => ["platform", "audit-logs", params] as const,
  invoices: (params: Record<string, unknown>) => ["finance", "invoices", params] as const,
  // M1.2 admin (T-617F) — everything org-related under "org" so one invalidate refreshes all
  orgTree: (asOf: string) => ["org", "tree", asOf] as const,
  assignments: (params: Record<string, unknown>) => ["org", "assignments", params] as const,
  departments: () => ["org", "departments"] as const,
  teams: (departmentId: string | null) => ["org", "teams", departmentId] as const,
  positions: (params: Record<string, unknown>) => ["org", "positions", params] as const,
  users: (params: Record<string, unknown>) => ["admin", "users", params] as const,
  roles: () => ["admin", "roles"] as const,
  notifications: () => ["notifications"] as const,
  notificationPrefs: () => ["notifications", "preferences"] as const,
};
