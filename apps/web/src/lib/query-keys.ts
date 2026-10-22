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
};
