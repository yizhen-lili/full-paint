"""
PreToolUse hook: blocks Edit, Write, MultiEdit, and file-writing Bash
when scripts/.needs_review marker exists.

Exit codes:
  0 = allow tool to proceed
  2 = block tool, show stderr to Claude (Claude Code convention)

Emergency override: set BYPASS_REVIEW=1 in environment.
"""
import json
import os
import sys
from pathlib import Path

MARKER = Path(__file__).parent / ".needs_review"

# Bash commands that manage the review lock itself - always allow through
LOCK_MANAGEMENT_KEYWORDS = [".needs_review", "clear_review.py"]

# Patterns that indicate a Bash command is writing to a file
FILE_WRITE_PATTERNS = [" > ", " >> ", "| tee ", "echo >", "cat >", "printf >"]


def is_file_writing_bash(command: str) -> bool:
    return any(p in command for p in FILE_WRITE_PATTERNS)


def block(reason: str) -> None:
    print(f"BLOCKED: {reason}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Run /reviewer now. The reviewer will unlock Edit/Write when done.", file=sys.stderr)
    print("Emergency override: set BYPASS_REVIEW=1 in environment.", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    # Emergency bypass for the human operator
    if os.environ.get("BYPASS_REVIEW") == "1":
        sys.exit(0)

    # No marker = no block
    if not MARKER.exists():
        sys.exit(0)

    # Parse tool input from stdin
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, ValueError):
        data = {}

    # ── Bash tool ──────────────────────────────────────────────────────────────
    command = data.get("command", "")
    if command:
        # Always allow lock-management commands (reviewer's clear_review.py call)
        if any(kw in command for kw in LOCK_MANAGEMENT_KEYWORDS):
            sys.exit(0)
        # Allow non-file-writing bash (grep, cat, pytest, etc.)
        if not is_file_writing_bash(command):
            sys.exit(0)
        block("/reviewer not invoked — cannot write files via Bash")

    # ── Edit / Write / MultiEdit tool ─────────────────────────────────────────
    file_path = data.get("file_path", data.get("new_path", "unknown"))
    block(f"/reviewer not invoked — cannot edit {file_path}")


if __name__ == "__main__":
    main()
