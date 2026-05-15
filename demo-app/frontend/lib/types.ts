export type ScorePoint = { round: number; avg_score: number };

export type SkillSummary = {
  skill: string;
  vi: string;             // display label injected client-side from display-meta
  en?: string;
  student_model: string;
  teacher_model: string;
  judge_model: string;
  batch_size: number;
  rounds_run: number;
  final_score: number;
  best_round: number;
  best_score: number;
  score_history: ScorePoint[];
  rubric_cache_keys: Record<string, string>;
  last_run?: string;
  seed?: number;
};

export type RuleCheck = { name: string; passed: boolean; reason: string };

export type EvalEntry = {
  round: number;
  test_case_id: string;
  workflow: string;
  rule_score: number;
  llm_judge_score: number | null;
  hybrid_score: number;
  judge_rationale: string;
  rule_checks: RuleCheck[];
  prompt: string;
  output: string;
};

export type ApiCall = {
  round: number;
  stage: "student" | "judge" | "teacher";
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
  timestamp: string;
};

export type Kpis = {
  skills_count: number;
  total_improvement_pct: number;
  best_peak: { skill: string; score: number; round: number };
  total_cost: number;
};
