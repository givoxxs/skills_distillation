.PHONY: dev backend frontend install clean

# Chạy backend (port 8000) + frontend (port 3000) song song trong một terminal.
# Ctrl-C kill cả hai cùng lúc (trap EXIT/INT/TERM → kill 0).
dev:
	@echo "→ backend  : http://127.0.0.1:8000"
	@echo "→ frontend : http://localhost:3000"
	@echo ""
	@trap 'kill 0' EXIT INT TERM; \
	$(MAKE) -s backend & \
	$(MAKE) -s frontend & \
	wait

backend:
	@cd backend && uv run uvicorn app.main:app --port 8000 --reload

frontend:
	@cd frontend && pnpm dev

install:
	cd backend && uv sync
	cd frontend && pnpm install

clean:
	rm -rf backend/.venv frontend/.next frontend/node_modules
