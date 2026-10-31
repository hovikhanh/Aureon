/** T-707F — SCR-40 cấp dashboard theo role (R-DEC-85). */
import { describe, expect, it } from "vitest";
import { levelsFor } from "./levels";

describe("levelsFor", () => {
  it("CEO/DIR: cả 3 cấp, mặc định executive", () => {
    expect(levelsFor("CEO")).toEqual(["executive", "department", "employee"]);
    expect(levelsFor("DIR")[0]).toBe("executive");
  });
  it("MGR: department + employee, mặc định department", () => {
    expect(levelsFor("MGR")).toEqual(["department", "employee"]);
  });
  it("EMP và role khác: chỉ employee", () => {
    expect(levelsFor("EMP")).toEqual(["employee"]);
    expect(levelsFor("")).toEqual(["employee"]);
  });
});
