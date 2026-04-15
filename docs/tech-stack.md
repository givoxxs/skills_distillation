# Tech Stack

## Tổng quan Layer

| Layer | Công nghệ | Mục đích |
|-------|-----------|-----------|
| Teacher LLM | Claude Haiku 4.5 | Rewrite Skill, generate evaluation rules |
| Student Models | Qwen3-8B (via OpenRouter), Phi-4, Others | Thực thi skills (không local hiện tại) |
| Skill Format | Markdown (`SKILL.md`) | Định dạng chuẩn cho mọi Skills |
| Evaluator | Rule-based + LLM Judge (Claude) | Đánh giá output tự động (hybrid) |
| CLI Framework | Click | Command-line interface (run.py, main.py) |
| Output Formatting | Rich | Terminal output formatting & visualization |
| Config Management | PyYAML + python-dotenv | Config files + environment variables |
| Testing | pytest | Unit tests (offline, no API) |
| Code Quality | pre-commit hooks + ruff | Linting & formatting automation |
| Orchestration | Python (distillation/orchestrator.py) | Điều phối pipeline |

---

## Optional Features (Future)

These are not currently integrated but can be added for extended functionality:

- **Vector DB**: ChromaDB hoặc FAISS (cho RAG features sau)
- **RAG Engine**: LangChain / LlamaIndex (retrieve examples)
- **Local Inference**: Ollama (để chạy student model on-device)
- **Experiment tracking**: MLflow hoặc W&B (track metrics)

---

## Dependencies

### Core Runtime (Required)

```bash
anthropic==0.84.0          # Anthropic API client (Teacher LLM)
openai==2.28.0             # OpenRouter API client (Student models)
python-dotenv==1.2.2       # Environment variable management
click>=8.1.0               # CLI framework
rich>=13.0.0               # Terminal output formatting
pyyaml>=6.0                # YAML config parsing
```

### Development (Optional)

```bash
pytest>=7.0                # Testing framework
pre-commit>=4.5.0          # Git hooks for code quality
```

Install with: `bash requirements.sh` or `pip install -r requirements.txt`

---

## Architecture Pattern

The system uses a **Teacher-Student optimization loop**:

1. **Teacher (Claude)** rewrites SKILL.md based on Student's failures
2. **Student (Qwen3-8B via OpenRouter)** executes tasks with new SKILL.md
3. **Evaluator (Hybrid)** scores the output
4. Loop repeats until quality threshold met

This is different from fine-tuning because:
- ✅ No model weights are modified
- ✅ No new training data needed
- ✅ Works with any model that follows instructions
- ✅ Ultra-fast iteration (minutes, not hours/days)
