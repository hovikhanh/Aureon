import { describe, expect, it } from "vitest";
import { formatValue, gateTone, overallStatus } from "./logic";

describe("gateTone", () => {
  it("maps each status to a tone and defaults unknown to muted", () => {
    expect(gateTone("pass")).toBe("success");
    expect(gateTone("warning")).toBe("warning");
    expect(gateTone("fail")).toBe("danger");
    expect(gateTone("no_data")).toBe("muted");
    expect(gateTone("weird")).toBe("muted");
  });
});

describe("formatValue", () => {
  it("formats by unit and dashes null/NaN", () => {
    expect(formatValue(80, "pct")).toBe("80.0%");
    expect(formatValue(4, "days_per_week")).toBe("4.0 d/wk");
    expect(formatValue(3, "count")).toBe("3");
    expect(formatValue(2.6, "count")).toBe("3");
    expect(formatValue(null, "pct")).toBe("—");
    expect(formatValue(undefined, "count")).toBe("—");
    expect(formatValue(NaN, "pct")).toBe("—");
  });
});

describe("overallStatus", () => {
  it("passes only when all gates pass", () => {
    expect(overallStatus(["pass", "pass", "pass", "pass"])).toBe("pass");
  });
  it("fails when any gate fails (G4 priority)", () => {
    expect(overallStatus(["pass", "pass", "pass", "fail"])).toBe("fail");
    expect(overallStatus(["warning", "fail", "pass", "pass"])).toBe("fail");
  });
  it("warns when a gate warns but none fail", () => {
    expect(overallStatus(["pass", "warning", "pass", "pass"])).toBe("warning");
  });
  it("is no_data when empty or mixed with no_data and no pass/warn/fail", () => {
    expect(overallStatus([])).toBe("no_data");
    expect(overallStatus(["no_data", "no_data"])).toBe("no_data");
    expect(overallStatus(["pass", "no_data"])).toBe("no_data");
  });
});
