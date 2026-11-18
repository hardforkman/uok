# START HERE — Universal Orchestrator Kit

Kit version: 1.0.0 · Spec version: 1.0.0

A portable, application-independent standard for AI agent and model
orchestration. You can hand this
directory to an AI coding agent in any supported environment; it contains
everything needed to understand, implement, and validate the system without
the original authoring application.

Руководство по применению на русском: [USAGE-GUIDE-RU.md](USAGE-GUIDE-RU.md).

> Note: this kit is a specification + reference kernel + validation package.
> It is not a running service. "Installing" it means implementing its adapter
> in YOUR environment and reporting honestly what works.

## Reading order

| Step | Document | Purpose |
|------|----------|---------|
| 1 | [NORTH-STAR.md](NORTH-STAR.md) | Vision, principles, boundaries |
| 2 | [UNIVERSAL-ORCHESTRATION-SPEC.md](UNIVERSAL-ORCHESTRATION-SPEC.md) | Normative architecture + requirement IDs |
| 3 | [core/TASK-CLASSIFICATION.md](core/TASK-CLASSIFICATION.md) | The 8 task categories |
| 4 | [core/ROUTING-POLICY.md](core/ROUTING-POLICY.md) + [core/routing-policy.yaml](core/routing-policy.yaml) | Tier/model/agent selection algorithm |
| 5 | [core/MODEL-REGISTRY.yaml](core/MODEL-REGISTRY.yaml) | Model entries, availability, cost metadata |
| 6 | [core/AGENT-CAPABILITIES.yaml](core/AGENT-CAPABILITIES.yaml) | The 11 capability roles |
| 7 | [core/EXECUTION-LIFECYCLE.md](core/EXECUTION-LIFECYCLE.md) | States, parallelism, isolation |
| 8 | [core/QUALITY-GATES.md](core/QUALITY-GATES.md) | Gates, metrics, security, self-improvement |
| 9 | [protocols/TASK-CONTRACT.md](protocols/TASK-CONTRACT.md), [protocols/AGENT-PROTOCOL.md](protocols/AGENT-PROTOCOL.md), [protocols/HANDOFF-CONTRACT.md](protocols/HANDOFF-CONTRACT.md) | Machine-readable contracts |
| 10 | [adapters/ADAPTER-IMPLEMENTATION-SPEC.md](adapters/ADAPTER-IMPLEMENTATION-SPEC.md) + your environment's adapter | Native integration |
| 11 | [templates/](templates/) | Project / model / agent configuration |
| 12 | [validation/SELF-TEST.md](validation/SELF-TEST.md) | Run the checks |
| 13 | [AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md](AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md) | **Receiving agents: execute this** |
| 14 | [handoff/INSTALLATION-REPORT-TEMPLATE.md](handoff/INSTALLATION-REPORT-TEMPLATE.md) | Report your results |

## If you are a receiving AI agent

Go directly to
[AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md](AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md).
It is independently executable: inspect → audit → plan → implement → validate
→ report. Do not stop at a plan unless genuinely blocked.

**Fast path.** If your environment's adapter directory contains an `install.py`,
it performs directive steps 8-12 for you (additive, idempotent, with backups):

| Environment | Installer | Status |
|---|---|---|
| Claude Code | `python3 adapters/claude-code/install.py` | integration_tested (live, 2026-11-17) |
| Qoder | `python3 adapters/qoder/install.py` | integration_tested (live, 2026-11-17) |
| Cursor | `python3 adapters/cursor/install.py` | implementation_available (installer tested; live checks pending) |
| Codex | `python3 adapters/codex/install.py` | implementation_available (installer tested; live checks pending) |
| other | none: follow the directive with `adapters/universal/README.md`; build your own adapter using `adapters/claude-code` and `adapters/qoder` (integration_tested) as reference implementations | specification_complete |

**Primary install path: `uok init`.** Once per machine, run
`python3 UNIVERSAL-ORCHESTRATOR-KIT/uok bootstrap`
to register a user-level `uok-init` skill; then in any project session type `uok init`
(or `/uok-init`; Codex: `$uok-init`) and the agent installs the kit there.
The same CLI works in a terminal: `python3 UNIVERSAL-ORCHESTRATOR-KIT/uok init --host <host>`.

Direct installer invocation remains available. Run each installer with `--dry-run` first.
All of them share `adapters/shared/` (installer core + G1 hook).
Every installer also creates a launcher skill: run `/uok <task>` (Claude Code, Qoder, Cursor) or the
`$uok` mention (Codex) to start orchestration; see USAGE-GUIDE-RU §6.1 and your adapter README §12-13.
Start the argument with a role id (`/uok research-analyst <task>`) to call one agent, with `all` to run the
full roster, or use `/uok roles` to list roles. Update the kit from its git remote with `bash updater.sh`
(`--check` previews; see README "Обновление").

Live checks for Qoder, Cursor and Codex: paste the prompt from
[handoff/LIVE-CHECKS.md](handoff/LIVE-CHECKS.md) into that application's agent chat.
Human review of the G1 hook: [handoff/HUMAN-REVIEW-G1.md](handoff/HUMAN-REVIEW-G1.md).

You still do steps 1-7 (identify, inspect, read, audit) and step 13 (report),
and you pass the model aliases you actually probed (`--models`).

## Quick validation

```bash
cd UNIVERSAL-ORCHESTRATOR-KIT
python3 validation/self_test.py        # structure, YAML, cross-references, consistency
python3 validation/behavior_tests.py   # 12 behavior scenarios against the reference kernel
```

Requires Python ≥ 3.10 and PyYAML (`pip install pyyaml`). No network access.

## Directory contents

```
UNIVERSAL-ORCHESTRATOR-KIT/
├── START-HERE.md / NORTH-STAR.md / UNIVERSAL-ORCHESTRATION-SPEC.md
├── AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md
├── core/          routing policy (md+yaml), model registry, agent capabilities,
│                  task classification, execution lifecycle, quality gates
├── protocols/     agent protocol, task contract, handoff contract (versioned schemas)
├── adapters/      implementation spec + claude-code / qoder / cursor / codex / universal
├── templates/     PROJECT-CONFIG.yaml / MODEL-CONFIG.yaml / AGENT-CONFIG.yaml
├── validation/    acceptance criteria, compatibility tests, self-test docs,
│                  executable self_test.py + behavior_tests.py + reference_router.py
└── handoff/       installation report template
```

Additions beyond the mandated skeleton (documented, intentional):
`core/routing-policy.yaml` (machine-readable policy), adapter `PROFILE.yaml`
capability matrices, and the executable validation scripts/fixtures. They make
the kit testable rather than merely readable.

## Honesty contract

Every capability claim in this kit carries a verification status
(`unknown` / `unverified` / `verified_doc` / `verified_local` / `verified_live`).
Adapter documentation was researched against official docs in November 2026;
anything not confirmed is tagged. Real model entries in the registry are
illustrative and `unverified` — confirm them in your environment. Test fixtures
(`test_only: true`) are deterministic fakes used only by the behavior tests.