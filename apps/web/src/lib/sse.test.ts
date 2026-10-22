import { describe, expect, it } from "vitest";
import { parseSseChunk } from "./sse";

describe("parseSseChunk", () => {
  it("parses complete frames and keeps the remainder", () => {
    const { events, rest } = parseSseChunk('id: 1\nevent: token\ndata: {"delta":"Xin"}\n\nevent: done\ndata: {"a"');
    expect(events).toEqual([{ event: "token", data: { delta: "Xin" }, id: "1" }]);
    expect(rest).toBe('event: done\ndata: {"a"');
  });
});
