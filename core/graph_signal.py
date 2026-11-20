#!/usr/bin/env python3
"""Deterministic context-graph impact signal for graph-aware routing (CG-06).

Kit version: 1.0.0 · Release 1.2.0. Pure stdlib, no network, no LLM. Reads a
Graphify graph.json and the task's write claims, and returns metrics the routing
policy (core/routing-policy.yaml `graph_impact`) turns into a tier delta. The
extractor only MEASURES; the router applies thresholds and the TIER-3 cap, so the
single source of truth for the bump stays in the versioned policy.

Fail-open: a malformed/absent graph yields status "unavailable" (no bump); a stale
graph yields "stale" (no bump); claims matching no indexed node yield
"no_touched_nodes" (no bump). Every result carries provenance (schema_version,
graphify_version) so the decision record can cite it honestly (CG-07).
"""
import fnmatch, json, os

MAX_GRAPH_BYTES = 100_000_000


def load_graph(path):
    """Parse graph.json defensively; return a dict or None (never raise)."""
    try:
        if os.path.getsize(path) > MAX_GRAPH_BYTES:
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def is_stale(graph_path, source_paths):
    """True if any listed source file is newer than the graph build (CG-03)."""
    try:
        gm = os.path.getmtime(graph_path)
    except OSError:
        return True
    return any(os.path.exists(p) and os.path.getmtime(p) > gm for p in source_paths)


def _node_file(node):
    for key in ("source_file", "file", "path"):
        v = node.get(key)
        if isinstance(v, str) and v:
            return v.replace("\\", "/")
    return None


def _community(node):
    return node.get("community", node.get("community_id"))


def compute_signal(graph, write_globs, stale=False):
    """Metrics for the nodes touched by write_globs plus their 1-hop impact.

    Returns a dict: status, max_degree, community_spread, impact_files,
    touched_nodes, schema_version, graphify_version. `status` is one of
    ok | stale | unavailable | no_touched_nodes. The router decides the bump.
    """
    g = graph.get("graph", {}) if isinstance(graph, dict) else {}
    prov = {"schema_version": g.get("schema_version", "unknown") if isinstance(g, dict) else "unknown",
            "graphify_version": g.get("graphify_version", "unknown") if isinstance(g, dict) else "unknown"}
    zero = {"max_degree": 0, "community_spread": 0, "impact_files": 0, "touched_nodes": 0, **prov}
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
        return {"status": "unavailable", **zero}
    if stale:
        return {"status": "stale", **zero}
    nodes = [n for n in graph["nodes"] if isinstance(n, dict)]
    # Real Graphify graph.json uses networkx-style "links"; the reference kernel and the
    # synthetic test graphs use "edges". Accept both so the signal works on real graphs.
    edges = [e for e in (graph.get("edges") or graph.get("links") or []) if isinstance(e, dict)]
    by_id = {n.get("id"): n for n in nodes if n.get("id") is not None}
    deg = {}
    for e in edges:
        for end in (e.get("source"), e.get("target")):
            if end is not None:
                deg[end] = deg.get(end, 0) + 1
    def degree(n):
        d = n.get("degree")
        return d if isinstance(d, int) else deg.get(n.get("id"), 0)
    globs = [g for g in (write_globs or []) if isinstance(g, str) and g]
    touched = []
    for n in nodes:
        f = _node_file(n)
        if f and any(fnmatch.fnmatch(f, gl) or f == gl for gl in globs):
            touched.append(n)
    if not touched:
        return {"status": "no_touched_nodes", **zero}
    touched_ids = {n.get("id") for n in touched}
    impact_ids = set(touched_ids)
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in touched_ids and t is not None:
            impact_ids.add(t)
        if t in touched_ids and s is not None:
            impact_ids.add(s)
    impact_nodes = [by_id[i] for i in impact_ids if i in by_id]
    files = {_node_file(n) for n in impact_nodes if _node_file(n)}
    communities = {_community(n) for n in impact_nodes if _community(n) is not None}
    return {"status": "ok", "max_degree": max((degree(n) for n in touched), default=0),
            "community_spread": len(communities), "impact_files": len(files),
            "touched_nodes": len(touched), **prov}
