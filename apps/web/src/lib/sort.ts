/** Server-side sort of a list screen: `sort_by` + `order` of the existing endpoints (10 §1.3). */
export interface SortState { field: string; order: "asc" | "desc" }

/** Click on a header: same column flips the order, another column starts ascending. */
export function nextSort(current: SortState, field: string): SortState {
  return current.field === field ? { field, order: current.order === "asc" ? "desc" : "asc" } : { field, order: "asc" };
}

export const ariaSort = (s: SortState, field: string): "ascending" | "descending" | "none" =>
  s.field !== field ? "none" : s.order === "asc" ? "ascending" : "descending";
