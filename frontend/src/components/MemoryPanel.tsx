import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { MemoryInfo } from "../api/types";

const LABELS: Record<string, string> = { tone: "Giọng văn", audience: "Độc giả", length: "Độ dài", language: "Ngôn ngữ" };

export function MemoryPanel({ userId, refreshKey = 0 }: { userId: string; refreshKey?: number }) {
  const [memory, setMemory] = useState<MemoryInfo | null>(null);

  useEffect(() => {
    api.memory(userId).then(setMemory).catch(() => setMemory(null));
  }, [userId, refreshKey]);

  const prefs = Object.entries(memory?.preferences ?? {}).filter(([, v]) => v);
  return (
    <aside className="card memory" aria-labelledby="memory-title">
      <h2 id="memory-title" className="heading">🧠 Agent nhớ gì về bạn</h2>
      {prefs.length ? (
        <ul className="memory__prefs">
          {prefs.map(([k, v]) => (
            <li key={k}><span className="label-inline">{LABELS[k] ?? k}:</span> {v}</li>
          ))}
        </ul>
      ) : (
        <p className="hint-strong">
          Chưa có sở thích nào. Hãy nói với agent, ví dụ “luôn viết bằng tiếng Việt”, để nó ghi nhớ.
        </p>
      )}
      <p className="label">Bài gần đây</p>
      {memory?.post_history.length ? (
        <ul className="memory__history">
          {memory.post_history.slice(0, 5).map((p) => (
            <li key={p.session_id}>{p.title || p.slug} <span className="meta">· {p.date}</span></li>
          ))}
        </ul>
      ) : (
        <p className="hint-strong">Chưa có bài nào.</p>
      )}
    </aside>
  );
}
