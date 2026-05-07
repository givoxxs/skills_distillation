# Skill Distillation — Makefile
# Usage: make <target>

CONDA_ENV   := skills
CONDA_RUN   := conda run -n $(CONDA_ENV)
BACKEND_DIR := ui/backend
UI_DIR      := ui

.PHONY: help backend frontend dev stop \
        install install-ui \
        run-distill run-eval run-skill \
        logs clean

# ── Default ───────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Skill Distillation — available targets"
	@echo ""
	@echo "  Setup"
	@echo "    make install       Install Python deps (conda env: $(CONDA_ENV))"
	@echo "    make install-ui    Install frontend deps (pnpm)"
	@echo ""
	@echo "  Running"
	@echo "    make backend       Start FastAPI backend  (port 8000)"
	@echo "    make frontend      Start Vite dev server  (port 5173)"
	@echo "    make dev           Start both in parallel"
	@echo "    make stop          Kill backend + frontend processes"
	@echo ""
	@echo "  Pipeline"
	@echo "    make run-distill SKILL=docx ROUNDS=3"
	@echo "    make run-eval    SKILL=docx MODEL=qwen/qwen3-8b"
	@echo "    make run-skill   SKILL=docx MODEL=qwen/qwen3-8b PROMPT='...' "
	@echo ""
	@echo "  Utils"
	@echo "    make logs          Tail backend run logs"
	@echo "    make clean         Remove __pycache__ and .pyc files"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────
install:
	$(CONDA_RUN) pip install fastapi "uvicorn[standard]" python-dotenv websockets
	$(CONDA_RUN) pip install -r distillation_v2/requirements.txt 2>/dev/null || true

install-ui:
	cd $(UI_DIR) && pnpm install

# ── Dev servers ───────────────────────────────────────────────────────────────
backend:
	cd $(BACKEND_DIR) && $(CONDA_RUN) uvicorn server:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd $(UI_DIR) && pnpm dev

# Run backend and frontend in parallel; Ctrl-C stops both
dev:
	@trap 'kill 0' INT; \
	  (cd $(BACKEND_DIR) && $(CONDA_RUN) uvicorn server:app --host 0.0.0.0 --port 8000 --reload) & \
	  (cd $(UI_DIR) && pnpm dev) & \
	  wait

stop:
	@echo "Stopping uvicorn and vite..."
	@pkill -f "uvicorn server:app" 2>/dev/null || true
	@pkill -f "vite"              2>/dev/null || true
	@echo "Done."

# ── Pipeline ──────────────────────────────────────────────────────────────────
SKILL  ?= docx
ROUNDS ?= 3
CASES  ?= 5
MODEL  ?= qwen/qwen3-8b
PROMPT ?= Summarize the document

run-distill:
	cd distillation_v2 && $(CONDA_RUN) python run.py \
	  --skill $(SKILL) --rounds $(ROUNDS) --test-cases $(CASES) --verbose

run-distill-dry:
	cd distillation_v2 && $(CONDA_RUN) python run.py \
	  --skill $(SKILL) --rounds $(ROUNDS) --dry-run

run-eval:
	cd skill_evaluation && $(CONDA_RUN) python run_eval.py \
	  --skill $(SKILL) --model $(MODEL)

run-skill:
	cd skill_runner && $(CONDA_RUN) python main.py run \
	  --skill $(SKILL) --model $(MODEL) --prompt "$(PROMPT)"

# ── Utils ─────────────────────────────────────────────────────────────────────
logs:
	@ls -t $(BACKEND_DIR)/logs/*.jsonl 2>/dev/null | head -5 | xargs tail -f 2>/dev/null \
	  || echo "No log files found in $(BACKEND_DIR)/logs/"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned."
