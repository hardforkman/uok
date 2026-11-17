# INSTALLATION REPORT — Universal Orchestrator Kit

Kit version: 1.0.0 · Spec version: 1.0.0
Template status: fill every section; write `none` / `not_executed` explicitly
where applicable. Never leave a section blank and never claim unexecuted
work. This report implements the `final_handoff` schema
(../protocols/HANDOFF-CONTRACT.md §3).

---

## 1. Installation identity

- Report ID / date:
- Receiving agent (product + version + runtime mode: TUI / IDE / headless / SDK):
- Target project(s) (`project_id`):
- Kit version installed:
- Installer (agent identity) and supervising human:

## 2. Environment audit summary

- Discovery evidence (paths inspected, commands run — redacted):
- Capability matrix: attach the filled `PROFILE.yaml` (per-capability status
  + evidence). Summarize the notable `verified_live` / `not_found` items:
- Pre-existing configuration found and preserved (files, backups taken):

## 3. Implementation performed

- Files created (paths + purpose):
- Files modified (paths + backup location + diff summary):
- Native mechanisms used (agents, hooks, permissions, isolation, model selectors):
- Fallback mechanisms implemented (per ADAPTER-IMPLEMENTATION-SPEC §4):
- Degradations recorded (e.g. degraded_model_routing, degraded_parallelism,
  degraded_independence) and their impact:
- User configuration preserved? (diff evidence; deviations and why):

## 4. Gap analysis

| Requirement area | Native support | Adaptation | Gap / not_implemented + reason |
|------------------|----------------|------------|--------------------------------|
| Multi-agent execution | | | |
| Per-task model routing | | | |
| Parallel safety | | | |
| Blocking enforcement (G1) | | | |
| Context isolation | | | |
| Independent review (G3) | | | |
| Approval gates | | | |
| Ledger / audit | | | |

## 5. Validation results (actual executions only)

| Test | Command / probe | Result | Evidence |
|------|-----------------|--------|----------|
| Kit self-test | `python3 validation/self_test.py` | pass / fail / not_executed | output excerpt |
| Behavior tests | `python3 validation/behavior_tests.py` | pass / fail / not_executed | output excerpt |
| L1 routing dry-run | | | |
| L2 agent registration | | | |
| L3 parallelism & claims | | | |
| L4 availability & fallback | | | |
| L5 independent review | | | |
| L6 approval & isolation | | | |

Failed probes: list with findings and follow-up tasks (a failed probe is a
finding, not something to hide).

## 6. Maturity declaration (per adapter)

- Adapter: `claude-code / qoder / cursor / codex / universal`
- Level reached: `specification_complete / implementation_available /
  integration_tested / operationally_verified`
- Justification (evidence for the level; what is missing for the next level):

## 7. Security & isolation attestation

- No secrets copied into kit files, configs, logs, or this report: yes/no
- Approval gates active for all six sensitive operation classes: yes/no
- Strict project isolation active; cross-project grants issued (list or none):
- Redaction method in use:
- Rollback plan for installation changes (backup restore instructions):

## 8. Known limitations

- (environment constraints, unverified items, degradations, residual risks)

## 9. Outstanding work

- (not_implemented items, failed probes, pending approvals, next tasks)

## 10. Recommended next phase

- (e.g. re-audit unverified capabilities after product update; run L4–L6
  probes; independent fresh-agent dry run for AC-12; policy tuning from
  measured metrics after N tasks)

---

Honesty attestation: every `verified_live` claim above was actually executed
in this environment; every unexecuted item is marked `not_executed`; no
capability, price, or test result was invented.

Installer signature (agent id) / date:
Human reviewer (if required by project gates) / date: