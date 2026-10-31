/** SCR-40 cấp dashboard theo role (R-DEC-85). Tách riêng để test logic (Vitest node). */
export type Level = "executive" | "department" | "employee";

export function levelsFor(role: string): Level[] {
  if (role === "CEO" || role === "DIR") return ["executive", "department", "employee"];
  if (role === "MGR") return ["department", "employee"];
  return ["employee"];
}
