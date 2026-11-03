/** SCR-49 tabs, also the `/knowledge/[tab]` sub-routes (R-DEC-137). Plain module: the server page imports it. */
export type KnowledgeTab = "decisions" | "documents" | "reports";
export const KNOWLEDGE_TABS: readonly KnowledgeTab[] = ["decisions", "documents", "reports"];
export const isKnowledgeTab = (v: string): v is KnowledgeTab => (KNOWLEDGE_TABS as readonly string[]).includes(v);
