# TASK CLASSIFICATION

Kit version: 1.0.0 · Spec version: 1.0.0 · Requirements: RT-01, LC-01
Consumed by: [ROUTING-POLICY.md](ROUTING-POLICY.md), [../protocols/TASK-CONTRACT.md](../protocols/TASK-CONTRACT.md)

Classification happens in lifecycle state CLASSIFIED, after ANALYZED. The
orchestrator assigns exactly one primary category plus attribute values.
When signals conflict, choose the category with the higher safety floor
(security > specialized > complex > others) and record the ambiguity.

## Categories

### CAT-01 — simple
- **Signals:** single-file or mechanical change; no design decisions; fully
  specified; trivially verifiable (rename, format, typo, small config tweak).
- **Base tier:** TIER-1 · **Default role:** implementation_engineer
- **Decomposition:** usually atomic; do not split below one verifiable change.
- **Verification:** targeted check (build/lint/diff review).

### CAT-02 — standard_engineering
- **Signals:** well-understood feature or fix within known patterns; a few
  files; moderate test surface; no architectural change.
- **Base tier:** TIER-2 · **Default role:** implementation_engineer
- **Decomposition:** split by component or by implement→test pairs.
- **Verification:** unit/integration tests + G2 gates.

### CAT-03 — complex_engineering
- **Signals:** cross-module change, concurrency, performance, migration,
  ambiguous requirements needing design work during implementation.
- **Base tier:** TIER-3 · **Default role:** senior_engineer
- **Decomposition:** design spike first, then implementation slices with
  explicit dependency edges.
- **Verification:** G2 + independent review (G3) when failure_impact ≥ high.

### CAT-04 — architecture_strategy
- **Signals:** system shape, technology selection, long-horizon trade-offs,
  multi-project impact.
- **Base tier:** TIER-3 (floor) · **Default role:** architect
- **Decomposition:** options analysis → decision record → downstream tasks.
- **Verification:** decision record reviewed against project constraints;
  human approval for strategy commitments.

### CAT-05 — research_investigation
- **Signals:** "find out", "compare", "locate", "explain"; output is knowledge,
  not code.
- **Base tier:** TIER-2 · **Default role:** research_analyst
- **Decomposition:** parallelizable sub-questions with disjoint sources.
- **Verification:** every claim carries source + verification status (NS-07).

### CAT-06 — testing_qa
- **Signals:** test creation, coverage, validation runs, quality audits.
- **Base tier:** TIER-2 · **Default role:** test_engineer
- **Decomposition:** by test layer or acceptance criterion.
- **Verification:** actual execution output required; no claimed passes
  without evidence.

### CAT-07 — security_sensitive
- **Signals:** authentication, authorization, cryptography, secrets, payment
  paths, injection surface, permission changes, audit findings.
- **Base tier:** TIER-3 (floor) · **Default role:** security_reviewer
- **Decomposition:** analysis (read-only) separate from remediation (mutating).
- **Verification:** security review mandatory; approval gates per SEC-07 when
  remediation touches credentials, access control, or production.
- **Note:** any task of another category that carries `sensitive_operations`
  inherits CAT-07's approval requirements even if its primary category differs.

### CAT-08 — specialized_domain
- **Signals:** domain expertise required (finance, ML ops, regulatory,
  hardware, protocol internals); generic engineering quality is insufficient.
- **Base tier:** TIER-4 (floor) · **Default role:** senior_engineer unless
  `required_role` names a specialist; `required_specialties` MUST be set.
- **Decomposition:** domain analysis → implementation → domain validation.
- **Verification:** specialist review; human approval for domain-consequential
  operations (e.g. financial transactions).

## Attributes assigned at classification

| Attribute | Values | Routing effect |
|-----------|--------|----------------|
| `complexity` | low / medium / high | +1 tier if high |
| `reasoning` | basic / standard / advanced | +1 tier if advanced |
| `failure_impact` | low / medium / high | +1 tier if high; review if high |
| `quality_bar` | standard / high | high ⇒ recommend independent review |
| `required_specialties` | list | capability filter |
| `min_context_tokens` | integer | capability filter |
| `required_tools` | list | tool-plane allowlist check |
| `sensitive_operations` | list (see routing-policy.yaml `approval`) | approval gate |
| `is_review` | bool | routes to TIER-5 with independence constraints |

## Classification rules

1. Classify from evidence (task text, touched paths, project constraints),
   not from the requester's preferred model.
2. Record category + attributes + one-line rationale in the task record.
3. Re-classify when execution reveals misclassification (e.g. a "simple" fix
   uncovering concurrency bugs); re-route through the normal algorithm and
   append to `routing_history`. Never silently continue at the old tier.
4. Decomposition produces children that are themselves classified; a parent
   completes only when all children reach terminal states and aggregation
   passes (see [EXECUTION-LIFECYCLE.md](EXECUTION-LIFECYCLE.md)).