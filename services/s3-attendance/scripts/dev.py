"""Developer commands that work the same on Linux, macOS and Windows.

Usage (from services/s3-attendance/):

    uv run scripts/dev.py check     ruff check, ruff format --check, mypy, lint-imports
    uv run scripts/dev.py fmt       auto-fix lint issues and format the code
    uv run scripts/dev.py test      unit + api tests (no database needed)
    uv run scripts/dev.py test-db   integration + e2e tests (needs PostgreSQL)
    uv run scripts/dev.py all       check, then every test
"""

import subprocess
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent

CHECK = [
    ["ruff", "check", "."],
    ["ruff", "format", "--check", "."],
    ["mypy"],
    ["lint-imports"],
]

COMMANDS: dict[str, list[list[str]]] = {
    "check": CHECK,
    # Format first: `ruff check --fix` exits non-zero on unfixable issues and would stop the run.
    "fmt": [["ruff", "format", "."], ["ruff", "check", "--fix", "."]],
    "test": [["pytest", "-m", "unit or api"]],
    "test-db": [["pytest", "-m", "integration or e2e"]],
    "all": [*CHECK, ["pytest"]],
}


def main(args: list[str]) -> int:
    if len(args) != 1 or args[0] not in COMMANDS:
        print(__doc__)
        return 2
    for command in COMMANDS[args[0]]:
        print("$", " ".join(command), flush=True)
        code = subprocess.call(command, cwd=SERVICE_DIR)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
