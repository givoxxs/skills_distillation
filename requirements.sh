# !/bin/bash
# python = 3.11+, tested with 3.12

# ── Core Runtime Dependencies ─────────────────────────────────────
pip install anthropic==0.84.0          # Anthropic API client (Teacher LLM)
pip install openai==2.28.0             # OpenRouter API client (Student models)
pip install python-dotenv==1.2.2       # Environment variable management
pip install click>=8.1.0                # CLI framework
pip install rich>=13.0.0                # Terminal output formatting
pip install pyyaml>=6.0                 # YAML config parsing
pip install python-docx>=1.1.0         # Read .docx files in evaluator (rule checks)

# ── Dev Dependencies (optional) ───────────────────────────────────
pip install pytest>=7.0                 # Testing framework
pip install pre-commit>=4.5.0           # Git hooks for code quality
