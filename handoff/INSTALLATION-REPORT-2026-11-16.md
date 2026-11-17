# INSTALLATION REPORT — Universal Orchestrator Kit (authoring-time handoff)

Kit version: 1.0.0 · Spec version: 1.0.0 · Date: 2026-11-16
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
├── START-HERE.md
├── NORTH-STAR.md
├── UNIVERSAL-ORCHESTRATION-SPEC.md
├── AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md
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
│   ├── claude-code/  README.md + PROFILE.yaml
│   ├── qoder/        README.md + PROFILE.yaml
│   ├── cursor/       README.md + PROFILE.yaml
│   ├── codex/        README.md + PROFILE.yaml
│   └── universal/    README.md + PROFILE.yaml
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
    └── INSTALLATION-REPORT-2026-11-16.md  (this report)
```

36 kit files, ~330 KB, plain Markdown/YAML/Python. No credentials anywhere
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

15 versioned machine-readable schemas (schema_version 1), embedded in the
protocol documents and parser-checked by self_test CHK-04: task,
resource_claim, routing_decision, lifecycle_event, gate_result,
approval_record, result_payload, agent_register, status_update, error_report,
escalation, validation_verdict, context_envelope, cross_project_grant,
final_handoff. Plus adapter_profile (5 instances). Evolution rules: strict
mode default, additive minor versions, breaking changes ⇒ new schema_version.

## 5. Adapter coverage and maturity

| Adapter | Maturity | Research basis (2026-11-16) |
|---------|----------|------------------------------|
| claude-code | specification_complete | sub-agents, hooks, memory pages verified_doc; permissions/headless/MCP partially unverified |
| qoder | specification_complete | subagent + memory pages verified_doc in detail (frontmatter, tiers, worktree isolation, parallel dispatch); permissions syntax/hooks event list partially unverified |
| cursor | specification_complete | rules + hooks + CLI pages verified_doc; custom subagents/per-agent model/parallelism not_found ⇒ documented fallbacks |
| codex | specification_complete | CLI, subagents, config reference, non-interactive pages verified_doc (incl. `--full-auto` removal, exec read-only default); subagent definition format unverified ⇒ profile fallback |
| universal | specification_complete | fallback design (role sessions, claim ledger, headless/API/manual ladder); baseline matrix all `unknown` pending probes |

No adapter is claimed operational. Live verification is the receiving
agent's job (COMPATIBILITY-TESTS §3).

## 6. Validation commands executed (actual)

| Command | Result |
|---------|--------|
| `python3 validation/self_test.py` | 16/16 checks passed (CHK-01…16) |
| `python3 validation/behavior_tests.py` | 28/28 assertions passed (TS-01…12) |
| PyYAML parse of all 12 YAML files | all pass |

Environment: macOS (darwin 23.2.0), Python 3.12.2, PyYAML 6.0.2. No network
calls in tests. Two defects were found and fixed during development
(approval flag lookup in the kernel; pairwise claim comparison before
acquisition) — final runs above are post-fix.

## 7. Test results summary

All 12 mandatory scenarios verified as actual kernel behavior: economical
routing, complexity escalation, specialization filter, safe parallelism,
dependency sequencing, unavailable-model fallback, retry/escalation chain,
independent review + rejection rework, approval blocking, isolation rejection
(project mismatch / missing grant / secret content), write-conflict
prevention, degraded-environment fallback with sequential enforcement.

## 8. Known limitations

- AC-12 independent fresh-agent dry run: not performed (`unverified`).
- Live adapter probes (L1–L6): not executed by the author; adapters remain
  specification_complete.
- Adapter research gaps are tagged `unverified`/`unknown`/`not_found` in
  each PROFILE.yaml (e.g. Cursor custom subagents, Codex subagent definition
  format, full hook event lists, Claude Code permission rule syntax).
- Registry contains no verified real-model facts; receiving agents must
  probe and fill MODEL-CONFIG before real routing.
- Reference kernel is a conformance tool, not a production scheduler;
  production execution uses native runtimes via adapters.
- Vendor docs moved during research (OpenAI codex docs → learn.chatgpt.com);
  some cited URLs may need re-navigation from the docs root.

## 9. Outstanding implementation work

1. Fresh-agent dry run of AUTONOMOUS-IMPLEMENTATION-DIRECTIVE in a second
   environment (validates AC-12).
2. Per-environment installation + L1–L6 live probes by receiving agents.
3. MODEL-CONFIG population from probed model lists (availability/cost).
4. Optional: JSON Schema export of the 15 contracts for non-Python consumers.
5. Optional: policy tuning loop after real metrics accumulate (QA-03/04).

## 10. Recommended next development phase

Install the kit into one real project per target environment (start with the
environment that has the strongest verified native support — Qoder or Claude
Code), run the live probes, and feed measured routing outcomes back into
versioned policy proposals. Do not broaden adapter claims before probes pass.

---

Maturity declaration (kit as a whole): **specification_complete +
reference-kernel integration_tested** (kernel behavior executed and passing;
no live vendor environment verified). Honesty attestation: every test result
above was actually executed in this session; no capability, pricing, or live
integration was invented.