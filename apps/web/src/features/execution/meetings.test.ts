/** T-717F — pure logic for the /meetings preview + chair approval (R-DEC-103). */
import { describe, expect, it } from "vitest";
import type { Api } from "@aureon/shared-types";

type NaturalLanguagePreviewOut = Api.NaturalLanguagePreviewOut;
type PredictedActionOut = Api.PredictedActionOut;
import {
  MATCH_VARIANT,
  actionTitle,
  canCreateTask,
  matchKey,
  ownerMatch,
  ownerName,
  unresolvedOwners,
  visibleExtracted,
} from "./meetings";

const act = (params: Record<string, unknown>): PredictedActionOut => ({
  action_name: "ACT-create_action_item", params, confidence: 0.9,
});

describe("ownerMatch", () => {
  it("reads owner_match_status, defaulting to unmatched when absent/unknown", () => {
    expect(ownerMatch(act({ owner_match_status: "matched" }))).toBe("matched");
    expect(ownerMatch(act({ owner_match_status: "ambiguous" }))).toBe("ambiguous");
    expect(ownerMatch(act({}))).toBe("unmatched");
    expect(ownerMatch(act({ owner_match_status: "weird" }))).toBe("unmatched");
  });
});

describe("canCreateTask", () => {
  it("allows a Task only for a matched owner (R-DEC-103)", () => {
    expect(canCreateTask(act({ owner_match_status: "matched" }))).toBe(true);
    expect(canCreateTask(act({ owner_match_status: "ambiguous" }))).toBe(false);
    expect(canCreateTask(act({ owner_match_status: "unmatched" }))).toBe(false);
  });
  it("rejects a non create_action_item step", () => {
    expect(canCreateTask({ action_name: "ACT-other", params: { owner_match_status: "matched" }, confidence: 1 })).toBe(false);
  });
});

describe("badge + i18n helpers", () => {
  it("maps each status to a variant + key", () => {
    expect(MATCH_VARIANT.matched).toBe("success");
    expect(MATCH_VARIANT.ambiguous).toBe("warning");
    expect(MATCH_VARIANT.unmatched).toBe("danger");
    expect(matchKey("matched")).toBe("match.matched");
  });
});

describe("params readers", () => {
  it("reads owner name / title defensively", () => {
    expect(ownerName(act({ owner_name: "An" }))).toBe("An");
    expect(ownerName(act({ owner_name: "  " }))).toBeNull();
    expect(ownerName(act({}))).toBeNull();
    expect(actionTitle(act({ title: "Do X" }))).toBe("Do X");
    expect(actionTitle(act({}))).toBe("");
  });
});

describe("preview aggregates", () => {
  const preview = {
    predicted_actions: [
      act({ owner_match_status: "matched" }),
      act({ owner_match_status: "ambiguous" }),
      act({ owner_match_status: "unmatched" }),
    ],
  } as unknown as NaturalLanguagePreviewOut;

  it("counts owners needing human resolution", () => {
    expect(unresolvedOwners(preview)).toBe(2);
    expect(unresolvedOwners(undefined)).toBe(0);
  });

  it("drops masked / empty extracted fields", () => {
    const vis = visibleExtracted([
      { field: "a", value: 1 },
      { field: "b", value: null },
      { field: "c", value: { masked: true } },
    ]);
    expect(vis.map((f) => f.field)).toEqual(["a", "c"]);
  });
});
