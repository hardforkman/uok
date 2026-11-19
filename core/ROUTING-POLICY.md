# ROUTING POLICY

Kit version: 1.0.0 · Spec version: 1.0.0 · Requirements: RT-01…RT-07
Machine-readable normative form: [routing-policy.yaml](routing-policy.yaml)
(reference kernel: [../validation/reference_router.py](../validation/reference_router.py))

This document defines how the orchestrator chooses a **tier**, **model**,
**agent role**, **tools**, and **execution environment** for each individual
task. The YAML file is the normative parameter set; this document is the
normative algorithm. If they conflict, that is a defect — report it, do not
silently pick one.

## 1. Inputs (RT-01)

Every routing decision MUST evaluate the following task attributes (fields
defined in [../protocols/TASK-CONTRACT.md](../protocols/TASK-CONTRACT.md)):

| Input | Field | Effect |
|-------|-------|--------|
| Task category | `category` (CAT-01…08) | base tier + default role |
| Technical complexity | `complexity` low/medium/high | +1 tier if high |
| Reasoning requirements | `reasoning` basic/standard/advanced | +1 tier if advanced |
| Required expertise | `required_specialties` | capability filter on models/agents |
| Context requirements | `min_context_tokens` | capability filter on models |
| Expected output quality | `quality_bar` standard/high | high ⇒ independent review recommended |
| Reliability | registry `reliability` | ranking key |
| Model availability | registry `availability` | hard filter (`unavailable` excluded) |
| Execution latency | registry `latency_class`, project `latency_preference` | ranking key |
| Token/API cost | registry `cost`, project `budget` | ranking key + budget ceiling |
| Tool requirements | `required_tools` | tool-plane filter; agent allowlist check |
| Security sensitivity | `sensitive_operations`, category CAT-07 | tier floor + approval gate |
| Failure impact | `failure_impact` low/medium/high | +1 tier if high; review requirement |
| Verification requirements | `is_review`, `require_independent_review` | TIER-5 routing + independence |

Routing MUST NOT key exclusively on project identity or model name (RT-02).
Project configuration supplies budgets, preferences, and permissions — never a
fixed model assignment for all tasks.

## 2. Tiers (RT-03)

| Tier | Name | Use |
|------|------|-----|
| TIER-1 | fast_economy | simple, low-risk tasks; optimize cost/latency |
| TIER-2 | standard | routine engineering, research, testing |
| TIER-3 | advanced_reasoning | complex engineering, architecture, security analysis |
| TIER-4 | specialized | declared domain expertise required |
| TIER-5 | independent_review | validation by a non-implementing actor |

Tiers are abstract. Concrete models bind to tiers through
`tier_affinity` in [MODEL-REGISTRY.yaml](MODEL-REGISTRY.yaml). No tier is
hardcoded to a vendor or model family (RT-04, NS-01).

## 3. Algorithm (deterministic)

```
route(task, registry, agents, policy, project):
  1. Validate task.category ∈ CAT-01…CAT-08.
  2. base ← policy.category_base_tier[task.category]
  3. delta ← modifiers.complexity[task.complexity]
           + modifiers.reasoning[task.reasoning]
           + modifiers.failure_impact[task.failure_impact]
           + graph_impact.delta when task.graph_signal is fresh (status ok) and a
             threshold is met (god_node_degree / community_spread / impact_files;
             CG-06). Stale/unavailable signal adds 0 and is flagged; an absent
             signal adds 0 silently. Same modifier_tier_cap applies.
  4. tier ← base + delta, capped at policy.modifier_tier_cap (TIER-3).
     Exception: CAT-08 keeps TIER-4; task.is_review ⇒ TIER-5 directly.
  5. tier ← max(tier, policy.tier_floors[task.category])   # hard floors
  6. If task.requested_tier is set and higher than computed tier, honor it
     (explicit human/agent escalation); never lower below floors.
  7. candidates ← registry models where:
       tier ∈ model.tier_affinity
       model.availability ∉ policy.selection.exclude_availability
       capabilities satisfy task.min_context_tokens / required_specialties /
       required tool_use  (unknown capabilities allowed but flagged)
       model cost within project budget ceiling (when both known)
  8. Rank candidates per policy.selection.rank_by:
       reliability desc (unknown = 0.5) → known input cost asc (unknown last)
       → latency fast<standard<slow (unknown last) → id asc.
  9. If candidates empty: walk policy.fallback.escalation_path upward from
     tier (never into TIER-5). If still empty ⇒ decision = human_escalation,
     task → ESCALATED. Never silently substitute a weaker tier (RT-07).
 10. Agent role ← task.required_role or policy.category_default_role[category].
     Verify role capabilities cover task.required_capabilities and role
     permissions cover task.required_tools (tool plane). If the role cannot
     legally use a required tool ⇒ re-route to a permitted role or escalate.
 11. Review independence (QA-01): if task.is_review, exclude the implementer's
     model_id and agent_instance_id; prefer a different model family.
 12. Approval: if task.sensitive_operations ∩ policy.approval.sensitive_operations
     ≠ ∅ or category = CAT-07 with mutating intent ⇒ requires_approval = true.
     Mutating intent is defined as: the task declares at least one
     `resource_claims` entry with `mode: write`. A read-only CAT-07 task
     (audit, assessment) does not require approval by this clause alone.
 13. Execution environment ← adapter capability matrix (native subagent,
     worktree-isolated agent, headless CLI, external runtime). Record choice.
 14. Emit decision record (RT-06): inputs, tier, model, role, tools, environment,
     alternatives considered, flags (unverified/unknown), rationale, timestamp.
```

## 4. Cost, latency, and budget behavior

- Cost metadata is `unknown` unless configured or measured (RT-05). Unknown
  costs sort last within equal reliability — they are never invented.
- Projects MAY set `budget.max_cost_per_task` and `budget.prefer_economy`.
  `prefer_economy` may lower the *ranking weight* of cost but MUST NOT lower
  the computed tier below its floor.
- Latency preference works the same way: a ranking hint, never a safety override.

## 5. Fallback and escalation (RT-07)

Defined in `policy.fallback`:

- **Model unavailable before start** → next same-tier candidate → escalate one
  tier → human escalation.
- **Execution failure** → retry with feedback (max 2, backoff 5s/30s) →
  same-tier alternative → escalate tier → human escalation.
- **Validation failure** → retry with reviewer feedback → escalate tier →
  human escalation. A failing reviewer verdict is never overridden silently.
- Every fallback step is appended to the task's `routing_history` and audit log.

## 6. Routing self-evaluation (QA-03)

After acceptance, the orchestrator records per-decision outcomes: first-pass
success, retries, validation failures, elapsed time, tokens, estimated cost.
Aggregated per (category, tier, model, role), these feed policy proposals.
Proposals are versioned diffs to `routing-policy.yaml` + this document, require
human approval, and may never modify `approval.*` or floors in a weakening
direction (QA-04, SEC-10).

## 7. Worked examples (illustrative, not requirements)

- Rename a variable across 3 files: CAT-01, complexity low ⇒ TIER-1,
  implementation_engineer, cheapest available fast model.
- Design a cross-service migration: CAT-04, complexity high ⇒ base TIER-3 +1
  capped at TIER-3, architect role, independent review subtask at TIER-5.
- Audit authentication for injection flaws: CAT-07 ⇒ floor TIER-3,
  security_reviewer, approval gate if remediation touches credentials.
- Price a financial reconciliation job: CAT-08 ⇒ TIER-4, required_role with
  `finance` specialty; `financial_transaction` operation ⇒ human approval.

## 8. Consistency rules (checked by self_test.py)

- Every CAT-id in `category_base_tier` and `category_default_role` exists in
  [TASK-CLASSIFICATION.md](TASK-CLASSIFICATION.md).
- Every tier referenced anywhere exists in `tiers`.
- Every default role exists in [AGENT-CAPABILITIES.yaml](AGENT-CAPABILITIES.yaml).
- `escalation_path` never contains TIER-5; floors never exceed the cap except
  for CAT-08/TIER-4 and review/TIER-5.

## Graph impact modifier (CG-06, release 1.2.0)

`graph_impact` is a formal additive complexity modifier (policy_version 1.1.0).
When a task carries a fresh `graph_signal` (status `ok`) and any threshold is met,
`graph_impact.delta` (+1) joins the modifier sum in step 3 — under the same
`modifier_tier_cap` (TIER-3) as complexity/reasoning/failure_impact. It adds no new
hard floor and never reaches TIER-4/TIER-5 (CAT-08 and is_review are unaffected).

Thresholds (`graph_impact.thresholds` in routing-policy.yaml):
- `god_node_degree` (25): a touched node whose degree >= this is a god node.
- `community_spread` (3): distinct communities among touched nodes + 1-hop impact.
- `impact_files` (10): distinct source files in the 1-hop impact set.

Metrics are measured by `core/graph_signal.py` (deterministic, stdlib, offline) from
`graphify-out/graph.json` and the task's write claims. Fail-open: `stale` or
`unavailable` signal adds 0 and is flagged; an absent signal adds 0 silently; claims
matching no indexed node yield `no_touched_nodes` (0). The decision record cites the
signal metrics and provenance (CG-07). Threshold changes are versioned policy changes
(policy_version) per QA-04 — never a silent core rewrite.
