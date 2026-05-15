.PHONY: dev backend frontend install clean test test-backend test-pipeline

# All Python commands run inside the shared conda env "skills".
# Override CONDA_ENV via env var if you really need to.
CONDA_ENV ?= skills
CONDA_PREFIX_PATH := /opt/anaconda3/envs/$(CONDA_ENV)
PYTHON := $(CONDA_PREFIX_PATH)/bin/python
UVICORN := $(CONDA_PREFIX_PATH)/bin/uvicorn
PYTEST := $(CONDA_PREFIX_PATH)/bin/pytest

# Chạy backend (port 8000) + frontend (port 3000) song song trong một terminal.
# Ctrl-C kill cả hai cùng lúc (trap EXIT/INT/TERM → kill 0).
dev:
	@echo "→ backend  : http://127.0.0.1:8000  (conda env: $(CONDA_ENV))"
	@echo "→ frontend : http://localhost:3000"
	@echo ""
	@trap 'kill 0' EXIT INT TERM; \
	$(MAKE) -s backend & \
	$(MAKE) -s frontend & \
	wait

backend:
	@cd backend && $(UVICORN) app.main:app --port 8000 --reload

frontend:
	@cd frontend && pnpm dev

install:
	@echo "Backend deps are managed inside the conda env '$(CONDA_ENV)'."
	@echo "If anything is missing run: conda run -n $(CONDA_ENV) pip install fastapi 'uvicorn[standard]' pydantic httpx pytest"
	cd frontend && pnpm install

clean:
	rm -rf frontend/.next frontend/node_modules

# Tests — run both demo-app/backend and distillation_v2 suites via the
# shared conda env. See ../.claude/rules/python-env.md.
test: test-backend test-pipeline

test-backend:
	cd backend && $(PYTEST)

test-pipeline:
	cd .. && $(PYTEST) distillation_v2/tests
