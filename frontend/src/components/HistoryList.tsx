import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { BlogSummary } from "../api/types";

interface Props {
  userId: string;
  onOpen: (sessionId: string) => void;
  refreshKey?: number;
}

export function HistoryList({ userId, onOpen, refreshKey = 0 }: Props) {
  const [items, setItems] = useState<BlogSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.listBlogs(userId).then((r) => setItems(r.items)).catch((e: Error) => setError(e.message));
  }, [userId]);

  useEffect(load, [load, refreshKey]);

  const remove = async (id: string) => {
    if (!window.confirm("Xoá bài viết này khỏi lịch sử?")) return;
    try {
      await api.deleteBlog(userId, id);
      setItems((list) => list?.filter((i) => i.session_id !== id) ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (error) return <p className="alert alert--error" role="alert">⚠ Không tải được lịch sử: {error}</p>;
  if (!items) return <p className="hint">Đang tải…</p>;
  if (!items.length)
    return (
      <div className="card empty-state">
        <p className="heading">Chưa có bài nào</p>
        <p>Viết bài đầu tiên của bạn ở tab “Viết bài”.</p>
      </div>
    );

  return (
    <ul className="history" aria-label="Lịch sử bài viết">
      {items.map((item) => (
        <li key={item.session_id} className="card history__item">
          <div>
            <p className="history__title">{item.title}</p>
            <p className="meta">
              {new Date(item.updated_at * 1000).toLocaleString("vi-VN")}
              {item.words ? ` · ${item.words} từ` : ""}
              {!item.has_post && " · chưa hoàn tất"}
            </p>
          </div>
          <div className="actions">
            <button type="button" className="btn btn--secondary" onClick={() => onOpen(item.session_id)}>
              Mở
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              aria-label={`Xoá ${item.title}`}
              onClick={() => remove(item.session_id)}
            >
              Xoá
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
