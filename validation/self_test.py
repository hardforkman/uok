#!/usr/bin/env python3
"""Universal Orchestrator Kit — structural & consistency self-test.

Checks (CHK-01…CHK-16): directory completeness, document substance, YAML
validity (files + embedded protocol schemas), markdown cross-references,
routing/registry/role consistency, lifecycle completeness, template
conservatism, requirement/AC/TS traceability, secret absence, version headers.

Run: python3 validation/self_test.py   (exit 0 = all pass)
Requires: Python >= 3.10, PyYAML. No network access.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

import reference_router as rk

ROOT = rk.KIT_ROOT
RESULTS: list[tuple[str, bool, str]] = []

REQUIRED_FILES = [
    "START-HERE.md", "NORTH-STAR.md", "UNIVERSAL-ORCHESTRATION-SPEC.md",
    "AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md",
    "core/ROUTING-POLICY.md", "core/MODEL-REGISTRY.yaml",
    "core/AGENT-CAPABILITIES.yaml", "core/TASK-CLASSIFICATION.md",
    "core/EXECUTION-LIFECYCLE.md", "core/QUALITY-GATES.md",
    "protocols/AGENT-PROTOCOL.md", "protocols/TASK-CONTRACT.md",
    "protocols/HANDOFF-CONTRACT.md",
    "adapters/ADAPTER-IMPLEMENTATION-SPEC.md",
    "templates/PROJECT-CONFIG.yaml", "templates/MODEL-CONFIG.yaml",
    "templates/AGENT-CONFIG.yaml",
    "validation/ACCEPTANCE-CRITERIA.md", "validation/COMPATIBILITY-TESTS.md",
    "validation/SELF-TEST.md",
    "handoff/INSTALLATION-REPORT-TEMPLATE.md",
]
ADAPTERS = ["claude-code", "qoder", "cursor", "codex", "universal"]
ADAPTER_SECTIONS = [
    "Environment discovery", "Native agent capabilities", "Model selection",
    "Custom agent support", "Parallel execution", "Tool integration",
    "Context management", "Permissions", "Hooks and events",
    "External API integration", "Limitations", "Installation procedure",
    "Verification procedure",
]
PROFILE_KEYS = [
    "instruction_files", "custom_agents", "per_agent_model_selection",
    "parallel_dispatch", "background_execution", "worktree_isolation",
    "blocking_hooks", "permission_modes", "mcp", "headless_invocation",
    "context_isolation", "nesting",
]
STATUSES = {"unknown", "unverified", "verified_doc", "verified_local",
            "verified_live", "not_found"}
EXPECTED_SCHEMAS = {
    "task", "resource_claim", "routing_decision", "lifecycle_event",
    "gate_result", "approval_record", "waiver", "result_payload",
    "agent_register", "status_update", "error_report", "escalation",
    "validation_verdict", "context_envelope", "cross_project_grant",
    "final_handoff",
}
SENSITIVE_OPS = {
    "production_deploy", "financial_transaction", "irreversible_data_change",
    "destructive_infra_change", "credential_access_change",
    "unauthorized_external_publication",
}


def record(check_id: str, ok: bool, detail: str):
    RESULTS.append((check_id, ok, detail))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def fenced_yaml_blocks(text: str):
    return re.findall(r"```yaml\n(.*?)```", text, re.DOTALL)


def main() -> int:
    # CHK-01 directory completeness
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    for a in ADAPTERS:
        if not (ROOT / "adapters" / a / "README.md").is_file():
            missing.append(f"adapters/{a}/README.md")
    record("CHK-01", not missing, f"missing files: {missing}" if missing
           else f"all {len(REQUIRED_FILES) + len(ADAPTERS)} required files present")

    # CHK-02 document substance (no empty placeholders)
    thin = [f for f in REQUIRED_FILES if f.endswith(".md")
            and (ROOT / f).is_file() and len(read(f).strip()) < 400]
    record("CHK-02", not thin, f"thin documents: {thin}" if thin
           else "all required markdown documents have substantive content")

    # CHK-03 YAML validity (all files)
    yaml_files = sorted(ROOT.rglob("*.yaml"))
    bad = []
    for f in yaml_files:
        try:
            yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception as exc:
            bad.append(f"{f.relative_to(ROOT)}: {exc}")
    record("CHK-03", not bad, "; ".join(bad) if bad
           else f"{len(yaml_files)} YAML files parse successfully")

    # CHK-04 embedded protocol schemas parse + coverage
    found_schemas, schema_errors = set(), []
    for doc in ["protocols/TASK-CONTRACT.md", "protocols/AGENT-PROTOCOL.md",
                "protocols/HANDOFF-CONTRACT.md"]:
        for block in fenced_yaml_blocks(read(doc)):
            try:
                data = yaml.safe_load(block)
                if not isinstance(data, dict) or "schema" not in data:
                    continue
                if data.get("schema_version") != 1 or "fields" not in data:
                    schema_errors.append(f"{doc}:{data.get('schema')} missing version/fields")
                found_schemas.add(data["schema"])
            except Exception as exc:
                schema_errors.append(f"{doc}: {exc}")
    absent = EXPECTED_SCHEMAS - found_schemas
    ok = not schema_errors and not absent
    record("CHK-04", ok, f"errors={schema_errors} missing={sorted(absent)}" if not ok
           else f"{len(found_schemas)} versioned machine-readable schemas present")

    # CHK-05 markdown cross-references resolve
    broken = []
    for md in sorted(ROOT.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        for _, target in re.findall(r"\[([^\]]*)\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "mailto:", "#", "skill://")):
                continue
            path = target.split("#")[0]
            if not path:
                continue
            if not (md.parent / path).exists():
                broken.append(f"{md.relative_to(ROOT)} -> {target}")
    record("CHK-05", not broken, "; ".join(broken) if broken
           else "all relative markdown links resolve")

    # CHK-06 routing policy consistency
    policy = rk.load_policy()
    problems = []
    cats = set(rk.CATEGORIES)
    if set(policy["category_base_tier"]) != cats:
        problems.append("category_base_tier keys != CAT-01..08")
    if set(policy["category_default_role"]) != cats:
        problems.append("category_default_role keys != CAT-01..08")
    classification = read("core/TASK-CLASSIFICATION.md")
    for c in cats:
        if c not in classification:
            problems.append(f"{c} missing in TASK-CLASSIFICATION.md")
    tiers = set(policy["tiers"])
    for mapping in ("category_base_tier", "tier_floors"):
        for v in policy[mapping].values():
            if v not in tiers:
                problems.append(f"{mapping} references unknown tier {v}")
    if "TIER-5" in policy["fallback"]["escalation_path"]:
        problems.append("escalation_path must not contain TIER-5")
    roles = rk.load_roles()
    for r in policy["category_default_role"].values():
        if r not in roles:
            problems.append(f"default role {r} not in AGENT-CAPABILITIES.yaml")
    record("CHK-06", not problems, "; ".join(problems) if problems
           else "categories, tiers, floors, escalation path, and roles consistent")

    # CHK-07 model registry integrity
    reg = rk.load_yaml("core/MODEL-REGISTRY.yaml")
    problems = []
    for m in reg["models"]:
        for field in ("id", "provider", "tier_affinity", "capabilities",
                      "availability", "cost"):
            if field not in m:
                problems.append(f"{m.get('id')}: missing {field}")
        if m.get("availability") not in {"unknown", "unverified",
                                         "verified_available", "unavailable"}:
            problems.append(f"{m['id']}: bad availability")
        for t in m.get("tier_affinity", []):
            if t not in tiers:
                problems.append(f"{m['id']}: bad tier {t}")
        if m.get("test_only") and m.get("provider") != "mock":
            problems.append(f"{m['id']}: test_only outside mock provider")
        if m.get("example") and m.get("availability") != "unverified":
            problems.append(f"{m['id']}: example entry must stay unverified")
    record("CHK-07", not problems, "; ".join(problems) if problems
           else f"{len(reg['models'])} registry entries valid; examples unverified; fixtures isolated")

    # CHK-08 agent capability registry integrity
    expected_roles = {
        "orchestrator", "architect", "senior_engineer", "implementation_engineer",
        "research_analyst", "debugging_specialist", "test_engineer",
        "security_reviewer", "code_reviewer", "documentation_specialist",
        "release_integration",
    }
    problems = []
    if set(roles) != expected_roles:
        problems.append(f"role set mismatch: {set(roles) ^ expected_roles}")
    for rid, r in roles.items():
        for field in ("responsibilities", "capabilities", "permissions",
                      "expected_outputs", "validation"):
            if field not in r:
                problems.append(f"{rid}: missing {field}")
    record("CHK-08", not problems, "; ".join(problems) if problems
           else "all 11 capability roles fully defined")

    # CHK-09 lifecycle completeness
    lc = read("core/EXECUTION-LIFECYCLE.md")
    problems = [s for s in rk.STATES if s not in lc]
    task_schema = None
    for block in fenced_yaml_blocks(read("protocols/TASK-CONTRACT.md")):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and data.get("schema") == "task":
            task_schema = data
    if task_schema:
        allowed = task_schema["fields"]["status"]["allowed"]
        if set(allowed) != set(rk.STATES):
            problems.append("task schema status enum != lifecycle states")
    else:
        problems.append("task schema not found")
    record("CHK-09", not problems, "; ".join(problems) if problems
           else "all 12 lifecycle states documented and schema-consistent")

    # CHK-10 template conservatism + required fields
    problems = []
    proj = rk.load_yaml("templates/PROJECT-CONFIG.yaml")
    for key in ("project_id", "isolation", "cross_project", "permissions",
                "approval", "quality", "budget", "execution", "audit"):
        if key not in proj:
            problems.append(f"PROJECT-CONFIG missing {key}")
    if proj.get("isolation") != "strict":
        problems.append("PROJECT-CONFIG isolation must default to strict")
    if proj.get("approval", {}).get("auto_approve") is not False:
        problems.append("auto_approve must be false")
    if not SENSITIVE_OPS <= set(proj.get("approval", {}).get("required_operations", [])):
        problems.append("required_operations must include all six sensitive ops")
    if proj.get("secret_redaction", {}).get("enabled") is not True:
        problems.append("secret_redaction must be enabled")
    if proj.get("audit", {}).get("enabled") is not True:
        problems.append("audit must be enabled")
    mcfg = rk.load_yaml("templates/MODEL-CONFIG.yaml")
    if set(mcfg.get("tier_bindings", {})) != tiers:
        problems.append("MODEL-CONFIG tier_bindings must cover all five tiers")
    if mcfg.get("selection", {}).get("allow_test_only_models") is not False:
        problems.append("allow_test_only_models must be false")
    acfg = rk.load_yaml("templates/AGENT-CONFIG.yaml")
    if set(acfg.get("enabled_roles", [])) != expected_roles:
        problems.append("AGENT-CONFIG enabled_roles must cover all 11 roles")
    ind = acfg.get("independence", {})
    if not (ind.get("exclude_implementer_instance") and ind.get("exclude_implementer_model")):
        problems.append("independence exclusions must be true")
    if acfg.get("parallelism", {}).get("require_disjoint_write_claims") is not True:
        problems.append("require_disjoint_write_claims must be true")
    record("CHK-10", not problems, "; ".join(problems) if problems
           else "templates complete with conservative, non-weakenable defaults")

    # CHK-11 requirement ID coverage in the spec
    spec = read("UNIVERSAL-ORCHESTRATION-SPEC.md")
    required_ids = (
        [f"ARCH-0{i}" for i in range(1, 5)]
        + [f"RT-0{i}" for i in range(1, 8)]
        + [f"ISO-0{i}" for i in range(1, 7)]
        + [f"SEC-{i:02d}" for i in range(1, 11)]
        + [f"QA-0{i}" for i in range(1, 5)]
        + [f"PROT-0{i}" for i in range(1, 4)]
        + [f"ADP-0{i}" for i in range(1, 4)]
        + [f"CFG-0{i}" for i in range(1, 3)]
        + [f"LC-0{i}" for i in range(1, 5)]
    )
    absent = [i for i in required_ids if i not in spec]
    record("CHK-11", not absent, f"missing requirement IDs: {absent}" if absent
           else f"all {len(required_ids)} requirement IDs defined in the spec")

    # CHK-12 adapter documentation completeness
    problems = []
    for a in ADAPTERS:
        text = read(f"adapters/{a}/README.md")
        for i, section in enumerate(ADAPTER_SECTIONS, 1):
            if f"## {i}. {section}" not in text:
                problems.append(f"{a}: missing section {i} {section}")
        profile = rk.load_yaml(f"adapters/{a}/PROFILE.yaml")
        if profile.get("schema") != "adapter_profile":
            problems.append(f"{a}: PROFILE schema mismatch")
        caps = profile.get("capabilities", {})
        for key in PROFILE_KEYS:
            if key not in caps:
                problems.append(f"{a}: PROFILE missing {key}")
            elif caps[key].get("status") not in STATUSES:
                problems.append(f"{a}: {key} bad status")
    record("CHK-12", not problems, "; ".join(problems) if problems
           else "all 5 adapters: 13 required sections + valid capability profiles")

    # CHK-13 acceptance criteria + scenario traceability
    problems = []
    ac = read("validation/ACCEPTANCE-CRITERIA.md")
    for i in range(1, 14):
        if f"AC-{i:02d}" not in ac:
            problems.append(f"AC-{i:02d} missing")
    ct = read("validation/COMPATIBILITY-TESTS.md")
    fx = rk.load_yaml("validation/fixtures/tasks.yaml")
    fx_ids = {s["id"] for s in fx["scenarios"]}
    for i in range(1, 14):
        tid = f"TS-{i:02d}"
        if tid not in ct:
            problems.append(f"{tid} missing in COMPATIBILITY-TESTS.md")
        if tid not in fx_ids:
            problems.append(f"{tid} missing in fixtures")
    record("CHK-13", not problems, "; ".join(problems) if problems
           else "AC-01..13 and TS-01..13 fully traceable")

    # CHK-14 secret scan across all kit text files
    hits = []
    for f in sorted(ROOT.rglob("*")):
        if f.is_file() and f.suffix in {".md", ".yaml", ".py"}:
            found = rk.scan_secrets(f.read_text(encoding="utf-8"))
            if found:
                hits.append(f"{f.relative_to(ROOT)}: {len(found)} hit(s)")
    record("CHK-14", not hits, "; ".join(hits) if hits
           else "no secret-like content in any kit file")

    # CHK-15 version header consistency
    problems = []
    for md in sorted(ROOT.rglob("*.md")):
        if "Kit version: 1.0.0" not in md.read_text(encoding="utf-8"):
            problems.append(str(md.relative_to(ROOT)))
    record("CHK-15", not problems, f"missing version header: {problems}" if problems
           else "all markdown documents carry the kit version header")

    # CHK-16 isolation/security mandatory language present where required
    problems = []
    handoff = read("protocols/HANDOFF-CONTRACT.md")
    for token in ("ISO-02", "ISO-04", "ISO-05", "SEC-03", "redaction"):
        if token not in handoff:
            problems.append(f"HANDOFF-CONTRACT missing {token}")
    gates = read("core/QUALITY-GATES.md")
    for token in ("SEC-07", "SEC-10", "QA-01", "G1", "G2", "G3", "G4"):
        if token not in gates:
            problems.append(f"QUALITY-GATES missing {token}")
    record("CHK-16", not problems, "; ".join(problems) if problems
           else "isolation and security requirements enforced in contracts and gates")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"self_test: {passed}/{len(RESULTS)} checks passed")
    for cid, ok, detail in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'} {cid}: {detail}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())