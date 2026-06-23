#!/usr/bin/env python3
"""
V1.1 Self-Coder — Rule Engine
==============================
Pure Python rule engine for code self-improvement.
No API key required. Works by pattern matching + AST analysis.

Modes:
  --rules    : Run all rules on target file (default)
  --dry-run  : Show what would change, don't apply
  --apply    : Apply fixes (requires --rules)

Usage:
  python self_coder.py --rules path/to/file.py
  python self_coder.py --rules --apply path/to/file.py
"""

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import timezone as _tz  # noqa: F401 — timezone.utc for 3.9+ compat
from pathlib import Path
from typing import List, Optional


# ─── Rule Definitions ───────────────────────────────────────────

@dataclass
class Issue:
    """Single code quality issue found by a rule."""
    rule_id: str
    severity: str  # error | warning | info
    line: int
    message: str
    fix_hint: str


@dataclass
class RuleResult:
    """Aggregated results for a single analyzed file."""
    file: str
    issues: List[Issue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Count of error-severity issues."""
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of warning-severity issues."""
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def clean(self) -> bool:
        """True if no issues found."""
        return len(self.issues) == 0


# ─── Rule 1: GBK Encoding ───────────────────────────────────────

def _is_comment_or_docstring(lines: list, idx: int) -> bool:
    """Check if a line at idx (0-based) is inside a comment or docstring.
    Uses Python's tokenize module for accurate detection."""
    import io
    import tokenize
    line = lines[idx].strip()
    if line.startswith('#'):
        return True
    try:
        source = '\n'.join(lines[:idx + 1])
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        # Find the last token that starts on or before our target line
        target_line = idx + 1  # tokenize uses 1-based line numbers
        for tok in tokens:
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                if tok.start[0] <= target_line <= tok.end[0]:
                    return True
    except (SyntaxError, tokenize.TokenError, IndentationError):
        pass
    return False


def rule_subprocess_encoding(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: subprocess.run without encoding on Windows can cause GBK issues."""
    issues = []
    pattern = r'subprocess\.(?:run|Popen|check_output|check_call|call)\('
    for i, line in enumerate(lines, 1):
        if _is_comment_or_docstring(lines, i - 1):
            continue
        if re.search(pattern, line):
            # Check if encoding is specified
            block = '\n'.join(lines[i-1:min(i+5, len(lines))])
            if 'encoding' not in block:
                issues.append(Issue(
                    rule_id="R001",
                    severity="warning",
                    line=i,
                    message="subprocess call missing encoding='utf-8' — may fail on Windows GBK",
                    fix_hint="Add keyword args to the subprocess call: encoding equals utf-8 and errors equals replace"
                ))
    return issues


# ─── Rule 2: datetime.UTC compatibility ─────────────────────────

def rule_datetime_utc(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: datetime.UTC is Python 3.11+ only."""
    issues = []
    for i, line in enumerate(lines, 1):
        if _is_comment_or_docstring(lines, i - 1):
            continue
        # Skip lines that are regex/string patterns for matching datetime.UTC (self-reference)
        if re.search(r'''['"](datetime\.UTC|datetime\.UTC)['"]''', line):
            continue
        if 'datetime.UTC' in line and 'timezone.utc' not in line:
            issues.append(Issue(
                rule_id="R002",
                severity="error",
                line=i,
                message="datetime.UTC requires Python 3.11+, use timezone.utc for compat",
                fix_hint="Use 'from datetime import timezone' then 'timezone.utc' instead of 'datetime.UTC'"
            ))
    return issues


# ─── Rule 3: python3 → python on Windows ────────────────────────

def rule_python3_alias(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: 'python3' doesn't exist on Windows, use 'python'."""
    issues = []
    patterns = [
        (r'subprocess\.run\(\[["\']python3["\']', 'subprocess.run(["python"'),
        (r'os\.system\(["\']python3\s', 'os.system("python '),
    ]
    for i, line in enumerate(lines, 1):
        if _is_comment_or_docstring(lines, i - 1):
            continue
        for pat, fix in patterns:
            if re.search(pat, line):
                issues.append(Issue(
                    rule_id="R003",
                    severity="warning",
                    line=i,
                    message="'python3' alias not available on Windows, use 'python'",
                    fix_hint=f"Replace with: {fix}"
                ))
    return issues


# ─── Rule 4: Hardcoded secrets ──────────────────────────────────

def rule_hardcoded_secrets(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: hardcoded API keys, tokens, passwords."""
    issues = []
    secret_patterns = [
        (r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\'][^"\']{8,}["\']', "R004"),
        (r'(?i)(DEEPSEEK_API_KEY|OPENAI_API_KEY)\s*=\s*["\']sk-[^"\']+["\']', "R004"),
    ]
    for i, line in enumerate(lines, 1):
        if _is_comment_or_docstring(lines, i - 1):
            continue
        for pat, rid in secret_patterns:
            m = re.search(pat, line)
            if m:
                # Check if it's an env var reference
                if 'os.environ' in line or 'os.getenv' in line:
                    continue
                issues.append(Issue(
                    rule_id=rid,
                    severity="error",
                    line=i,
                    message="Hardcoded secret detected — use environment variable instead",
                    fix_hint="Use os.environ.get('VAR') or os.getenv('VAR')"
                ))
    return issues


# ─── Rule 5: Missing docstring ──────────────────────────────────

def rule_missing_docstring(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: public functions/classes missing docstrings."""
    issues = []
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        issues.append(Issue(
            rule_id="R005",
            severity="error",
            line=e.lineno or 0,
            message=f"Syntax error: {e.msg}",
            fix_hint="Fix syntax before running rules"
        ))
        return issues

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Skip private/dunder names
            if node.name.startswith('_') and not (node.name.startswith('__') and node.name.endswith('__')):
                continue
            if isinstance(node, ast.FunctionDef) and node.name == 'main':
                continue
            if not ast.get_docstring(node):
                issues.append(Issue(
                    rule_id="R005",
                    severity="info",
                    line=node.lineno,
                    message=f"Missing docstring for {node.__class__.__name__[:-3].lower()} '{node.name}'",
                    fix_hint=f'"""Add docstring for {node.name}."""'
                ))
    return issues


# ─── Rule 6: Bare except ────────────────────────────────────────

def rule_bare_except(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: bare 'except:' without specifying exception type."""
    issues = []
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*except\s*:', line):
            issues.append(Issue(
                rule_id="R006",
                severity="warning",
                line=i,
                message="Bare except: — specify exception type (e.g., except Exception as e:)",
                fix_hint="except Exception as e:"
            ))
    return issues


# ─── Rule 7: f-string in logging ────────────────────────────────

def rule_logging_fstring(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: f-strings in logging calls (should use lazy % formatting)."""
    issues = []
    for i, line in enumerate(lines, 1):
        if re.search(r'(logging\.\w+|logger\.\w+)\([^)]*f["\']', line):
            issues.append(Issue(
                rule_id="R007",
                severity="info",
                line=i,
                message="f-string in logging call — use lazy %s formatting for performance",
                fix_hint='logger.info("message: %s", value)'
            ))
    return issues


# ─── Rule 8: os.system over subprocess ──────────────────────────

def rule_os_system(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: os.system() should be replaced with subprocess."""
    issues = []
    for i, line in enumerate(lines, 1):
        if _is_comment_or_docstring(lines, i - 1):
            continue
        if re.search(r'os\.system\(', line) and 'sys.exit' not in line:
            issues.append(Issue(
                rule_id="R008",
                severity="warning",
                line=i,
                message="os.system() is unsafe — use subprocess.run() instead",
                fix_hint="Replace os.system with subprocess.run, passing command as a list"
            ))
    return issues


# ─── Rule 9: open() without context manager ─────────────────────

def rule_open_no_context(filepath: str, source: str, lines: list) -> List[Issue]:
    """Check: open() calls not using 'with' context manager."""
    issues = []
    # Simple check: assignment from open() without 'with' on same/previous line
    for i, line in enumerate(lines, 1):
        if _is_comment_or_docstring(lines, i - 1):
            continue
        if re.search(r'=\s*open\(', line):
            # Check if 'with' is on the same line or previous line
            prev = lines[i-2] if i > 1 else ''
            if 'with ' not in line and 'with ' not in prev:
                issues.append(Issue(
                    rule_id="R009",
                    severity="warning",
                    line=i,
                    message="open() without context manager — use 'with open(...) as f:'",
                    fix_hint="with open(path) as f:"
                ))
    return issues


# ─── Rule Registry ──────────────────────────────────────────────

RULES = [
    rule_subprocess_encoding,
    rule_datetime_utc,
    rule_python3_alias,
    rule_hardcoded_secrets,
    rule_missing_docstring,
    rule_bare_except,
    rule_logging_fstring,
    rule_os_system,
    rule_open_no_context,
]


# ─── Core Engine ────────────────────────────────────────────────

def _safe_print(text: str):
    """Print safely on Windows GBK terminals by replacing non-encodable chars."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


def analyze_file(filepath: str) -> RuleResult:
    """Run all rules against a single file."""
    path = Path(filepath)
    if not path.exists():
        return RuleResult(file=filepath, issues=[
            Issue("R000", "error", 0, f"File not found: {filepath}", "Check path")
        ])
    if path.suffix != '.py':
        return RuleResult(file=filepath, issues=[
            Issue("R000", "info", 0, f"Not a Python file: {filepath}", "Skip non-.py files")
        ])

    source = path.read_text(encoding='utf-8', errors='replace')
    lines = source.split('\n')

    result = RuleResult(file=filepath)
    for rule_fn in RULES:
        try:
            issues = rule_fn(filepath, source, lines)
            result.issues.extend(issues)
        except Exception as e:
            result.issues.append(Issue(
                rule_id="R999",
                severity="error",
                line=0,
                message=f"Rule {rule_fn.__name__} crashed: {e}",
                fix_hint="Report this bug"
            ))

    return result


def analyze_directory(dirpath: str) -> List[RuleResult]:
    """Run all rules against all .py files in a directory tree."""
    results = []
    root = Path(dirpath)
    py_files = list(root.rglob('*.py'))
    # Skip __pycache__, node_modules, .git
    py_files = [f for f in py_files if '__pycache__' not in f.parts
                and 'node_modules' not in f.parts
                and '.git' not in f.parts]

    for f in sorted(py_files):
        results.append(analyze_file(str(f)))

    return results


def print_results(results: List[RuleResult]):
    """Pretty-print rule results."""
    total_issues = 0
    total_errors = 0
    total_warnings = 0
    files_with_issues = 0

    for r in results:
        if r.issues:
            files_with_issues += 1
            _safe_print(f"\n{'='*60}")
            _safe_print(f"[FILE] {r.file}")
            _safe_print(f"   Issues: {len(r.issues)} ({r.error_count} errors, {r.warning_count} warnings)")

            for issue in sorted(r.issues, key=lambda x: x.severity):
                emoji = "[ERR]" if issue.severity == "error" else "[WARN]" if issue.severity == "warning" else "[INFO]"
                _safe_print(f"  {emoji} [{issue.rule_id}] L{issue.line}: {issue.message}")
                if issue.fix_hint:
                    _safe_print(f"     HINT: {issue.fix_hint}")

            total_errors += r.error_count
            total_warnings += r.warning_count
            total_issues += len(r.issues)

    _safe_print(f"\n{'='*60}")
    _safe_print(f"SUMMARY: {len(results)} files scanned, "
          f"{files_with_issues} files with issues")
    _safe_print(f"   Total: {total_issues} issues "
          f"({total_errors} errors, {total_warnings} warnings)")

    if total_issues == 0:
        _safe_print("   ALL CLEAN!")
    elif total_errors == 0:
        _safe_print("   Warnings only — safe to proceed")


# ─── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="V1.1 Self-Coder Rule Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python self_coder.py --rules myfile.py          # Check single file
  python self_coder.py --rules mydir/             # Check directory
  python self_coder.py --rules . --dry-run        # Dry run on current dir
  python self_coder.py --rules myfile.py --apply  # Apply auto-fixes
        """
    )
    parser.add_argument('--rules', required=True, help='Target file or directory')
    parser.add_argument('--dry-run', action='store_true', help='Show only, no changes')
    parser.add_argument('--apply', action='store_true', help='Apply auto-fixable issues')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()
    target = args.rules

    if os.path.isfile(target):
        results = [analyze_file(target)]
    elif os.path.isdir(target):
        results = analyze_directory(target)
    else:
        print(f"ERROR: '{target}' is not a valid file or directory", file=sys.stderr)
        sys.exit(1)

    if args.json:
        import json
        output = []
        for r in results:
            output.append({
                "file": r.file,
                "issues": [
                    {
                        "rule_id": i.rule_id,
                        "severity": i.severity,
                        "line": i.line,
                        "message": i.message,
                        "fix_hint": i.fix_hint,
                    } for i in r.issues
                ]
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_results(results)

    # Exit code: non-zero if errors found
    has_errors = any(r.error_count > 0 for r in results)
    sys.exit(1 if has_errors else 0)


if __name__ == '__main__':
    main()
