# Context Graph (Graphify) — optional kit extension

Kit version: 1.0.0 · Release 1.2.0 (additive extension; the core spec is unchanged).
Status: `verified_local` (installer + hook tests). Live skill invocation inside each host:
`unverified` until the checks below are run and reported.

Community integration — **not affiliated with or endorsed by Graphify Labs**.
Graphify (github.com/Graphify-Labs/graphify) is Apache-2.0; the kit invokes its CLI
(PyPI `graphifyy`, double-y) and vendors none of its code. "graphify" is a mark of Graphify Labs.

The graph is shared, read-only project memory: code parsed locally with tree-sitter,
every edge tagged `EXTRACTED` or `INFERRED`. The kit stays fully functional without it
(fail-open; the degradation is reported honestly as `degraded_context_graph`).

## Rules

- **CG-01 — Graph-first orientation.** When `.orchestrator/policy/graphify.yaml` has
  `enabled: true`, the orchestrator and roles orient with `graphify query`, `graphify path A B`,
  `graphify explain X` before broad file reads. The context envelope is built from the scoped
  subgraph, not from grep sweeps. `INFERRED` edges are leads, not evidence: confirm them in
  the source before claiming them (the kit's `verified_*` statuses apply).
- **CG-02 — Claims from impact.** Write claims (LC-04) are derived from the impact subgraph
  of the change (`graphify query`/`path` around the touched nodes), not guessed from file
  names. The graph output used is recorded with the task as evidence.
- **CG-03 — Freshness.** A stale graph (`needs_update`, or files changed since `built_at`)
  must be refreshed by the MAIN session (`graphify update .`) before routing/claims rely on
  it, or the task reports `degraded_context_graph`. Never route or claim on a stale graph silently.
- **CG-04 — Workers are read-only on the graph.** `uok-*` agents may only query/path/explain/section.
  G1 denies every mutating graphify subcommand (extract/update/install/hook/add/merge-graphs/
  label/watch/serve) for workers and protects `graphify-out/`, `.graphifyrc`, `.graphifyignore`
  from worker writes. Strict-mode workers use `.orchestrator/hooks/uok_graph.py` (no quotes,
  no options, fixed graph and backend).
- **CG-05 — Secrets never enter the graph.** `.graphifyignore` mirrors the G1 `DENIED_GLOBS`
  (marked UOK block, maintained by the installer). Builds are code-only and offline:
  `GRAPHIFY_BACKEND=none`, `--code-only`. No docs/PDF/media semantic pass without explicit
  human approval (it would call an LLM backend).
- **CG-06 — Graph impact modifier (formal).** Graph metrics feed the `graph_impact`
  complexity modifier in `core/routing-policy.yaml` (policy_version 1.1.0): when the
  signal is fresh and a touched node is a god node (degree >= god_node_degree) or the
  1-hop impact crosses >= community_spread communities or >= impact_files files, the tier
  delta gains +1 — under the SAME TIER-3 modifier cap as other modifiers. No new hard
  floors; TIER-5 stays review-only. Stale/unavailable signal adds 0 and is flagged
  (`graph_signal_stale` / `graph_signal_unavailable`); absent signal adds 0 silently.
  Metrics are computed by `core/graph_signal.py` and recorded in the routing decision.
- **CG-07 — Honesty and provenance.** `policy/graphify.yaml` records `cli_version`,
  `schema_version`, `nodes`, `built_at`, `verification`. The installer never claims live
  host behaviour it did not observe. Graphify releases frequently (0.9.x): the recorded
  version is the one actually probed; upgrades are a human decision
  (`uv tool upgrade graphifyy`, then `uok refresh`).

## Install / opt-out

    uok init                      # auto: integrate if the graphify CLI is on PATH (no network)
    uok init --graphify install   # also fetch the CLI via uv/pipx (the /uok-init skill uses this)
    uok init --graphify off       # skip the integration entirely
    uv tool install graphifyy     # manual CLI install (Python >= 3.11; uv manages its own)
    graphify hook install         # optional: auto-rebuild on commit/checkout (human choice)

The kit itself still requires only Python >= 3.10 + PyYAML. Graphify needs Python >= 3.11
(0.9.111+); uv/pipx provide an isolated interpreter, so the kit's floor is unchanged.

## Live checks (run in the host, then report)

1. `/uok-init` (Codex: `$uok-init`) in a scratch project with the CLI installed: the
   `/graphify` skill (Codex: `$graphify`) is present, `graphify-out/graph.json` built,
   no `--strict` graphify hook installed.
2. `/uok research-analyst explain how module X works`: the role queries the graph before
   reading files; the report cites graph output.
3. A worker attempts `graphify extract .` -> G1 denies (CG-04). A worker writes
   `graphify-out/graph.json` -> G1 denies. A worker writes `.graphifyignore` -> G1 denies.
4. Strict mode: worker runs `python3 -I <root>/.orchestrator/hooks/uok_graph.py query <words>`
   -> allowed; `graphify query "x"` (quotes) -> denied by the restricted shell.
5. Delete a source file, then route a task: the orchestrator notices staleness and updates
   the graph or flags `degraded_context_graph` (CG-03).
