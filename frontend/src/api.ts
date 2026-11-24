export type Mode = "solo" | "ai_assisted" | "interviewer";

export const MODE_LABEL: Record<Mode, string> = {
  solo: "Solo",
  ai_assisted: "AI-assisted",
  interviewer: "Interviewer",
};

export interface ProblemSummary {
  slug: string;
  title: string;
  difficulty: "Easy" | "Medium" | "Hard";
  topics: string[];
}

export interface Problem extends ProblemSummary {
  statement: string;
  constraints: string;
  examples: { input: string; output: string; explanation?: string }[];
  function_name: string;
  starter_code: string;
  visible_tests: { name: string; args: unknown[]; expected: unknown }[];
  hidden_test_count: number;
}

export interface SessionEvent {
  id: string;
  type: "prompt" | "ai_reply" | "run" | "submit";
  ts: number;
  text: string;
}

export interface TestRow {
  name: string;
  category: string;
  hidden: boolean;
  passed: boolean;
  error: string | null;
  ms: number | null;
  input?: string;
  expected?: string;
  got?: string;
}

export interface RunResult {
  compile_error: string | null;
  timed_out: boolean;
  results: TestRow[];
}

export interface Evidence {
  event_id: string;
  quote: string;
}

export interface DimensionScore {
  track: "readiness" | "prompting";
  dimension: string;
  weight: number;
  score: number;
  scored_by: "code" | "judge";
  evidence: Evidence[];
  rationale: string;
  judge_runs: number[];
}

export interface Evaluation {
  readiness: number;
  prompting: number | null;
  combined: number;
  label: string;
  rubric_version: string;
  judge_model: string | null;
  dimensions: DimensionScore[];
  rewrite: { event_id: string; original: string; rewritten: string; why: string } | null;
}

export interface Session {
  id: string;
  problem_slug: string;
  problem_title: string;
  mode: Mode;
  status: "active" | "scoring" | "scored" | "error";
  created_at: number;
  time_limit_s: number;
  events: SessionEvent[];
  last_code: string;
  submit_summary: {
    hidden_passed: number;
    hidden_total: number;
    failed_hidden: string[];
    compile_error: string | null;
  } | null;
  evaluation: Evaluation | null;
  error: string | null;
}

export interface RecentSession {
  id: string;
  problem_title: string;
  mode: Mode;
  status: Session["status"];
  created_at: number;
  combined: number | null;
  label: string | null;
}

export interface Health {
  ok: boolean;
  offline_mode: boolean;
  api_key_set: boolean;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new Error("Can't reach the backend. Check that the backend terminal is running on port 8000.");
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) => call<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => call<Health>("/health"),
  problems: () => call<ProblemSummary[]>("/problems"),
  problem: (slug: string) => call<Problem>(`/problems/${slug}`),
  recent: () => call<RecentSession[]>("/sessions"),
  session: (id: string) => call<Session>(`/sessions/${id}`),
  startSession: (problem_slug: string, mode: Mode) => post<Session>("/sessions", { problem_slug, mode }),
  run: (id: string, code: string) => post<RunResult>(`/sessions/${id}/run`, { code }),
  chat: (id: string, message: string, code: string) =>
    post<{ prompt: SessionEvent; reply: SessionEvent }>(`/sessions/${id}/chat`, { message, code }),
  submit: (id: string, code: string, ai_pasted_chars: number) =>
    post<Session>(`/sessions/${id}/submit`, { code, ai_pasted_chars }),
  rescore: (id: string) => post<Session>(`/sessions/${id}/rescore`, {}),
};

// ------------------------------------------------------------------ golden set

export interface GoldenSummary {
  total: number;
  labeled_by_you: number;
  labelers: string[];
  sessions: { id: string; mode: Mode; problem_title: string; labeled: boolean }[];
}

export interface GoldenDimension {
  id: string;
  name: string;
  track: "readiness" | "prompting";
  definition: string;
  anchors: Record<string, string>;
}

export interface GoldenSession {
  id: string;
  mode: Mode;
  problem: { title: string; statement: string; constraints: string; optimal_time: string; optimal_space: string };
  final_code: string;
  events: SessionEvent[];
  facts: Record<string, string>;
  dimensions: GoldenDimension[];
  your_label: { scores: Record<string, number>; notes: string; labeled_at: string } | null;
  rubric_version: string;
}

export const goldenApi = {
  summary: (labeler: string) => call<GoldenSummary>(`/golden/summary?labeler=${encodeURIComponent(labeler)}`),
  session: (id: string, labeler: string) =>
    call<GoldenSession>(`/golden/sessions/${encodeURIComponent(id)}?labeler=${encodeURIComponent(labeler)}`),
  label: (id: string, labeler: string, scores: Record<string, number>, notes: string) =>
    post<unknown>(`/golden/sessions/${encodeURIComponent(id)}/labels`, { labeler, scores, notes }),
  addFromApp: (sessionId: string) => post<{ golden_id: string }>(`/sessions/${sessionId}/golden`, {}),
};
