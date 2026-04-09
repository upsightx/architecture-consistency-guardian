# Architecture Consistency Guardian

An [OpenClaw](https://github.com/openclaw/openclaw) skill that enforces system-wide consistency before code changes. It transforms the default "patch the error site" behavior into a disciplined "scan globally → identify source of truth → modify as a group → audit for residue → verify" workflow.

## Problem

When AI agents (or humans) fix code, they tend to:
- Fix only the current file, ignoring callers, config, docs, and tests
- Rename a variable in one place but leave the old name in 10 others
- Fix a state machine branch without checking if other modules use stale status values
- Update a path in config but leave hardcoded copies elsewhere
- Remove a legacy module but keep silent fallbacks that route back to it
- Report "fixed" without checking what old logic is still alive

This skill forces a **global-first posture** for every change that touches shared contracts.

## When to Use

- Unifying variable/field/parameter names across files
- Consolidating state machines (status values, transitions, write-back entries)
- Cleaning legacy paths, fallbacks, or retired modules
- Aligning configuration sources (DB paths, env vars, runtime config)
- Syncing documentation with code after refactoring
- Any bug fix where the root cause might be contract drift

## Mandatory 8-Phase Workflow

1. **Classify** — Determine the consistency category (naming, state-machine, config-path, etc.)
2. **Identify Source of Truth** — Find the canonical file; flag competing sources
3. **Global Scan** — Search ALL references, not just the current file
4. **Modification Plan** — List affected files and changes before touching code
5. **Grouped Execution** — Modify source of truth → callers → config → compat → tests → docs
6. **Residue Audit** — Search for old names, old states, old paths, old fallbacks still present
7. **Regression Verification** — Run tests, grep for zero old-name hits, validate config resolution
8. **Structured Report** — Output: source of truth, scope, changes, residual compat, verification results

## Bundled Scripts

| Script | Purpose |
|--------|---------|
| `scripts/grep_legacy.py` | Scan for legacy name/path/status residue |
| `scripts/scan_contract_drift.py` | Detect multiple competing sources of truth |
| `scripts/summarize_impacts.py` | Aggregate scan results into impact summaries |

### Quick Examples

```bash
# Find legacy residue
python3 scripts/grep_legacy.py /path/to/project old_status_field legacy_module_name

# Detect contract drift (multiple sources defining the same thing)
python3 scripts/scan_contract_drift.py /path/to/project

# Pipe grep results into impact summary
python3 scripts/grep_legacy.py /path/to/project old_name --json | \
  python3 scripts/summarize_impacts.py --source-of-truth config.py
```

## Directory Structure

```
architecture-consistency-guardian/
├── SKILL.md                    # Core workflow and hard rules
├── references/
│   ├── workflow.md             # Detailed workflow with decision branches
│   ├── output_template.md      # Structured report template
│   ├── risk_patterns.md        # 8 common consistency risk patterns
│   └── contract_template.md    # Architecture contract template
├── templates/
│   ├── consistency_report_template.md
│   └── architecture_contract_template.md
└── scripts/
    ├── grep_legacy.py
    ├── scan_contract_drift.py
    └── summarize_impacts.py
```

## Installation

Copy the skill directory to your OpenClaw skills folder:

```bash
cp -r architecture-consistency-guardian ~/.openclaw/skills/
```

Or install from the `.skill` package:

```bash
openclaw skill install architecture-consistency-guardian.skill
```

## License

MIT
