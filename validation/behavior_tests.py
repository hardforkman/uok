#!/usr/bin/env python3
"""Behavior tests TS-01…TS-12 — execute the reference kernel against the
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

    # Report
    print(f"behavior_tests: {len(PASSES)} checks passed, {len(FAILURES)} failed")
    for p in PASSES:
        print(f"  PASS {p}")
    for f in FAILURES:
        print(f"  FAIL {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())