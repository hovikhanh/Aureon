/** U-34: the outcome step of an open deal is not reached. */
import { describe, expect, it } from "vitest";
import { stageProgress } from "./stage-progress";

const states = (stage: string) => Object.fromEntries(stageProgress(stage).map((s) => [s.stage, s.state]));

describe("stageProgress", () => {
  it("open deal: earlier stages reached, the current one marked, the outcome upcoming", () => {
    expect(states("proposal")).toEqual({ lead: "reached", qualified: "reached", proposal: "current", negotiation: "upcoming", closed_won: "upcoming" });
  });

  it("the first stage reaches nothing else", () => {
    expect(states("lead")).toEqual({ lead: "current", qualified: "upcoming", proposal: "upcoming", negotiation: "upcoming", closed_won: "upcoming" });
  });

  it.each(["closed_won", "closed_lost"])("%s: every open stage reached, the outcome is current", (stage) => {
    expect(states(stage)).toEqual({ lead: "reached", qualified: "reached", proposal: "reached", negotiation: "reached", [stage]: "current" });
  });
});
