import { describe, expect, it } from "vitest";
import { formatValue, gateSourceKey, gateTone, overallStatus } from "./logic";

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
    expect(formatValue(66.67, "pct", "vi", "ngày/tuần")).toBe("66,7%");
    expect(formatValue(80, "pct", "en", "d/wk")).toBe("80.0%");
    expect(formatValue(3.5, "days_per_week", "vi", "ngày/tuần")).toBe("3,5 ngày/tuần");
    expect(formatValue(3, "count", "vi", "")).toBe("3");
    expect(formatValue(2.6, "count", "vi", "")).toBe("3");
    expect(formatValue(1200, "count", "vi", "")).toBe("1.200");
    expect(formatValue(null, "pct", "vi", "")).toBe("—");
    expect(formatValue(undefined, "count", "vi", "")).toBe("—");
    expect(formatValue(NaN, "pct", "vi", "")).toBe("—");
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

describe("gateSourceKey (U-13)", () => {
  it("maps the API's source_ref to an i18n key; an unknown one has no label", () => {
    expect(gateSourceKey("METRIC-STR-01")).toBe("metric.METRIC-STR-01");
    expect(gateSourceKey("/ai/briefings")).toBe("acceptance.sourceRef.briefings");
    expect(gateSourceKey("/idp/incidents")).toBe("acceptance.sourceRef.incidents");
    expect(gateSourceKey("/internal/x")).toBeNull();
  });
});
