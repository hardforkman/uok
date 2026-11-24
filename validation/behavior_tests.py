#!/usr/bin/env python3
"""Behavior tests TS-01…TS-13 — execute the reference kernel against the
scenario fixtures (validation/fixtures/tasks.yaml) and the shipped policy,
registry (test_only mock models), and role definitions.

These verify ACTUAL kernel behavior (routing decisions, state transitions,
claim conflicts, envelope rejection), not documentation presence. They do
NOT verify any live vendor environment — live compatibility probes are
manual procedures in validation/COMPATIBILITY-TESTS.md §3.

Run: python3 validation/behavior_tests.py   (exit 0 = all pass)
"""
from __future__ import annotations

import copy
import sys

import reference_router as rk

FAILURES: list[str] = []
PASSES: list[str] = []
POLICY = MODELS = ROLES = None


def check(scenario: str, cond: bool, detail: str):
    if cond:
        PASSES.append(f"{scenario}: {detail}")
    else:
        FAILURES.append(f"{scenario}: {detail}")


def fixtures():
    data = rk.load_yaml("validation/fixtures/tasks.yaml")
    return {s["id"]: s for s in data["scenarios"]}


def mock_models(mutations=None):
    models = copy.deepcopy(rk.load_registry(test_mode=True))
    for mut in mutations or []:
        for m in models:
            if m["id"] == mut["id"]:
                m.update({k: v for k, v in mut.items() if k != "id"})
    return models


def new_task(raw):
    t = copy.deepcopy(raw)
    t["status"] = "RECEIVED"
    return t


def advance(kernel, task_id, target, actor="orchestrator"):
    order = rk.STATES
    task = kernel.tasks[task_id]
    while task["status"] != target:
        nxt = order[order.index(task["status"]) + 1]
        if nxt == "ROUTED" and not task.get("routing"):
            task["routing"] = rk.route(task, POLICY, MODELS, ROLES)
        kernel.transition(task_id, nxt, actor, f"advance to {nxt}")
        if nxt == target:
            break


def complete(kernel, task_id):
    advance(kernel, task_id, "VALIDATING")
    kernel.tasks[task_id]["result"] = {
        "summary": "done", "status": "success",
        "artifacts": ["diff.patch"], "evidence": ["test output: 12 passed"],
    }
    kernel.transition(task_id, "COMPLETED", "orchestrator", "gates passed")


def main():
    global POLICY, MODELS, ROLES
    policy = rk.load_policy()
    roles = rk.load_roles()
    fx = fixtures()
    models = mock_models()
    POLICY, MODELS, ROLES = policy, models, roles

    # TS-01 — simple task routed to economical model
    s = fx["TS-01"]
    d = rk.route(s["task"], policy, models, roles)
    e = s["expect"]
    check("TS-01", d["tier"] == e["tier"] and d["model_id"] == e["model_id"]
          and d["decision"] == e["decision"],
          f"tier={d['tier']} model={d['model_id']} decision={d['decision']}")

    # TS-02 — complex task escalated to stronger model
    s = fx["TS-02"]
    d = rk.route(s["task"], policy, models, roles)
    e = s["expect"]
    check("TS-02", d["tier"] == e["tier"] and d["model_id"] == e["model_id"],
          f"tier={d['tier']} model={d['model_id']} (modifiers capped at TIER-3)")

    # TS-03 — specialized agent/model
    s = fx["TS-03"]
    d = rk.route(s["task"], policy, models, roles)
    e = s["expect"]
    check("TS-03", d["tier"] == e["tier"] and d["model_id"] == e["model_id"]
          and d["agent_role"] == s["task"]["required_role"],
          f"tier={d['tier']} model={d['model_id']} role={d['agent_role']}")

    # TS-04 — independent tasks in parallel
    s = fx["TS-04"]
    kernel = rk.LifecycleKernel(policy)
    a, b = (new_task(t) for t in s["tasks"])
    kernel.register(a); kernel.register(b)
    check("TS-04", kernel.can_parallel(a["task_id"], b["task_id"]),
          "disjoint write claims + no dependencies => parallel allowed")
    kernel.ledger.acquire(a["task_id"], a["resource_claims"])
    kernel.ledger.acquire(b["task_id"], b["resource_claims"])
    check("TS-04", True, "both claim sets acquired without conflict")

    # TS-05 — dependent tasks sequential
    s = fx["TS-05"]
    kernel = rk.LifecycleKernel(policy)
    a, b = (new_task(t) for t in s["tasks"])
    kernel.register(a); kernel.register(b)
    check("TS-05", not kernel.can_parallel(a["task_id"], b["task_id"]),
          "dependency edge blocks parallelism")
    advance(kernel, b["task_id"], "DECOMPOSED")
    try:
        kernel.transition(b["task_id"], "DEPENDENCIES_RESOLVED", "orchestrator", "premature")
        check("TS-05", False, "premature dependency resolution was NOT blocked")
    except rk.TransitionError:
        check("TS-05", True, "premature dependency resolution blocked")
    complete(kernel, a["task_id"])
    kernel.transition(b["task_id"], "DEPENDENCIES_RESOLVED", "orchestrator", "dep completed")
    check("TS-05", kernel.tasks[b["task_id"]]["status"] == "DEPENDENCIES_RESOLVED",
          "resolution allowed after dependency COMPLETED")

    # TS-06 — model unavailable => same-tier alternative
    s = fx["TS-06"]
    d = rk.route(s["task"], policy, mock_models(s["registry_mutations"]), roles)
    e = s["expect"]
    check("TS-06", d["tier"] == e["tier"] and d["model_id"] == e["model_id"],
          f"fallback model={d['model_id']}")
    check("TS-06", any(x["model_id"] == "mock-fast" and x["reason"] == "unavailable"
                       for x in d["alternatives"]),
          "unavailable candidate recorded in alternatives")

    # TS-07 — failure fallback chain + tier escalation + human escalation
    s = fx["TS-07"]
    d = rk.route(s["task"], policy, mock_models(s["registry_mutations"]), roles)
    e = s["expect"]
    check("TS-07", d["tier"] == e["tier"] and d["model_id"] == e["model_id"]
          and e["flag"] in d["flags"],
          f"escalated to {d['tier']}/{d['model_id']} flags={d['flags']}")
    steps = [rk.plan_fallback(policy, "execution_failure", i) for i in range(3)]
    check("TS-07", steps == e["retry_steps"], f"retry chain {steps}")
    all_down = [{"id": m["id"], "availability": "unavailable"} for m in models]
    d2 = rk.route(s["task"], policy, mock_models(all_down), roles)
    check("TS-07", d2["decision"] == "human_escalation" and d2["model_id"] == "none",
          "all models unavailable => human escalation, no silent substitution")

    # TS-08 — reviewer rejection + independence
    s = fx["TS-08"]
    d = rk.route(s["task"], policy, models, roles, implementer=s["implementer"])
    e = s["expect"]
    check("TS-08", d["tier"] == e["tier"] and d["model_id"] == e["model_id"]
          and d["model_id"] != s["implementer"]["model_id"],
          f"independent reviewer model={d['model_id']}")
    kernel = rk.LifecycleKernel(policy)
    impl = new_task(fx["TS-02"]["task"])
    kernel.register(impl)
    impl["routing"] = rk.route(impl, policy, models, roles)
    advance(kernel, impl["task_id"], "VALIDATING")
    kernel.transition(impl["task_id"], "EXECUTING", "code_reviewer",
                      "verdict=reject; retry with feedback")
    check("TS-08", kernel.tasks[impl["task_id"]]["status"] == "EXECUTING",
          "rejection re-enters EXECUTING with feedback")
    check("TS-08", rk.plan_fallback(policy, "validation_failure", 2) == "escalate_tier",
          "exhausted retries => escalate_tier (never silent accept)")

    # TS-09 — sensitive task approval gate
    s = fx["TS-09"]
    kernel = rk.LifecycleKernel(policy)
    t = new_task(s["task"])
    kernel.register(t)
    t["routing"] = rk.route(t, policy, models, roles)
    check("TS-09", t["routing"]["requires_approval"], "requires_approval computed")
    advance(kernel, t["task_id"], "APPROVED_IF_REQUIRED")
    try:
        kernel.transition(t["task_id"], "EXECUTING", "orchestrator", "no approval")
        check("TS-09", False, "execution WITHOUT approval was NOT blocked")
    except rk.TransitionError:
        check("TS-09", True, "execution without approval blocked")
    t["approvals"] = [{
        "approval_id": "A-1", "task_id": t["task_id"],
        "operations": ["production_deploy"], "approver": "human:test",
        "granted_at": "2026-11-16T00:00:00Z",
    }]
    kernel.transition(t["task_id"], "EXECUTING", "orchestrator", "approval recorded")
    check("TS-09", kernel.tasks[t["task_id"]]["status"] == "EXECUTING",
          "execution with scoped approval allowed")

    # TS-10 — isolation violations prevented
    s = fx["TS-10"]
    # Construct an obviously fake key-shaped string at runtime (never stored
    # in kit files) to prove the redaction scanner rejects secret-like content.
    fake_secret = "sk-" + "fixture0123456789" * 2
    for name, expected in s["expect"].items():
        env = copy.deepcopy(s["envelopes"][name])
        if name == "secret_leak":
            env["task_statement"] = env["task_statement"].replace(
                "fixture secret marker", fake_secret)
        # Grants are authoritative only from the receiver-held registry
        # (ISO-04); envelope-embedded grants are never trusted.
        receiver_grants = env.get("cross_project_grants") if name == "granted_cross_project" else None
        try:
            rk.validate_envelope(env, "demo", grants=receiver_grants)
            outcome = "accepted"
        except rk.EnvelopeError as exc:
            outcome = "rejected"
        check("TS-10", outcome == expected, f"{name}: {outcome} (expected {expected})")
        if name == "granted_cross_project":
            try:
                rk.validate_envelope(env, "demo")  # no receiver registry
                untrusted = "accepted"
            except rk.EnvelopeError:
                untrusted = "rejected"
            check("TS-10", untrusted == "rejected",
                  f"embedded-only grant not trusted: {untrusted} (expected rejected)")

    # TS-11 — conflicting parallel writes prevented
    s = fx["TS-11"]
    kernel = rk.LifecycleKernel(policy)
    a, b = (new_task(t) for t in s["tasks"])
    kernel.register(a); kernel.register(b)
    check("TS-11", not kernel.can_parallel(a["task_id"], b["task_id"]),
          "overlapping write claims block parallelism")
    kernel.ledger.acquire(a["task_id"], a["resource_claims"])
    try:
        kernel.ledger.acquire(b["task_id"], b["resource_claims"])
        check("TS-11", False, "conflicting acquire was NOT blocked")
    except rk.ClaimConflict:
        check("TS-11", True, "conflicting acquire blocked")

    # TS-12 — environment without native multi-agent support
    s = fx["TS-12"]
    profile = rk.load_yaml(f"adapters/{s['profile']}/PROFILE.yaml")
    env, flags = rk.select_execution_environment(profile, s["task"])
    e = s["expect"]
    check("TS-12", env in e["environment_in"], f"fallback environment={env}")
    check("TS-12", all(f in flags for f in e["flags_include"]),
          f"degradation flags recorded: {flags}")
    kernel = rk.LifecycleKernel(policy, max_concurrent=1)
    t1 = new_task(s["task"])
    t2 = new_task(dict(s["task"], task_id="T-demo-012b"))
    kernel.register(t1); kernel.register(t2)
    for t in (t1, t2):
        t["routing"] = rk.route(t, policy, models, roles, environment=env)
        advance(kernel, t["task_id"], "APPROVED_IF_REQUIRED")
    kernel.transition(t1["task_id"], "EXECUTING", "orchestrator", "slot 1")
    try:
        kernel.transition(t2["task_id"], "EXECUTING", "orchestrator", "slot 2")
        check("TS-12", False, "sequential enforcement FAILED")
    except rk.TransitionError:
        check("TS-12", True, "sequential execution enforced (concurrency=1)")

    # --- Audit regression checks ------------------------------------------

    # CAT-08 with all-high modifiers must stay TIER-4 (no ladder overflow)
    tier, _ = rk.compute_tier({"category": "CAT-08", "complexity": "high",
                               "reasoning": "advanced", "failure_impact": "high"}, policy)
    check("TS-03", tier == "TIER-4", f"CAT-08 all-high modifiers stay TIER-4 (got {tier})")
    tier, _ = rk.compute_tier({"category": "CAT-01", "requested_tier": "TIER-5"}, policy)
    check("TS-02", tier == "TIER-4",
          f"requested TIER-5 without review clamps to TIER-4 (got {tier})")

    # Fallback chain progresses through consumed steps, ends at human escalation
    consumed, seq = [], []
    for _ in range(4):
        step = rk.plan_fallback(policy, "execution_failure", 2, consumed=consumed)
        seq.append(step)
        if step == "human_escalation":
            break
        consumed.append(step)
    check("TS-07", seq == ["same_tier_alternative", "escalate_tier", "human_escalation"],
          f"consumed-step progression {seq}")

    # Reviewer instance exclusion + same-family degradation flag
    rt = dict(fx["TS-08"]["task"], agent_instance_id="impl-1")
    d = rk.route(rt, policy, models, roles,
                 implementer={"model_id": "mock-advanced",
                              "agent_instance_id": "impl-1", "family": "mock-advanced"})
    check("TS-08", d["agent_instance_id"] != "impl-1",
          f"reviewer instance differs from implementer ({d['agent_instance_id']})")
    same_fam = mock_models([{"id": "mock-reviewer", "family": "mock-advanced"}])
    d = rk.route(fx["TS-08"]["task"], policy, same_fam, roles,
                 implementer={"model_id": "mock-advanced",
                              "agent_instance_id": "impl-1", "family": "mock-advanced"})
    check("TS-08", "degraded_independence" in d["flags"],
          "same-family-only review flagged degraded_independence")

    # CAT-07 mutating intent (write claim) requires approval; read-only does not
    t7 = {"task_id": "T-demo-cat07", "category": "CAT-07",
          "created_at": "2026-11-17T00:00:00Z",
          "resource_claims": [{"path": "firewall.rules", "mode": "write"}]}
    d = rk.route(t7, policy, models, roles)
    check("TS-09", d["requires_approval"], "CAT-07 with write claim requires approval")
    d = rk.route(dict(t7, resource_claims=[{"path": "audit.log", "mode": "read"}]),
                 policy, models, roles)
    check("TS-09", not d["requires_approval"], "read-only CAT-07 does not force approval")

    # Expired and empty-operations approvals are invalid at EXECUTING entry
    kernel = rk.LifecycleKernel(policy)
    t = new_task(fx["TS-09"]["task"])
    kernel.register(t)
    t["routing"] = rk.route(t, policy, models, roles)
    advance(kernel, t["task_id"], "APPROVED_IF_REQUIRED")
    base_appr = {"approval_id": "A-x", "task_id": t["task_id"],
                 "operations": ["production_deploy"], "approver": "human:test",
                 "granted_at": "2026-11-16T00:00:00Z"}
    t["approvals"] = [dict(base_appr, expires_at="2020-01-01T00:00:00Z")]
    try:
        kernel.transition(t["task_id"], "EXECUTING", "orchestrator", "expired approval")
        check("TS-09", False, "expired approval was NOT blocked")
    except rk.TransitionError:
        check("TS-09", True, "expired approval blocked")
    t["approvals"] = [dict(base_appr, operations=[])]
    try:
        kernel.transition(t["task_id"], "EXECUTING", "orchestrator", "empty-ops approval")
        check("TS-09", False, "empty-operations approval was NOT blocked")
    except rk.TransitionError:
        check("TS-09", True, "empty-operations approval approves nothing")

    # G3 blocks COMPLETED for high-impact tasks; gate_result or waiver unblocks
    kernel = rk.LifecycleKernel(policy)
    t = new_task(dict(fx["TS-02"]["task"], task_id="T-demo-g3", failure_impact="high"))
    kernel.register(t)
    t["routing"] = rk.route(t, policy, models, roles)
    advance(kernel, t["task_id"], "VALIDATING")
    t["result"] = {"summary": "done", "status": "success",
                   "artifacts": ["diff.patch"], "evidence": ["test output: 12 passed"]}
    try:
        kernel.transition(t["task_id"], "COMPLETED", "orchestrator", "no review verdict")
        check("TS-08", False, "COMPLETED without G3 verdict was NOT blocked")
    except rk.TransitionError:
        check("TS-08", True, "G3 independent-review verdict required at COMPLETED")
    t["gate_results"] = [{"gate": "G3", "passed": True, "at": "2026-11-17",
                          "evidence": ["review verdict: approve"]}]
    kernel.transition(t["task_id"], "COMPLETED", "orchestrator", "G3 passed")
    check("TS-08", kernel.tasks[t["task_id"]]["status"] == "COMPLETED",
          "G3 gate_result with evidence unblocks COMPLETED")
    t2 = new_task(dict(fx["TS-02"]["task"], task_id="T-demo-g3w", failure_impact="high",
                       waivers=[{"scope": "review", "approver": "human:test",
                                 "covers": [], "granted_at": "2026-11-17"}]))
    kernel.register(t2)
    t2["routing"] = rk.route(t2, policy, models, roles)
    advance(kernel, t2["task_id"], "VALIDATING")
    t2["result"] = dict(t["result"])
    kernel.transition(t2["task_id"], "COMPLETED", "orchestrator", "human review waiver")
    check("TS-08", kernel.tasks[t2["task_id"]]["status"] == "COMPLETED",
          "explicit human review waiver substitutes G3")

    # Dependency cycles rejected at DECOMPOSED; dependency waiver is explicit
    kernel = rk.LifecycleKernel(policy)
    a = new_task({"task_id": "T-cyc-a", "category": "CAT-02",
                  "created_at": "2026-11-17T00:00:00Z", "depends_on": ["T-cyc-b"]})
    b = new_task({"task_id": "T-cyc-b", "category": "CAT-02",
                  "created_at": "2026-11-17T00:00:00Z", "depends_on": ["T-cyc-a"]})
    kernel.register(a); kernel.register(b)
    try:
        advance(kernel, "T-cyc-a", "DECOMPOSED")
        check("TS-05", False, "dependency cycle was NOT rejected")
    except rk.TransitionError:
        check("TS-05", True, "dependency cycle rejected at DECOMPOSED")
    kernel = rk.LifecycleKernel(policy)
    a = new_task({"task_id": "T-wa-a", "category": "CAT-02",
                  "created_at": "2026-11-17T00:00:00Z"})
    b = new_task({"task_id": "T-wa-b", "category": "CAT-02",
                  "created_at": "2026-11-17T00:00:00Z", "depends_on": ["T-wa-a"]})
    kernel.register(a); kernel.register(b)
    advance(kernel, "T-wa-b", "DECOMPOSED")
    try:
        kernel.transition("T-wa-b", "DEPENDENCIES_RESOLVED", "orchestrator", "no waiver")
        check("TS-05", False, "unwaived incomplete dependency was NOT blocked")
    except rk.TransitionError:
        check("TS-05", True, "incomplete dependency blocked without waiver")
    b["waivers"] = [{"scope": "dependency", "approver": "human:test",
                     "covers": ["T-wa-a"], "granted_at": "2026-11-17"}]
    kernel.transition("T-wa-b", "DEPENDENCIES_RESOLVED", "orchestrator", "human waiver")
    check("TS-05", kernel.tasks["T-wa-b"]["status"] == "DEPENDENCIES_RESOLVED",
          "explicit human dependency waiver allows resolution")

    # FAILED child blocks parent; partial_acceptance waiver unblocks
    kernel = rk.LifecycleKernel(policy)
    child = new_task({"task_id": "T-ch-1", "category": "CAT-02",
                      "created_at": "2026-11-17T00:00:00Z"})
    parent = new_task({"task_id": "T-par-1", "category": "CAT-02",
                       "created_at": "2026-11-17T00:00:00Z", "children": ["T-ch-1"]})
    kernel.register(child); kernel.register(parent)
    kernel.tasks["T-ch-1"]["status"] = "FAILED"
    parent["routing"] = rk.route(parent, policy, models, roles)
    advance(kernel, "T-par-1", "VALIDATING")
    parent["result"] = {"summary": "partial", "status": "success",
                        "artifacts": [], "evidence": ["child 1 failed, rest passed"]}
    try:
        kernel.transition("T-par-1", "COMPLETED", "orchestrator", "failed child")
        check("TS-05", False, "FAILED child did NOT block parent COMPLETED")
    except rk.TransitionError:
        check("TS-05", True, "FAILED child blocks parent COMPLETED")
    parent["waivers"] = [{"scope": "partial_acceptance", "approver": "human:test",
                          "covers": ["T-ch-1"], "granted_at": "2026-11-17"}]
    kernel.transition("T-par-1", "COMPLETED", "orchestrator", "human partial acceptance")
    check("TS-05", kernel.tasks["T-par-1"]["status"] == "COMPLETED",
          "human partial_acceptance waiver unblocks parent")

    # Grants: expired and whole-project wildcard scopes rejected (ISO-04)
    base_env = fx["TS-10"]["envelopes"]["granted_cross_project"]
    base_grant = base_env["cross_project_grants"][0]
    for label, mutation in [
        ("expired grant", {"expires_at": "2020-01-01T00:00:00Z"}),
        ("whole-project scope", {"scope": ["projects/shared-lib"]}),
        ("wildcard scope", {"scope": ["projects/shared-lib/**"]}),
    ]:
        env = copy.deepcopy(base_env)
        grant = dict(copy.deepcopy(base_grant), **mutation)
        try:
            rk.validate_envelope(env, "demo", grants=[grant])
            outcome = "accepted"
        except rk.EnvelopeError:
            outcome = "rejected"
        check("TS-10", outcome == "rejected", f"{label}: {outcome} (expected rejected)")

    # doc_only_verification flag when the chosen mechanism is only verified_doc
    # Synthetic profiles, so the check does not depend on which real adapter is currently doc-only.
    def _profile(status):
        return {"capabilities": {k: {"status": status} for k in
                ("custom_agents", "parallel_dispatch", "per_agent_model_selection")}}
    _, dflags = rk.select_execution_environment(_profile("verified_doc"), {})
    check("TS-12", "doc_only_verification" in dflags, f"doc-only adapter flagged: {dflags}")
    _, lflags = rk.select_execution_environment(_profile("verified_live"), {})
    check("TS-12", "doc_only_verification" not in lflags, f"live-verified adapter not flagged: {lflags}")
    cc_profile = rk.load_yaml("adapters/claude-code/PROFILE.yaml")
    _, ccflags = rk.select_execution_environment(cc_profile, {})
    check("TS-12", "doc_only_verification" not in ccflags,
          "live-verified adapter not flagged doc-only")

    # TS-13 — graph-aware routing: graph_impact complexity modifier (CG-06)
    import importlib.util, os
    _gs_path = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(rk.__file__)),
                                             "..", "core", "graph_signal.py"))
    _spec = importlib.util.spec_from_file_location("graph_signal", _gs_path)
    gs = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gs)

    s = fx["TS-13"]
    d = rk.route(s["task"], policy, models, roles)
    e = s["expect"]
    check("TS-13", d["tier"] == e["tier"] and d["model_id"] == e["model_id"]
          and "graph_impact_applied" in d["flags"],
          f"god-node signal bumps TIER-2 -> {d['tier']} model={d['model_id']}")
    check("TS-13", d.get("graph_signal", {}).get("max_degree") == s["task"]["graph_signal"]["max_degree"],
          "routing decision records the graph_signal metrics as evidence (CG-07)")

    synth = {"graph": {"schema_version": 48, "graphify_version": "0.9.112"},
             "nodes": [{"id": "A", "source_file": "src/core.py", "community": 0},
                       {"id": "B", "source_file": "src/util.py", "community": 0},
                       {"id": "C", "source_file": "src/api.py", "community": 1},
                       {"id": "D", "source_file": "src/db.py", "community": 2},
                       {"id": "E", "source_file": "src/ui.py", "community": 1}],
             "edges": [{"source": "B", "target": "A"}, {"source": "C", "target": "A"},
                       {"source": "D", "target": "A"}, {"source": "E", "target": "A"},
                       {"source": "A", "target": "B"}, {"source": "C", "target": "D"}]}
    sig = gs.compute_signal(synth, ["src/core.py"])
    check("TS-13", sig["status"] == "ok" and sig["max_degree"] == 5,
          f"extractor computes touched-node degree from edges (max_degree={sig['max_degree']})")
    check("TS-13", sig["community_spread"] == 3 and sig["impact_files"] == 5,
          f"1-hop impact: communities={sig['community_spread']} files={sig['impact_files']}")
    check("TS-13", gs.compute_signal({"nodes": "broken"}, ["src/core.py"])["status"] == "unavailable"
          and gs.compute_signal({}, ["x"])["status"] == "unavailable",
          "malformed graph fails open to unavailable (no bump)")
    check("TS-13", gs.compute_signal(synth, ["src/missing.py"])["status"] == "no_touched_nodes",
          "claims matching no indexed node -> no_touched_nodes (no bump)")

    base = dict(s["task"]); base.pop("graph_signal")
    below = dict(base, graph_signal={"status": "ok", "max_degree": 2, "community_spread": 1, "impact_files": 2})
    db = rk.route(below, policy, models, roles)
    check("TS-13", db["tier"] == "TIER-2" and "graph_impact_applied" not in db["flags"],
          "below all thresholds -> no bump (stays TIER-2)")
    capped = dict(base, complexity="high",
                  graph_signal={"status": "ok", "max_degree": 40, "community_spread": 1, "impact_files": 2})
    dc = rk.route(capped, policy, models, roles)
    check("TS-13", dc["tier"] == "TIER-3",
          f"complexity high + graph bump still capped at TIER-3 (got {dc['tier']})")
    st = rk.route(dict(base, graph_signal={"status": "stale"}), policy, models, roles)
    check("TS-13", st["tier"] == "TIER-2" and "graph_signal_stale" in st["flags"],
          "stale signal -> no bump + graph_signal_stale flag (CG-03)")
    un = rk.route(dict(base, graph_signal={"status": "unavailable"}), policy, models, roles)
    check("TS-13", un["tier"] == "TIER-2" and "graph_signal_unavailable" in un["flags"],
          "unavailable signal -> no bump + graph_signal_unavailable flag (fail-open)")
    rv = rk.route(dict(base, is_review=True, reviews_task_id="T-x",
                       graph_signal={"status": "ok", "max_degree": 99, "community_spread": 9, "impact_files": 99}),
                  policy, models, roles)
    check("TS-13", rv["tier"] == "TIER-5",
          "review task stays TIER-5; graph_impact never touches the reviewer tier")
    sec = rk.route(dict(base, category="CAT-07",
                        graph_signal={"status": "ok", "max_degree": 99, "community_spread": 9, "impact_files": 99}),
                   policy, models, roles)
    check("TS-13", sec["tier"] == "TIER-3",
          f"CAT-07 security floor holds at TIER-3 under graph bump (got {sec['tier']})")

    # Report
    print(f"behavior_tests: {len(PASSES)} checks passed, {len(FAILURES)} failed")
    for p in PASSES:
        print(f"  PASS {p}")
    for f in FAILURES:
        print(f"  FAIL {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())