# Universal Orchestrator Kit

[![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](#) [![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Kit version: 1.0.0 (spec lineage) — the release number lives in [`VERSION`](VERSION) and on the [Releases](https://github.com/hardforkman/uok/releases) page.

A governance and safety layer for AI coding agents: **roles, evidence-based routing, a
PreToolUse security hook, and human approval gates** — installed into any project, on any
supported host, in minutes.

> **Graphify is the memory and the map; the Universal Orchestrator Kit is the governance and
> the safety.** They compose: the optional Graphify integration gives every role a
> read-only map of the codebase, while the kit decides who works, at what tier, with which
> checks, and what stays forbidden.

## What you get

- **11 worker roles** (`uok-*`) with one-line launch: `/uok <task>` (Claude Code, Qoder,
  Cursor, DSH) or `$uok <task>` (Codex). Single role: `/uok research-analyst <task>`; all
  roles: `/uok all <task>`; roster: `/uok roles`.
- **Cost-aware routing**: every task is classified (`core/TASK-CLASSIFICATION.md`) into
  CAT-01…08 and routed to the cheapest sufficient tier TIER-1…TIER-5
  (`core/routing-policy.yaml`). No silent escalation; review is TIER-5 and never a
  escalation target.
- **The G1 hook** (PreToolUse): blocks secret files, writes outside the project, worker
  writes into `.orchestrator/`, `.claude/` and the kit itself; asks a human before
  sensitive operations (force-push, deploys, credential changes). Fail-closed for workers,
  audited to `.orchestrator/audit/g1.log`.
- **Honest verification**: no success claim without command output. Every capability carries
  an explicit status — `verified_doc` / `verified_local` / `verified_live` / `unverified`.
- **Per-project statistics**: `uok stats` (or `--json`) reports what the kit actually did in
  a project — every G1 decision by cause, context-graph size and freshness, ledgers — and
  states plainly what is not measured. No invented benefit numbers.
- **Parallel workers with disjoint write claims**, independent review for high-impact work,
  human approval for production deploys and publication.
- **Optional context graph**: with [Graphify](https://github.com/Graphify-Labs/graphify)
  installed, roles orient by querying a code-only graph instead of reading files one by one;
  claims are derived from the impact subgraph. Fully offline (`GRAPHIFY_BACKEND=none`),
  fail-open, and community-built — **not affiliated with or endorsed by Graphify Labs**
  (Apache-2.0, see [`NOTICE-GRAPHIFY.md`](NOTICE-GRAPHIFY.md); rules CG-01…07 in
  [`core/CONTEXT-GRAPH.md`](core/CONTEXT-GRAPH.md)).

## Quick start

```bash
git clone https://github.com/hardforkman/uok.git ~/uok
python3 ~/uok/uok bootstrap          # registers the /uok-init skill for every host found
```

Then, in any project, open an agent session and type one phrase:

> Read `~/uok/START-HERE.md` and install the kit into this project as described there.

or directly: `uok init` (the `/uok-init` skill), which plans with `--dry-run` first, then
installs. Restart the session afterwards — role agents load at session start. That's it:
launch work with `/uok <task>`.

Requirements: Python 3.10+, PyYAML (`pip install pyyaml`). Hosts: Claude Code, Qoder,
Cursor, Codex (per-project installers), and DeepSeek Harness (user-level skills; DSH runs no
PreToolUse hook, so the kit's boundaries are enforced by its rules and the host's approval
flow — the launcher skill spells this out honestly).

## Updating

```bash
bash ~/uok/updater.sh --check        # what would come, changes nothing
bash ~/uok/updater.sh                # update to the latest RELEASE (tag vX.Y.Z) + refresh all projects
bash ~/uok/updater.sh --edge         # follow the main branch (unreleased work)
bash ~/uok/updater.sh --no-refresh   # update the kit folder only
python3 ~/uok/uok --version          # which release is installed
```

Releases are the default on purpose: an update rewrites the G1 hook, role agents and policy
in every recorded project, so only deliberately released versions reach them. The update is
fast-forward only and never clobbers local edits; a kit copy that is not a git repository
(release zip, folder copy) is repaired automatically — the old folder is preserved as
`<kit>.backup-<timestamp>` and replaced by a fresh clone. Projects are re-applied from the
registry (`~/.uok/projects.json`) with their original mode and models, and the user-level
skills (`~/.claude/skills`, `~/.dsh/skills`, …) are re-synced so their version never drifts
behind the release; user files are never touched, backups go to `.orchestrator/backups/`.

## How it is verified

The kit ships its own validation: `validation/self_test.py` (16 structural checks),
`validation/behavior_tests.py` (63 behavior checks incl. the graph-aware routing scenario
TS-13), `adapters/shared/hooks/test_g1_guard.py` (128 hook tests),
`adapters/shared/test_install_skill.py`, `adapters/shared/test_uok_cli.py` and
`adapters/shared/test_graphify_integration.py` — all six run before every release.
Live checks per host are documented in `handoff/LIVE-CHECKS.md` and recorded in
`handoff/INSTALLATION-REPORT-*.md`; the G1 hook additionally requires a recorded human
review (`handoff/HUMAN-REVIEW-G1.md`).

## Documentation

- [`USAGE-GUIDE.md`](USAGE-GUIDE.md) — the practical guide (English); Russian edition:
  [`USAGE-GUIDE-RU.md`](USAGE-GUIDE-RU.md).
- [`START-HERE.md`](START-HERE.md) — first-run entry point and adapter status table.
- [`UNIVERSAL-ORCHESTRATION-SPEC.md`](UNIVERSAL-ORCHESTRATION-SPEC.md) — the normative spec
  (requirement IDs ARCH/RT/ISO/SEC/QA/PROT/ADP/CFG/LC).
- [`AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md`](AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md) — the
  step-by-step agent directive.
- [`adapters/`](adapters/) — per-host installers and documentation.
- [`handoff/`](handoff/) — verification reports, live checks, human review.

## License

MIT — see [`LICENSE`](LICENSE) (c) 2026 hardforkman.
