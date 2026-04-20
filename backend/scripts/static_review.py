"""
Static project-rule checks specific to PaintLearn backend.
Catches things ruff/bandit cannot: architectural rules, naming conventions, structural requirements.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
VENV_PARTS = {"venv", "migrations", ".git", "__pycache__"}


def _is_excluded(path: Path) -> bool:
    return any(part in VENV_PARTS for part in path.parts)


# ── Rule 1: Every FastAPI endpoint must declare response_model ─────────────────

def check_response_models() -> list[str]:
    issues = []
    ROUTER_METHODS = {"get", "post", "put", "patch", "delete"}

    for router_path in ROOT.glob("*/router.py"):
        if _is_excluded(router_path):
            continue
        try:
            source = router_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                func = dec.func
                if not (isinstance(func, ast.Attribute) and func.attr in ROUTER_METHODS):
                    continue
                has_response_model = any(kw.arg == "response_model" for kw in dec.keywords)
                if not has_response_model:
                    issues.append(
                        f"  {router_path.relative_to(ROOT)}:{node.lineno}"
                        f" - {node.name}() is missing response_model="
                    )
    return issues


# ── Rule 2: No raise HTTPException in source (use AppError subclasses) ─────────

def check_no_http_exception() -> list[str]:
    issues = []
    for path in ROOT.rglob("*.py"):
        if _is_excluded(path) or "tests" in path.parts or "scripts" in path.parts:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            if "raise HTTPException" in line:
                issues.append(
                    f"  {path.relative_to(ROOT)}:{i}"
                    f" - raise HTTPException found (use AppError subclass instead)"
                )
    return issues


# ── Rule 3: Every module with router.py must have a tests/{module}/ dir ────────

def check_test_directories() -> list[str]:
    issues = []
    tests_dir = ROOT / "tests"
    for router_path in ROOT.glob("*/router.py"):
        if _is_excluded(router_path):
            continue
        module = router_path.parent.name
        if not (tests_dir / module).is_dir():
            issues.append(f"  tests/{module}/ missing — no tests for module '{module}'")
    return issues


# ── Rule 4: No plain token stored in DB (must use _hash_token) ─────────────────

def check_token_hashing() -> list[str]:
    """
    Flag .token = <something> assignments where the value is NOT _hash_token().
    Only checks attribute assignments (obj.token = ...) to target DB writes.
    """
    issues = []
    for path in ROOT.rglob("*.py"):
        if _is_excluded(path) or "tests" in path.parts or "scripts" in path.parts:
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            continue

        for node in ast.walk(tree):
            # Only care about `something.token = value`
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not (isinstance(target, ast.Attribute) and target.attr == "token"):
                    continue
                # The RHS must be a call to _hash_token
                rhs = node.value
                is_hashed = (
                    isinstance(rhs, ast.Call)
                    and isinstance(rhs.func, ast.Name)
                    and rhs.func.id == "_hash_token"
                )
                if not is_hashed:
                    issues.append(
                        f"  {path.relative_to(ROOT)}:{node.lineno}"
                        f" - .token assigned without _hash_token()"
                    )
    return issues


# ── Rule 5: Every module with router.py must have a module plan doc ────────────

def check_module_plans() -> list[str]:
    issues = []
    plans_dir = ROOT.parent / "docs" / "module_plans"
    plan_files = list(plans_dir.glob("*.md")) if plans_dir.exists() else []
    plan_names = " ".join(f.name for f in plan_files)

    for router_path in ROOT.glob("*/router.py"):
        if _is_excluded(router_path):
            continue
        module = router_path.parent.name
        if module not in plan_names:
            issues.append(
                f"  docs/module_plans/ has no plan for module '{module}'"
                f" — create docs/module_plans/XX_{module}.md before implementing"
            )
    return issues


# ── Runner ─────────────────────────────────────────────────────────────────────

RULES = [
    ("All endpoints declare response_model", check_response_models),
    ("No direct raise HTTPException", check_no_http_exception),
    ("Test directory exists per module", check_test_directories),
    ("Tokens stored via _hash_token only", check_token_hashing),
    ("Module plan doc exists per module", check_module_plans),
]


def main() -> None:
    all_passed = True

    for label, check_fn in RULES:
        issues = check_fn()
        if issues:
            print(f"  [FAIL] {label}")
            for issue in issues:
                print(issue)
            all_passed = False
        else:
            print(f"  [OK]   {label}")

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
