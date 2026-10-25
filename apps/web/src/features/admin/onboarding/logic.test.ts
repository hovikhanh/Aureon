import { afterEach, describe, expect, it, vi } from "vitest";
import { canOpen, clockTone, currentStep, dropHidden, elapsedMs, firstMissing, formatElapsed, randomPassword, STEPS, suggestRole, type OnboardingState } from "./logic";

const st = (done: string[], extra: Partial<OnboardingState> = {}): OnboardingState => ({
  status: "in_progress", version: 3,
  steps: Object.fromEntries(STEPS.map((k) => [k, { status: done.includes(k) ? (k === "goals_import" ? "skipped" : "done") : "pending" }])),
  ...extra,
});

describe("SCR-66 onboarding logic (TC-M16-15)", () => {
  afterEach(() => vi.useRealTimers());

  it("resumes at the first open step after reload", () => {
    expect(currentStep(st([]))).toBe("company");
    expect(currentStep(st(["company", "org_import"]))).toBe("review");
    expect(currentStep(st(["company", "org_import", "review", "users", "goals_import"]))).toBe("finish");
    expect(currentStep(st([], { status: "completed" }))).toBe("finish");
    expect(canOpen(st(["company"]), "company")).toBe(true);
    expect(canOpen(st(["company"]), "review")).toBe(false);
    expect(canOpen(st([]), "finish")).toBe(true);
  });

  it("missing_steps → back to the first missing step in wizard order", () => {
    expect(firstMissing(["users", "org_import"])).toBe("org_import");
    expect(firstMissing(undefined)).toBeNull();
  });

  it("clock colour by threshold (fake timer): ≤ 8 h green, ≤ 24 h yellow, > 24 h red", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-20T00:00:00Z"));
    const s = st([], { started_at: "2026-10-20T00:00:00Z" });
    vi.advanceTimersByTime(8 * 3_600_000);
    expect(clockTone(elapsedMs(s, Date.now()))).toBe("ok");
    vi.advanceTimersByTime(60_000);
    expect(clockTone(elapsedMs(s, Date.now()))).toBe("warn");
    vi.advanceTimersByTime(16 * 3_600_000);
    expect(clockTone(elapsedMs(s, Date.now()))).toBe("late");
    expect(formatElapsed(elapsedMs(s, Date.now()))).toBe("24:01");
    expect(elapsedMs({ ...s, completed_at: "2026-10-20T02:30:00Z" }, Date.now())).toBe(2.5 * 3_600_000);
  });

  it("role suggestion, password ≥ 12, level-4 columns dropped", () => {
    expect(suggestRole({ employee_id: "e", employee_code: "NV-1", full_name: "A", department_id: "d", is_head: true })).toBe("MGR");
    expect(suggestRole({ employee_id: "e", employee_code: "NV-2", full_name: "B", department_id: "d", is_head: false })).toBe("EMP");
    expect(randomPassword(4)).toHaveLength(12);
    expect(randomPassword()).toHaveLength(16);
    expect(dropHidden({ "Mã NV": "employee_code", "Lương (VND)": "salary", X: null }, ["employee_code"])).toEqual({ mapping: { "Mã NV": "employee_code", "Lương (VND)": null, X: null }, dropped: ["Lương (VND)"] });
  });
});
