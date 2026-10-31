export interface Preferences {
  tone?: string;
  audience?: string;
  length?: string;
  language?: string;
}

export interface Seo {
  slug?: string;
  meta_description?: string;
  keywords?: string[];
  keyword_density_percent?: Record<string, number>;
}

export interface Stats {
  word_count?: number;
  reading_time_minutes?: number;
  heading_count?: number;
  code_block_count?: number;
}

export interface BlogSummary {
  session_id: string;
  title: string;
  topic: string;
  has_post: boolean;
  words?: number | null;
  updated_at: number;
  preferences: Preferences;
}

export interface BlogDetail extends BlogSummary {
  outline: string;
  post: string;
  seo: Seo;
  stats: Stats;
  loop_iterations: Record<string, number>;
  final: string;
  blocked: boolean;
}

export interface AppConfig {
  model: string;
  auth_mode: string;
  features: { research: boolean; memory: boolean; persistent_sessions: boolean; artifact_bucket: boolean };
  limits: { max_input_chars: number; max_loop_iterations: number };
}

export interface MemoryInfo {
  preferences: Preferences;
  post_history: { session_id: string; title: string; slug: string; date: string; words?: number }[];
}

export type StreamMessage =
  | { type: "run_started"; session_id: string }
  | { type: "step_started"; tool: string; step: string; author: string }
  | { type: "step_finished"; tool: string; step: string; author: string; ok: boolean; error?: string | null }
  | { type: "message"; author: string; text: string }
  | { type: "state"; values: Record<string, unknown> }
  | { type: "blocked"; reason: string }
  | { type: "error"; error: string }
  | { type: "done"; result: BlogDetail };
