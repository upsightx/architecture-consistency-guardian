#!/usr/bin/env python3
"""Scan directories for legacy name/path/status residue.

Usage:
    python3 grep_legacy.py <directory> <pattern1> [pattern2] ... [--ext .py .md] [--ignore-dir .git __pycache__]

Examples:
    python3 grep_legacy.py /path/to/project old_status feedback_loop change_applier
    python3 grep_legacy.py /path/to/project "evolution_changes" --ext .py .sql
    python3 grep_legacy.py /path/to/project "DB_PATH.*=.*/" --regex
"""

import argparse
import os
import re
import sys
from collections import defaultdict


DEFAULT_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.md', '.yaml', '.yml',
    '.json', '.toml', '.cfg', '.ini', '.sql', '.sh', '.bash',
}
DEFAULT_IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    '.mypy_cache', '.pytest_cache', 'dist', 'build', '.egg-info',
}


def scan_file(filepath, patterns, use_regex=False):
    """Scan a single file for pattern matches. Returns list of (line_no, line, pattern)."""
    hits = []
    try:
        with open(filepath, 'r', errors='replace') as f:
            for line_no, line in enumerate(f, 1):
                for pat in patterns:
                    if use_regex:
                        if re.search(pat, line):
                            hits.append((line_no, line.rstrip(), pat))
                    else:
                        if pat in line:
                            hits.append((line_no, line.rstrip(), pat))
    except (OSError, UnicodeDecodeError):
        pass
    return hits


def scan_directory(directory, patterns, extensions, ignore_dirs, use_regex=False):
    """Walk directory and scan files. Returns {filepath: [(line_no, line, pattern)]}."""
    results = defaultdict(list)
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fname in files:
            ext = os.path.splitext(fname)[1]
            if ext not in extensions:
                continue
            fpath = os.path.join(root, fname)
            # Skip symlinks to avoid loops
            if os.path.islink(fpath):
                continue
            hits = scan_file(fpath, patterns, use_regex)
            if hits:
                results[fpath] = hits
    return results


def print_results(results, directory):
    """Print results grouped by file."""
    if not results:
        print("✅ No legacy residue found.")
        return

    total_hits = sum(len(v) for v in results.values())
    print(f"⚠️  Found {total_hits} hit(s) across {len(results)} file(s):\n")

    # Group by pattern for summary
    by_pattern = defaultdict(list)
    for fpath, hits in sorted(results.items()):
        rel = os.path.relpath(fpath, directory)
        for line_no, line, pat in hits:
            by_pattern[pat].append((rel, line_no, line))

    # Summary table
    print("## Summary by pattern\n")
    print(f"| Pattern | Files | Hits |")
    print(f"|---------|-------|------|")
    for pat, entries in sorted(by_pattern.items()):
        files = len(set(e[0] for e in entries))
        print(f"| `{pat}` | {files} | {len(entries)} |")

    # Detail
    print(f"\n## Detail\n")
    for fpath, hits in sorted(results.items()):
        rel = os.path.relpath(fpath, directory)
        print(f"### {rel}")
        for line_no, line, pat in hits:
            # Truncate long lines
            display = line[:120] + "..." if len(line) > 120 else line
            print(f"  L{line_no}: {display}  ← `{pat}`")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Scan for legacy name/path/status residue in a codebase."
    )
    parser.add_argument("directory", help="Root directory to scan")
    parser.add_argument("patterns", nargs="+", help="Patterns to search for")
    parser.add_argument("--ext", nargs="*", default=None,
                        help="File extensions to include (e.g., .py .md)")
    parser.add_argument("--ignore-dir", nargs="*", default=None,
                        help="Directory names to skip")
    parser.add_argument("--regex", action="store_true",
                        help="Treat patterns as regular expressions")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of markdown")

    args = parser.parse_args()

    extensions = set(args.ext) if args.ext else DEFAULT_EXTENSIONS
    ignore_dirs = set(args.ignore_dir) if args.ignore_dir else DEFAULT_IGNORE_DIRS

    if not os.path.isdir(args.directory):
        print(f"Error: {args.directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    results = scan_directory(args.directory, args.patterns, extensions, ignore_dirs, args.regex)

    if args.json:
        import json
        out = {}
        for fpath, hits in results.items():
            rel = os.path.relpath(fpath, args.directory)
            out[rel] = [{"line": ln, "text": txt, "pattern": pat} for ln, txt, pat in hits]
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print_results(results, args.directory)


if __name__ == "__main__":
    main()
