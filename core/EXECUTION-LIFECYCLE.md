# EXECUTION LIFECYCLE

Kit version: 1.0.0 · Spec version: 1.0.0 · Requirements: LC-01…LC-04, ISO-01…ISO-03
Task fields: [../protocols/TASK-CONTRACT.md](../protocols/TASK-CONTRACT.md)
Reference state machine: [../validation/reference_router.py](../validation/reference_router.py) (`LifecycleKernel`)

## 1. States and transitions (LC-01)

```
RECEIVED → ANALYZED → CLASSIFIED → DECOMPOSED → DEPENDENCIES_RESOLVED
        → ROUTED → APPROVED_IF_REQUIRED → EXECUTING → VALIDATING
        → COMPLETED | FAILED | ESCALATED
```

| From | To | Trigger / condition |
|------|----|---------------------|
| RECEIVED | ANALYZED | orchestrator reads task, gathers project context |
| ANALYZED | CLASSIFIED | category + attributes assigned (TASK-CLASSIFICATION.md) |
| CLASSIFIED | DECOMPOSED | atomic task, or children created with dependency edges |
| DECOMPOSED | DEPENDENCIES_RESOLVED | all `depends_on` tasks COMPLETED (or explicitly waived by human) |
| DEPENDENCIES_RESOLVED | ROUTED | routing decision recorded (all four planes, RT-06) |
| ROUTED | APPROVED_IF_REQUIRED | no approval needed ⇒ pass-through; else wait for recorded human approval (SEC-07) |
| APPROVED_IF_REQUIRED | EXECUTING | resource claims acquired; agent starts |
| EXECUTING | VALIDATING | agent submits result; G2 checks run |
| VALIDATING | COMPLETED | gates pass (+ G3 review when required); acceptance recorded |
| VALIDATING | EXECUTING | validation failed, retries remain (feedback attached) |
| EXECUTING | FAILED | retries exhausted and fallback chain exhausted |
| any non-terminal | ESCALATED | fallback reaches human_escalation, approval denied, timeout, or cancellation by human |
| any non-terminal | FAILED | cancellation with failure semantics (see §5) |

Rules:
- Transitions are append-only events in the task's `history` (timestamp,
  actor, from, to, reason). No state may be skipped except the documented
  pass-through of APPROVED_IF_REQUIRED.
- A parent task enters VALIDATING only after all children reach terminal
  states; it aggregates child results (§7).
- ESCALATED tasks are frozen: no agent may resume them without a new human
  instruction, which creates a new routing decision.

## 2. Task identity and structure (LC-02)

- `task_id`: globally unique, stable, opaque string (recommended:
  `T-<project>-<seq>` or UUID). Never reused.
- `parent_id` / `children`: decomposition tree. Cycles are invalid.
- `depends_on`: DAG edges across the tree; cycles are invalid and MUST be
  rejected at DECOMPOSED.
- `priority`: integer 0–100 (higher first) among ready tasks; ties broken by
  creation order. Priority never overrides dependencies or safety.
- Assignments: `agent_role`, `agent_instance_id`, `model_id`, `environment`
  are set at ROUTED and immutable during EXECUTING (re-route requires a new
  decision entry after failure/escalation).

## 3. Retry, timeout, failure (LC-02)

- Retry policy comes from `routing-policy.yaml fallback`: max 2 retries,
  backoff 5s then 30s, feedback from the failed attempt attached.
- Timeouts: per-task `timeout_seconds`; defaults by tier — TIER-1: 300,
  TIER-2: 1800, TIER-3: 3600, TIER-4: 3600, TIER-5: 1800. Adapters MAY map
  these to native limits (e.g. Qoder `timeoutMins`/`maxTurns`). Timeout ⇒
  cancel execution, release claims, then fallback chain.
- Failure handling: execute `fallback.on_execution_failure` in order; each
  step logged. FAILED is terminal for the attempt chain; the orchestrator
  decides whether to spawn a revised task (new id, linked via `supersedes`).
- Error reports follow [../protocols/AGENT-PROTOCOL.md](../protocols/AGENT-PROTOCOL.md)
  `error` message semantics (retryable vs permanent classification).

## 4. Parallel execution safety (LC-03, LC-04)

Two tasks may run concurrently only if BOTH hold:

1. **Dependency safety:** neither depends (transitively) on the other, and
   all their dependencies are satisfied.
2. **Resource safety:** their `resource_claims` are compatible —
   - write–write overlap on any path/state key ⇒ conflict;
   - write–read overlap ⇒ conflict by default (reader may opt into
     `allow_stale_reads: true` for research-only tasks);
   - read–read ⇒ safe.

Conflict prevention strategies (choose per adapter capability, document choice):

| Strategy | Mechanism | When |
|----------|-----------|------|
| `resource_lock` | orchestrator-held claim ledger; a task acquires its write claims before EXECUTING and releases at terminal state | any environment; default in reference kernel |
| `worktree_isolation` | each writer works in its own git worktree/branch; merge coordinated afterwards | git repos; native support e.g. Qoder `isolation: worktree` |
| `merge_coordination` | release_integration role owns merges; writers never touch shared branches directly | parallel feature work |
| `native_isolation` | application-native sandboxing/session isolation | where the adapter documents it as verified |

Never allow multiple agents uncontrolled concurrent writes to the same
resource. If no strategy is available in the environment, serialize the
conflicting tasks and record the degradation in the installation report.

## 5. Cancellation

- Human cancellation is always honored immediately.
- Cancelling a parent propagates to all non-terminal children.
- On cancellation: stop execution, release resource claims, mark task FAILED
  with `cancelled: true` (or ESCALATED if a human decision is pending), write
  audit event. Partial artifacts are left in place but flagged unaccepted;
  rollback follows SEC-08 if the task had mutating side effects.

## 6. Context and project isolation (ISO-01…ISO-03)

- Every task belongs to exactly one `project_id`. The orchestrator MUST
  refuse tasks whose context envelope mixes projects without an explicit
  cross-project grant (ISO-04, see HANDOFF-CONTRACT.md).
- Context envelope construction: project instructions + task statement +
  declared relevant artifacts ONLY (context minimality). No whole-repo dumps
  into subagent prompts when a scoped subset suffices.
- Subagent/native-agent contexts are isolated by default; intermediate
  reasoning does not leak into sibling tasks. Results return only through
  the result-submission contract.
- Cross-project access: explicit grant record (grantor, scope, reason,
  expiry), enforced at envelope build time, logged. Secrets never transfer
  (ISO-05) — redaction runs before every transfer (SEC-03).

## 7. Result aggregation and final acceptance

- Children results aggregate into the parent's `result` with per-child
  status and evidence links. Any FAILED child blocks parent COMPLETED unless
  a human explicitly accepts partial completion (recorded).
- Final acceptance (G4, QUALITY-GATES.md) checks: all acceptance criteria
  evidenced, required reviews approved, approvals recorded, metrics emitted.
- The orchestrator emits the final handoff per
  [../protocols/HANDOFF-CONTRACT.md](../protocols/HANDOFF-CONTRACT.md).