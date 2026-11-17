#!/usr/bin/env python3
"""Safe code search for uok-* agents (Universal Orchestrator Kit, Claude Code adapter).

Usage:  python3 -I <project root>/.orchestrator/hooks/uok_search.py PATTERN [RELATIVE_DIR]

The restricted shell gives uok-* agents no grep/cat. This script is the allowlisted
replacement: it searches only inside the project root, never follows symlinks out of
it, and skips every secret-bearing name the G1 guard denies (it imports the guard's
own DENIED_GLOBS, so the two cannot drift). PATTERN is a Python regex limited by the
guard to the restricted-shell character set (letters, digits, _ . / : @ % + , = - space).
Output: path:line:text, at most 200 matches; long lines are truncated.
"""
import os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
# Project root = two levels above .orchestrator/hooks/, independent of cwd or environment.
os.environ["CLAUDE_PROJECT_DIR"] = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import g1_guard as g  # noqa: E402  (same protected directory)

MAX_MATCHES, MAX_LINE, MAX_FILE = 200, 300, 2_000_000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
SKIP_REL = ("./.orchestrator/audit", "./.orchestrator/claims")   # audit log holds command fragments (R3)
MAX_SCAN_LINE = 10_000                                            # bound regex work per line (R4)


def main(argv):
    if not 1 <= len(argv) <= 2:
        print(__doc__.strip().splitlines()[2]); return 2
    root = g.REAL_ROOT
    if len(argv) == 2 and not argv[1].isascii():
        print("refused: non-ASCII directory"); return 2
    if argv[0].count("+") > 1 or len(argv[0]) > 200:   # bound backtracking (security review round 6)
        print("refused: pattern may contain at most one '+' and 200 characters"); return 2
    try:
        rx = re.compile(argv[0])
    except re.error as e:
        print(f"bad pattern: {e}"); return 2
    start = g.resolve(os.path.join(root, argv[1])) if len(argv) == 2 else root
    start_rel = os.path.relpath(start, root).lower() + "/"
    if not (start == root or start.startswith(root + os.sep)) or g.denied_path(start) \
            or any(start_rel.startswith(p) for p in g.NO_READ_FOR_UOK) \
            or any(part in SKIP_DIRS for part in start_rel.split("/")):
        print("refused: directory outside project root or secret-bearing"); return 2
    n = 0
    for d, dirs, files in os.walk(start, followlinks=False):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not g.denied_path(os.path.join(d, x))
                         and not ("./" + os.path.relpath(os.path.join(d, x), root)).startswith(SKIP_REL))
        for f in sorted(files):
            path = os.path.join(d, f)
            real = os.path.realpath(path)
            real_rel = os.path.relpath(real, root).lower() + "/"
            if g.denied_path(path) or not (real.startswith(root + os.sep)) \
                    or any(real_rel.startswith(p) for p in g.NO_READ_FOR_UOK):
                continue
            try:
                if os.path.getsize(real) > MAX_FILE:
                    continue
                with open(real, encoding="utf-8", errors="strict") as fh:
                    for i, line in enumerate(fh, 1):
                        if len(line) <= MAX_SCAN_LINE and rx.search(line):
                            print(f"{os.path.relpath(path, root)}:{i}:{line.rstrip()[:MAX_LINE]}")
                            n += 1
                            if n >= MAX_MATCHES:
                                print("... truncated at 200 matches"); return 0
            except (OSError, UnicodeDecodeError):
                continue
    if n == 0:
        print("no matches")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
