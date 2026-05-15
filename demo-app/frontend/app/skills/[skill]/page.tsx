import Link from "next/link";
import { notFound } from "next/navigation";
import { TopBar } from "@/components/topbar";
import { SkillDetailClient } from "./skill-detail-client";
import { apiCallsBySkill, evalBySkill, skillMdBySkill, summaries, workflowsBySkill } from "@/lib/mock-data";

const BILINGUAL = true;

export default async function SkillDetailPage({
  params,
}: {
  params: Promise<{ skill: string }>;
}) {
  const { skill } = await params;
  const summary = summaries[skill];

  if (!summary) {
    notFound();
  }

  const workflows = workflowsBySkill[skill];
  const evalByRound = evalBySkill[skill];
  const apiCalls = apiCallsBySkill[skill];
  const skillMdByRound = skillMdBySkill[skill];

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
