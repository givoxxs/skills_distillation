import Link from "next/link";
import { Bi } from "@/components/bi";
import { Icon } from "@/components/icon";
import { TopBar } from "@/components/topbar";
import { Sparkline } from "@/components/charts/sparkline";
import { fetchSummary, type RealSummary } from "@/lib/api";
import { displayMetaFor } from "@/lib/display-meta";

const BILINGUAL = true;
const SKILLS = ["docx", "internal-comms", "slack-gif-creator"] as const;

type Kpis = {
  skills_count: number;
  total_improvement_pct: number;
  best_peak: { skill: string; score: number; round: number };
};

function computeKpis(summaries: RealSummary[]): Kpis {
  const totalImprovement =
    summaries.reduce((acc, s) => {
      const r1 = s.score_history[0]?.avg_score ?? 0;
      return acc + (s.best_score - r1) / Math.max(r1, 1e-9);
    }, 0) / Math.max(summaries.length, 1);
  const best = summaries.reduce((a, b) => (a.best_score > b.best_score ? a : b));
  return {
    skills_count: summaries.length,
    total_improvement_pct: +(totalImprovement * 100).toFixed(1),
    best_peak: { skill: best.skill, score: best.best_score, round: best.best_round },
  };
}

export default async function OverviewPage() {
  const summaries = await Promise.all(SKILLS.map(fetchSummary));
  const kpis = computeKpis(summaries);

  return (
    <>
      <TopBar
        crumbs={[{ label: BILINGUAL ? "Tổng quan · Overview" : "Tổng quan" }]}
        actions={
          <Link href="/run" className="btn btn-primary">
            <Icon name="play" size={16} />
            Chạy mini distillation
          </Link>
        }
      />

      <div className="page stack-lg">
        <div className="stack-sm" style={{ maxWidth: 720 }}>
          <div className="eyebrow">
            <Bi
              vi="Đồ án — Skill distillation"
              en={BILINGUAL ? "Thesis — Skill distillation" : null}
              showEn={BILINGUAL}
            />
          </div>
          <h1 className="h-display">
            Chưng cất{" "}
            <em style={{ fontStyle: "italic", color: "var(--primary)" }}>SKILL.md</em>{" "}
            xuống mô hình nhỏ.
          </h1>
          <p
            className="muted"
            style={{ fontSize: "var(--text-lg)", lineHeight: 1.55, maxWidth: 640 }}
          >
            Vòng lặp Teacher–Student–Judge viết lại tài liệu hướng dẫn của Anthropic để Gemma 4-26B
            thực thi đạt mức gần với Claude. Bảng dưới là kết quả thực nghiệm trên ba skill, mỗi
            skill 8–10 vòng.
          </p>
        </div>

        <div className="grid-3">
          <div className="kpi-card">
            <div className="kpi-label">
              <Bi vi="Skill đã chưng cất" en={BILINGUAL ? "Skills distilled" : null} showEn={BILINGUAL} />
            </div>
            <div className="kpi-value tnum">{kpis.skills_count}</div>
            <div className="kpi-meta">docx · internal-comms · slack-gif-creator</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">
              <Bi vi="Cải thiện trung bình" en={BILINGUAL ? "Avg. improvement" : null} showEn={BILINGUAL} />
            </div>
            <div className="kpi-value tnum" style={{ color: "var(--accent)" }}>
              +{kpis.total_improvement_pct}%
            </div>
            <div className="kpi-meta">tính theo (Peak − R1) / R1</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">
              <Bi vi="Điểm peak cao nhất" en={BILINGUAL ? "Best peak score" : null} showEn={BILINGUAL} />
            </div>
            <div className="kpi-value tnum">{kpis.best_peak.score.toFixed(3)}</div>
            <div className="kpi-meta">
              <span className="mono">{kpis.best_peak.skill}</span> tại R{kpis.best_peak.round}
            </div>
          </div>
        </div>

        <div className="stack">
          <div className="row-between">
            <h2 className="h2">
              <Bi
                vi="Ba skill, ba quỹ đạo học"
                en={BILINGUAL ? "Three skills, three learning trajectories" : null}
                showEn={BILINGUAL}
              />
            </h2>
            <span className="badge badge-outline">
              <span className="mono">
                student={summaries[0].student_model.split("/").pop()} · teacher=
                {summaries[0].teacher_model.split("/").pop()}
              </span>
            </span>
          </div>
          <div className="grid-3">
            {summaries.map((s) => {
              const meta = displayMetaFor(s.skill);
              const r1 = s.score_history[0]?.avg_score ?? 0;
              const improvement = ((s.best_score - r1) / Math.max(r1, 1e-9)) * 100;
              return (
                <Link key={s.skill} className="skill-card" href={`/skills/${s.skill}`}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                    }}
                  >
                    <div>
                      <div className="skill-title">{meta.vi}</div>
                      <div className="skill-id">{s.skill}</div>
                    </div>
                    <span className="badge badge-success" title="Improvement R1 → Peak">
                      <Icon name="spark" size={11} />+{improvement.toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ margin: "6px 0 -2px" }}>
                    <Sparkline
                      data={s.score_history}
                      peakRound={s.best_round}
                      width={280}
                      height={56}
                    />
                  </div>
                  <div className="skill-card-stats">
                    <div className="stat">
                      <div className="stat-label">Rounds</div>
                      <div className="stat-value">{s.rounds_run}</div>
                    </div>
                    <div className="stat">
                      <div className="stat-label">R1</div>
                      <div className="stat-value">{r1.toFixed(3)}</div>
                    </div>
                    <div className="stat">
                      <div className="stat-label">Peak</div>
                      <div className="stat-value accent">{s.best_score.toFixed(3)}</div>
                    </div>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      color: "var(--fg-subtle)",
                      fontSize: 12,
                    }}
                  >
                    <span>
                      Final {s.final_score.toFixed(3)}{" "}
                      <span style={{ color: "var(--fg-faint)" }}>· R{s.rounds_run}</span>
                    </span>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        color: "var(--primary)",
                      }}
                    >
                      Xem chi tiết
                      <Icon name="arrow-r" size={12} />
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        <div className="card">
          <div className="row-between" style={{ marginBottom: 16 }}>
            <h3 className="h3">
              <Bi
                vi="Phương pháp tóm tắt"
                en={BILINGUAL ? "Method, at a glance" : null}
                showEn={BILINGUAL}
              />
            </h3>
            <span className="badge">
              <span className="mono">3-stage loop</span>
            </span>
          </div>
          <div className="grid-3">
            {[
              {
                n: "01",
                label: "Student",
                body: `${summaries[0].student_model} chạy SKILL.md hiện tại trên các test case, sinh output.`,
                color: "var(--primary)",
              },
              {
                n: "02",
                label: "Judge",
                body:
                  "Claude chấm từng output theo rubric. Rule-check chạy trước; điểm rule quá thấp thì bỏ qua judge.",
                color: "var(--accent)",
              },
              {
                n: "03",
                label: "Teacher",
                body:
                  "Claude đọc rationale của judge, viết lại SKILL.md cho vòng kế tiếp, lưu thành SKILL_round_N.md.",
                color: "var(--success)",
              },
            ].map((step) => (
              <div key={step.n} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="mono" style={{ fontSize: 11, color: "var(--fg-faint)" }}>
                    {step.n}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-serif)",
                      fontWeight: 600,
                      fontSize: 18,
                      color: step.color,
                    }}
                  >
                    {step.label}
                  </span>
                </div>
                <p
                  style={{
                    margin: 0,
                    fontSize: 14,
                    lineHeight: 1.55,
                    color: "var(--fg-muted)",
                  }}
                >
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
