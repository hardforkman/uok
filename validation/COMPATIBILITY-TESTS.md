# COMPATIBILITY TESTS

Kit version: 1.0.0 · Spec version: 1.0.0 · Requirements: VAL-01, VAL-02, ADP-03

Two test layers:

1. **Reference-kernel behavior tests (§2)** — executable, deterministic, run
   anywhere with Python + PyYAML. They prove the specification's routing,
   lifecycle, isolation, and approval behavior is implementable and
   consistent. They do NOT prove anything about a live vendor environment.
2. **Live compatibility probes (§3)** — manual/safe procedures the receiving
   agent executes in its actual environment during installation. Only these
   can raise an adapter above `integration_tested`.

## 1. Scenario index

| ID | Mandatory behavior (directive §14) | Kernel test | Live probe |
|----|----------------------------------|-------------|------------|
| TS-01 | Simple task routed to an economical model | ✅ | L1 |
| TS-02 | Complex task escalated to a stronger model | ✅ | L1 |
| TS-03 | Task requiring a specialized agent | ✅ | L2 |
| TS-04 | Independent tasks executed in parallel | ✅ | L3 |
| TS-05 | Dependent tasks executed sequentially | ✅ | L3 |
| TS-06 | A model becoming unavailable | ✅ | L4 |
| TS-07 | A failed task triggering fallback | ✅ | L4 |
| TS-08 | A reviewer rejecting an implementation | ✅ | L5 |
| TS-09 | A sensitive task requiring approval | ✅ | L6 |
| TS-10 | A project-isolation violation prevented | ✅ | L6 |
| TS-11 | Conflicting parallel file modifications prevented | ✅ | L3 |
| TS-12 | Environment lacking native multi-agent support | ✅ | L2 |

## 2. Kernel behavior tests (executed)

Run: `python3 validation/behavior_tests.py`
Fixtures: [fixtures/tasks.yaml](fixtures/tasks.yaml) · Kernel:
[reference_router.py](reference_router.py) · Models: `test_only` mock entries
from [../core/MODEL-REGISTRY.yaml](../core/MODEL-REGISTRY.yaml) (no network).

Assertions per scenario (actual behavior, not doc presence):

- **TS-01** CAT-01/low ⇒ TIER-1, highest-reliability economical fixture model.
- **TS-02** CAT-02 + high complexity/advanced reasoning/high impact ⇒ tier
  modifiers applied and capped at TIER-3; advanced fixture model selected.
- **TS-03** CAT-08 + `required_specialties: [finance]` ⇒ TIER-4; only the
  specialist fixture model passes the capability filter; role honored.
- **TS-04** two tasks, disjoint write claims, no dependencies ⇒
  `can_parallel == true`; both claim sets acquire cleanly.
- **TS-05** B `depends_on` A ⇒ parallel blocked; B cannot reach
  DEPENDENCIES_RESOLVED until A is COMPLETED; then it can.
- **TS-06** primary TIER-1 model marked `unavailable` ⇒ same-tier backup
  selected; unavailable candidate recorded in `alternatives`.
- **TS-07** all TIER-1 models down ⇒ tier escalation to TIER-2 with
  `tier_escalated` flag; retry chain = 2× retry_with_feedback then
  same_tier_alternative; ALL models down ⇒ `human_escalation`, never a
  silent weaker substitution.
- **TS-08** review task ⇒ TIER-5, implementer's model excluded; reviewer
  `reject` re-enters EXECUTING with feedback; exhausted retries ⇒
  escalate_tier (never silent accept).
- **TS-09** `sensitive_operations: [production_deploy]` ⇒ requires_approval;
  EXECUTING blocked without an approval record; allowed with a task-scoped
  record covering exactly the declared operations.
- **TS-10** envelopes rejected for: wrong project, ungranted cross-project
  artifact, secret-like content; accepted with a valid scoped grant.
  Regression: envelope-embedded grants are never trusted (receiver-held
  registry only); expired grants and whole-project/wildcard scopes rejected.
- **TS-11** identical write claims ⇒ `can_parallel == false`; second claim
  acquisition raises ClaimConflict.
- **TS-12** universal profile (no verified native capabilities) ⇒ fallback
  environment selected with `degraded_multi_agent`, `degraded_parallelism`,
  `degraded_model_routing` flags; concurrency=1 kernel blocks a second
  simultaneous EXECUTING task. Regression: doc-only-verified adapter
  (codex profile) adds `doc_only_verification`; live-verified adapter
  (claude-code profile) does not.

Audit regression checks (added 2026-11-17 after independent review):

- **TS-02/03** CAT-08 with all-high modifiers stays TIER-4 (no ladder
  overflow); `requested_tier: TIER-5` without review clamps to TIER-4.
- **TS-05** dependency cycles rejected at DECOMPOSED; incomplete dependency
  blocked without an explicit human waiver, allowed with one; FAILED child
  blocks parent COMPLETED unless a human `partial_acceptance` waiver covers it.
- **TS-07** fallback chain progresses through consumed steps
  (same_tier_alternative → escalate_tier → human_escalation), never loops.
- **TS-08** reviewer instance differs from implementer instance;
  same-family-only reviewer pool flagged `degraded_independence`; G3 verdict
  with evidence required at COMPLETED for high-impact tasks; explicit human
  review waiver substitutes.
- **TS-09** CAT-07 with a write claim requires approval (read-only does not);
  expired approvals and empty-operations approvals are invalid.

Authoring-time result (2026-11-17, post-audit): **51/51 checks passed**
(re-run recorded in the installation report / final handoff).

## 3. Live compatibility probes (receiving agent executes)

Safety rules: probes run in a scratch directory or read-only against the real
repo; NEVER touch production, credentials, or shared state; anything mutating
needs the SEC-07 gates. Record each probe outcome with evidence and tag
`verified_live` only when actually executed. Note the runtime mode (TUI /
headless / SDK) per probe.

- **L1 — Routing dry-run (TS-01/02):** create two ledger tasks (one trivial,
  one complex) in `.orchestrator/tasks/`; run the router
  (`reference_router.route` with your probed MODEL-CONFIG bindings, or your
  native equivalent); verify tier/model differ appropriately and decision
  records contain all four planes. Then execute the trivial one end-to-end
  through your environment's cheapest configured model.
- **L2 — Agent registration & specialization (TS-03/12):** install one
  read-only reviewer agent and one worker agent per your adapter README;
  verify the runtime actually lists/dispatches them; verify the reviewer's
  tool allowlist denies writes (attempt a harmless write in scratch — must
  be denied). If native agents are unsupported, verify the role-session
  fallback works and record the degradation.
- **L3 — Parallelism & claims (TS-04/05/11):** dispatch two read-only agents
  concurrently (safe); then attempt two writers with overlapping claims in
  scratch — the ledger/hooks must block the second; verify a dependent task
  waits for its dependency.
- **L4 — Availability & fallback (TS-06/07):** mark one configured model
  unavailable in MODEL-CONFIG (or use a genuinely absent model id); re-route
  a pending task; verify same-tier alternative or recorded escalation.
  Simulate an execution failure (e.g. failing test) and verify the retry →
  fallback chain events appear in the audit log.
- **L5 — Independent review (TS-08):** run implement → review on a scratch
  change; verify the reviewer instance/model differs from the implementer;
  force a rejection (seed a defect) and verify rework, not silent acceptance.
- **L6 — Approval & isolation gates (TS-09/10):** create a task with
  `sensitive_operations: [production_deploy]` but NO deploy action — verify
  the orchestrator blocks at APPROVED_IF_REQUIRED and asks the human; deny
  it and verify ESCALATED. Build an envelope referencing another project's
  file without a grant — verify refusal.

## 4. Reporting

Probe results go into the installation report
([../handoff/INSTALLATION-REPORT-TEMPLATE.md](../handoff/INSTALLATION-REPORT-TEMPLATE.md)):
per-probe status (`verified_live` / `not_executed` / `failed`), evidence,
runtime mode, and the resulting adapter maturity level. A failed probe is a
finding, not a reason to hide the probe.