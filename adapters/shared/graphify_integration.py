#!/usr/bin/env python3
"""Graphify context-graph integration for UOK installers (release 1.1.0, spec 1.0.0).

Optional, additive, fail-open: the kit installs and works without Graphify.
Community integration - not affiliated with or endorsed by Graphify Labs.
Graphify is Apache-2.0 (github.com/Graphify-Labs/graphify); the kit invokes its CLI
(PyPI package `graphifyy`, double-y) and never vendors its code. Rules: core/CONTEXT-GRAPH.md.

Modes (--graphify): install (default of `uok init`: fetch the CLI via uv/pipx if missing) |
auto (default of a direct installer run and of refresh: PATH only, no network) | off. When enabled: project-scoped host skill
(soft hooks, never --strict), .graphifyignore aligned with G1 secret globs (CG-05),
code-only offline graph (GRAPHIFY_BACKEND=none), policy/graphify.yaml, and `context_graph`
in the adapter yaml read by g1_guard.py. Every claim carries an honest verification status.
"""
import datetime, json, os, re, shutil, subprocess

HOST_PLATFORM = {"claude-code": "claude", "codex": "codex", "cursor": "cursor", "qoder": None}
HOST_SKILL_PARENT = {"claude-code": ".claude/skills", "qoder": ".qoder/skills",
                     "cursor": ".cursor/skills", "codex": ".agents/skills"}
IGNORE_BEGIN, IGNORE_END = "# UOK:BEGIN graphify", "# UOK:END graphify"
# Mirrors g1_guard.DENIED_GLOBS (SEC-02 / CG-05): secret-bearing names must never be indexed.
SECRET_IGNORE = [".env", ".env.*", "*credentials*", "*secret*", "*.pem", "*.key", "*.p12", "*.pfx",
                 "id_rsa*", "id_ed25519*", "id_ecdsa*", "id_dsa*", ".ssh/", ".aws/", ".gnupg/", ".kube/",
                 ".netrc", ".npmrc", ".pypirc", ".docker/", "hosts.yml"]
EXTRA_IGNORE = [".orchestrator/", "graphify-out/", ".git/"]


def _run(cmd, cwd, timeout):
    env = dict(os.environ, GRAPHIFY_BACKEND="none")   # CG-05: no LLM backend, code-only, offline
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as ex:
        return 1, str(ex)


def find_cli():
    exe = shutil.which("graphify")
    if exe:
        return exe
    cand = os.path.expanduser("~/.local/bin/graphify")   # uv/pipx default target, may be off PATH
    return cand if os.path.isfile(cand) and os.access(cand, os.X_OK) else None


def probe_version(exe):
    rc, out = _run([exe, "--version"], os.getcwd(), 30)
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out) if rc == 0 else None
    return ".".join(m.groups()) if m else "unknown"


def fetch_cli(inst):
    """--graphify install only: uv first, then pipx. Never pip into the system environment."""
    for tool, cmd in (("uv", ["uv", "tool", "install", "graphifyy"]),
                      ("pipx", ["pipx", "install", "graphifyy"])):
        if shutil.which(tool):
            inst.changes.append(f"install graphify CLI via {tool} (network, user-level, reversible)")
            rc, out = _run(cmd, inst.root, 600)
            if rc != 0:
                inst.warnings.append(f"graphify CLI install via {tool} failed: {out[-200:]}")
                continue
            exe = find_cli()
            if exe:
                if not shutil.which("graphify"):
                    inst.warnings.append("graphify installed to ~/.local/bin which is not on PATH; "
                                         "run `uv tool update-shell` and restart the session")
                return exe
    return None


def install_skill(inst, exe):
    """Project-scoped skill, soft hooks only (never --strict: it would deny worker Read/Grep)."""
    host = getattr(inst, "HOST", "claude-code")   # FIX: standalone claude-code installer has no HOST attr
    cmds = []
    if HOST_PLATFORM.get(host):
        cmds.append([exe, HOST_PLATFORM[host], "install", "--project"])
    cmds.append([exe, "install", "--project", "--platform", "agents"])   # cross-framework fallback
    for cmd in cmds:
        rc, out = _run(cmd, inst.root, 180)
        if rc == 0:
            src, dst = inst.p(".agents", "skills", "graphify"), inst.p(HOST_SKILL_PARENT[host], "graphify")
            if host != "codex" and os.path.isdir(src) and not os.path.isdir(dst):
                shutil.copytree(src, dst)   # qoder/cursor: host reads its own skills dir
                inst.changes.append(f"create {HOST_SKILL_PARENT[host]}/graphify/ (copied from .agents/skills)")
            inst.changes.append(f"graphify skill installed ({' '.join(cmd[1:])})")
            return True
    inst.warnings.append("graphify skill install failed; graph queries still work via the CLI and UOK rules")
    return False


def write_ignore(inst):
    path = inst.p(".graphifyignore")
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    block = "\n".join([IGNORE_BEGIN] + SECRET_IGNORE + EXTRA_IGNORE + [IGNORE_END])
    if IGNORE_BEGIN in old and IGNORE_END in old:
        i, j = old.index(IGNORE_BEGIN), old.index(IGNORE_END) + len(IGNORE_END)
        new = old[:i] + block + old[j:]
    else:
        new = (old.rstrip("\n") + "\n\n" if old.strip() else "") + block
    inst.write(path, new if new.endswith("\n") else new + "\n",
               "graphify ignore aligned with G1 secret globs (CG-05)")


def build_graph(inst, exe):
    graph = inst.p("graphify-out", "graph.json")
    if inst.dry:
        inst.changes.append("build/update graphify-out/graph.json (code-only, offline)")
        return None
    cmd = [exe, "update", "."] if os.path.exists(graph) else [exe, "extract", ".", "--code-only"]
    rc, out = _run(cmd, inst.root, 900)
    if rc != 0 or not os.path.exists(graph):
        inst.degradations.append(f"degraded_context_graph: graph build failed ({out[-160:]}); kit works without it")
        return None
    return graph


def graph_meta(graph):
    try:
        if os.path.getsize(graph) > 100_000_000:
            return {}, 0
        data = json.load(open(graph, encoding="utf-8"))
        g = data.get("graph", {}) if isinstance(data, dict) else {}
        return g, len(data.get("nodes", [])) if isinstance(data, dict) else 0
    except (OSError, ValueError):
        return {}, 0


def write_policy(inst, enabled, ver, meta, nodes, planned=False):
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    verification = "not_executed" if planned or not enabled else "verified_local"
    text = ("# Graphify context-graph integration (core/CONTEXT-GRAPH.md, CG-01..07).\n"
            "# Written by the installer; uok-* workers cannot write this file.\n"
            f"enabled: {'true' if enabled else 'false'}\n"
            "mode: code-only            # GRAPHIFY_BACKEND=none: no LLM, no network for code\n"
            f"cli_version: \"{ver or 'unknown'}\"\n"
            "graph: graphify-out/graph.json\n"
            f"schema_version: {meta.get('schema_version', 'unknown')}\n"
            f"nodes: {nodes}\n"
            f"built_at: \"{ts}\"\n"
            f"verification: {verification}"
            "   # build executed here; live skill invocation in the host is unverified\n")
    inst.write(inst.p(".orchestrator", "policy", "graphify.yaml"), text, "context-graph policy (CG-07)")


def add_gitignore(inst):
    path = inst.p(".gitignore")
    old = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []
    new = list(dict.fromkeys(old + ["graphify-out/"]))
    if new != old:
        inst.write(path, "\n".join(new) + "\n", "ignore the generated context graph")


def graph_rule(inst):
    """One instruction-section bullet, shared by every adapter (only when enabled)."""
    return ("- Context graph (Graphify, community integration): orient with `graphify query/path/explain` "
            "before broad file reads (CG-01); derive write claims from the impact subgraph (CG-02); "
            "stale graph => main session runs `graphify update .` or reports `degraded_context_graph` (CG-03). "
            "Workers never rebuild the graph (CG-04); strict-mode workers query via "
            "`python3 -I {root}/.orchestrator/hooks/uok_graph.py query|path|explain|section ...`. "
            f"Rules: `{inst.kit_rel}/core/CONTEXT-GRAPH.md`.")


def skill_paragraph(kit_rel):
    return ("Context graph (Graphify, optional): if `.orchestrator/policy/graphify.yaml` has `enabled: true`, "
            "orient with `graphify query/path/explain` before broad file reads (CG-01); derive write claims "
            "from the impact subgraph (CG-02); a stale graph means `graphify update .` in the main session "
            "or an honest `degraded_context_graph` flag (CG-03). Workers never rebuild the graph (CG-04); "
            "in strict mode they query via `.orchestrator/hooks/uok_graph.py`. "
            f"Rules: `{kit_rel}/core/CONTEXT-GRAPH.md`.\n\n")


def apply(inst):
    """Installer step. Sets inst.context_graph for adapter.yaml; fail-open on every failure."""
    inst.context_graph = "none"
    mode = getattr(inst, "graphify", "auto")
    if mode == "off":
        inst.kept.append("graphify integration skipped (--graphify off)")
        return
    exe = find_cli()
    if inst.dry:
        write_ignore(inst)
        if exe:
            inst.changes.append("graphify: install host skill (project, soft hooks), build code-only graph (offline)")
            inst.context_graph = "graphify"
        elif mode == "install":
            inst.changes.append("graphify: CLI not on PATH - will FETCH `graphifyy` via uv/pipx "
                                "(network, user-level; skip with --graphify off)")
        else:
            inst.changes.append("graphify: CLI not on PATH - would record degraded_context_graph (auto: no network)")
        write_policy(inst, bool(exe), None, {}, 0, planned=True)
        return
    ver = probe_version(exe) if exe else None
    if not exe and mode == "install":
        exe = fetch_cli(inst)
        ver = probe_version(exe) if exe else None
    write_ignore(inst)
    if not exe:
        inst.degradations.append("degraded_context_graph: graphify CLI not found; run "
                                 "`uv tool install graphifyy` (or pipx) then `uok refresh`, "
                                 "or `uok init --graphify install`")
        write_policy(inst, False, None, {}, 0)
        return
    install_skill(inst, exe)
    graph = build_graph(inst, exe)
    enabled = graph is not None
    meta, nodes = graph_meta(graph) if enabled else ({}, 0)
    write_policy(inst, enabled, ver, meta, nodes)
    if enabled:
        inst.context_graph = "graphify"
        add_gitignore(inst)
        inst.graphify_results.append(f"context graph ({nodes} nodes, schema "
                                     f"{meta.get('schema_version', '?')}, graphify {ver}): PASS")
