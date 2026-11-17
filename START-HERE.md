# START HERE — Universal Orchestrator Kit

Kit version: 1.0.0 · Spec version: 1.0.0

A portable, application-independent standard for AI agent and model
orchestration. You can hand this
directory to an AI coding agent in any supported environment; it contains
everything needed to understand, implement, and validate the system without
the original authoring application.

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