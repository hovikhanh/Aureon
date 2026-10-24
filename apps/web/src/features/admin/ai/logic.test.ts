/** TC-M16-16/20 (unit) — SCR-64 pure rules + KillSwitchBanner state (T-644F/T-646F). */
import { describe, expect, it } from "vitest";
import type { KillSwitch, Tool } from "./types";
import { agentName, bannerHasAdminLink, bannerState, cappedDefault, costTone, filterTools, levelKey, levelOptions, matrixTools, parseMoney } from "./logic";

const ks = (p: Partial<KillSwitch>) => ({ enabled: false, mode: "WRITE_OFF", agents: [], reason: null, changed_by: null, changed_at: null, ...p }) as KillSwitch;

describe("KillSwitchBanner state", () => {
  it("hidden when off or on load error", () => {
    expect(bannerState(ks({ enabled: false }), false)).toBeNull();
    expect(bannerState(undefined, true)).toBeNull();
    expect(bannerState(ks({ enabled: true }), true)).toBeNull();
  });
  it("text by mode + agent scope", () => {
    expect(bannerState(ks({ enabled: true, mode: "WRITE_OFF" }), false)).toEqual({ textKey: "killSwitch.banner.WRITE_OFF", scope: "all" });
    expect(bannerState(ks({ enabled: true, mode: "L0", agents: ["ceo"] }), false)).toEqual({ textKey: "killSwitch.banner.L0", scope: ["ceo"] });
  });
  it("admin link only for ADM/CEO", () => {
    expect(["ADM", "CEO", "DIR", "MGR", "EMP"].map(bannerHasAdminLink)).toEqual([true, true, false, false, false]);
  });
});

describe("autonomy helpers", () => {
  it("labels + L3/L4 disabled under the M1 ceiling", () => {
    expect(levelKey("L2")).toBe("level.L2");
    expect(levelKey("bogus")).toBe("level.L0");
    expect(levelOptions().filter((o) => o.disabled).map((o) => o.value)).toEqual(["L3", "L4"]);
  });
  it("root default L3 is struck through and shown as L2", () => {
    expect(cappedDefault("L3")).toMatchObject({ struck: "L3", shown: "L2" });
    expect(cappedDefault("L1")).toMatchObject({ struck: null, shown: "L1" });
  });
  it("cost tone 80/100 %", () => {
    expect([10, 80, 99.9, 100, 140].map(costTone)).toEqual(["ok", "warning", "warning", "danger", "danger"]);
  });
  it("parses VND thresholds written with dots", () => {
    expect(parseMoney("50.000.000")).toBe(50_000_000);
    expect(parseMoney("")).toBeNull();
  });
  it("matrix keeps only WRITE/EXECUTION; filters by kind", () => {
    const tools = [{ name: "a", kind: "READ" }, { name: "b", kind: "WRITE" }, { name: "c", kind: "EXECUTION" }, { name: "d", kind: "APPROVAL" }] as Tool[];
    expect(matrixTools(tools).map((t) => t.name)).toEqual(["b", "c"]);
    expect(filterTools(tools, { kind: "READ", domain: "", agent: "", mine: false }).map((t) => t.name)).toEqual(["a"]);
  });
});

describe("agentName (T-651: no hard-coded legacy label)", () => {
  const a = { name_vi: "CEO Agent VI", name_en: "CEO Agent" };
  it("uses the catalog name per locale", () => {
    expect(agentName(a, "ceo", "vi")).toBe("CEO Agent VI");
    expect(agentName(a, "ceo", "en")).toBe("CEO Agent");
  });
  it("v2.1 `assistant` → i18n label when given, else the raw code", () => {
    expect(agentName(undefined, "assistant", "vi", "Trợ lý (v2.1)")).toBe("Trợ lý (v2.1)");
    expect(agentName(undefined, "assistant", "vi")).toBe("assistant");
    expect(agentName(undefined, "other", "en", "x")).toBe("other");
  });
});
