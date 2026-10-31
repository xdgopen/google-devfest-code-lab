import type { BlogDetail, StreamMessage } from "../api/types";

export const DETAIL: BlogDetail = {
  session_id: "s1",
  title: "Planning Loops",
  topic: "Planning loops",
  has_post: true,
  words: 120,
  updated_at: 1761900000,
  preferences: { tone: "Thân thiện" },
  outline: "# Planning Loops\n\n## Intro",
  post: "# Planning Loops\n\nAgents plan first.\n\n```py\nprint(1)\n```",
  seo: { slug: "planning-loops", meta_description: "Agents plan first.", keywords: ["agents", "loops"] },
  stats: { word_count: 120, reading_time_minutes: 1, code_block_count: 1 },
  loop_iterations: { RobustBlogPlanner: 2, RobustBlogWriter: 1 },
  final: "**Alternate titles**\n1. A\n2. B\n3. C",
  blocked: false,
};

export const STREAM: StreamMessage[] = [
  { type: "run_started", session_id: "s1" },
  { type: "step_started", tool: "RobustBlogPlanner", step: "plan", author: "Blogger" },
  { type: "state", values: { blog_outline: DETAIL.outline, loop_iterations: { RobustBlogPlanner: 2 } } },
  { type: "step_finished", tool: "RobustBlogPlanner", step: "plan", author: "Blogger", ok: true },
  { type: "step_started", tool: "RobustBlogWriter", step: "write", author: "Blogger" },
  { type: "state", values: { blog_post: DETAIL.post } },
  { type: "step_finished", tool: "RobustBlogWriter", step: "write", author: "Blogger", ok: true },
  { type: "step_started", tool: "seo_suggestions", step: "seo", author: "Blogger" },
  { type: "step_finished", tool: "seo_suggestions", step: "seo", author: "Blogger", ok: true },
  { type: "done", result: DETAIL },
];

export function sseBody(messages: StreamMessage[]): ReadableStream<Uint8Array> {
  const text = messages.map((m) => `data: ${JSON.stringify(m)}\n\n`).join("");
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(controller) {
      // split in odd chunks to exercise the incremental parser
      for (let i = 0; i < bytes.length; i += 37) controller.enqueue(bytes.slice(i, i + 37));
      controller.close();
    },
  });
}
