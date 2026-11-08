import { describe, expect, it } from "vitest";
import { ariaSort, nextSort } from "./sort";

describe("table sort (U-10)", () => {
  it("flips the active column, starts another ascending", () => {
    expect(nextSort({ field: "a", order: "asc" }, "a")).toEqual({ field: "a", order: "desc" });
    expect(nextSort({ field: "a", order: "desc" }, "a")).toEqual({ field: "a", order: "asc" });
    expect(nextSort({ field: "a", order: "desc" }, "b")).toEqual({ field: "b", order: "asc" });
  });

  it("aria-sort is only on the active column", () => {
    expect(ariaSort({ field: "a", order: "asc" }, "a")).toBe("ascending");
    expect(ariaSort({ field: "a", order: "desc" }, "a")).toBe("descending");
    expect(ariaSort({ field: "a", order: "desc" }, "b")).toBe("none");
  });
});
