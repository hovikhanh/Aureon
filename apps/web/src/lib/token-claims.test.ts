import { describe, expect, it } from "vitest";
import { scopePillarsOf } from "./token-claims";

const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");

describe("scopePillarsOf (display-only khối claim)", () => {
  it("reads scope_pillars from a JWT payload and a mock token", () => {
    expect(scopePillarsOf(`h.${b64({ scope_pillars: ["F"] })}.sig`)).toEqual(["F"]);
    expect(scopePillarsOf(`mock.${b64({ scope_pillars: ["C", "O"] })}`)).toEqual(["C", "O"]);
  });
  it("is empty (toàn khối) when absent, malformed or unknown", () => {
    expect(scopePillarsOf(`h.${b64({ sub: "x" })}.s`)).toEqual([]);
    expect(scopePillarsOf("garbage")).toEqual([]);
    expect(scopePillarsOf("h.%%%.s")).toEqual([]);
    expect(scopePillarsOf(`h.${b64({ scope_pillars: ["X", 3, "S"] })}.s`)).toEqual(["S"]);
  });
});
