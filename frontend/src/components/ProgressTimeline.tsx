import { STEP_LABELS, progressPercent, retriesFor, type RunState, type StepStatus } from "../hooks/runReducer";

const STATUS_TEXT: Record<StepStatus, { icon: string; text: string }> = {
  pending: { icon: "○", text: "Đang chờ" },
  running: { icon: "◐", text: "Đang chạy" },
  done: { icon: "✓", text: "Hoàn tất" },
  error: { icon: "✗", text: "Lỗi" },
};

export function ProgressTimeline({ state, onCancel }: { state: RunState; onCancel?: () => void }) {
  const percent = progressPercent(state);
  const planRetries = retriesFor(state.loopIterations, "RobustBlogPlanner");
  const writeRetries = retriesFor(state.loopIterations, "RobustBlogWriter");

  return (
    <section className="card" aria-labelledby="progress-title">
      <div className="row-between">
        <h2 id="progress-title" className="heading">Tiến trình</h2>
        {state.status === "running" && onCancel && (
          <button type="button" className="btn btn--ghost" onClick={onCancel}>Huỷ</button>
        )}
      </div>

      <div
        className="progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label="Tiến độ viết bài"
      >
        <div className="progress__fill" style={{ width: `${percent}%` }} />
      </div>

      <ol className="timeline">
        {state.order.map((id) => {
          const status = state.steps[id] ?? "pending";
          const retries = id === "plan" ? planRetries : id === "write" ? writeRetries : 0;
          return (
            <li key={id} className={`timeline__item timeline__item--${status}`}>
              <span className="timeline__icon" aria-hidden="true">{STATUS_TEXT[status].icon}</span>
              <span className="timeline__label">{STEP_LABELS[id]}</span>
              <span className="timeline__status">{STATUS_TEXT[status].text}</span>
              {retries > 0 && (
                <span className="badge" title="Số lần validator yêu cầu viết lại">↻ {retries} lần sửa</span>
              )}
            </li>
          );
        })}
      </ol>

      <p className="sr-only" aria-live="polite">
        {state.status === "done" ? "Bài viết đã hoàn tất" : state.log[state.log.length - 1] ?? ""}
      </p>
    </section>
  );
}
