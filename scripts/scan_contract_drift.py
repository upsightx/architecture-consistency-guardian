#!/usr/bin/env python3
"""Detect multiple competing sources of truth in a codebase.

Scans for patterns that indicate contract drift:
- Multiple files defining the same config constant
- Multiple files writing to the same DB table
- Multiple files defining status/state value sets
- Multiple files acting as entry points for the same operation

Usage:
    python3 scan_contract_drift.py <directory> [--pattern-file <file>] [--ext .py]

The optional --pattern-file is a text file with one pattern per line (category:regex format)::

    config:DB_PATH\\s*=
    write:INSERT INTO observations
    state:STATUS_VALUES\\s*=
"""

import argparse
import os
import re
import sys
from collections import defaultdict


# Built-in detection patterns grouped by drift category
BUILTIN_PATTERNS = {
    "config_definition": [
        # Config constants being defined (not just read)
        r'^\s*[A-Z_]+PATH\s*=\s*["\'/]',
        r'^\s*[A-Z_]+DIR\s*=\s*["\'/]',
        r'^\s*[A-Z_]+URL\s*=\s*["\'/]',
        r'^\s*DB_PATH\s*=',
        r'^\s*DATABASE_PATH\s*=',
        r'^\s*MEMORY_DB_PATH\s*=',
        r'os\.environ\.get\(["\'\'][A-Z_]+PATH',
        r'os\.environ\[["\'\'][A-Z_]+PATH',
    ],
    "table_write": [
        r'INSERT\s+INTO\s+\w+',
        r'UPDATE\s+\w+\s+SET',
        r'\.execute\(["\'\']INSERT',
        r'\.execute\(["\'\']UPDATE',
        r'cursor\.execute.*INSERT',
        r'cursor\.execute.*UPDATE',
    ],
    "state_definition": [
        r'STATUS_VALUES\s*=',
        r'VALID_STATES\s*=',
        r'STATE_TRANSITIONS\s*=',
        r'ALLOWED_TRANSITIONS\s*=',
        r'status.*=.*["\'\']draft["\'\'].*["\'\']pending',
        r'lifecycle_status',
    ],
    "entry_point": [
        r'def\s+(process|handle|execute|dispatch|run|main)\s*\(',
        r'def\s+heartbeat\s*\(',
        r'def\s+evolve\s*\(',
        r'def\s+add_observation\s*\(',
    ],
}

DEFAULT_EXTENSIONS = {'.py', '.js', '.ts'}
DEFAULT_IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    '.mypy_cache', '.pytest_cache', 'dist', 'build',
}


def load_custom_patterns(filepath):
    """Load patterns from a file. Format: category:regex per line."""
    patterns = defaultdict(list)
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                cat, pat = line.split(':', 1)
                patterns[cat.strip()].append(pat.strip())
            else:
                patterns["custom"].append(line)
    return dict(patterns)


def scan_for_drift(directory, patterns, extensions, ignore_dirs):
    """Scan directory for contract drift patterns.
    
    Returns: {category: {pattern_desc: [(filepath, line_no, line)]}}
    """
    results = defaultdict(lambda: defaultdict(list))

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fname in files:
            ext = os.path.splitext(fname)[1]
            if ext not in extensions:
                continue
            fpath = os.path.join(root, fname)
            if os.path.islink(fpath):
                continue
            try:
                with open(fpath, 'r', errors='replace') as f:
                    for line_no, line in enumerate(f, 1):
                        for category, pats in patterns.items():
                            for pat in pats:
                                if re.search(pat, line):
                                    results[category][pat].append(
                                        (fpath, line_no, line.rstrip())
                                    )
            except (OSError, UnicodeDecodeError):
                continue

    return results


def analyze_drift(results, directory):
    """Analyze results to find competing sources (same pattern in multiple files)."""
    drift_warnings = []

    for category, pattern_hits in results.items():
        for pat, hits in pattern_hits.items():
            # Get unique files
            files = sorted(set(os.path.relpath(h[0], directory) for h in hits))
            if len(files) > 1:
                drift_warnings.append({
                    "category": category,
                    "pattern": pat,
                    "files": files,
                    "hit_count": len(hits),
                    "severity": "high" if category in ("config_definition", "state_definition") else "medium",
                })

    # Sort by severity then hit count
    severity_order = {"high": 0, "medium": 1, "low": 2}
    drift_warnings.sort(key=lambda w: (severity_order.get(w["severity"], 9), -w["hit_count"]))
    return drift_warnings


def print_report(drift_warnings, results, directory):
    """Print drift analysis report."""
    if not drift_warnings:
        print("✅ No contract drift detected. Each pattern maps to a single file.")
        return

    print(f"⚠️  Detected {len(drift_warnings)} potential contract drift(s):\n")

    print("| Severity | Category | Pattern | Files | Hits |")
    print("|----------|----------|---------|-------|------|")
    for w in drift_warnings:
        sev = "🔴" if w["severity"] == "high" else "🟡"
        files_str = ", ".join(w["files"][:3])
        if len(w["files"]) > 3:
            files_str += f" (+{len(w['files'])-3} more)"
        print(f"| {sev} {w['severity']} | {w['category']} | `{w['pattern'][:50]}` | {files_str} | {w['hit_count']} |")

    print("\n## Details\n")
    for w in drift_warnings:
        sev = "🔴" if w["severity"] == "high" else "🟡"
        print(f"### {sev} {w['category']}: `{w['pattern'][:60]}`")
        print(f"Found in {len(w['files'])} files:")
        for f in w["files"]:
            print(f"  - {f}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Detect competing sources of truth (contract drift) in a codebase."
    )
    parser.add_argument("directory", help="Root directory to scan")
    parser.add_argument("--pattern-file", help="Custom pattern file (category:regex per line)")
    parser.add_argument("--ext", nargs="*", default=None,
                        help="File extensions to scan")
    parser.add_argument("--ignore-dir", nargs="*", default=None,
                        help="Directory names to skip")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--builtin-only", action="store_true",
                        help="Use only built-in patterns (ignore --pattern-file)")

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: {args.directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    extensions = set(args.ext) if args.ext else DEFAULT_EXTENSIONS
    ignore_dirs = set(args.ignore_dir) if args.ignore_dir else DEFAULT_IGNORE_DIRS

    patterns = dict(BUILTIN_PATTERNS)
    if args.pattern_file and not args.builtin_only:
        custom = load_custom_patterns(args.pattern_file)
        for cat, pats in custom.items():
            if cat in patterns:
                patterns[cat].extend(pats)
            else:
                patterns[cat] = pats

    results = scan_for_drift(args.directory, patterns, extensions, ignore_dirs)
    warnings = analyze_drift(results, args.directory)

    if args.json:
        import json
        print(json.dumps(warnings, indent=2, ensure_ascii=False))
    else:
        print_report(warnings, results, args.directory)


if __name__ == "__main__":
    main()
