import { useState, type FormEvent } from "react";
import type { Preferences } from "../api/types";

export const SAMPLE_TOPICS = [
  "How to build an AI agent using planning loops",
  "Explain the difference between REST and gRPC in microservices",
  "A guide to using Python's asyncio for backend concurrency",
  "Why developers should use Docker for local database setups",
];

const OPTIONS: Record<keyof Preferences, { label: string; values: string[] }> = {
  tone: { label: "Giọng văn", values: ["Thân thiện", "Chuyên nghiệp", "Hài hước"] },
  audience: { label: "Độc giả", values: ["Người mới", "Kỹ sư", "Chuyên gia"] },
  length: { label: "Độ dài", values: ["Ngắn (~800 từ)", "Vừa (~1500 từ)", "Dài (~2500 từ)"] },
  language: { label: "Ngôn ngữ", values: ["Vietnamese", "English"] },
};

const GITHUB_RE = /^https?:\/\/(www\.)?github\.com\/[\w.-]+\/[\w.-]+\/?$/i;

export interface ComposeValues {
  topic: string;
  githubUrl: string;
  preferences: Preferences;
}

export function validateCompose(v: ComposeValues, maxChars: number): Record<string, string> {
  const errors: Record<string, string> = {};
  const topic = v.topic.trim();
  if (topic.length < 5) errors.topic = "Hãy nhập chủ đề (ít nhất 5 ký tự).";
  else if (topic.length > maxChars) errors.topic = `Chủ đề quá dài (tối đa ${maxChars} ký tự).`;
  if (v.githubUrl.trim() && !GITHUB_RE.test(v.githubUrl.trim()))
    errors.githubUrl = "Chỉ hỗ trợ URL repository dạng https://github.com/owner/repo";
  return errors;
}

export function buildMessage(v: ComposeValues): string {
  const repo = v.githubUrl.trim();
  return repo ? `${v.topic.trim()}\n\nGitHub repository: ${repo}` : v.topic.trim();
}

interface Props {
  maxChars: number;
  disabled?: boolean;
  defaults?: Preferences;
  onSubmit: (message: string, preferences: Preferences) => void;
}

export function ComposeForm({ maxChars, disabled, defaults, onSubmit }: Props) {
  const [values, setValues] = useState<ComposeValues>({ topic: "", githubUrl: "", preferences: { ...defaults } });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const found = validateCompose(values, maxChars);
    setErrors(found);
    if (Object.keys(found).length === 0) onSubmit(buildMessage(values), values.preferences);
  };

  const setPref = (key: keyof Preferences, value: string) =>
    setValues((v) => ({
      ...v,
      preferences: { ...v.preferences, [key]: v.preferences[key] === value ? undefined : value },
    }));

  return (
    <form className="card compose" onSubmit={submit} noValidate aria-label="Tạo bài blog mới">
      <h2 className="heading">Hôm nay bạn muốn viết về gì?</h2>

      <label htmlFor="topic" className="label">Chủ đề</label>
      <textarea
        id="topic"
        className="input"
        rows={3}
        value={values.topic}
        placeholder="Ví dụ: How to build an AI agent using planning loops"
        aria-invalid={Boolean(errors.topic)}
        aria-describedby={errors.topic ? "topic-error" : "topic-hint"}
        onChange={(e) => setValues({ ...values, topic: e.target.value })}
      />
      {errors.topic ? (
        <p id="topic-error" className="field-error" role="alert">⚠ {errors.topic}</p>
      ) : (
        <p id="topic-hint" className="hint">{values.topic.length}/{maxChars} ký tự</p>
      )}

      <div className="samples" aria-label="Chủ đề gợi ý">
        {SAMPLE_TOPICS.map((t) => (
          <button type="button" key={t} className="chip" onClick={() => setValues({ ...values, topic: t })}>
            {t}
          </button>
        ))}
      </div>

      <label htmlFor="github" className="label">GitHub repository (tuỳ chọn)</label>
      <input
        id="github"
        className="input"
        type="url"
        value={values.githubUrl}
        placeholder="https://github.com/google/adk-python"
        aria-invalid={Boolean(errors.githubUrl)}
        aria-describedby={errors.githubUrl ? "github-error" : undefined}
        onChange={(e) => setValues({ ...values, githubUrl: e.target.value })}
      />
      {errors.githubUrl && <p id="github-error" className="field-error" role="alert">⚠ {errors.githubUrl}</p>}

      <div className="pref-grid">
        {(Object.keys(OPTIONS) as (keyof Preferences)[]).map((key) => (
          <fieldset key={key} className="pref">
            <legend className="label">{OPTIONS[key].label}</legend>
            <div className="chips">
              {OPTIONS[key].values.map((value) => {
                const selected = values.preferences[key] === value;
                return (
                  <button
                    type="button"
                    key={value}
                    className={`chip ${selected ? "chip--selected" : ""}`}
                    aria-pressed={selected}
                    onClick={() => setPref(key, value)}
                  >
                    {selected && <span aria-hidden="true">✓ </span>}
                    {value}
                  </button>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>

      <button type="submit" className="btn btn--primary btn--block" disabled={disabled}>
        {disabled ? "Đang viết…" : "Bắt đầu viết"}
      </button>
    </form>
  );
}
