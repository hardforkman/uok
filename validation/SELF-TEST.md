# SELF-TEST

Kit version: 1.0.0 · Spec version: 1.0.0 · Requirements: VAL-01, VAL-02

## How to run

```bash
cd UNIVERSAL-ORCHESTRATOR-KIT
python3 validation/self_test.py        # structural & consistency checks CHK-01…16
python3 validation/behavior_tests.py   # behavior scenarios TS-01…12 (28 assertions)
```

Dependencies: Python ≥ 3.10, PyYAML (`pip install pyyaml`). No network access,
no credentials, no side effects outside reading kit files. Both scripts exit
0 on full pass, 1 on any failure, and print per-check results.

## What self_test.py checks

| Check | Subject |
|-------|---------|
| CHK-01 | Required directory/file completeness (mandated skeleton + adapter READMEs) |
| CHK-02 | Document substance — no empty placeholder documents |
| CHK-03 | Every YAML file parses with PyYAML |
| CHK-04 | Embedded protocol schemas parse, are versioned, and cover all 15 contracts |
| CHK-05 | All relative markdown cross-references resolve |
| CHK-06 | Routing consistency: categories ↔ tiers ↔ floors ↔ escalation path ↔ roles |
| CHK-07 | Registry integrity: required fields, availability enums, examples stay `unverified`, fixtures isolated to the mock provider |
| CHK-08 | All 11 capability roles fully defined |
| CHK-09 | Lifecycle completeness: 12 states documented and schema-consistent |
| CHK-10 | Template required fields + conservative defaults (strict isolation, no auto-approve, redaction/audit on, all six sensitive ops gated, independence non-removable) |
| CHK-11 | All requirement IDs (ARCH/RT/ISO/SEC/QA/PROT/ADP/CFG/LC) present in the spec |
| CHK-12 | Adapter docs: 13 required sections each + valid capability profiles with legal statuses |
| CHK-13 | Traceability: AC-01…13 and TS-01…12 present in docs and fixtures |
| CHK-14 | Secret scan across every kit file (key/token/password/private-key patterns) |
| CHK-15 | Version header consistency across all markdown |
| CHK-16 | Isolation/security enforcement language present in handoff contract and gates |

## What behavior_tests.py verifies

Actual kernel behavior against [fixtures/tasks.yaml](fixtures/tasks.yaml):
routing tiers/models/roles, fallback and escalation chains, lifecycle
transition legality, dependency gating, claim-conflict prevention, approval
blocking, envelope rejection (project mismatch, missing grant, secret
content), review independence, and degraded-environment fallbacks. See
[COMPATIBILITY-TESTS.md](COMPATIBILITY-TESTS.md) §2 for the assertion list.

## Scope honesty

These tests validate the KIT and its reference kernel. They do not validate
any live vendor environment; adapter claims remain at their tagged
verification statuses until the receiving agent runs the live probes
(COMPATIBILITY-TESTS §3). If PyYAML is unavailable, report the tests as
`not_executed` — never claim a pass that did not run.

## Authoring-time execution record

- 2026-11-16: `self_test.py` → 16/16 checks passed; `behavior_tests.py` →
  28/28 checks passed (macOS, Python 3.12.2, PyYAML 6.0.2). Re-run both after
  any kit modification.