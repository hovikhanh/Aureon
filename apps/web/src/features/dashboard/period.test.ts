import { describe, expect, it } from "vitest";
import { choiceOf, isPeriod, periodFor } from "./period";

const REF = new Date("2026-10-20T00:00:00Z"); // DEMO_REFERENCE_DATE

describe("period picker (T-510)", () => {
  it("maps choices relative to the business date", () => {
    expect(periodFor("thisMonth", REF)).toBe("2026-10");
    expect(periodFor("lastMonth", REF)).toBe("2026-09"); // = default demo period (DEC-237)
    expect(periodFor("q3", REF)).toBe("2026-Q3");
    expect(periodFor("q4", REF)).toBe("2026-Q4");
    expect(periodFor("lastMonth", new Date("2027-01-05T00:00:00Z"))).toBe("2026-12");
  });
  it("reverse-maps and validates keys", () => {
    expect(choiceOf("2026-09", REF)).toBe("lastMonth");
    expect(choiceOf("2025-01", REF)).toBeNull();
    expect(isPeriod("2026-Q3")).toBe(true);
    expect(isPeriod("2026-13")).toBe(false);
    expect(isPeriod("x; drop")).toBe(false);
  });
});
