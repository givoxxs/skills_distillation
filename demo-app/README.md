# Skill Distillation Lab — Demo App

Demo dashboard cho đồ án tốt nghiệp *Skill Distillation* (Phan Văn Toàn, K22 22T_DT2, GVHD TS. Phạm Minh Tuấn, 2026).

Kiến trúc 2 service chạy độc lập:

```
demo-app/
├── frontend/   # Next.js 16 (App Router) + Tailwind v4 — dashboard pixel-perfect theo design Academic Clean
└── backend/    # FastAPI — phục vụ /api/run SSE cho trang "Chạy thử"
```

## Yêu cầu hệ thống

- Node ≥ 20, pnpm ≥ 9
- **Conda env `skills`** (Python 3.12) — đã có sẵn `fastapi`, `uvicorn`, `pydantic`, `pytest`, `httpx`. Xem `.claude/rules/python-env.md` để hiểu vì sao project gắn cứng vào env này.

Verify môi trường:

```bash
/opt/anaconda3/envs/skills/bin/python --version    # Python 3.12.x
/opt/anaconda3/envs/skills/bin/pip list | grep -iE "fastapi|uvicorn|pytest"
```

Nếu thiếu dep:

```bash
conda run -n skills pip install fastapi 'uvicorn[standard]' pydantic httpx pytest
```

## Chạy lần đầu

### Cách nhanh — `make dev` (khuyến nghị)

Một lệnh duy nhất khởi cả backend + frontend song song trong cùng terminal. Ctrl-C kill cả hai. Makefile dùng các binary của conda env `skills` qua absolute path nên không cần `conda activate` trước:

```bash
cd demo-app
make install     # chỉ cài frontend (pnpm install); backend deps đã có trong conda env
make dev         # backend :8000 + frontend :3000
```

Mở trình duyệt → `http://localhost:3000`.

### Cách thủ công — hai terminal

#### Terminal 1 — Backend (port 8000)

```bash
cd demo-app/backend
/opt/anaconda3/envs/skills/bin/uvicorn app.main:app --port 8000 --reload
# → API listening at http://127.0.0.1:8000
# → GET /api/health → {"status":"ok"}
```

#### Terminal 2 — Frontend (port 3000)

```bash
cd demo-app/frontend
pnpm install                 # nếu chưa cài
pnpm dev
# → http://localhost:3000
```

## Bốn route

| Route | Mô tả |
|---|---|
| `/` | **Tổng quan** — 3 KPI + 3 skill card với sparkline mini |
| `/skills/[skill]` | **Chi tiết skill** — 4 panel (learning curve, diff SKILL.md, test case explorer, cost) |
| `/run` | **Chạy thử** — form + SSE stream + mini live curve |
| `/about` | **Giới thiệu** — thông tin đề tài + abstract + tech stack |

Sidebar điều hướng + toggle dark/light ở footer sidebar. Bilingual VN-lead, EN-sub.

## Cấu hình

### Frontend → backend URL

Mặc định frontend gọi backend ở `http://localhost:8000`. Đổi qua biến môi trường:

```bash
NEXT_PUBLIC_BACKEND_URL=http://my-backend:8000 pnpm dev
```

### Backend env

Không bắt buộc. Tạo `backend/.env` nếu muốn wire vào pipeline thật:

```bash
cp .env.example .env
```

Hiện tại `/api/run` **simulate** event stream — không gọi LLM thật, không tốn credit. Logic mô phỏng nằm trong `backend/app/services/runner.py`. Để swap sang subprocess thật:

1. Mở `backend/app/services/runner.py`.
2. Thay `stream_events()` bằng wrapper gọi `asyncio.create_subprocess_exec(sys.executable, "<repo>/distillation_v2/run.py", ...)` và parse stdout (xem `HANDOFF.md`).

Trang `/run` có toggle "Backend SSE" ↔ "Local simulation" — nếu backend không chạy, UI tự fallback simulate phía client.

## Architecture decisions

### Mock data trong frontend, không qua backend

Trang tổng quan + chi tiết skill đọc dữ liệu trực tiếp từ `frontend/lib/mock-data.ts` (TypeScript port của `design/data.js`). Backend hiện không phơi bày `/api/skills/*` — vì pipeline thực tế chưa sinh `eval_detail.jsonl`/`api_calls.jsonl` (chỉ có `summary.json` + `SKILL_round_*.md`). Quyết định này:

- Đơn giản hoá dev/test — frontend chạy được không cần backend.
- Đảm bảo pixel-perfect số liệu theo design (đồng bộ với báo cáo).
- Backend chỉ làm việc nó cần làm: SSE.

Khi pipeline có đủ JSONL, mở rộng `backend/app/routes/skills.py` theo `HANDOFF.md` rồi switch frontend sang fetch.

### Chart SVG hand-built thay vì Recharts

Bốn chart (Sparkline / LearningCurve / CostStackedBar / MiniLiveCurve) là Client Component SVG thuần — port verbatim từ `design/charts.jsx`. Lý do:

- Pixel-perfect khớp prototype (peak amber dot, area gradient, dashed threshold, monospace ticks).
- Không kéo theo dep Recharts ~150 KB.
- Dễ tinh chỉnh inline.

Export PNG dùng `XMLSerializer + canvas.toDataURL` — không cần `html-to-image`.

## Tests

```bash
# All tests (demo-app/backend + distillation_v2 từ root)
cd ..
/opt/anaconda3/envs/skills/bin/pytest

# Hoặc chia ra qua Makefile
cd demo-app
make test-backend      # chỉ FastAPI suite (~8s)
make test-pipeline     # distillation_v2 suite
make test              # cả hai
```

Cấu trúc test layout (theo Python multi-subproject convention):

```
skill_distillation/
├── pyproject.toml                        # [tool.pytest.ini_options].testpaths
├── demo-app/backend/
│   ├── pyproject.toml                    # [tool.pytest.ini_options] cho subproject
│   └── tests/
│       ├── conftest.py                   # TestClient fixture
│       ├── test_health.py
│       ├── test_skills_routes.py
│       ├── test_run_routes.py            # SSE schema check
│       └── test_data_loader.py
└── distillation_v2/tests/                # pipeline test suite (đã có sẵn)
```

## Verify

```bash
# Frontend type-check
cd demo-app/frontend && pnpm exec tsc --noEmit
# → No errors

# Backend boot
cd demo-app/backend && /opt/anaconda3/envs/skills/bin/python -c "from app.main import app; print(app.title)"
# → Skill Distillation Lab — Backend

# End-to-end SSE smoke test
curl -X POST http://127.0.0.1:8000/api/run -H 'Content-Type: application/json' -d '{"skill":"docx"}'
# → {"run_id":"..."}
curl -N http://127.0.0.1:8000/api/run/<run_id>/stream
# → stream of SSE events: status / log / test_case_done / round_done / complete
```

## Cấu trúc thư mục

```
demo-app/
├── README.md                            # tài liệu này
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                   # root layout + Google fonts + theme + sidebar shell
│   │   ├── globals.css                  # @import "tailwindcss"; @import "./design-tokens.css";
│   │   ├── design-tokens.css            # tokens Academic Clean (slate + blue + amber)
│   │   ├── page.tsx                     # /
│   │   ├── about/page.tsx               # /about
│   │   ├── run/
│   │   │   ├── page.tsx                 # /run (Server Component)
│   │   │   └── run-client.tsx           # SSE client + stepper + log stream + mini curve
│   │   └── skills/[skill]/
│   │       ├── page.tsx                 # /skills/:skill (Server Component, await params)
│   │       └── skill-detail-client.tsx  # 4 panel + drawer + state
│   ├── components/
│   │   ├── theme-provider.tsx           # next-themes
│   │   ├── sidebar.tsx                  # Client — usePathname() + theme toggle
│   │   ├── topbar.tsx                   # crumbs + actions slot
│   │   ├── bi.tsx                       # Bilingual lockup (VN lead, EN sub)
│   │   ├── icon.tsx                     # Inline SVG icons (Lucide-style)
│   │   ├── diff-viewer.tsx              # LCS diff side-by-side
│   │   └── charts/
│   │       ├── sparkline.tsx
│   │       ├── learning-curve.tsx
│   │       ├── cost-stacked-bar.tsx
│   │       └── mini-live-curve.tsx
│   └── lib/
│       ├── types.ts                     # SkillSummary, EvalEntry, ApiCall, Kpis
│       └── mock-data.ts                 # ported from design/data.js (deterministic PRNG)
└── backend/
    ├── pyproject.toml                   # uv-managed (package=false)
    ├── .env.example
    └── app/
        ├── __init__.py
        ├── main.py                      # FastAPI app + CORS
        ├── models.py                    # Pydantic v2
        ├── routes/
        │   └── run.py                   # POST /api/run, GET /api/run/{id}/stream
        └── services/
            └── runner.py                # In-memory registry + SSE generator
```

## Acceptance checklist (mapped to HANDOFF.md §5)

- [x] `pnpm tsc --noEmit` ở `frontend/` — 0 lỗi.
- [x] `uvicorn app.main:app` boot; `GET /api/health` → `{"status":"ok"}`.
- [x] `/` render 3 KPI + 3 skill card với sparkline (R1=0.793, peak=0.921 @ R5 cho docx).
- [x] `/skills/docx` đủ 4 panel; learning curve highlight R5 amber; diff R0 → R5 hiển thị nội dung thật của `SKILL_round_0` vs `SKILL_round_5`.
- [x] Test case row click mở Drawer với prompt / output / rationale / rule checks.
- [x] `/run` Start → SSE stream events đúng schema; stepper advance `queued → running → judging → teacher → done`.
- [x] Theme toggle hoạt động, không flash.
- [ ] Mobile responsive 375px — `design-tokens.css` đã có `@media (max-width: 900px)`; cần test thực tế khi demo trên slide.
- [x] PNG export trên learning curve + cost chart (dùng `XMLSerializer + canvas.toDataURL`).

## Liên hệ thiết kế gốc

- Design system: `Koro Design System` (override sang **Academic Clean** theo brief của user).
- Spec: xem `HANDOFF.md` trong design archive gốc (không commit vào repo này).
- Source prototype: HTML/JSX trong `/tmp/design-extract/proj-1/project/` (đã port verbatim).
