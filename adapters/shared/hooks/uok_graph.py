#!/usr/bin/env python3
"""Read-only context-graph queries for uok-* agents (Universal Orchestrator Kit).

Usage: python3 -I <root>/.orchestrator/hooks/uok_graph.py query|path|explain|section WORDS...

The restricted shell forbids quotes, so `graphify query "..."` cannot be allowlisted.
This wrapper is the allowlisted replacement (CG-04): it joins plain words into the
question, accepts ONLY read-only subcommands, rejects every option (no --graph, no
--backend: the graph and backend are fixed), and runs the graphify CLI without a shell,
offline (GRAPHIFY_BACKEND=none), query logging disabled. `path` takes exactly two node
names. Output is bounded. Fail-closed: no CLI / no graph => exit 2.
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
os.environ["CLAUDE_PROJECT_DIR"] = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import g1_guard as g  # noqa: E402  (same protected directory; root resolution cannot drift)

READ_ONLY = {"query", "explain", "section", "path"}
MAX_WORDS, MAX_OUT, TIMEOUT = 400, 20000, 60


def main(argv):
    if not argv or argv[0] not in READ_ONLY:
        print("refused: only query|path|explain|section are available to workers (CG-04)"); return 2
    args = argv[1:]
    if not args or any(a.startswith("-") for a in args):
        print("refused: options are not allowed; the graph and backend are fixed"); return 2
    if argv[0] == "path" and len(args) != 2:
        print("refused: path takes exactly two node names"); return 2
    question = " ".join(args)
    if len(question) > MAX_WORDS or not question.isascii():
        print("refused: question too long or non-ASCII"); return 2
    exe = shutil.which("graphify")
    graph = os.path.join(g.REAL_ROOT, "graphify-out", "graph.json")
    if not exe or not os.path.isfile(graph):
        print("context graph unavailable; ask the orchestrator to build it (graphify extract . --code-only)"); return 2
    env = dict(os.environ, GRAPHIFY_BACKEND="none", GRAPHIFY_QUERY_LOG_DISABLE="1")
    try:
        r = subprocess.run([exe, argv[0], *args], cwd=g.REAL_ROOT, capture_output=True,
                           text=True, timeout=TIMEOUT, env=env)
    except (OSError, subprocess.TimeoutExpired) as ex:
        print(f"graph query failed: {ex}"); return 2
    out = ((r.stdout or "") + (r.stderr or ""))[:MAX_OUT]
    print(out.rstrip() or "(empty answer)")
    return 0 if r.returncode == 0 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
