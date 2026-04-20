"""
Run all quality gates for the backend.
Called by Claude Code hooks after editing backend source files.
Also callable standalone: python scripts/quality_check.py

When all gates pass, creates scripts/.needs_review marker.
The PreToolUse hook blocks Edit/Write until /reviewer clears this marker.
"""
import json
import subprocess
import sys
from pathlib import Path

MARKER = Path(__file__).parent / ".needs_review"


def run_check(cmd: str, label: str) -> bool:
    print(f"\n{'-' * 50}")
    print(f"  {label}")
    print(f"{'-' * 50}")
    result = subprocess.run(cmd, shell=True)  # noqa: S602
    if result.returncode != 0:
        print(f"\n  [FAIL] {label} FAILED -- fix before continuing\n")
        return False
    print(f"\n  [OK] {label} passed\n")
    return True


def is_backend_source_file(path: str) -> bool:
    p = path.replace("\\", "/")
    return (
        "backend" in p
        and p.endswith(".py")
        and "/tests/" not in p
        and "/migrations/" not in p
        and "/venv/" not in p
        and "/scripts/" not in p
    )


def main() -> None:
    # When called by hook: read stdin to check if the edited file is a backend source
    if not sys.stdin.isatty():
        try:
            data = json.loads(sys.stdin.read())
            file_path = data.get("file_path", "")
            if file_path and not is_backend_source_file(file_path):
                sys.exit(0)  # not a backend source file, skip silently
        except (json.JSONDecodeError, KeyError):
            pass  # standalone call or unexpected format, run checks anyway

    print("\nPaintLearn Backend Quality Gates\n")

    checks = [
        (
            "venv\\Scripts\\ruff check . --exclude venv,migrations --quiet",
            "Gate 1 - Ruff (lint & style)",
        ),
        (
            "venv\\Scripts\\bandit -c pyproject.toml -r . -q",
            "Gate 2 - Bandit (security scan)",
        ),
        (
            "venv\\Scripts\\python scripts\\static_review.py",
            "Gate 3 - Static review (project rules)",
        ),
        (
            "venv\\Scripts\\python -m pytest tests/ -x -q --tb=short",
            "Gate 4 - Pytest (all tests)",
        ),
    ]

    for cmd, label in checks:
        ok = run_check(cmd, label)
        if not ok:
            print("Stopping -- fix the above failure before proceeding.\n")
            sys.exit(1)

    # Create marker — PreToolUse hook will block Edit/Write until reviewer clears it
    MARKER.touch()

    print("=" * 50)
    print("All mechanical gates passed.")
    print("=" * 50)
    print()
    print("BLOCKED: Edit/Write tools are now disabled.")
    print("Reason: reviewer has not yet been invoked.")
    print()
    print("Run /reviewer now.")
    print("The reviewer sub-agent will clear the block when done.")
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
