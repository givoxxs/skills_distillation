#!/usr/bin/env bash
# Start the FastAPI backend for the Skill Distillation UI
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
conda run -n skills uvicorn server:app --host 0.0.0.0 --port 8000 --reload
