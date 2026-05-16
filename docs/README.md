# `docs/` — Mục lục

Tài liệu thuộc đồ án Skill Distillation. Trỏ ngược lại repo root [`README.md`](../README.md) cho overview.

## Cấu trúc

```
docs/
├── README.md                    ← (file này)
├── phan_tich_de_cuong.md        ← Phân tích đề cương ĐATN (MSSV + GVHD + ý tưởng gốc)
├── notes/
│   ├── skills_research.md       ← Khảo cứu literature, ~3.6 k từ + BibTeX (EN)
│   ├── skills_research_vi.md    ← Bản tiếng Việt tương đương
│   └── skills_section_1.md      ← Phương pháp phân tầng skill để test model (notes)
└── thesis/                      ← Draft báo cáo đồ án — gitignored
    ├── 00_README.md
    ├── 01..07_*.md              ← 5 chương + Kết luận + TLTK
    ├── TODO.md                  ← Danh sách việc bổ sung trước bảo vệ
    ├── figures/                 ← PNG biểu đồ học (sinh bởi scripts/)
    ├── prompts/                 ← Prompt khảo cứu / design UI
    └── scripts/                 ← plot_learning_curves.py
```

## Từng file

| File | Mục đích | Trạng thái |
|---|---|---|
| `phan_tich_de_cuong.md` | Phân tích đề cương — câu hỏi nghiên cứu, hai sản phẩm kỹ thuật, thông tin hồ sơ. | Hoàn chỉnh |
| `notes/skills_research_vi.md` | Khảo cứu literature về Skill / APO / LLM-as-Judge / SLM failure modes. | Hoàn chỉnh, có ⚠️ flags cần verify trước nộp |
| `notes/skills_research.md` | Bản EN của trên. | Hoàn chỉnh |
| `notes/skills_section_1.md` | Phương pháp phân tầng skill (Tier 1–3) để test phân biệt năng lực Claude vs SLLM. | Notes nội bộ, chưa link vào báo cáo |
| `thesis/` | Draft báo cáo 5 chương + TODO. | Đang iterate, gitignored |

## Đã xoá ngày 2026-05-16

Các file phase-0 sau bị purge khỏi `docs/` vì đã được README mới + thesis chapters thay thế, hoặc đã outdated:

- `architecture.md`, `pipeline.md`, `tech-stack.md` — kiến trúc + pipeline + stack v1 (Qwen/Phi-4 chưa từng chạy)
- `scope.md`, `results-and-risks.md` — MVP scope + placeholder số "30% → 70%"
- `project-structure.md` — đã drift so với layout hiện tại (`demo-app/` mới)
- `contribution-and-insights.md` — partial overlap với `notes/skills_research_vi.md` §6
- `customizations-guide.md` — hướng dẫn Copilot 15/04/2026, project đã chuyển sang Claude Code
- `researchs/` — thư mục rỗng

Nội dung quan trọng từ những file này đã được tổng hợp lại trong `../README.md` (overview) và `thesis/` (chi tiết). Xem `git log -- docs/` nếu cần khôi phục.
