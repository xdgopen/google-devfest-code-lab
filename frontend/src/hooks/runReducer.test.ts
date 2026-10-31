import { DETAIL, STREAM } from "../test/fixtures";
import { initialRunState, progressPercent, retriesFor, runReducer, type RunState } from "./runReducer";

const play = (msgs = STREAM, from: RunState = runReducer(initialRunState, { type: "start" })) =>
  msgs.reduce((s, msg) => runReducer(s, { type: "message", msg }), from);

describe("runReducer", () => {
  it("tracks steps, live outline/post and final result", () => {
    const mid = play(STREAM.slice(0, 3));
    expect(mid.status).toBe("running");
    expect(mid.steps.plan).toBe("running");
    expect(mid.outline).toBe(DETAIL.outline);
    expect(progressPercent(mid)).toBe(17);

    const end = play();
    expect(end.status).toBe("done");
    expect(end.steps).toEqual({ plan: "done", write: "done", seo: "done" });
    expect(end.result).toEqual(DETAIL);
    expect(progressPercent(end)).toBe(100);
    expect(end.log).toContain("✓ RobustBlogWriter");
  });

  it("adds optional steps (research/context) to the front", () => {
    const s = play([{ type: "step_started", tool: "fetch_repo_context", step: "context", author: "Blogger" }]);
    expect(s.order).toEqual(["context", "plan", "write", "seo"]);
  });

  it("records tool errors, guardrail blocks and stream errors", () => {
    const err = play([
      { type: "step_started", tool: "fetch_repo_context", step: "context", author: "B" },
      { type: "step_finished", tool: "fetch_repo_context", step: "context", author: "B", ok: false, error: "nope" },
    ]);
    expect(err.steps.context).toBe("error");
    expect(err.log.at(-1)).toBe("✗ fetch_repo_context: nope");

    const blocked = play([{ type: "blocked", reason: "prompt_injection" }, { type: "done", result: { ...DETAIL, blocked: true } }]);
    expect(blocked.status).toBe("blocked");
    expect(blocked.blockedReason).toBe("prompt_injection");

    const failed = play([{ type: "error", error: "quota" }, { type: "done", result: DETAIL }]);
    expect(failed.status).toBe("error");
    expect(runReducer(failed, { type: "fail", error: "net" }).error).toBe("net");
    expect(runReducer(failed, { type: "reset" })).toEqual(initialRunState);
  });

  it("ignores unknown tools for the step list", () => {
    const s = play([{ type: "step_started", tool: "x", step: "tool", author: "B" }]);
    expect(s.steps).toEqual({});
  });

  it("computes retries from loop iterations", () => {
    expect(retriesFor({ RobustBlogPlanner: 3 }, "RobustBlogPlanner")).toBe(2);
    expect(retriesFor({}, "RobustBlogWriter")).toBe(0);
  });
});
