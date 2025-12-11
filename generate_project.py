"""Simple project generator for a minimal LLM evaluation pipeline.

This writes a few starter files (.gitignore, README.md, requirements.txt, and
the basic src/ package) into the target directory. By default it writes into the
current working directory.

Usage (PowerShell):
    python generate_project.py --dir .
"""

from pathlib import Path
import argparse


FILES = {
    ".gitignore": """
# Python
__pycache__/
*.pyc
.venv/
env/
venv/
*.egg-info/

# Data
*.sqlite3
data/
models/

# OS
.DS_Store

# IDE
.vscode/
.idea/

# Secrets
*.env
""",

    "README.md": """# BeyondChats — LLM Evaluation Pipeline (S-Tier)

Public repo: acrocantosauras/llm-evaluation-pipeline

## What this repo contains
S-Tier implementation of an evaluation pipeline for LLM responses which evaluates:
- Relevance & completeness
- Hallucinations / factual accuracy
- Latency & cost estimation

## Quickstart (local)
1. Clone the repo:

   git clone https://github.com/acrocantosauras/llm-evaluation-pipeline.git
   cd llm-evaluation-pipeline

2. Create and activate a virtual environment (Windows PowerShell example):

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

3. Install dependencies:

   pip install -r requirements.txt

4. Run any prepared script or the test harness:

   python -m src.main

## Contributing

This is intended as a small, self-contained generator for a minimal evaluation pipeline. See `src/` for more details.
""",

    "requirements.txt": """# Add your core runtime dependencies here
pytest
black
""",

    "src/main.py": """def main():
    print('This is a placeholder entrypoint for the LLM evaluation pipeline.')


if __name__ == '__main__':
    main()
""",

    "src/__init__.py": """# Package initializer for the evaluation pipeline.
""",
}


def write_project(target_dir: Path, files_map: dict, overwrite: bool = True):
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, content in files_map.items():
        file_path = target_dir / rel_path
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists() and not overwrite:
            print(f"Skipping existing file: {file_path}")
            continue

        with file_path.open("w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")

        print(f"Wrote {file_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a minimal project structure")
    parser.add_argument(
        "--dir",
        "-d",
        default=".",
        help="Target directory for the generated project",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Don't overwrite existing files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_project(args.dir, FILES, overwrite=not args.no_overwrite)


if __name__ == "__main__":
    main()
