#!/usr/bin/env python3
"""Aggregate scan results into an impact summary for consistency reports.

Reads JSON output from grep_legacy.py or scan_contract_drift.py and produces
a structured impact summary suitable for Phase 8 reports.

Usage:
    python3 grep_legacy.py <dir> <patterns...> --json | python3 summarize_impacts.py
    python3 summarize_impacts.py --file scan_results.json [--source-of-truth runtime_config.py]

Can also be used as a library:
    from summarize_impacts import summarize
    summary = summarize(results_dict, source_of_truth="runtime_config.py")
"""

import argparse
import json
import sys
from collections import defaultdict


def classify_file(filepath):
    """Classify a file into a role category."""
    path_lower = filepath.lower()

    if any(k in path_lower for k in ['test_', '_test.', 'tests/', 'test/']):
        return 'test'
    if path_lower.endswith('.md'):
        return 'documentation'
    if any(k in path_lower for k in ['config', 'settings', 'env']):
        return 'configuration'
    if any(k in path_lower for k in ['migration', 'schema', 'alembic']):
        return 'schema'
    if any(k in path_lower for k in ['skill.md', 'readme']):
        return 'documentation'
    return 'source'


def summarize(results, source_of_truth=None):
    """Summarize grep_legacy.py JSON output into an impact report.
    
    Args:
        results: dict of {filepath: [{line, text, pattern}]} from grep_legacy --json
        source_of_truth: optional canonical file path
    
    Returns:
        dict with summary statistics and categorized impacts
    """
    if not results:
        return {
            "total_files": 0,
            "total_hits": 0,
            "clean": True,
            "by_category": {},
            "by_pattern": {},
            "source_of_truth_affected": False,
        }

    total_hits = sum(len(hits) for hits in results.values())
    
    # Group by file category
    by_category = defaultdict(lambda: {"files": [], "hits": 0})
    for filepath, hits in results.items():
        cat = classify_file(filepath)
        by_category[cat]["files"].append(filepath)
        by_category[cat]["hits"] += len(hits)

    # Group by pattern
    by_pattern = defaultdict(lambda: {"files": set(), "hits": 0})
    for filepath, hits in results.items():
        for hit in hits:
            pat = hit.get("pattern", "unknown")
            by_pattern[pat]["files"].add(filepath)
            by_pattern[pat]["hits"] += 1
    # Convert sets to sorted lists
    for pat in by_pattern:
        by_pattern[pat]["files"] = sorted(by_pattern[pat]["files"])

    # Check if source of truth is affected
    sot_affected = False
    if source_of_truth:
        for filepath in results:
            if source_of_truth in filepath:
                sot_affected = True
                break

    return {
        "total_files": len(results),
        "total_hits": total_hits,
        "clean": total_hits == 0,
        "by_category": dict(by_category),
        "by_pattern": dict(by_pattern),
        "source_of_truth_affected": sot_affected,
        "source_of_truth": source_of_truth,
    }


def print_summary(summary):
    """Print a human-readable impact summary."""
    if summary["clean"]:
        print("✅ Clean — no legacy residue detected.")
        return

    print(f"## Impact Summary\n")
    print(f"- **Total files affected**: {summary['total_files']}")
    print(f"- **Total hits**: {summary['total_hits']}")
    
    if summary.get("source_of_truth"):
        status = "⚠️ YES" if summary["source_of_truth_affected"] else "✅ No"
        print(f"- **Source of truth ({summary['source_of_truth']}) affected**: {status}")

    # By category
    print(f"\n### By file category\n")
    print(f"| Category | Files | Hits |")
    print(f"|----------|-------|------|")
    for cat, data in sorted(summary["by_category"].items(), key=lambda x: -x[1]["hits"]):
        print(f"| {cat} | {len(data['files'])} | {data['hits']} |")

    # By pattern
    print(f"\n### By pattern\n")
    print(f"| Pattern | Files | Hits |")
    print(f"|---------|-------|------|")
    for pat, data in sorted(summary["by_pattern"].items(), key=lambda x: -x[1]["hits"]):
        display = pat[:60] + "..." if len(pat) > 60 else pat
        print(f"| `{display}` | {len(data['files'])} | {data['hits']} |")

    # Affected files list
    print(f"\n### Affected files\n")
    all_files = set()
    for data in summary["by_category"].values():
        all_files.update(data["files"])
    for f in sorted(all_files):
        cat = classify_file(f)
        print(f"- `{f}` ({cat})")


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate legacy scan results into an impact summary."
    )
    parser.add_argument("--file", help="JSON file from grep_legacy.py --json (default: stdin)")
    parser.add_argument("--source-of-truth", help="Canonical file path to check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            results = json.load(f)
    else:
        if sys.stdin.isatty():
            print("Error: Provide --file or pipe JSON from grep_legacy.py --json", file=sys.stderr)
            sys.exit(1)
        results = json.load(sys.stdin)

    summary = summarize(results, source_of_truth=args.source_of_truth)

    if args.json:
        # Convert sets for JSON serialization
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=list))
    else:
        print_summary(summary)


if __name__ == "__main__":
    main()
