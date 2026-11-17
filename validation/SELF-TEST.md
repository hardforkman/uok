# SELF-TEST

Kit version: 1.0.0 · Spec version: 1.0.0 · Requirements: VAL-01, VAL-02

## How to run

```bash
cd UNIVERSAL-ORCHESTRATOR-KIT
python3 validation/self_test.py        # structural & consistency checks CHK-01…16
python3 validation/behavior_tests.py   # behavior scenarios TS-01…12 (51 assertions)
python3 adapters/shared/hooks/test_g1_guard.py   # G1 hook suite (123 tests)
python3 adapters/shared/test_install_skill.py    # installer skill-launcher step (5 tests, scratch projects)
python3 adapters/shared/test_uok_cli.py          # uok launcher: init dispatch + bootstrap (11 tests, scratch HOME)
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
| CHK-04 | Embedded protocol schemas parse, are versioned, and cover all 16 contracts |
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
content), review independence, and degraded-environment fallbacks. Since
2026-11-17 the suite also carries audit regression checks: tier-overflow
clamps, consumed-step fallback progression, reviewer instance exclusion,
G3/G4 completion enforcement, approval/grant expiry, waiver semantics,
cycle rejection, and doc-only-verification flagging. See
[COMPATIBILITY-TESTS.md](COMPATIBILITY-TESTS.md) §2 for the assertion list.

## Scope honesty

These tests validate the KIT and its reference kernel. They do not validate
any live vendor environment; adapter claims remain at their tagged
verification statuses until the receiving agent runs the live probes
(COMPATIBILITY-TESTS §3). If PyYAML is unavailable, report the tests as
`not_executed` — never claim a pass that did not run.

## Authoring-time execution record

- 2026-11-16: `self_test.py` → 16/16 checks passed; `behavior_tests.py` →
  28/28 checks passed (macOS, Python 3.12.2, PyYAML 6.0.2).
- 2026-11-17 (post independent audit, all findings fixed): `self_test.py` →
  16/16 checks passed; `behavior_tests.py` → 51/51 checks passed (same
  environment). Re-run both after any kit modification.
- 2026-11-17 (skill launcher added): `test_g1_guard.py` → 123/123;
  `test_install_skill.py` → 5/5 (skill creation, frontmatter, idempotency,
  dry-run, user-skill preservation on all four hosts); full installs of all
  four adapters into scratch projects exited 0 with the skill created and a
  no-change rerun. Live skill invocation in each host remains pending
  (`verified_doc` mechanisms, installer `verified_local`).
- 2026-11-17 (uok init primary path): `test_uok_cli.py` → 11/11 (init
  dispatch/dry-run/auto-detect/ambiguity, bootstrap creation/frontmatter/
  idempotency/backup/user-skill preservation/dry-run/home-marker detection,
  scratch HOME). Live in Qoder Desktop (2026-11-17): bootstrap → skill pickup
  without restart → `uok-init` invocation → `uok init` install, exit 0, hook
  suite OK, smoke PASS (handoff/INSTALLATION-REPORT-qoder-2026-11-17.md);
  other hosts pending.