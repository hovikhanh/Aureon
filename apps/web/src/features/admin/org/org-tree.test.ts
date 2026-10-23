/** T-617F (TC-M12-18) — SCR-51 tree nesting + parent picker without cycles. */
import { describe, expect, it } from "vitest";
import { nestDepartments, parentCandidates } from "./org-tree";

const d = (id: string, parent: string | null, headcount = 1) => ({ id, parent_id: parent, code: id, name: id, headcount });

describe("nestDepartments", () => {
  it("nests by parent_id, sums headcount, keeps orphans as roots", () => {
    const tree = nestDepartments([d("B", null, 2), d("A", null, 1), d("A1", "A", 3), d("A11", "A1", 4), d("X", "missing", 5)]);
    expect(tree.map((n) => n.dept.id)).toEqual(["A", "B", "X"]);
    expect(tree[0]!.total).toBe(8);
    expect(tree[0]!.children[0]!.children[0]!.dept.id).toBe("A11");
  });
});

describe("parentCandidates", () => {
  it("excludes the department itself and its descendants", () => {
    const rows = [d("A", null), d("A1", "A"), d("A11", "A1"), d("B", null)];
    expect(parentCandidates(rows, "A1").map((x) => x.id)).toEqual(["A", "B"]);
    expect(parentCandidates(rows, null)).toHaveLength(4);
  });
});
