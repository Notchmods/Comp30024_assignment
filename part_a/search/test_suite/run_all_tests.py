#!/usr/bin/env python3
"""Run all CSV test cases against `python -m search`.

Usage:
  python run_all_tests.py
  python run_all_tests.py --show-output
  python run_all_tests.py --pattern "test_cases/*.csv"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_project_root(script_dir: Path) -> Path:
    """
    Climb up from the script directory until we find the 
    folder that CONTAINS the 'search' directory.
    """
    for parent in [script_dir] + list(script_dir.parents):
        # We want the folder that HAS 'search' as a child, 
        # but is not 'search' itself.
        if (parent / "search").is_dir() and (parent / "search" / "__main__.py").exists():
            return parent
    return script_dir


def discover_tests(root: Path, patterns: list[str]) -> list[Path]:
    tests: set[Path] = set()
    for pattern in patterns:
        tests.update(root.glob(pattern))
    return sorted(p for p in tests if p.is_file() and p.suffix.lower() == ".csv")


def parse_solution_file(root: Path) -> dict[str, list[str]]:
    """
    Parse expected `$SOLUTION ...` lines from solution.txt.
    Key is section name from `# === name ===` (usually matches csv stem).
    """
    candidate_paths = [
        root / "search" / "solution.txt",
        root / "solution.txt",
    ]
    path = next((p for p in candidate_paths if p.exists()), None)
    if path is None:
        return {}

    expected: dict[str, list[str]] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()

            if line.startswith("# ===") and line.endswith("==="):
                if current_name is not None:
                    expected[current_name] = current_lines
                current_name = line.removeprefix("# ===").removesuffix("===").strip()
                current_lines = []
                continue

            if line.startswith("$SOLUTION ") and current_name is not None:
                current_lines.append(line)

    if current_name is not None:
        expected[current_name] = current_lines

    return expected


def extract_solution_lines(stdout: str) -> list[str]:
    return [line.strip() for line in stdout.splitlines() if line.strip().startswith("$SOLUTION ")]


def run_one(
    test_path: Path,
    root: Path,
    expected_map: dict[str, list[str]],
    show_output: bool,
) -> tuple[bool, str]:
    with test_path.open("rb") as f:
        proc = subprocess.run(
            [sys.executable, "-m", "search"],
            cwd=root,
            stdin=f,
            capture_output=True,
            text=True,
        )

    rel_name = str(test_path.relative_to(root))
    test_key = test_path.stem
    expected = expected_map.get(test_key)
    actual = extract_solution_lines(proc.stdout)

    ok = proc.returncode == 0
    mismatch_reason = None

    if expected is None:
        ok = False
        mismatch_reason = f"No expected entry found in solution.txt for '{test_key}'"
    elif actual != expected:
        ok = False
        mismatch_reason = "Output does not match expected solution sequence"

    status = "PASS" if ok else "FAIL"

    lines = [f"[{status}] {rel_name}"]

    if mismatch_reason:
        lines.append(f"Reason: {mismatch_reason}")
        if expected is not None:
            lines.append("--- expected $SOLUTION lines ---")
            if expected:
                lines.extend(expected)
            else:
                lines.append("<no $SOLUTION lines>")
        lines.append("--- actual $SOLUTION lines ---")
        if actual:
            lines.extend(actual)
        else:
            lines.append("<no $SOLUTION lines>")

    if show_output or not ok:
        if proc.stdout.strip():
            lines.append("--- stdout ---")
            lines.append(proc.stdout.rstrip())
        if proc.stderr.strip():
            lines.append("--- stderr ---")
            lines.append(proc.stderr.rstrip())

    return ok, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all CSV test cases for Part A")
    parser.add_argument(
        "--pattern",
        action="append",
        default=None,
        help="Glob pattern(s) relative to project root. Can be used multiple times.",
    )
    parser.add_argument(
        "--show-output",
        action="store_true",
        help="Show solver output for passing tests as well.",
    )
    parser.add_argument(
        "--stop-on-fail",
        action="store_true",
        help="Stop as soon as a test fails.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    root = find_project_root(script_dir)
    patterns = args.pattern if args.pattern else [
        "test_cases/*.csv",
        "search/test_cases/*.csv",
        "test-*.csv",
        "search/test-*.csv",
    ]
    tests = discover_tests(root, patterns)
    expected_map = parse_solution_file(root)

    if not tests:
        print("No CSV tests found.")
        return 1

    if not expected_map:
        print("Warning: solution.txt is missing or has no parsed sections; tests will be marked FAIL due to missing expected output.")

    print(f"Found {len(tests)} test case(s).")

    passed = 0
    failed = 0

    for test in tests:
        ok, report = run_one(test, root, expected_map, args.show_output)
        print(report)
        print()

        if ok:
            passed += 1
        else:
            failed += 1
            if args.stop_on_fail:
                break

    print("=" * 40)
    print(f"Summary: {passed} passed, {failed} failed, {passed + failed} total")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
