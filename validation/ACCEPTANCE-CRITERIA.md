# ACCEPTANCE CRITERIA

Kit version: 1.0.0 · Spec version: 1.0.0
Requirements: VAL-01 (executable validation exists and runs), VAL-02 (behavior
tests verify actual kernel behavior, not documentation presence).

Each criterion has a stable ID, a verification method, and the requirement it
traces to. The kit is acceptable only when every criterion passes or its
failure is honestly reported with impact.

| ID | Criterion | Verification method | Traces to |
|----|-----------|---------------------|-----------|
| AC-01 | Every required directory and file exists (mandated skeleton + documented additions) | self_test CHK-01 | directive §3, §17 |
| AC-02 | Every required document is implemented with substantive content; no empty placeholders | self_test CHK-02 + manual reading | §15, §17 |
| AC-03 | All YAML files parse with a real parser; templates contain required fields and conservative defaults | self_test CHK-03, CHK-10 (PyYAML) | §12, CFG-01/02 |
| AC-04 | Universal architecture internally consistent: three layers, four routing planes, stable terminology, no vendor dependency in Layer A | self_test CHK-11 + manual review of spec §1–2 | ARCH-01…04 |
| AC-05 | Routing behavior and task lifecycle explicitly defined and mutually consistent (categories ↔ tiers ↔ roles ↔ states) | self_test CHK-06, CHK-09; behavior_tests TS-01/02/03/05/06/07 | RT-01…07, LC-01…04 |
| AC-06 | Agent and task protocols documented with versioned machine-readable schemas, error semantics, evolution rules | self_test CHK-04 (16 schemas parse, version 1) | PROT-01…03 |
| AC-07 | Context isolation and security are mandatory requirements, enforced in contracts/gates and proven by behavior tests | self_test CHK-16; behavior_tests TS-09/10/11 | ISO-01…06, SEC-01…10 |
| AC-08 | Adapter implementation requirements actionable: 13 documented aspects, discovery procedure, fallback ladder, installation preservation | self_test CHK-12 + manual review | ADP-01…03 |
| AC-09 | Every adapter directory contains a meaningful README + capability profile with verification statuses | self_test CHK-12 | §3, §11, ADP-03 |
| AC-10 | Validation scenarios cover all 12 mandatory behaviors and execute against the reference kernel with real assertions | behavior_tests TS-01…TS-12 (28 checks) | §14, QA-01…04 |
| AC-11 | Cross-document references consistent (links resolve; IDs traceable spec → core → protocols → adapters → tests) | self_test CHK-05, CHK-13 | §15 |
| AC-12 | An independent receiving agent can implement the system from the kit alone: AUTONOMOUS-IMPLEMENTATION-DIRECTIVE is self-contained, 13 executable steps, blocker protocol | manual review: no reference to authoring app/conversation; dry-run by a fresh agent | §13, §17 |
| AC-13 | Honest reporting: verification-status ladder applied everywhere; spec readiness distinguished from operational readiness; no fabricated capabilities/tests | self_test CHK-07 (examples unverified, fixtures isolated), CHK-14 (no secrets); manual review of adapter tags | NS-07, §11, §17 |

## Verification commands

```bash
cd UNIVERSAL-ORCHESTRATOR-KIT
python3 validation/self_test.py        # AC-01…AC-09, AC-11, AC-13 (structural)
python3 validation/behavior_tests.py   # AC-05, AC-07, AC-10 (behavioral)
```

AC-12 additionally requires a human or fresh-agent dry run: hand the kit to an
agent in a different environment and confirm it reaches an installation report
without external context. Record the outcome in the installation report.

## Current status (updated 2026-11-17)

- AC-01…AC-11, AC-13: verified by executed self-tests (see SELF-TEST.md for
  actual run outputs and dates; post-audit runs: 16/16 structural, 51/51
  behavior, 123/123 G1 hook tests).
- AC-12: partial. A fresh Claude Code session independently live-verified the
  installed adapter on 2026-11-17 (see
  [../handoff/INSTALLATION-REPORT-claude-code-2026-11-17.md](../handoff/INSTALLATION-REPORT-claude-code-2026-11-17.md)).
  A full install-from-kit-alone run by a receiving agent in a second
  environment was executed live in Qoder on 2026-11-17 (`uok init` primary
  path, see ../handoff/INSTALLATION-REPORT-qoder-2026-11-17.md);
  Cursor/Codex still pending → `unverified` for those.
- Live-environment adapter verification: claude-code `integration_tested`
  (live checks 1–12 executed); qoder `integration_tested` (LIVE-CHECKS
  items a–e executed live 2026-11-17); cursor/codex `implementation_available`
  (installers tested on sample projects, not yet live inside the apps —
  prompts in [../handoff/LIVE-CHECKS.md](../handoff/LIVE-CHECKS.md));
  universal `specification_complete`.