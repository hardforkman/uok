#!/usr/bin/env python3
"""Universal Orchestrator Kit — reference kernel (specification conformance tool).

Implements the normative behavior of:
  core/routing-policy.yaml + core/ROUTING-POLICY.md   -> route()
  core/EXECUTION-LIFECYCLE.md                         -> LifecycleKernel, ClaimLedger
  protocols/HANDOFF-CONTRACT.md                       -> validate_envelope()
  adapters/ADAPTER-IMPLEMENTATION-SPEC.md §4          -> select_execution_environment()

This is NOT a production scheduler. It proves the specification is executable
and internally consistent; production execution uses the environment's native
runtime via the adapters. Requires: Python >= 3.10, PyYAML. No network access.
"""
from __future__ import annotations

import fnmatch
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

KIT_ROOT = Path(__file__).resolve().parent.parent

TIER_ORDER = ["TIER-1", "TIER-2", "TIER-3", "TIER-4", "TIER-5"]
CATEGORIES = [f"CAT-0{i}" for i in range(1, 9)]
STATES = [
    "RECEIVED", "ANALYZED", "CLASSIFIED", "DECOMPOSED", "DEPENDENCIES_RESOLVED",
    "ROUTED", "APPROVED_IF_REQUIRED", "EXECUTING", "VALIDATING",
    "COMPLETED", "FAILED", "ESCALATED",
]
TERMINAL = {"COMPLETED", "FAILED", "ESCALATED"}
TRANSITIONS = {
    "RECEIVED": {"ANALYZED"},
    "ANALYZED": {"CLASSIFIED"},
    "CLASSIFIED": {"DECOMPOSED"},
    "DECOMPOSED": {"DEPENDENCIES_RESOLVED"},
    "DEPENDENCIES_RESOLVED": {"ROUTED"},
    "ROUTED": {"APPROVED_IF_REQUIRED"},
    "APPROVED_IF_REQUIRED": {"EXECUTING"},
    "EXECUTING": {"VALIDATING", "FAILED", "ESCALATED"},
    "VALIDATING": {"COMPLETED", "EXECUTING", "FAILED", "ESCALATED"},
}
for _s in STATES:
    if _s not in TERMINAL:
        TRANSITIONS.setdefault(_s, set()).update({"ESCALATED", "FAILED"})

LATENCY_RANK = {"fast": 0, "standard": 1, "slow": 2}
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_\-]{16,}",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?i)(api[_-]?key|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}",
]


class RoutingError(Exception):
    pass


class TransitionError(Exception):
    pass


class ClaimConflict(Exception):
    pass


class EnvelopeError(Exception):
    pass


def load_yaml(rel: str):
    with open(KIT_ROOT / rel, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_policy():
    return load_yaml("core/routing-policy.yaml")


def load_registry(test_mode: bool = False):
    reg = load_yaml("core/MODEL-REGISTRY.yaml")
    models = reg["models"]
    if test_mode:
        return [m for m in models if m.get("test_only")]
    return [m for m in models if not m.get("test_only")]


def load_roles():
    return {r["id"]: r for r in load_yaml("core/AGENT-CAPABILITIES.yaml")["roles"]}


def _known(value):
    return value is not None and value != "unknown"


def _tier_idx(tier: str) -> int:
    return TIER_ORDER.index(tier)


def compute_tier(task: dict, policy: dict) -> tuple[str, list[str]]:
    """Steps 2-6 of ROUTING-POLICY.md §3. Returns (tier, flags)."""
    flags: list[str] = []
    category = task["category"]
    if category not in CATEGORIES:
        raise RoutingError(f"unknown category {category}")
    if task.get("is_review"):
        return policy["review"]["tier"], flags
    base = policy["category_base_tier"][category]
    mods = policy["modifiers"]
    delta = (
        mods["complexity"][task.get("complexity", "medium")]
        + mods["reasoning"][task.get("reasoning", "standard")]
        + mods["failure_impact"][task.get("failure_impact", "medium")]
    )
    idx = _tier_idx(base) + delta
    if category == "CAT-08":
        idx = _tier_idx("TIER-4")          # CAT-08 keeps TIER-4 regardless of deltas
    else:
        idx = min(idx, _tier_idx(policy["modifier_tier_cap"]))
    floor = policy["tier_floors"].get(category)
    if floor:
        idx = max(idx, _tier_idx(floor))
    requested = task.get("requested_tier")
    if requested and _tier_idx(requested) > idx:
        idx = _tier_idx(requested)
        flags.append("requested_tier_honored")
    idx = min(idx, _tier_idx("TIER-4"))    # TIER-5 is reachable only via is_review
    return TIER_ORDER[idx], flags


def _capability_check(model: dict, task: dict) -> tuple[bool, str, list[str]]:
    """Returns (eligible, rejection_reason, flags). Unknown capabilities are
    allowed but flagged (policy.selection.allow_unknown_capabilities)."""
    caps = model.get("capabilities", {})
    flags: list[str] = []
    min_ctx = task.get("min_context_tokens")
    if min_ctx:
        ctx = caps.get("context_window_tokens", "unknown")
        if _known(ctx):
            if ctx < min_ctx:
                return False, f"context {ctx} < required {min_ctx}", flags
        else:
            flags.append("unknown_context_window")
    for spec in task.get("required_specialties", []):
        declared = caps.get("specialties") or []
        if spec not in declared:
            return False, f"missing specialty {spec}", flags
    if task.get("required_tools"):
        tool_use = caps.get("tool_use", "unknown")
        if tool_use is False:
            return False, "model declares no tool_use", flags
        if tool_use == "unknown":
            flags.append("unknown_tool_use")
    if task.get("reasoning") == "advanced":
        reasoning = caps.get("reasoning", "unknown")
        if _known(reasoning) and reasoning != "advanced":
            return False, f"reasoning {reasoning} < advanced", flags
        if not _known(reasoning):
            flags.append("unknown_reasoning")
    return True, "", flags


def _rank_key(model: dict, policy: dict):
    neutral = policy["selection"]["unknown_reliability_neutral"]
    rel = model.get("reliability", "unknown")
    rel = rel if _known(rel) else neutral
    cost = model.get("cost", {}).get("input_per_mtok", "unknown")
    cost = cost if _known(cost) else float("inf")
    lat = model.get("latency_class", "unknown")
    lat = LATENCY_RANK.get(lat, 3)
    return (-rel, cost, lat, model["id"])


def _candidates(tier, models, task, policy):
    eligible, rejected, flags = [], [], []
    for m in models:
        if tier not in m.get("tier_affinity", []):
            continue
        if m.get("availability") in policy["selection"]["exclude_availability"]:
            rejected.append({"model_id": m["id"], "reason": "unavailable"})
            continue
        ok, reason, cflags = _capability_check(m, task)
        if not ok:
            rejected.append({"model_id": m["id"], "reason": reason})
            continue
        if m.get("availability") != "verified_available":
            cflags.append("unverified_model")
        eligible.append(m)
        flags.extend(cflags)
    eligible.sort(key=lambda m: _rank_key(m, policy))
    return eligible, rejected, sorted(set(flags))


def route(task: dict, policy: dict, models: list, roles: dict,
          implementer: dict | None = None, environment: str = "native_subagent") -> dict:
    """Full routing decision (all four planes, RT-06). `implementer` is
    {model_id, agent_instance_id, family} for review independence (QA-01)."""
    tier, flags = compute_tier(task, policy)
    alternatives: list[dict] = []

    if task.get("is_review"):
        if not task.get("reviews_task_id"):
            raise RoutingError("review task requires reviews_task_id")
        models = [m for m in models
                  if not (implementer and m["id"] == implementer.get("model_id"))]
        if implementer and not any(
            m.get("family") != implementer.get("family") for m in models
        ):
            flags.append("degraded_independence")

    escalation_path = policy["fallback"]["escalation_path"]
    start = _tier_idx(tier)
    chosen, model = None, None
    for idx in range(start, len(escalation_path)):
        t = escalation_path[idx]
        if t == "TIER-5":
            continue
        eligible, rejected, cflags = _candidates(t, models, task, policy)
        alternatives.extend(rejected)
        if eligible:
            chosen, model = t, eligible[0]
            alternatives.extend(
                {"model_id": m["id"], "reason": "ranked lower"} for m in eligible[1:]
            )
            flags.extend(cflags)
            if idx > start:
                flags.append("tier_escalated")
            break
    if task.get("is_review"):
        eligible, rejected, cflags = _candidates("TIER-5", models, task, policy)
        alternatives.extend(rejected)
        if eligible:
            if implementer:
                # prefer_different_family: different-family candidates rank first
                eligible.sort(key=lambda m: (
                    0 if m.get("family") != implementer.get("family") else 1,
                    _rank_key(m, policy)))
            chosen, model = "TIER-5", eligible[0]
            flags.extend(cflags)
        else:
            chosen, model = None, None

    role_id = task.get("required_role") or policy["category_default_role"][task["category"]]
    if role_id not in roles:
        raise RoutingError(f"unknown role {role_id}")
    role = roles[role_id]
    missing = set(task.get("required_capabilities", [])) - set(role["capabilities"])
    if missing:
        raise RoutingError(f"role {role_id} lacks capabilities {sorted(missing)}")
    if chosen and chosen not in role.get("tier_affinity", []) and not task.get("is_review"):
        flags.append("role_tier_mismatch")

    sensitive = set(task.get("sensitive_operations", []))
    known_ops = set(policy["approval"]["sensitive_operations"])
    if sensitive - known_ops:
        raise RoutingError(f"unknown sensitive operations {sensitive - known_ops}")
    # CAT-07 "mutating intent" = any declared write claim (ROUTING-POLICY §3 step 12)
    cat07_mutating = task["category"] == "CAT-07" and any(
        c.get("mode") == "write" for c in task.get("resource_claims", []))
    requires_approval = bool(sensitive) or bool(task.get("requires_approval")) or cat07_mutating

    instance_id = task.get("agent_instance_id", f"{role_id}-1")
    if task.get("is_review") and implementer:
        # exclude_implementer_instance (QA-01): reviewer instance must differ
        while instance_id == implementer.get("agent_instance_id"):
            instance_id += "-r"

    if model is None:
        return {
            "decided_at": task.get("created_at", "unknown"),
            "tier": tier, "model_id": "none", "agent_role": role_id,
            "agent_instance_id": instance_id,
            "tools": task.get("required_tools", []), "environment": environment,
            "alternatives": alternatives, "flags": sorted(set(flags)) + ["no_candidate"],
            "rationale": "no eligible model in tier or escalation path; human escalation required",
            "decision": "human_escalation", "requires_approval": requires_approval,
        }
    return {
        "decided_at": task.get("created_at", "unknown"),
        "tier": chosen, "model_id": model["id"], "agent_role": role_id,
        "agent_instance_id": instance_id,
        "tools": task.get("required_tools", []), "environment": environment,
        "alternatives": alternatives, "flags": sorted(set(flags)),
        "rationale": f"category {task['category']} -> tier {chosen}; "
                     f"model {model['id']} ranked first among eligible candidates",
        "decision": "route", "requires_approval": requires_approval,
    }


def plan_fallback(policy: dict, event: str, attempts_used: int,
                  consumed: list[str] | None = None) -> str:
    """Next step of the fallback chain for an event, given retries already
    used and chain steps already consumed. Steps are applied in order;
    exhaustion ends at human_escalation (RT-07)."""
    consumed = list(consumed or [])
    chains = {
        "model_unavailable": policy["fallback"]["on_model_unavailable"],
        "execution_failure": policy["fallback"]["on_execution_failure"],
        "validation_failure": policy["fallback"]["on_validation_failure"],
    }
    if event not in chains:
        raise RoutingError(f"unknown fallback event {event}")
    chain = chains[event]
    if "retry_with_feedback" in chain and attempts_used < policy["fallback"]["max_retries"]:
        return "retry_with_feedback"
    for step in chain:
        if step == "retry_with_feedback" or step in consumed:
            continue
        return step
    return "human_escalation"


def claims_conflict(claims_a: list[dict], claims_b: list[dict]) -> list[str]:
    """Pairwise compatibility of two declared claim sets (LC-03/04)."""
    problems = []
    for c in claims_a:
        for o in claims_b:
            if not (fnmatch.fnmatch(c["path"], o["path"])
                    or fnmatch.fnmatch(o["path"], c["path"]) or c["path"] == o["path"]):
                continue
            if c["mode"] == "write" and o["mode"] == "write":
                problems.append(f"write-write {c['path']}")
            elif c["mode"] == "write" and o["mode"] == "read" \
                    and not o.get("allow_stale_reads"):
                problems.append(f"write-read {c['path']}")
            elif c["mode"] == "read" and o["mode"] == "write" \
                    and not c.get("allow_stale_reads"):
                problems.append(f"read-write {c['path']}")
    return problems


class ClaimLedger:
    """Universal LC-04 mechanism: orchestrator-held resource claims."""

    def __init__(self):
        self.held: dict[str, list[dict]] = {}

    def conflicts(self, task_id: str, claims: list[dict]) -> list[str]:
        problems = []
        for other_id, other_claims in self.held.items():
            if other_id == task_id:
                continue
            problems.extend(f"{p} vs {other_id}"
                            for p in claims_conflict(claims, other_claims))
        return problems

    def acquire(self, task_id: str, claims: list[dict]):
        problems = self.conflicts(task_id, claims)
        if problems:
            raise ClaimConflict("; ".join(problems))
        self.held[task_id] = claims

    def release(self, task_id: str):
        self.held.pop(task_id, None)


def _expired(record: dict) -> bool:
    exp = record.get("expires_at")
    if not exp:
        return False
    try:
        when = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
    except ValueError:
        return True                      # unparseable expiry ⇒ treat as invalid
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when <= datetime.now(timezone.utc)


def _approval_valid(record: dict, task_id: str) -> bool:
    return (record.get("task_id") == task_id
            and bool(record.get("operations"))
            and bool(record.get("approver"))
            and not _expired(record))


def _waiver(task: dict, scope: str, covers: str | None = None) -> bool:
    for w in task.get("waivers", []):
        if w.get("scope") != scope or not w.get("approver") or _expired(w):
            continue
        if covers is None or covers in (w.get("covers") or []):
            return True
    return False


def _review_required(task: dict) -> bool:
    return (task.get("failure_impact") == "high"
            or task.get("category") == "CAT-07"
            or bool(task.get("require_independent_review")))


class LifecycleKernel:
    """State machine + gate enforcement from EXECUTION-LIFECYCLE.md."""

    def __init__(self, policy: dict, ledger: ClaimLedger | None = None,
                 max_concurrent: int | None = None):
        self.policy = policy
        self.ledger = ledger or ClaimLedger()
        self.tasks: dict[str, dict] = {}
        self.max_concurrent = max_concurrent

    def register(self, task: dict):
        if task["status"] != "RECEIVED":
            raise TransitionError("tasks must start at RECEIVED")
        self.tasks[task["task_id"]] = task
        task.setdefault("history", [])

    def _has_cycle(self) -> bool:
        graph = {tid: t.get("depends_on", []) for tid, t in self.tasks.items()}
        visiting, done = set(), set()

        def visit(node):
            if node in visiting:
                return True
            if node in done:
                return False
            visiting.add(node)
            for dep in graph.get(node, []):
                if dep in graph and visit(dep):
                    return True
            visiting.discard(node)
            done.add(node)
            return False

        return any(visit(n) for n in graph)

    def transition(self, task_id: str, to: str, actor: str, reason: str):
        task = self.tasks[task_id]
        frm = task["status"]
        if to not in TRANSITIONS.get(frm, set()):
            raise TransitionError(f"illegal transition {frm} -> {to}")
        if to == "DECOMPOSED" and self._has_cycle():
            raise TransitionError("dependency graph contains a cycle (TASK-CONTRACT §2)")
        if to == "DEPENDENCIES_RESOLVED":
            for dep in task.get("depends_on", []):
                dep_task = self.tasks.get(dep)
                if dep_task is not None and dep_task["status"] == "COMPLETED":
                    continue
                if _waiver(task, "dependency", covers=dep):
                    continue
                raise TransitionError(f"dependency {dep} not COMPLETED")
        if to == "ROUTED" and not task.get("routing"):
            raise TransitionError("ROUTED requires a routing decision")
        if to == "EXECUTING":
            requires = task.get("requires_approval") or task.get("routing", {}).get("requires_approval")
            if frm == "APPROVED_IF_REQUIRED" and requires:
                ops = set(task.get("sensitive_operations", []))
                valid = [a for a in task.get("approvals", [])
                         if _approval_valid(a, task_id)]
                approved = set()
                for a in valid:
                    approved |= set(a.get("operations", []))
                if not valid or not ops <= approved:
                    raise TransitionError(
                        "missing/expired human approval for required operations")
            running = [t for t in self.tasks.values() if t["status"] == "EXECUTING"]
            if self.max_concurrent is not None and len(running) >= self.max_concurrent:
                raise TransitionError("concurrency limit reached (degraded parallelism)")
            self.ledger.acquire(task_id, task.get("resource_claims", []))
        if to == "COMPLETED":
            result = task.get("result")
            if not result or not result.get("evidence"):
                raise TransitionError("COMPLETED requires result with evidence")
            for ch in task.get("children", []):
                child = self.tasks[ch]
                if child["status"] == "COMPLETED":
                    continue
                if child["status"] == "FAILED" and _waiver(task, "partial_acceptance", covers=ch):
                    continue
                raise TransitionError(f"child {ch} not COMPLETED")
            if _review_required(task) and not _waiver(task, "review"):
                g3 = [g for g in task.get("gate_results", [])
                      if g.get("gate") == "G3" and g.get("passed") and g.get("evidence")]
                if not g3:
                    raise TransitionError(
                        "G3 independent review verdict required (QA-01); "
                        "record gate_result or a human review waiver")
            requires = task.get("requires_approval") or task.get("routing", {}).get("requires_approval")
            if requires:
                valid = [a for a in task.get("approvals", [])
                         if _approval_valid(a, task_id)]
                ops = set(task.get("sensitive_operations", []))
                approved = set()
                for a in valid:
                    approved |= set(a.get("operations", []))
                if not valid or not ops <= approved:
                    raise TransitionError("G4: approvals missing or expired at acceptance")
        if to in TERMINAL:
            self.ledger.release(task_id)
        task["history"].append({"at": "kernel", "actor": actor,
                                "from": frm, "to": to, "reason": reason})
        task["status"] = to
        return task

    def _dep_closure(self, task_id: str) -> set[str]:
        seen: set[str] = set()
        stack = list(self.tasks[task_id].get("depends_on", []))
        while stack:
            dep = stack.pop()
            if dep in seen:
                continue
            seen.add(dep)
            if dep in self.tasks:
                stack.extend(self.tasks[dep].get("depends_on", []))
        return seen

    def can_parallel(self, a_id: str, b_id: str) -> bool:
        a, b = self.tasks[a_id], self.tasks[b_id]
        if b_id in self._dep_closure(a_id) or a_id in self._dep_closure(b_id):
            return False
        if claims_conflict(a.get("resource_claims", []), b.get("resource_claims", [])):
            return False
        problems = self.ledger.conflicts(b_id, a.get("resource_claims", []))
        return not problems


def scan_secrets(text: str) -> list[str]:
    hits = []
    for pat in SECRET_PATTERNS:
        hits.extend(re.findall(pat, text))
    return hits


def validate_envelope(envelope: dict, expected_project: str,
                      grants: list[dict] | None = None) -> None:
    """HANDOFF-CONTRACT §1 receiver checks. Raises EnvelopeError on violation.

    Grants are authoritative ONLY when present in the receiver-held registry
    (`grants`); grants embedded in the envelope are never trusted (ISO-04).
    Whole-project wildcard scopes are rejected; every grant must be unexpired,
    unrevoked, and scoped to explicit artifact paths."""
    registry = {g["grant_id"]: g for g in (grants or [])}
    if envelope.get("project_id") != expected_project:
        raise EnvelopeError("project mismatch (ISO-02)")
    if not envelope.get("redaction", {}).get("passed"):
        raise EnvelopeError("redaction pass missing/failed (SEC-03)")
    if not envelope.get("forbidden_content_ack"):
        raise EnvelopeError("forbidden content ack missing (ISO-05)")
    if scan_secrets(yaml.safe_dump(envelope)):
        raise EnvelopeError("secret-like content in envelope (ISO-05)")
    for artifact in envelope.get("artifacts", []):
        if artifact.startswith(f"{expected_project}/") or not artifact.startswith("projects/"):
            continue
        owner = artifact.split("/")[1]
        if owner == expected_project:
            continue
        matched = None
        for g in registry.values():
            if g.get("revoked") or g.get("source_project") != owner:
                continue
            if g.get("target_project") not in (None, expected_project):
                continue
            if _expired(g):
                continue
            scopes = g.get("scope", [])
            for s in scopes:
                if s in (f"projects/{owner}", f"projects/{owner}/", f"projects/{owner}/*",
                         f"projects/{owner}/**", "projects/*", "projects/**", "*", "**"):
                    raise EnvelopeError(
                        f"grant {g.get('grant_id')} uses whole-project wildcard scope (ISO-04)")
                if fnmatch.fnmatch(artifact, s) or artifact == s:
                    matched = g
                    break
            if matched:
                break
        if not matched:
            raise EnvelopeError(f"cross-project artifact without grant: {artifact} (ISO-04)")


def select_execution_environment(profile: dict, task: dict) -> tuple[str, list[str]]:
    """ADAPTER-IMPLEMENTATION-SPEC §4 fallback ladder, environment plane.
    `profile` is an adapter PROFILE.yaml dict."""
    caps = profile.get("capabilities", {})

    def ok(key):
        return caps.get(key, {}).get("status") in ("verified_doc", "verified_local", "verified_live")

    flags = []
    if ok("custom_agents"):
        env = "native_subagent"
        if ok("worktree_isolation") and task.get("resource_claims"):
            env = "worktree_agent"
    elif ok("headless_invocation"):
        env = "headless_cli"
        flags.append("degraded_multi_agent")
    else:
        env = "manual"
        flags.append("degraded_multi_agent")
    if not ok("parallel_dispatch"):
        flags.append("degraded_parallelism")
    if not ok("per_agent_model_selection"):
        flags.append("degraded_model_routing")
    used = ["custom_agents", "parallel_dispatch", "per_agent_model_selection"]
    if env == "worktree_agent":
        used.append("worktree_isolation")
    if env == "headless_cli":
        used = ["headless_invocation", "parallel_dispatch", "per_agent_model_selection"]
    statuses = [caps.get(k, {}).get("status") for k in used]
    if "verified_local" not in statuses and "verified_live" not in statuses \
            and any(s == "verified_doc" for s in statuses):
        flags.append("doc_only_verification")
    return env, flags