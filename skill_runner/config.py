from dataclasses import dataclass, field
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class RunConfig:
    # OpenRouter
    api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    base_url: str = "https://openrouter.ai/api/v1"

    # Model
    model: str = "qwen/qwen3-8b"
    temperature: float = 0.0
    max_tokens: int = 16384  # qwen3 thinking needs headroom: ~4-8k think + tool calls

    # Agent loop
    max_iterations: int = 20

    # Tools
    bash_timeout: int = 120

    # Paths
    skills_dir: str = "./skills"
    workspace_dir: str = "./workspace"
    log_dir: str = "./logs"

    # Input files — filenames (not paths) to preserve in workspace across clean
    input_files: list[str] = field(default_factory=list)

    # Output — if set, copy all workspace output files here after each run.
    # Recommended structure: "<base>/distillation/<skill>/<test_case_id>/round_<N>/"
    # Leave None to skip (workspace files stay until next run cleans them).
    output_dir: str | None = None

    # Debug
    verbose: bool = False

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set. Copy .env.example to .env and fill in your key.")
