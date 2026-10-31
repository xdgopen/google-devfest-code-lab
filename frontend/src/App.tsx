import { useEffect, useMemo, useState } from "react";
import { api, getUserId } from "./api/client";
import type { AppConfig, BlogDetail } from "./api/types";
import { ComposeForm } from "./components/ComposeForm";
import { HistoryList } from "./components/HistoryList";
import { MemoryPanel } from "./components/MemoryPanel";
import { ProgressTimeline } from "./components/ProgressTimeline";
import { ResultView } from "./components/ResultView";
import { useBlogRun } from "./hooks/useBlogRun";

type View = "write" | "history";

const BLOCK_REASONS: Record<string, string> = {
  prompt_injection: "Yêu cầu có dấu hiệu cố ghi đè chỉ dẫn của hệ thống.",
  blocked_topic: "Chủ đề vi phạm chính sách nội dung.",
  too_long: "Yêu cầu quá dài.",
  empty: "Yêu cầu trống.",
};

export default function App() {
  const userId = useMemo(getUserId, []);
  const [view, setView] = useState<View>("write");
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [opened, setOpened] = useState<BlogDetail | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const { state, start, cancel } = useBlogRun(userId);

  useEffect(() => {
    api.config().then(setConfig).catch(() => setConfig(null));
  }, []);

  useEffect(() => {
    if (state.status === "done" || state.status === "blocked") setRefreshKey((k) => k + 1);
  }, [state.status]);

  const openBlog = async (sessionId: string) => {
    setOpened(await api.getBlog(userId, sessionId));
    setView("write");
  };

  const running = state.status === "running";
  const liveResult = state.result ?? (state.post || state.outline
    ? { post: state.post, outline: state.outline, final: "", seo: {}, stats: {} }
    : null);
  const shown = running || state.status !== "idle" ? liveResult : opened;

  return (
    <div className="app">
      <a href="#main" className="skip-link">Bỏ qua tới nội dung</a>
      <header className="topbar">
        <div className="brand">
          <span className="brand__logo" aria-hidden="true">B</span>
          <span>
            <span className="display">Blogger Agent</span>
            <span className="brand__sub">Lập dàn ý → Viết → Kiểm duyệt, chạy bằng Google ADK</span>
          </span>
        </div>
        <nav className="nav" aria-label="Điều hướng chính">
          <button className={`nav__btn ${view === "write" ? "nav__btn--active" : ""}`} aria-current={view === "write" ? "page" : undefined} onClick={() => setView("write")}>
            ✍ Viết bài
          </button>
          <button className={`nav__btn ${view === "history" ? "nav__btn--active" : ""}`} aria-current={view === "history" ? "page" : undefined} onClick={() => setView("history")}>
            📚 Lịch sử
          </button>
        </nav>
      </header>

      <main id="main" className="layout">
        {view === "write" ? (
          <>
            <div className="col-main">
              <ComposeForm
                maxChars={config?.limits.max_input_chars ?? 2000}
                disabled={running}
                onSubmit={(message, prefs) => {
                  setOpened(null);
                  start(message, prefs);
                }}
              />
              {state.status === "blocked" && (
                <p className="alert alert--warning" role="alert">
                  🛡 Guardrail đã chặn yêu cầu. {BLOCK_REASONS[state.blockedReason ?? ""] ?? state.result?.final}
                </p>
              )}
              {state.status === "error" && (
                <p className="alert alert--error" role="alert">⚠ Có lỗi xảy ra: {state.error}</p>
              )}
              {state.status !== "idle" && state.status !== "blocked" && (
                <ProgressTimeline state={state} onCancel={cancel} />
              )}
              {shown && (shown.post || shown.outline) && (
                <ResultView userId={userId} result={shown} />
              )}
            </div>
            <div className="col-side">
              <MemoryPanel userId={userId} refreshKey={refreshKey} />
              {config && (
                <p className="meta footer-meta">
                  Model: <code>{config.model}</code> · {config.features.persistent_sessions ? "Session lưu trong DB" : "Session in-memory"}
                </p>
              )}
            </div>
          </>
        ) : (
          <div className="col-full">
            <h1 className="display">Bài viết của bạn</h1>
            <HistoryList userId={userId} onOpen={openBlog} refreshKey={refreshKey} />
          </div>
        )}
      </main>
    </div>
  );
}
