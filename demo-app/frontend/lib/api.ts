/* Server-side fetch helpers for the FastAPI backend. Used inside Server
 * Components (async page.tsx) so the result is rendered on the server. */

import type { SkillSummary } from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000";

const FETCH_OPTS: RequestInit = {
  // Always refresh — these are static files but they can change between runs.
  // Demo scale is tiny so no caching tradeoff worth tuning.
  cache: "no-store",
};

export type SkillListEntry = {
  name: string;
  rounds_run: number;
  final_score: number;
  best_score: number;
  best_round: number;
  student_model: string;
  teacher_model: string;
};

export type RealSummary = Omit<SkillSummary, "vi" | "en" | "last_run" | "seed">;

export type SkillMdResponse = {
  requested_round: number;
  round: number;
  content: string;
  fallback: boolean;
};

async function get<T>(path: string): Promise<T> {
  const url = `${BACKEND_URL}${path}`;
  const res = await fetch(url, FETCH_OPTS);
  if (!res.ok) {
    throw new Error(`fetch ${path} → ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export function fetchSkills(): Promise<SkillListEntry[]> {
  return get<SkillListEntry[]>("/api/skills");
}

export function fetchSummary(skill: string): Promise<RealSummary> {
  return get<RealSummary>(`/api/skills/${encodeURIComponent(skill)}/summary`);
}

export function fetchAvailableRounds(skill: string): Promise<{ rounds: number[] }> {
  return get<{ rounds: number[] }>(
    `/api/skills/${encodeURIComponent(skill)}/available-rounds`
  );
}

export function fetchSkillMd(skill: string, round: number): Promise<SkillMdResponse> {
  return get<SkillMdResponse>(
    `/api/skills/${encodeURIComponent(skill)}/skill-md?round=${round}`
  );
}

export { BACKEND_URL };
