import { createSseParser } from "./sse";
import type { AppConfig, BlogDetail, BlogSummary, MemoryInfo, Preferences, StreamMessage } from "./types";

const USER_KEY = "blogger.userId";

export function getUserId(): string {
  try {
    const existing = localStorage.getItem(USER_KEY);
    if (existing && /^[A-Za-z0-9_-]{1,64}$/.test(existing)) return existing;
    const id = `u_${(crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)).replace(/[^A-Za-z0-9]/g, "").slice(0, 24)}`;
    localStorage.setItem(USER_KEY, id);
    return id;
  } catch {
    return "anonymous";
  }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not json */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  config: () => fetch("/api/config").then((r) => json<AppConfig>(r)),

  createSession: (userId: string, preferences: Preferences) =>
    fetch(`/api/users/${userId}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preferences }),
    }).then((r) => json<{ session_id: string }>(r)),

  listBlogs: (userId: string) =>
    fetch(`/api/users/${userId}/blogs`).then((r) => json<{ items: BlogSummary[] }>(r)),

  getBlog: (userId: string, sessionId: string) =>
    fetch(`/api/users/${userId}/blogs/${sessionId}`).then((r) => json<BlogDetail>(r)),

  deleteBlog: async (userId: string, sessionId: string) => {
    const res = await fetch(`/api/users/${userId}/blogs/${sessionId}`, { method: "DELETE" });
    if (!res.ok && res.status !== 204) throw new Error(res.statusText);
  },

  memory: (userId: string) => fetch(`/api/users/${userId}/memory`).then((r) => json<MemoryInfo>(r)),

  exportUrl: (userId: string, sessionId: string, format: "md" | "html") =>
    `/api/users/${userId}/blogs/${sessionId}/export?format=${format}`,

  async run(
    userId: string,
    sessionId: string,
    message: string,
    onMessage: (msg: StreamMessage) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const res = await fetch(`/api/users/${userId}/sessions/${sessionId}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ message }),
      signal,
    });
    if (!res.ok || !res.body) {
      await json(res);
      return;
    }
    const parse = createSseParser(onMessage);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      parse(decoder.decode(value, { stream: true }));
    }
    parse(decoder.decode() + "\n\n");
  },
};
