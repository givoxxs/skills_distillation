# Skill Distillation Lab — Demo App

Dashboard demo cho đồ án tốt nghiệp *Skill Distillation* (Phan Văn Toàn, K22 22T_DT2, GVHD TS. Phạm Minh Tuấn, 2026).

Đọc dữ liệu thực từ `distillation_v2/results/stable/` (summary + 9 phiên bản `SKILL.md` + `eval_detail.jsonl` + `api_calls.jsonl`), trình bày qua 4 route cho hội đồng bảo vệ.

```
demo-app/
├── frontend/   # Next.js 16 App Router + Tailwind v4 + TS
└── backend/    # FastAPI — read-only data API + SSE replay
```

## Yêu cầu hệ thống

- Node ≥ 20, pnpm ≥ 9
- **Conda env `skills`** (Python 3.12) — đã có sẵn `fastapi`, `uvicorn`, `pydantic`, `pytest`, `httpx`. Xem `../.claude/rules/python-env.md` để hiểu vì sao project gắn cứng vào env này.

Verify môi trường:

```bash
/opt/anaconda3/envs/skills/bin/python --version    # Python 3.12.x
/opt/anaconda3/envs/skills/bin/pip list | grep -iE "fastapi|uvicorn|pytest"
```

Thiếu dep:

```bash
conda run -n skills pip install fastapi 'uvicorn[standard]' pydantic httpx pytest
```

## Chạy lần đầu

### Cách nhanh — `make dev` (khuyến nghị)

```bash
cd demo-app
make install     # chỉ pnpm install cho frontend; backend deps đã có trong conda env
make dev         # backend :8000 + frontend :3000 trong cùng 1 terminal, Ctrl-C kill cả hai
```

Mở trình duyệt → `http://localhost:3000`.

Makefile dùng absolute path tới conda binary (`/opt/anaconda3/envs/skills/bin/uvicorn`) nên không cần `conda activate skills` trước.

### Cách thủ công — hai terminal

```bash
# Terminal 1
cd demo-app/backend
/opt/anaconda3/envs/skills/bin/uvicorn app.main:app --port 8000 --reload

# Terminal 2
cd demo-app/frontend && pnpm dev
```

## Bốn route

| Route | Mô tả |
|---|---|
| `/` | **Overview** — 3 KPI + 3 skill card với sparkline mini, tính từ 3 `summary.json` thật |
| `/skills/[skill]` | **Skill detail** — 4 panel (learning curve · diff `SKILL.md` · test case explorer · cost) |
| `/run` | **Live run** — form + SSE stream replay toàn bộ round 1 (~26 test case, batch 5) |
| `/about` | **About** — thông tin đề tài, abstract, tech stack |

Sidebar có 2 toggle: **VN ↔ EN** (lang context) + **light ↔ dark** (theme). Mặc định VN + light. Cả 2 persist qua `localStorage`.

## Cấu hình

### Frontend → backend URL

Mặc định frontend gọi backend ở `http://127.0.0.1:8000`. Đổi qua biến môi trường:

```bash
NEXT_PUBLIC_BACKEND_URL=http://my-backend:8000 pnpm dev
```

### Backend env

Không bắt buộc. Tạo `backend/.env` chỉ khi muốn wire backend sang gọi LLM thật trong tương lai:

```bash
cp .env.example .env
# OPENROUTER_API_KEY=...
# ANTHROPIC_API_KEY=...
# DISTILL_REPO_ROOT=/Users/soc_036/study_dir/skill_distillation
```

`/run` hiện **replay** từ JSONL có sẵn — không gọi LLM, không tốn credit.

## Architecture decisions

### Frontend đọc dữ liệu thật qua backend, KHÔNG mock

Overview + Skill detail đều fetch từ backend qua Server Components (`fetch(BACKEND_URL/api/...)` với `cache: "no-store"`). Backend đọc trực tiếp từ `distillation_v2/results/stable/<skill>/`:

| Trường | Nguồn |
|---|---|
| KPI / score_history / sparkline / learning curve | `summary.json` |
| Diff SKILL.md giữa round X ↔ Y | `SKILL_round_{X,Y}.md` thật trên disk |
| Test case explorer | `eval_detail.jsonl` (26–27 record/round/skill) |
| Workflow filter | derive từ `summary.rubric_cache_keys` |
| Drawer rule_checks / judge rationale / prompt | `eval_detail.checks` + `eval_detail.llm_judge_reasoning` + `test_cases/<skill>.json` lookup |
| Cost & timing breakdown | **mock** (`lib/mock-data.ts`) — `api_calls.jsonl` thiếu `round`/`cost_usd`/`latency_ms`, panel có badge `demo data` |
| `/run` SSE replay | `eval_detail.jsonl` + `api_calls.jsonl` ghép vào 1 stream |

### Chart SVG hand-built thay vì Recharts

4 chart (Sparkline / LearningCurve / CostStackedBar / MiniLiveCurve) là Client Component SVG thuần — port từ design prototype. Pixel-perfect, không cần Recharts dep ~150 KB. Export PNG dùng `XMLSerializer + canvas.toDataURL` — không cần `html-to-image`.

### Diff viewer tự viết (LCS)

`components/diff-viewer.tsx` cài đặt diff side-by-side bằng LCS qua `Uint16Array` DP. Hai pane **scroll đồng bộ** (driver lock + `requestAnimationFrame`) — kéo bên này, bên kia chạy theo như git review.

### EN / VI toggle qua context

`components/language-provider.tsx` cung cấp `useLang()` với `lang: "vi" | "en"` persist qua `localStorage:sdl:lang`. Component `<Bi vi="…" en="…" />` switch nội dung theo lang. **Technical terms** (SKILL.md, hybrid, R1, peak, judge, rule, prompt, round, batch…) giữ tiếng Anh trong cả 2 mode bằng cách viết verbatim trong cả hai prop.

### Theme provider tự viết, không next-themes

Trong React 19 + Next 16, `next-themes` 0.4.6 inject `<script>` bên trong Client Component → hard-error. Project dùng `components/theme-provider.tsx` tự viết, cùng pattern với LanguageProvider. Để tránh flash light → dark cho user chọn dark trước đó: layout inject 1 inline script trong `<head>` (`THEME_BOOTSTRAP`) đọc `localStorage:sdl:theme` đồng bộ trước paint.

### `/run` replay full round, batch 5

Backend `services/runner.py` replay TOÀN BỘ test cases của round 1 (~26 cho docx) chia thành 6 batch x 5 TC (1 batch cuối ~1 TC). Mỗi event SSE bám sát schema thật của pipeline:

```
event: status         { phase: queued|running|judging|teacher|done }
event: log            { line, tag: system|student|judge|teacher|rule|status }
event: test_case_done { test_case_id, hybrid_score }
event: round_done     { round, avg_score }
event: complete       { skill, final_score }
```

Tốc độ phát ~22s wall-clock (SPEEDUP=0.40 áp lên delay thực). Nếu file JSONL biến mất runner tự fallback sang simulated mode với log `(fallback simulation — <reason>)`.

## Backend API contract

```
GET  /api/health                          → { status: "ok" }
GET  /api/skills                          → SkillListEntry[]
GET  /api/skills/{skill}/summary          → Summary (raw summary.json)
GET  /api/skills/{skill}/skill-md?round=N → { round, content, requested_round, fallback }
GET  /api/skills/{skill}/eval[?round=N]   → EvalEntry[] (eval_detail.jsonl + test_cases prompt lookup)
GET  /api/skills/{skill}/available-rounds → { rounds: number[] }
POST /api/run  body={skill}               → { run_id }
GET  /api/run/{run_id}/stream             → SSE
```

Read-only — không bao giờ ghi vào `distillation_v2/`.

## Tests

```bash
# Tất cả test (demo-app/backend + distillation_v2 từ root)
cd ..
/opt/anaconda3/envs/skills/bin/pytest

# Qua Makefile
cd demo-app
make test-backend      # 25 test cho FastAPI (~8s)
make test-pipeline     # distillation_v2 suite
make test              # cả hai
```

Backend tests cover: `/api/health`, OpenAPI schema, list_skills, get_summary (happy + 404), skill-md (exact round + fallback), eval (round filter + multi-round), POST /run (3 skills + invalid skill 422), SSE stream (phase ordering + test_case_done schema + final_score correlation), data_loader unit tests (LRU cache identity, canonical order, fallback math).

## Verify

```bash
# Frontend type-check
cd demo-app/frontend && pnpm exec tsc --noEmit         # → No errors found

# Backend boot
cd demo-app/backend
/opt/anaconda3/envs/skills/bin/python -c "from app.main import app; print(app.title)"
# → Skill Distillation Lab — Backend

# End-to-end smoke test
curl -s http://127.0.0.1:8000/api/skills | python -m json.tool
RUN_ID=$(curl -s -X POST http://127.0.0.1:8000/api/run \
  -H 'Content-Type: application/json' -d '{"skill":"docx"}' | jq -r .run_id)
curl -N http://127.0.0.1:8000/api/run/$RUN_ID/stream
# → SSE stream ~22s, kết thúc bằng event: complete với final_score thật
```

## Cấu trúc thư mục

```
demo-app/
├── README.md                                 # file này
├── Makefile                                  # make dev / install / test{,-backend,-pipeline} / clean
├── frontend/                                 # Next.js 16 App Router
│   ├── app/
│   │   ├── layout.tsx                        # fonts (next/font) + ThemeProvider + LanguageProvider + bootstrap script
│   │   ├── globals.css                       # import tailwindcss + design-tokens
│   │   ├── design-tokens.css                 # tokens Academic Clean (slate + blue + amber)
│   │   ├── page.tsx                          # / Overview (async server fetch x3 summary)
│   │   ├── about/page.tsx                    # /about
│   │   ├── run/
│   │   │   ├── page.tsx                      # /run server shell
│   │   │   └── run-client.tsx                # EventSource client + stepper + log + mini curve
│   │   └── skills/[skill]/
│   │       ├── page.tsx                      # /skills/:skill (await params + fetch summary/eval/skill-md parallel)
│   │       └── skill-detail-client.tsx       # 4 panel + drawer + sort + workflow filter
│   ├── components/
│   │   ├── theme-provider.tsx                # in-house (no next-themes)
│   │   ├── language-provider.tsx             # useLang() context + localStorage:sdl:lang
│   │   ├── sidebar.tsx                       # Client — usePathname + theme + lang toggles
│   │   ├── topbar.tsx                        # breadcrumbs + action slot
│   │   ├── bi.tsx                            # <Bi vi en /> switcher
│   │   ├── icon.tsx                          # Inline SVG icons
│   │   ├── diff-viewer.tsx                   # LCS diff + synchronised scroll
│   │   └── charts/{sparkline,learning-curve,cost-stacked-bar,mini-live-curve}.tsx
│   ├── lib/
│   │   ├── types.ts                          # SkillSummary, EvalEntry, ApiCall, Kpis
│   │   ├── api.ts                            # fetch helpers — server-side, no-store cache
│   │   ├── display-meta.ts                   # static VN/EN labels per skill
│   │   └── mock-data.ts                      # mock (chỉ còn dùng cho Cost panel)
│   └── package.json
└── backend/                                  # FastAPI + Pydantic v2 (conda-managed)
    ├── pyproject.toml                        # [tool.pytest.ini_options]
    ├── .env.example
    ├── tests/                                # 25 tests, pytest
    │   ├── conftest.py                       # TestClient fixture
    │   ├── test_health.py
    │   ├── test_skills_routes.py             # /api/skills/*
    │   ├── test_run_routes.py                # /api/run + SSE schema
    │   └── test_data_loader.py               # unit tests cho data_loader
    └── app/
        ├── main.py                           # FastAPI + CORS + include routes
        ├── config.py                         # DISTILL_REPO_ROOT, STABLE_DIR, KNOWN_SKILLS
        ├── models.py                         # Pydantic schemas
        ├── routes/
        │   ├── skills.py                     # /api/skills/* (read-only data)
        │   └── run.py                        # /api/run + /api/run/{id}/stream
        └── services/
            ├── data_loader.py                # LRU-cached reads of summary/eval/api_calls/SKILL_round_*
            └── runner.py                     # SSE replay (with simulated fallback)
```

## Acceptance checklist

- [x] `pnpm exec tsc --noEmit` ở `frontend/` — 0 lỗi.
- [x] `uvicorn app.main:app` boot; `GET /api/health` → `{"status":"ok"}`.
- [x] `/` render 3 KPI + 3 skill card với sparkline (số khớp `summary.json`: docx peak 0.921 @ R5).
- [x] `/skills/docx` đủ 4 panel; learning curve highlight R5 amber; diff R0 → R5 hiển thị nội dung thật của `SKILL_round_0.md` vs `SKILL_round_5.md`; 2 pane scroll đồng bộ.
- [x] Test case row click mở Drawer với prompt thật (từ `test_cases/docx.json`) + rationale (từ `llm_judge_reasoning`) + 16 rule_checks (từ `eval_detail.checks`).
- [x] `/run` Start → SSE replay 26 test case x 6 batch trong ~22s; stepper advance `queued → running → judging → teacher → done`; `final_score` khớp avg thật.
- [x] Theme toggle hoạt động, không flash light→dark khi reload (bootstrap script).
- [x] Language toggle VN ↔ EN hoạt động trên mọi page.
- [x] 25/25 backend pytest pass.
- [ ] Mobile responsive 375px — CSS đã có `@media (max-width: 900px)`; cần test thực tế khi demo trên slide.

## Deploy ra internet — free 100%

Mục tiêu: cho hội đồng / người ngoài access link `https://<vercel>.vercel.app` → toàn bộ demo chạy như local. Hai service tách rời, hai platform free:

| Service | Platform | Plan | Ghi chú |
|---|---|---|---|
| Frontend (Next.js) | **Vercel** | Hobby (free vĩnh viễn) | Auto-deploy từ GitHub, ~100 GB BW/tháng |
| Backend (FastAPI) | **Render** | Web Service Free (750h/m) | Sleep sau 15 min idle → cold start ~30–60s khi user đầu tiên click sau đó |

### Bước 1 — Push repo lên GitHub

Nếu chưa có:
```bash
gh repo create skills-distillation --public --source . --push
# hoặc: thêm remote + git push thủ công
```

### Bước 2 — Deploy backend lên Render

1. Mở `https://dashboard.render.com` → **New +** → **Blueprint**.
2. Connect GitHub repo, chọn branch `main`.
3. Render đọc `demo-app/render.yaml`, tạo Web Service `skill-distillation-backend`.
4. Trong tab Environment, sửa `ALLOWED_ORIGINS` thêm Vercel domain (lát sau khi có):
   ```
   ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000
   ```
5. Bấm Deploy. Build mất ~3–5 phút (Docker từ scratch).
6. Khi sống: copy URL Render, ví dụ `https://skill-distillation-backend.onrender.com`.
7. Verify: `curl https://<your-render-domain>/api/health` → `{"status":"ok"}`.

> **Docker chi tiết:** `demo-app/backend/Dockerfile` bake sẵn `distillation_v2/results/stable/` + `test_cases/` vào image (~5 MB) qua build context = repo root. `DISTILL_REPO_ROOT` được set sang `/data` trong image nên `data_loader.py` đọc đúng path mà không cần volume mount.

### Bước 3 — Deploy frontend lên Vercel

1. Mở `https://vercel.com/new` → import GitHub repo.
2. **Root Directory**: `demo-app/frontend`.
3. **Build Command**: để mặc định (`next build`).
4. **Environment Variables** → thêm:
   ```
   NEXT_PUBLIC_BACKEND_URL=https://skill-distillation-backend.onrender.com
   ```
5. Deploy. Build mất ~1–2 phút.
6. Khi xong: copy Vercel domain, **quay lại Render → cập nhật `ALLOWED_ORIGINS`** với domain Vercel → trigger redeploy backend.

### Bước 4 — Smoke test

Mở `https://<your-vercel-domain>.vercel.app/`. Browser console KHÔNG được có CORS error. Các route:
- `/` → 3 KPI + 3 skill card với sparkline thật
- `/skills/docx` → 4 panel, diff R0 → R5 hiển thị nội dung thật
- `/run` → bấm Start → SSE stream 8 round, kết thúc với peak 0.921 @ R5

### Cold-start mitigation (tuỳ chọn)

Render free tier sleep sau 15 phút idle. Một số cách giảm shock:
- Trong UI thêm dòng "Backend đang warm up… (lần đầu mất ~30s)" khi fetch `/api/health` mất > 10s.
- Hoặc ping endpoint `/api/health` từ cron job free (vd. `cron-job.org`) mỗi 10 phút → giữ container awake (chỉ trong giờ bảo vệ).
- Hoặc upgrade Render lên **Starter $7/m** để bỏ sleep.

### File / endpoint cần biết

| File | Vai trò |
|---|---|
| `demo-app/render.yaml` | Blueprint Render — đọc khi tạo service |
| `demo-app/backend/Dockerfile` | Image cho production |
| `demo-app/backend/.dockerignore` | Skip dev artefacts khi build |
| `ALLOWED_ORIGINS` env var | CORS whitelist, dạng comma-separated |
| `DISTILL_REPO_ROOT` env var | Path tới `distillation_v2/` data. Default `/data` trong Docker |
| `NEXT_PUBLIC_BACKEND_URL` (Vercel) | URL backend FE sẽ gọi |

### Khi deploy thất bại

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| Render build "context exceeded" | `.dockerignore` chưa skip dir lớn — check |
| CORS error trong browser | `ALLOWED_ORIGINS` thiếu Vercel domain — sửa env, redeploy |
| 502/504 trên `/api/run/{id}/stream` | Render free idle hoặc proxy timeout; thử reload |
| `/api/skills` trả 502 với "stable dir missing" | Image không có data — check `.dockerignore` whitelist |

## Lưu ý cho người maintain

- **Không ghi vào `distillation_v2/results/stable/`** — backend là read-only client.
- Nếu upstream thêm `cost_usd` / `round` / `latency_ms` / `timestamp` vào `api_calls.jsonl`, có thể bỏ mock + wire frontend Cost panel sang fetch thật.
- Wallclock của `/run` điều chỉnh qua hằng `SPEEDUP` (`backend/app/services/runner.py`). `BATCH_SIZE` cũng định nghĩa ở đó.
- Pre-paint theme script trong `app/layout.tsx` (`THEME_BOOTSTRAP`) chạy đồng bộ trước React — không touch nó nếu không hiểu kỹ.
