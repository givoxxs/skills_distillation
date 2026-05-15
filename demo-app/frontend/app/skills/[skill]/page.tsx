import Link from "next/link";
import { notFound } from "next/navigation";
import { TopBar } from "@/components/topbar";
import { SkillDetailClient } from "./skill-detail-client";
import {
  apiCallsBySkill,
  evalBySkill,
  workflowsBySkill as MOCK_WORKFLOWS,
} from "@/lib/mock-data";
import { fetchAvailableRounds, fetchSkillMd, fetchSummary } from "@/lib/api";
import { displayMetaFor } from "@/lib/display-meta";
import type { SkillSummary } from "@/lib/types";

const BILINGUAL = true;
const SUPPORTED = new Set(["docx", "internal-comms", "slack-gif-creator"]);

export default async function SkillDetailPage({
  params,
}: {
  params: Promise<{ skill: string }>;
}) {
  const { skill } = await params;
  if (!SUPPORTED.has(skill)) notFound();

  let realSummary;
  let availableRounds: { rounds: number[] };
  try {
    [realSummary, availableRounds] = await Promise.all([
      fetchSummary(skill),
      fetchAvailableRounds(skill),
    ]);
  } catch (e) {
    throw new Error(
      `Backend không phản hồi tại ${process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000"}. ` +
        `Đảm bảo \`make dev\` (hoặc \`uvicorn\` riêng) đang chạy.\n\n${(e as Error).message}`
    );
  }

  // Fetch all real SKILL.md files in parallel
  const skillMdResponses = await Promise.all(
    availableRounds.rounds.map((r) => fetchSkillMd(skill, r))
  );
  const skillMdByRound: Record<number, string> = {};
  for (const r of skillMdResponses) {
    skillMdByRound[r.round] = r.content;
  }
  // Fill any gap (e.g. round 0 missing) by inheriting nearest prior round
  for (let r = 0; r <= realSummary.rounds_run; r++) {
    if (skillMdByRound[r]) continue;
    for (let prior = r; prior >= 0; prior--) {
      if (skillMdByRound[prior]) {
        skillMdByRound[r] = skillMdByRound[prior];
        break;
      }
    }
  }

  const meta = displayMetaFor(skill);
  const summary: SkillSummary = {
    ...realSummary,
    vi: meta.vi,
    en: meta.en,
  };

  // Workflows derived from real rubric_cache_keys when available, fallback to mock list
  const workflows =
    Object.keys(realSummary.rubric_cache_keys || {}).length > 0
      ? Object.keys(realSummary.rubric_cache_keys).sort()
      : MOCK_WORKFLOWS[skill] || [];

  // Test cases + cost — still mock (eval_detail.jsonl / api_calls.jsonl
  // are not yet emitted by distillation_v2). Surface this in the UI.
  const evalByRound = evalBySkill[skill] || {};
  const apiCalls = apiCallsBySkill[skill] || [];

  return (
    <>
      <TopBar
        crumbs={[
          { label: "Tổng quan", href: "/" },
          { label: BILINGUAL ? "Skills" : "Skills", href: "/" },
          { label: <span className="mono">{summary.skill}</span> },
        ]}
        actions={
          <Link href="/run" className="btn btn-sm">
            Chạy mini cho skill này
          </Link>
        }
      />
      <SkillDetailClient
        summary={summary}
        workflows={workflows}
        evalByRound={evalByRound}
        apiCalls={apiCalls}
        skillMdByRound={skillMdByRound}
        bilingual={BILINGUAL}
      />
    </>
  );
}
