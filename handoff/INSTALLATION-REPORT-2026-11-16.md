# INSTALLATION REPORT — Universal Orchestrator Kit (authoring-time handoff)

Kit version: 1.0.0 · Spec version: 1.0.0 · Date: 2026-11-16, updated 2026-11-17
This is the kit author's final handoff (directive §18), filled from the
INSTALLATION-REPORT-TEMPLATE. It reports the kit's own delivery state — NOT
an installation into a target project. Receiving agents produce their own
reports from the template after installing.

## 1. Identity

- Deliverable: `UNIVERSAL-ORCHESTRATOR-KIT/` at `/Users/snm/UNIORK/`
- Authoring environment: Qoder Desktop agent session (macOS, Python 3.12.2,
  PyYAML 6.0.2). The kit itself is application-independent (ARCH-04).
- Kit version: 1.0.0 · Protocol schema version: 1 · Policy version: 1.0.0

## 2. Completed directory tree

```
UNIVERSAL-ORCHESTRATOR-KIT/
├── uok                              (addition: launcher CLI — init + bootstrap)
├── START-HERE.md
├── NORTH-STAR.md
├── UNIVERSAL-ORCHESTRATION-SPEC.md
├── AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md
├── USAGE-GUIDE-RU.md                  (addition: Russian usage guide)
├── core/
│   ├── ROUTING-POLICY.md
│   ├── routing-policy.yaml            (addition: machine-readable policy)
│   ├── MODEL-REGISTRY.yaml
│   ├── AGENT-CAPABILITIES.yaml
│   ├── TASK-CLASSIFICATION.md
│   ├── EXECUTION-LIFECYCLE.md
│   └── QUALITY-GATES.md
├── protocols/
│   ├── AGENT-PROTOCOL.md
│   ├── TASK-CONTRACT.md
│   └── HANDOFF-CONTRACT.md
├── adapters/
│   ├── ADAPTER-IMPLEMENTATION-SPEC.md
│   ├── claude-code/  README.md + PROFILE.yaml + install.py
│   ├── qoder/        README.md + PROFILE.yaml + install.py
│   ├── cursor/       README.md + PROFILE.yaml + install.py
│   ├── codex/        README.md + PROFILE.yaml + install.py
│   ├── universal/    README.md + PROFILE.yaml
│   └── shared/       uok_install.py (shared installer core) + test_install_skill.py + test_uok_cli.py
│       └── hooks/    g1_guard.py + uok_search.py + test_g1_guard.py + README.md
├── templates/
│   ├── PROJECT-CONFIG.yaml
│   ├── MODEL-CONFIG.yaml
│   └── AGENT-CONFIG.yaml
├── validation/
│   ├── ACCEPTANCE-CRITERIA.md
│   ├── COMPATIBILITY-TESTS.md
│   ├── SELF-TEST.md
│   ├── self_test.py                   (addition: executable structural tests)
│   ├── behavior_tests.py              (addition: executable behavior tests)
│   ├── reference_router.py            (addition: reference kernel)
│   └── fixtures/tasks.yaml            (addition: TS-01…12 scenario data)
└── handoff/
    ├── INSTALLATION-REPORT-TEMPLATE.md
    ├── INSTALLATION-REPORT-2026-11-16.md  (this report)
    ├── INSTALLATION-REPORT-claude-code-2026-11-17.md  (live installation)
    ├── INSTALLATION-REPORT-qoder-2026-11-17.md  (live uok init path)
    ├── LIVE-CHECKS.md                 (live-probe prompts for Qoder/Cursor/Codex)
    └── HUMAN-REVIEW-G1.md             (human review guide for the G1 hook)
```

54 kit files, ~512 KB (sum of file bytes), plain Markdown/YAML/Python. No credentials anywhere
(CHK-14 secret scan passes).

## 3. Architectural decisions

1. Three layers (A universal core / B adapters / C runtime) with four
   explicit routing planes (model, agent, tool, execution-environment) —
   ARCH-01/02. Layer A contains zero vendor dependencies.
2. Deterministic routing: category base tier + additive modifiers (capped
   TIER-3) + hard floors + capability filters + deterministic ranking;
   escalation never enters TIER-5; exhaustion ⇒ human escalation. Fully
   specified in prose AND machine-readable YAML AND executable kernel.
3. Registry honesty: real-vendor entries are illustrative (`example: true`,
   `availability: unverified`, costs `unknown`); deterministic `test_only`
   mock fixtures power the behavior tests without network or fabrication.
4. Roles ≠ models: 11 capability roles; one model may serve many roles;
   reviewer independence enforced by model/instance exclusion.
5. Isolation via context envelopes with mandatory redaction attestation and
   scoped, expiring cross-project grants; parallelism via a resource-claim
   ledger (write-write and write-read conflicts blocked) with worktree/native
   alternatives per adapter.
6. Verification-status ladder (`unknown` → `verified_live`) and adapter
   maturity ladder (`specification_complete` → `operationally_verified`)
   applied to every claim; documentation alone never implies operational.
7. Executable validation: the specification is proven by a reference kernel
   (routing, lifecycle state machine, claims, envelopes, fallback selection)
   rather than asserted by prose.

## 4. Implemented protocols and schemas

16 versioned machine-readable schemas (schema_version 1), embedded in the
protocol documents and parser-checked by self_test CHK-04: task,
resource_claim, routing_decision, lifecycle_event, gate_result,
approval_record, waiver, result_payload, agent_register, status_update,
error_report, escalation, validation_verdict, context_envelope,
cross_project_grant, final_handoff. Plus adapter_profile (5 instances).
Evolution rules: strict mode default, additive minor versions, breaking
changes ⇒ new schema_version.

## 5. Adapter coverage and maturity

| Adapter | Maturity (2026-11-17) | Basis |
|---------|----------|------------------------------|
| claude-code | integration_tested | Installed in /Users/snm/UNIORK; live checks 1–12 executed by a fresh Claude Code session (agent dispatch, model aliases, restricted shell, claim enforcement, independent review) — see INSTALLATION-REPORT-claude-code-2026-11-17.md. Not production-hardened; human review still required for sensitive work |
| qoder | integration_tested | Live inside Qoder Desktop 2026-11-17: `uok init` primary path, `/uok` launcher, worker dispatch, SEC-02/04 denials, full SEC-07 human-approval round-trip, claims + parallel writers (LC-04), read-only research-analyst — all LIVE-CHECKS items a–e passed (INSTALLATION-REPORT-qoder-2026-11-17.md); model selectors unverified |
| cursor | implementation_available | Same installer test basis; `preToolUse` input fields unverified; not yet live inside Cursor |
| codex | implementation_available | Same installer test basis (apply_patch parsing, ask→deny); not yet live inside Codex |
| universal | specification_complete | fallback design (role sessions, claim ledger, headless/API/manual ladder); baseline matrix all `unknown` pending probes |

Research basis (2026-11-16/17): official docs fetched and tagged per claim in
each PROFILE.yaml; gaps stay `unverified`/`unknown`/`not_found`.

## 6. Validation commands executed (actual)

| Command | Result |
|---------|--------|
| `python3 validation/self_test.py` | 16/16 checks passed (CHK-01…16) |
| `python3 validation/behavior_tests.py` | 51/51 assertions passed (TS-01…12 + audit regressions) |
| `python3 adapters/shared/hooks/test_g1_guard.py` | 123/123 tests passed (standard/strict/host-format suites) |
| `python3 adapters/shared/test_install_skill.py` | 5/5 tests passed (skill step: creation/frontmatter/idempotency/dry-run/user-skill preservation, all 4 hosts) |
| Full installs of all 4 adapters into scratch projects | exit 0 each; skill created; smoke deny PASS; qoder rerun: zero changes |
| `python3 adapters/shared/test_uok_cli.py` | 11/11 tests passed (init dispatch/dry-run/auto-detect; bootstrap creation/idempotency/backup/user-skill preservation, scratch HOME) |
| PyYAML parse of all 12 YAML files | all pass |

Environment: macOS (darwin 23.2.0), Python 3.12.2, PyYAML 6.0.2. No network
calls in tests. Two defects were found and fixed during development
(approval flag lookup in the kernel; pairwise claim comparison before
acquisition); an independent audit on 2026-11-17 found 12 further issues,
all fixed (§6a) — final runs above are post-fix.

## 6a. Independent audit and fixes (2026-11-17)

An independent review agent re-ran both suites, reproduced defects, and
returned ACCEPT_WITH_FINDINGS (12 findings, 7 major). All were fixed and
covered by new regression assertions (28 → 51 behavior checks):

| # | Finding | Fix |
|---|---------|-----|
| F1 | CAT-08 with all-high modifiers overflowed the tier ladder (IndexError) | compute_tier clamps CAT-08 to TIER-4; requested_tier clamped below TIER-5 |
| F2 | Expired/empty-operations approvals accepted at EXECUTING | `_approval_valid`: task-scoped, named human approver, non-empty ops, unexpired; G4 rechecks expiry at COMPLETED |
| F3 | Envelope-embedded cross-project grants trusted | validate_envelope accepts grants ONLY from the receiver-held registry; expiry enforced; whole-project/wildcard scopes rejected; HANDOFF-CONTRACT §1 documents grant authority |
| F4 | Fallback chain could repeat a consumed step forever | plan_fallback takes `consumed` and progresses to human_escalation |
| F5 | Reviewer could share the implementer's instance/family silently | instance exclusion + different-family preference; `degraded_independence` flag when only same-family reviewers exist |
| F6 | Waivers/cycles/G3 undocumented or unenforced | transition(): cycle rejection at DECOMPOSED, explicit human waivers (dependency/review/partial_acceptance), G3 verdict with evidence at COMPLETED; waiver schema added; EXECUTION-LIFECYCLE §8 |
| F7 | CAT-07 "mutating intent" undefined; requires_approval missing from routing_decision schema | defined as any declared write claim; schema field added; kernel + tests |
| F8 | Claude Code nesting depth claimed verified_doc from conflicting sources | retagged `unverified` in README + PROFILE |
| F9 | Layer A lifecycle doc cited Qoder-specific mechanisms | vendor examples removed (adapter-neutral wording) |
| F10 | Report file count/size stale | recounted: 49 files, ~544 KB |
| F11 | verified_doc mechanisms selected without a caveat flag | `doc_only_verification` flag in select_execution_environment |
| F12 | Commented example pricing looked like real figures | replaced with null placeholders |

## 6b. Skill launcher (2026-11-17 addition)

Every installer now creates a native launcher skill so the kit runs via a
shortcut: `/uok <task>` in Claude Code (`.claude/skills/uok/SKILL.md`,
`disable-model-invocation: true`, `$ARGUMENTS`), Qoder
(`.qoder/skills/uok/SKILL.md`) and Cursor (`.cursor/skills/uok/SKILL.md`,
task in the same message); `$uok` mention in Codex
(`.agents/skills/uok/SKILL.md` — Codex skills are not slash commands).
Mechanisms are `verified_doc` (official docs, URLs in each PROFILE.yaml
`skills` entry); the installer step is `verified_local`
(test_install_skill.py 5/5 + full scratch installs). Live invocation in
each host is pending. The skill body defers to the marked instruction
section and `.orchestrator/policy/`; user-authored `uok` skills are never
overwritten; G1 additionally write-protects `.agents/` for workers.

## 6c. Primary installation path: `uok init` (2026-11-17 addition)

New launcher CLI at the kit root (`uok`, stdlib-only Python):
- `uok init [--host auto|…] [--project DIR] [--mode] [--models] [--dry-run]`
  dispatches to the adapter installer; host auto-detection is a documented
  heuristic (env prefixes → project config dirs → home config dirs), and the
  session skill always passes `--host` explicitly.
- `uok bootstrap [--host auto|all|…]` registers a user-level `uok-init` skill
  once per machine, so typing `uok init` (or `/uok-init`; Codex: `$uok-init`)
  in ANY project session performs the primary installation. Global skill
  directories verified against official docs (2026-11-17):
  `~/.claude/skills/`, `~/.qoder/skills/`, `~/.cursor/skills/`,
  `~/.agents/skills/` (PROFILE.yaml `skills` entries). Bootstrap is additive
  and idempotent, backs up kit-managed updates to `~/.uok/backups/<ts>/`, and
  never touches user-authored skills.
Evidence: test_uok_cli.py 11/11 (`verified_local`); **live in Qoder Desktop
2026-11-17**: bootstrap → skill hot-pickup without restart → `uok-init`
invocation → `uok init` install into a scratch project, exit 0, hook suite OK,
smoke PASS; then `/uok <task>` in a new session on the installed project ran the
lifecycle with live G1 hook logging; worker dispatch + live denials SEC-04
(worker write to host config), SEC-02 (.env read), the full SEC-07
ask → human-rejection round-trip (default permission mode), claims
enforcement with two parallel disjoint-claim writers (in-claim allows,
out-of-claim and cross-claim denies, LC-04), and a read-only
`uok-research-analyst` dispatch also verified_live — all LIVE-CHECKS items
a–e passed, Qoder adapter raised to `integration_tested`
(INSTALLATION-REPORT-qoder-2026-11-17.md). Live invocation in Cursor / Codex
pending.

## 7. Test results summary

All 12 mandatory scenarios verified as actual kernel behavior: economical
routing, complexity escalation, specialization filter, safe parallelism,
dependency sequencing, unavailable-model fallback, retry/escalation chain,
independent review + rejection rework, approval blocking, isolation rejection
(project mismatch / missing grant / secret content), write-conflict
prevention, degraded-environment fallback with sequential enforcement.

## 8. Known limitations

- AC-12 full install-from-kit-alone dry run: performed only partially — a
  fresh Claude Code session live-verified the installed adapter; a complete
  independent installation in Qoder/Cursor/Codex is still pending.
- Live probes inside Qoder, Cursor, Codex: not executed (agent CLIs absent on
  the authoring machine); prompts ready in LIVE-CHECKS.md.
- Live invocation of the `/uok` (`$uok`) launcher skill in each host: not
  executed; installer-side evidence only (§6b).
- Live invocation of `uok init` / `uok-init`: verified_live in Qoder Desktop
  (INSTALLATION-REPORT-qoder-2026-11-17.md); Claude Code / Cursor / Codex pending.
- Human security review of the G1 hook: not done (guide: HUMAN-REVIEW-G1.md).
- Adapter research gaps are tagged `unverified`/`unknown`/`not_found` in
  each PROFILE.yaml (e.g. Cursor custom subagents and preToolUse fields,
  Claude Code nesting depth, full hook event lists).
- Registry contains no verified real-model facts; receiving agents must
  probe and fill MODEL-CONFIG before real routing. Claude Code model aliases
  observed live (sonnet/opus/haiku/fable) are session-specific, not registry
  facts.
- Reference kernel is a conformance tool, not a production scheduler;
  production execution uses native runtimes via adapters.
- Vendor docs moved during research (OpenAI codex docs → learn.chatgpt.com);
  some cited URLs may need re-navigation from the docs root.

## 9. Outstanding implementation work

1. Live installation + probes inside Qoder, Cursor, Codex (LIVE-CHECKS.md
   prompts); completes AC-12 per environment.
2. Human review of the G1 hook per HUMAN-REVIEW-G1.md.
3. MODEL-CONFIG population from probed model lists (availability/cost).
4. Optional: JSON Schema export of the 16 contracts for non-Python consumers.
5. Optional: policy tuning loop after real metrics accumulate (QA-03/04).

## 10. Recommended next development phase

Install the kit into one real project per target environment (start with the
environment that has the strongest verified native support — Qoder or Claude
Code), run the live probes, and feed measured routing outcomes back into
versioned policy proposals. Do not broaden adapter claims before probes pass.

---

Maturity declaration (kit as a whole): **specification_complete +
reference-kernel integration_tested + claude-code adapter integration_tested
(live) + qoder adapter integration_tested (live, 2026-11-17)**;
cursor/codex implementation_available; universal
specification_complete. No adapter is operationally_verified. Honesty
attestation: every test result above was actually executed; no capability,
pricing, or live integration was invented.