# TASK CONTRACT

Kit version: 1.0.0 · Spec version: 1.0.0 · Schema version: 1
Requirements: PROT-01…PROT-03, LC-01…LC-04, RT-06, ISO-01…ISO-06

The task object is the single source of truth for a unit of work. It is
language- and application-neutral: YAML or JSON serialization, stored in the
task ledger (`.orchestrator/tasks/` by default) or the environment's native
task system when the adapter maps fields losslessly.

## 1. Machine-readable schema (normative)

Field schema format: `type`, `required`, `allowed` (enum), `rules` (prose
constraints checked by implementations and by validation).

```yaml
schema: task
schema_version: 1
fields:
  task_id:            { type: string, required: true,  rules: "globally unique, stable, never reused" }
  project_id:         { type: string, required: true,  rules: "exactly one project per task (ISO-01/02)" }
  title:              { type: string, required: true }
  statement:          { type: string, required: true,  rules: "the work to perform; instructions arrive only here and via project instruction files (SEC-05)" }
  category:           { type: string, required: true,  allowed: [CAT-01, CAT-02, CAT-03, CAT-04, CAT-05, CAT-06, CAT-07, CAT-08] }
  status:             { type: string, required: true,  allowed: [RECEIVED, ANALYZED, CLASSIFIED, DECOMPOSED, DEPENDENCIES_RESOLVED, ROUTED, APPROVED_IF_REQUIRED, EXECUTING, VALIDATING, COMPLETED, FAILED, ESCALATED] }
  complexity:         { type: string, required: false, allowed: [low, medium, high], default: medium }
  reasoning:          { type: string, required: false, allowed: [basic, standard, advanced], default: standard }
  failure_impact:     { type: string, required: false, allowed: [low, medium, high], default: medium }
  quality_bar:        { type: string, required: false, allowed: [standard, high], default: standard }
  required_specialties: { type: array, items: string, required: false, default: [] }
  required_capabilities: { type: array, items: string, required: false, default: [], rules: "must be covered by the assigned role (AGENT-CAPABILITIES.yaml)" }
  min_context_tokens: { type: integer, required: false, rules: ">= 0; capability filter on models" }
  required_tools:     { type: array, items: string, required: false, default: [], rules: "tool plane; must be within role+project allowlists (SEC-04)" }
  required_role:      { type: string, required: false, rules: "role id from AGENT-CAPABILITIES.yaml; overrides category default" }
  requested_tier:     { type: string, required: false, allowed: [TIER-1, TIER-2, TIER-3, TIER-4, TIER-5], rules: "may raise, never lower below floors" }
  is_review:          { type: boolean, required: false, default: false }
  reviews_task_id:    { type: string, required: false, rules: "required when is_review=true; independence enforced (QA-01)" }
  sensitive_operations: { type: array, items: string, required: false, default: [], allowed_items: [production_deploy, financial_transaction, irreversible_data_change, destructive_infra_change, credential_access_change, unauthorized_external_publication], rules: "non-empty ⇒ approval gate (SEC-07)" }
  parent_id:          { type: string, required: false }
  children:           { type: array, items: string, required: false, default: [], rules: "no cycles" }
  depends_on:         { type: array, items: string, required: false, default: [], rules: "DAG; no cycles; cross-project deps require grant (ISO-04)" }
  supersedes:         { type: string, required: false, rules: "task_id this task replaces after failure" }
  priority:           { type: integer, required: false, default: 50, rules: "0..100; never overrides dependencies or safety" }
  timeout_seconds:    { type: integer, required: false, rules: "> 0; tier defaults in EXECUTION-LIFECYCLE.md §3" }
  resource_claims:    { type: array, required: false, default: [], items_schema: resource_claim, rules: "write claims must be disjoint across concurrent tasks (LC-03/04)" }
  requires_approval:  { type: boolean, required: false, default: false }
  require_independent_review: { type: boolean, required: false, default: false, rules: "forces G3 review verdict at COMPLETED (QA-01); also implied by failure_impact=high or CAT-07" }
  waivers:            { type: array, required: false, default: [], items_schema: waiver, rules: "explicit human waivers only; never implicit (EXECUTION-LIFECYCLE.md §8)" }
  approvals:          { type: array, required: false, default: [], items_schema: approval_record }
  routing:            { type: object, required: false, schema_ref: routing_decision, rules: "required from ROUTED onward" }
  routing_history:    { type: array, required: false, default: [], items_schema: routing_decision }
  history:            { type: array, required: false, default: [], items_schema: lifecycle_event, rules: "append-only transition log" }
  gate_results:       { type: array, required: false, default: [], items_schema: gate_result }
  result:             { type: object, required: false, schema_ref: result_payload, rules: "required for COMPLETED" }
  cancelled:          { type: boolean, required: false, default: false }
  created_at:         { type: string, required: true, rules: "ISO 8601 timestamp" }
```

```yaml
schema: resource_claim
schema_version: 1
fields:
  path:              { type: string, required: true, rules: "file path, glob, or state key (e.g. db:migrations)" }
  mode:              { type: string, required: true, allowed: [read, write] }
  allow_stale_reads: { type: boolean, required: false, default: false, rules: "readers only; opts into write-read concurrency" }
```

```yaml
schema: routing_decision
schema_version: 1
fields:
  decided_at:        { type: string, required: true }
  tier:              { type: string, required: true, allowed: [TIER-1, TIER-2, TIER-3, TIER-4, TIER-5] }
  model_id:          { type: string, required: true, rules: "registry id; may be 'none' only when decision=human_escalation" }
  agent_role:        { type: string, required: true }
  agent_instance_id: { type: string, required: true }
  tools:             { type: array, items: string, required: true }
  environment:       { type: string, required: true, rules: "execution-environment plane: native_subagent | worktree_agent | headless_cli | external_runtime | manual" }
  alternatives:      { type: array, required: true, rules: "candidates considered, with rejection reasons" }
  flags:             { type: array, items: string, required: false, default: [], rules: "e.g. unverified_model, unknown_capability, tier_escalated, degraded_independence" }
  rationale:         { type: string, required: true }
  decision:          { type: string, required: false, allowed: [route, human_escalation], default: route }
  requires_approval: { type: boolean, required: true, rules: "computed at routing (SEC-07); true ⇒ EXECUTING blocked until a valid, unexpired approval_record covers every sensitive operation" }
```

```yaml
schema: lifecycle_event
schema_version: 1
fields:
  at:      { type: string, required: true }
  actor:   { type: string, required: true }
  from:    { type: string, required: true }
  to:      { type: string, required: true }
  reason:  { type: string, required: true }
```

```yaml
schema: gate_result
schema_version: 1
fields:
  gate:     { type: string, required: true, allowed: [G1, G2, G3, G4] }
  passed:   { type: boolean, required: true }
  at:       { type: string, required: true }
  evidence: { type: array, items: string, required: true, rules: "references to actual artifacts/outputs; empty evidence ⇒ passed must be false" }
  findings: { type: array, required: false, default: [] }
```

```yaml
schema: approval_record
schema_version: 1
fields:
  approval_id: { type: string, required: true }
  task_id:     { type: string, required: true }
  operations:  { type: array, items: string, required: true, rules: "exact sensitive_operations approved; no standing authorization" }
  approver:    { type: string, required: true, rules: "human identity" }
  granted_at:  { type: string, required: true }
  expires_at:  { type: string, required: false }
  scope_note:  { type: string, required: false }
```

```yaml
schema: waiver
schema_version: 1
fields:
  scope:      { type: string, required: true, allowed: [dependency, review, partial_acceptance], rules: "what the waiver substitutes; never isolation/redaction/sensitive-ops" }
  approver:   { type: string, required: true, rules: "human identity; agent-issued waivers are invalid" }
  covers:     { type: array, items: string, required: false, default: [], rules: "task_ids covered (dependency/partial_acceptance); empty for review scope" }
  granted_at: { type: string, required: true }
  expires_at: { type: string, required: false, rules: "past or unparseable expiry invalidates the waiver" }
  reason:     { type: string, required: false }
```

```yaml
schema: result_payload
schema_version: 1
fields:
  summary:      { type: string, required: true }
  status:       { type: string, required: true, allowed: [success, partial, failure] }
  artifacts:    { type: array, items: string, required: true, rules: "paths/links to diffs, outputs, reports" }
  evidence:     { type: array, items: string, required: true, rules: "actual command outputs or test results; no evidence-free success claims" }
  metrics:      { type: object, required: false, rules: "tokens, elapsed_seconds, estimated_cost; unknown values recorded as 'unknown'" }
  child_results: { type: array, required: false, rules: "aggregated child task ids + statuses (parents)" }
  followups:    { type: array, required: false, default: [] }
```

## 2. Validation rules (implementation requirements)

1. Required fields present; enums respected; unknown fields rejected at
   schema_version 1 (strict mode) — see §4 evolution.
2. `is_review=true` ⇒ `reviews_task_id` set, category may be any, tier forced
   TIER-5, independence exclusions applied.
3. `sensitive_operations` non-empty ⇒ `requires_approval=true` and execution
   blocked until a matching `approval_record` exists (SEC-07).
4. Dependency graph (parent/children + depends_on) must be acyclic.
5. `resource_claims` write paths must not overlap with any concurrently
   EXECUTING task's claims (mode rules in EXECUTION-LIFECYCLE.md §4).
6. State transitions must follow the lifecycle table; every transition
   appends a `lifecycle_event`.
7. `result` required for COMPLETED; `evidence` must be non-empty when
   `status=success`.

## 3. Error semantics

Task-level failures use the `error_report` message
([AGENT-PROTOCOL.md](AGENT-PROTOCOL.md)): `retryable` errors enter the retry
chain; `permanent` errors skip retries and go to fallback/escalation.
Timeout and cancellation are lifecycle events, not agent errors.

## 4. Compatibility and schema evolution

- `schema_version: 1` is the baseline. Consumers MUST check it.
- Additive evolution (new optional fields) ⇒ minor kit version; consumers
  ignore unknown optional fields ONLY when the producer declares
  `compat: additive` in the ledger header. Default is strict.
- Breaking changes (renames, removals, semantic changes) ⇒ new schema_version
  with a migration note in the kit changelog. Old ledgers remain readable via
  their declared version.
- No field may carry secrets (SEC-02/03); redaction is applied before
  serialization into any handoff.