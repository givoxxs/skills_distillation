import { Bi } from "@/components/bi";
import { Icon } from "@/components/icon";
import { TopBar } from "@/components/topbar";
import { kpis } from "@/lib/mock-data";

const BILINGUAL = true;

export default function AboutPage() {
  return (
    <>
      <TopBar
        crumbs={[
          { label: "Tổng quan", href: "/" },
          { label: BILINGUAL ? "Giới thiệu · About" : "Giới thiệu" },
        ]}
      />
      <div className="page page-narrow stack-lg">
        <div className="stack-sm">
          <div className="eyebrow">
            <Bi vi="Đồ án tốt nghiệp" en={BILINGUAL ? "Bachelor's thesis" : null} showEn={BILINGUAL} />
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
            Chưng cất tài liệu hướng dẫn của Anthropic xuống mô hình ngôn ngữ nhỏ qua vòng lặp Teacher–Student–Judge.
          </p>
        </div>

        <div className="card">
          <h3 className="h3" style={{ marginBottom: 16 }}>
            <Bi vi="Thông tin đề tài" en={BILINGUAL ? "Project metadata" : null} showEn={BILINGUAL} />
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
            <dt className="stat-label">Sinh viên</dt>
            <dd style={{ margin: 0, fontWeight: 500 }}>Phan Văn Toàn</dd>

            <dt className="stat-label">Khoá</dt>
            <dd style={{ margin: 0 }}>
              K22 · <span className="mono">22T_DT2</span>
            </dd>

            <dt className="stat-label">GVHD</dt>
            <dd style={{ margin: 0 }}>TS Phạm Minh Tuấn</dd>

            <dt className="stat-label">Năm bảo vệ</dt>
            <dd style={{ margin: 0 }} className="mono">
              2026
            </dd>

            <dt className="stat-label">Khoa</dt>
            <dd style={{ margin: 0 }}>Công nghệ Thông tin</dd>
          </dl>
        </div>

        <div className="stack-sm">
          <h3 className="h3">
            <Bi vi="Tóm tắt" en={BILINGUAL ? "Abstract" : null} showEn={BILINGUAL} />
          </h3>
          <div style={{ fontSize: 16, lineHeight: 1.75, color: "var(--fg)", maxWidth: "64ch" }}>
            <p>
              Tháng 10/2025, Anthropic công bố cơ chế <strong>Agent Skills</strong>: mỗi skill là một thư
              mục có file{" "}
              <span className="mono" style={{ fontSize: 14 }}>
                SKILL.md
              </span>{" "}
              kèm scripts và assets, được nạp theo nguyên tắc <em>progressive disclosure</em>. Cùng một{" "}
              <span className="mono" style={{ fontSize: 14 }}>
                SKILL.md
              </span>{" "}
              khi chạy với mô hình nhỏ (Gemma 3 26B qua OpenRouter) đạt điểm thấp hơn rõ rệt so với Claude.
            </p>
            <p>
              Đồ án này đề xuất một <strong>pipeline 3 stage</strong> — <em>Student → Judge → Teacher</em>{" "}
              — lặp nhiều vòng để viết lại{" "}
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
              <strong style={{ color: "var(--accent)" }}>+{kpis.total_improvement_pct}%</strong>. Dashboard
              này là công cụ trình bày kết quả và là live demo cho hội đồng bảo vệ.
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
            <Bi vi="Công nghệ sử dụng" en={BILINGUAL ? "Tech stack" : null} showEn={BILINGUAL} />
          </div>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            {(
              [
                ["Frontend", ["Next.js 16", "Tailwind v4", "next-themes", "lucide-react"]],
                ["Backend", ["FastAPI", "Pydantic v2", "Uvicorn", "SSE"]],
                ["Models", ["Anthropic Claude Sonnet 4.5", "Google Gemma 3 26B", "OpenRouter"]],
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
          UI này là <strong>prototype mức cao</strong> dùng dữ liệu mock thực tế. Phần{" "}
          <span className="mono">/run</span> kết nối với FastAPI thật qua SSE; nếu backend không chạy, UI
          tự động fallback về local simulation.
        </div>
      </div>
    </>
  );
}
