import type { BlogDetail, StreamMessage } from "../api/types";

export type StepId = "research" | "context" | "plan" | "write" | "seo";
export type StepStatus = "pending" | "running" | "done" | "error";

export const STEP_LABELS: Record<StepId, string> = {
  research: "Nghiên cứu",
  context: "Đọc repository",
  plan: "Lập dàn ý",
  write: "Viết bài",
  seo: "SEO & thống kê",
};

export interface RunState {
  status: "idle" | "running" | "done" | "error" | "blocked";
  steps: Partial<Record<StepId, StepStatus>>;
  order: StepId[];
  outline: string;
  post: string;
  loopIterations: Record<string, number>;
  result: BlogDetail | null;
  error: string | null;
  blockedReason: string | null;
  log: string[];
}

export const initialRunState: RunState = {
  status: "idle",
  steps: {},
  order: ["plan", "write", "seo"],
  outline: "",
  post: "",
  loopIterations: {},
  result: null,
  error: null,
  blockedReason: null,
  log: [],
};

const isStep = (s: string): s is StepId => s in STEP_LABELS;

export type RunAction = { type: "start" } | { type: "reset" } | { type: "message"; msg: StreamMessage } | { type: "fail"; error: string };

export function runReducer(state: RunState, action: RunAction): RunState {
  switch (action.type) {
    case "reset":
      return initialRunState;
    case "start":
      return { ...initialRunState, status: "running" };
    case "fail":
      return { ...state, status: "error", error: action.error };
    case "message":
      return applyMessage(state, action.msg);
  }
}

function applyMessage(state: RunState, msg: StreamMessage): RunState {
  switch (msg.type) {
    case "step_started": {
      if (!isStep(msg.step)) return { ...state, log: [...state.log, `▶ ${msg.tool}`] };
      const order = state.order.includes(msg.step) ? state.order : [msg.step, ...state.order];
      return { ...state, order, steps: { ...state.steps, [msg.step]: "running" }, log: [...state.log, `▶ ${msg.tool}`] };
    }
    case "step_finished": {
      if (!isStep(msg.step)) return state;
      const status: StepStatus = msg.ok ? "done" : "error";
      return {
        ...state,
        steps: { ...state.steps, [msg.step]: status },
        log: [...state.log, `${msg.ok ? "✓" : "✗"} ${msg.tool}${msg.error ? `: ${msg.error}` : ""}`],
      };
    }
    case "state": {
      const v = msg.values;
      return {
        ...state,
        outline: typeof v.blog_outline === "string" ? v.blog_outline : state.outline,
        post: typeof v.blog_post === "string" ? v.blog_post : state.post,
        loopIterations: (v.loop_iterations as Record<string, number>) ?? state.loopIterations,
      };
    }
    case "blocked":
      return { ...state, status: "blocked", blockedReason: msg.reason };
    case "error":
      return { ...state, status: "error", error: msg.error };
    case "done":
      return {
        ...state,
        status: msg.result.blocked ? "blocked" : state.status === "error" ? "error" : "done",
        result: msg.result,
        outline: msg.result.outline || state.outline,
        post: msg.result.post || state.post,
        loopIterations: msg.result.loop_iterations ?? state.loopIterations,
      };
    default:
      return state;
  }
}

/** 0–100 progress for the lesson-style progress bar. */
export function progressPercent(state: RunState): number {
  if (state.status === "done") return 100;
  const total = state.order.length;
  if (!total) return 0;
  const score = state.order.reduce((acc, id) => {
    const s = state.steps[id];
    return acc + (s === "done" || s === "error" ? 1 : s === "running" ? 0.5 : 0);
  }, 0);
  return Math.round((score / total) * 100);
}

export function retriesFor(loopIterations: Record<string, number>, loop: string): number {
  return Math.max(0, (loopIterations[loop] ?? 1) - 1);
}
