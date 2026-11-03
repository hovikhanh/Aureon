/** SCR-49 tabs, also the `/knowledge/[tab]` sub-routes (R-DEC-137). Plain module: the server page imports it. */
export type KnowledgeTab = "decisions" | "documents" | "reports";
export const KNOWLEDGE_TABS: readonly KnowledgeTab[] = ["decisions", "documents", "reports"];
export const isKnowledgeTab = (v: string): v is KnowledgeTab => (KNOWLEDGE_TABS as readonly string[]).includes(v);

/**
 * Permission each tab's API needs (10: EP-43 `/execution/decisions` `execution:read`, EP-DC search
 * `/idp/documents/search` `idp:read`, EP-RPT-06 `/reporting/reports` `dashboard:read`). SCR-49 is open
 * to every role, so a tab whose API would 403 for the role (REV: no `execution:read`/`dashboard:read`)
 * is hidden instead of rendered as an error (M6). Display only — the API still enforces.
 */
export const KNOWLEDGE_TAB_PERMISSION: Readonly<Record<KnowledgeTab, string>> = {
  decisions: "execution:read", documents: "idp:read", reports: "dashboard:read",
};
export const visibleKnowledgeTabs = (perms: readonly string[]): KnowledgeTab[] =>
  KNOWLEDGE_TABS.filter((k) => perms.includes(KNOWLEDGE_TAB_PERMISSION[k]));
