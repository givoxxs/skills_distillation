import { Bi } from "@/components/bi";
import { Icon } from "@/components/icon";
import { TopBar } from "@/components/topbar";
import { fetchSummary } from "@/lib/api";

const SKILLS = ["docx", "internal-comms", "slack-gif-creator"] as const;

export default async function AboutPage() {
  const summaries = await Promise.all(SKILLS.map(fetchSummary));
  const totalImprovementPct = +(
    (summaries.reduce((acc, s) => {
      const r1 = s.score_history[0]?.avg_score ?? 0;
      return acc + (s.best_score - r1) / Math.max(r1, 1e-9);
    }, 0) /
      Math.max(summaries.length, 1)) *
    100
  ).toFixed(1);

  return (
    <>
      <TopBar
        crumbs={[
          { label: <Bi vi="Tổng quan" en="Overview" />, href: "/" },
          { label: <Bi vi="Giới thiệu" en="About" /> },
        ]}
      />
      <div className="page page-narrow stack-lg">
        <div className="stack-sm">
          <div className="eyebrow">
            <Bi vi="Đồ án tốt nghiệp" en="Bachelor's thesis" />
          </div>
          <h1 className="h-display">Skill Distillation Lab</h1>
          <p
            className="muted"
            style={{
              fontSize: 18,
              lineHeight: 1.6,
              fontStyle: "italic",
              fontFamily: "var(--font-serif)",
            }}
          >
            <Bi
              vi="Chưng cất tài liệu hướng dẫn của Anthropic xuống mô hình ngôn ngữ nhỏ qua vòng lặp Teacher–Student–Judge."
              en="Distilling Anthropic's skill documentation down to a small language model through a Teacher–Student–Judge loop."
            />
          </p>
        </div>

        <div className="card">
          <h3 className="h3" style={{ marginBottom: 16 }}>
            <Bi vi="Thông tin đề tài" en="Project metadata" />
          </h3>
          <dl
            style={{
              display: "grid",
              gridTemplateColumns: "160px 1fr",
              gap: "10px 24px",
              margin: 0,
              fontSize: 14,
            }}
          >
            <dt className="stat-label">
              <Bi vi="Sinh viên" en="Student" />
            </dt>
            <dd style={{ margin: 0, fontWeight: 500 }}>Phan Văn Toàn</dd>

            <dt className="stat-label">
              <Bi vi="Khoá" en="Cohort" />
            </dt>
            <dd style={{ margin: 0 }}>
              K22 · <span className="mono">22T_DT2</span>
            </dd>

            <dt className="stat-label">
              <Bi vi="GVHD" en="Supervisor" />
            </dt>
            <dd style={{ margin: 0 }}>TS Phạm Minh Tuấn</dd>

            <dt className="stat-label">
              <Bi vi="Năm bảo vệ" en="Defense year" />
            </dt>
            <dd style={{ margin: 0 }} className="mono">
              2026
            </dd>

            <dt className="stat-label">
              <Bi vi="Khoa" en="Faculty" />
            </dt>
            <dd style={{ margin: 0 }}>
              <Bi vi="Công nghệ Thông tin" en="Information Technology" />
            </dd>
          </dl>
        </div>

        <div className="stack-sm">
          <h3 className="h3">
            <Bi vi="Tóm tắt" en="Abstract" />
          </h3>
          <div style={{ fontSize: 16, lineHeight: 1.75, color: "var(--fg)", maxWidth: "64ch" }}>
            <p>
              <Bi
                vi={
                  <>
                    Tháng 10/2025, Anthropic công bố cơ chế <strong>Agent Skills</strong>: mỗi skill là
                    một thư mục có file{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      SKILL.md
                    </span>{" "}
                    kèm scripts và assets, được nạp theo nguyên tắc <em>progressive disclosure</em>. Cùng
                    một{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      SKILL.md
                    </span>{" "}
                    khi chạy với mô hình nhỏ (Gemma 4-26B qua OpenRouter) đạt điểm thấp hơn rõ rệt so với
                    Claude.
                  </>
                }
                en={
                  <>
                    In October 2025 Anthropic shipped <strong>Agent Skills</strong>: each skill is a
                    directory containing a{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      SKILL.md
                    </span>{" "}
                    file plus scripts and assets, loaded under a <em>progressive disclosure</em> policy.
                    The same{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      SKILL.md
                    </span>{" "}
                    scores noticeably lower when executed by a small model (Gemma 4-26B via OpenRouter)
                    than by Claude.
                  </>
                }
              />
            </p>
            <p>
              <Bi
                vi={
                  <>
                    Đồ án này đề xuất một <strong>pipeline 3 stage</strong> —{" "}
                    <em>Student → Judge → Teacher</em> — lặp nhiều vòng để viết lại{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      SKILL.md
                    </span>{" "}
                    sao cho mô hình nhỏ thực thi tốt hơn. Hệ thống đã được đánh giá trên ba skill (
                    <span className="mono" style={{ fontSize: 14 }}>
                      docx
                    </span>
                    ,{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      internal-comms
                    </span>
                    ,{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      slack-gif-creator
                    </span>
                    ), với mức cải thiện peak so với round 1 trung bình{" "}
                    <strong style={{ color: "var(--accent)" }}>+{totalImprovementPct}%</strong>. Dashboard
                    này là công cụ trình bày kết quả và là live demo cho hội đồng bảo vệ.
                  </>
                }
                en={
                  <>
                    This thesis proposes a <strong>three-stage pipeline</strong> —{" "}
                    <em>Student → Judge → Teacher</em> — that iteratively rewrites{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      SKILL.md
                    </span>{" "}
                    so the small model executes it more reliably. The system has been evaluated on three
                    skills (
                    <span className="mono" style={{ fontSize: 14 }}>
                      docx
                    </span>
                    ,{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      internal-comms
                    </span>
                    ,{" "}
                    <span className="mono" style={{ fontSize: 14 }}>
                      slack-gif-creator
                    </span>
                    ), with an average peak-vs-R1 improvement of{" "}
                    <strong style={{ color: "var(--accent)" }}>+{totalImprovementPct}%</strong>. This
                    dashboard is the reporting tool and live demo for the thesis committee.
                  </>
                }
              />
            </p>
          </div>
        </div>

        <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
          <a
            className="btn"
            href="https://github.com/givoxxs/skills_distillation"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Icon name="github" size={16} />
            Source code
            <Icon name="external" size={14} />
          </a>
          <button type="button" className="btn">
            <Icon name="doc" size={16} />
            Thesis report (PDF)
          </button>
        </div>

        <div className="stack-sm">
          <div className="eyebrow">
            <Bi vi="Công nghệ sử dụng" en="Tech stack" />
          </div>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            {(
              [
                ["Frontend", ["Next.js 16", "Tailwind v4", "next-themes", "lucide-react"]],
                ["Backend", ["FastAPI", "Pydantic v2", "Uvicorn", "SSE"]],
                ["Models", ["Anthropic Claude Haiku 4.5", "Google Gemma 4-26B", "OpenRouter"]],
              ] as const
            ).map(([group, items]) => (
              <div
                key={group}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  marginRight: 24,
                  marginBottom: 8,
                }}
              >
                <div className="stat-label">{group}</div>
                <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
                  {items.map((it) => (
                    <span key={it} className="badge">
                      <span className="mono" style={{ fontSize: 11 }}>
                        {it}
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <hr className="hr-dashed" />

        <div className="muted" style={{ fontSize: 13 }}>
          <Bi
            vi={
              <>
                UI này dùng dữ liệu thật từ <span className="mono">distillation_v2/results/stable/</span>{" "}
                (summary + SKILL.md + eval_detail). Phần <span className="mono">/run</span> hiện đang là
                simulated SSE (xem README §architecture decisions); nếu backend không chạy, UI tự động
                fallback về local simulation.
              </>
            }
            en={
              <>
                The UI reads real data from <span className="mono">distillation_v2/results/stable/</span>{" "}
                (summary + SKILL.md + eval_detail). The <span className="mono">/run</span> page is a
                simulated SSE stream today (see README §architecture decisions); if the backend is
                unreachable the UI falls back to local simulation.
              </>
            }
          />
        </div>
      </div>
    </>
  );
}
