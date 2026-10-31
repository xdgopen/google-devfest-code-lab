import { createSseParser } from "./sse";
import type { StreamMessage } from "./types";

describe("createSseParser", () => {
  it("parses frames split across chunks", () => {
    const got: StreamMessage[] = [];
    const parse = createSseParser((m) => got.push(m));
    parse('data: {"type":"run_st');
    parse('arted","session_id":"a"}\n');
    expect(got).toHaveLength(0);
    parse('\ndata: {"type":"error","error":"x"}\r\n\r\n');
    expect(got).toEqual([
      { type: "run_started", session_id: "a" },
      { type: "error", error: "x" },
    ]);
  });

  it("ignores malformed and empty frames", () => {
    const got: StreamMessage[] = [];
    const parse = createSseParser((m) => got.push(m));
    parse(": comment\n\ndata: {oops}\n\ndata: {\"type\":\"blocked\",\"reason\":\"r\"}\n\n");
    expect(got).toEqual([{ type: "blocked", reason: "r" }]);
  });
});
