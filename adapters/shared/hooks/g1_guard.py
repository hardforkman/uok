#!/usr/bin/env python3
"""G1 pre-dispatch guard (Universal Orchestrator Kit, Claude Code adapter).

PreToolUse hook. Reads the hook JSON on stdin and:
  - DENIES access to secret-bearing paths (.env*, *credentials*, *secret*, ...) (SEC-02),
  - DENIES writes outside the project root (ISO-02),
  - DENIES writes / MCP payloads with secret-like content (SEC-03),
  - DENIES writes outside the caller's claim or inside another writer's claim (LC-04),
  - DENIES uok-* writes to the guard's own controls (.claude/, .git/, .orchestrator/, CLAUDE.md, kit validation/),
  - in `enforcement: strict` only: sandboxes uok-* workers (exact shell allowlist, no Grep/Glob/MCP,
    no reads outside the root) (SEC-04),
  - ASKS the human for sensitive shell operations (SEC-07).
Malformed input for non-security-relevant tools fails open (logged);
security-relevant tools (writes, MCP, uok-* Bash) fail closed.
Every decision is logged to .orchestrator/audit/g1.log.
"""
import fnmatch, functools, json, os, re, sys, time

def _project_root():
    """Project root, independent of the host application: an explicit env var if the host sets one,
    else the directory two levels above this file when installed as <root>/.orchestrator/hooks/,
    else the working directory."""
    for var in ("UOK_PROJECT_DIR", "CLAUDE_PROJECT_DIR", "QODER_PROJECT_DIR", "CURSOR_PROJECT_DIR"):
        if os.environ.get(var):
            return os.environ[var]
    here = os.path.dirname(os.path.realpath(__file__))
    if here.endswith(os.sep + os.path.join(".orchestrator", "hooks")):
        return os.path.dirname(os.path.dirname(here))
    return os.getcwd()


# Host event/decision format: claude (default) | qoder | cursor | codex  (`--format X` on the command line).
FORMAT = sys.argv[sys.argv.index("--format") + 1] if "--format" in sys.argv[:-1] else "claude"
ROOT = _project_root()
REAL_ROOT = os.path.realpath(ROOT)  # canonicalised below, after canonical() is defined
AUDIT = os.path.join(ROOT, ".orchestrator", "audit", "g1.log")
DENIED_GLOBS = [".env", ".env.*", "*credentials*", "*secret*", "*.pem", "*.key", "*.p12", "*.pfx",
                "id_rsa*", "id_ed25519*", "id_ecdsa*", "id_dsa*", ".ssh", ".aws", ".gnupg", ".kube",
                ".netrc", ".npmrc", ".pypirc", ".docker", "hosts.yml"]
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_\-]{16,}",
    r"AKIA[0-9A-Z]{16}",
    r"gh[pousr]_[A-Za-z0-9]{36,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}",
]
# Sensitive shell operations (SEC-07). Detection is token-based per segment, linear in the
# command length: no backtracking regex runs on attacker-controlled input (round 4, N1).
MAX_INSPECT_CMD = 20000
MAX_PATH_LEN, MAX_PATH_PARTS = 4096, 256
# possessive-free but linear: the cluster is a single [A-Za-z]{0,40} run between fixed letters
RM_CLUSTER = re.compile(r"\brm\s+-[A-Za-z]{0,40}?(?:[rR][A-Za-z]{0,40}?f|f[A-Za-z]{0,40}?[rR])")
DROP_SQL = re.compile(r"(?i)\bDROP\s+(TABLE|DATABASE)\b")   # no nested/adjacent unbounded quantifiers
WRAPPERS = {"sudo", "command", "exec", "nohup", "time", "env", "xargs", "doas", "nice", "timeout"}
KEYWORDS = {"then", "do", "else", "elif", "!", "if", "while", "until"}
SQL_CLIENTS = {"psql", "mysql", "sqlite3", "mariadb", "clickhouse-client", "sqlcmd", "duckdb"}


def _short_flags(tokens):
    return "".join(t[1:] for t in tokens if t.startswith("-") and not t.startswith("--"))


def sensitive_segment(seg):
    """Return the SEC-07 operation a single shell segment performs, judged by its leading verb."""
    tokens = seg.replace("(", " ").replace(")", " ").replace("{", " ").replace("}", " ").split()
    i, n = 0, len(tokens)
    while i < n:   # index walk, linear (round 5, R-a)
        t = tokens[i]
        if t in KEYWORDS or t in WRAPPERS or ("=" in t and not t.startswith("-")):
            i += 1
            if t in WRAPPERS:   # skip the wrapper's own options, e.g. `sudo -u root`, `env -i`, `xargs -n1`
                while i < n and tokens[i].startswith("-"):
                    i += 2 if tokens[i] in ("-u", "-g", "-n", "-I", "-L", "-P", "-C") and i + 1 < n else 1
            continue
        break
    tokens = tokens[i:]
    if not tokens:
        return None
    verb, args = os.path.basename(tokens[0]), tokens[1:]
    if verb == "git":   # skip git global options (`git -C dir push`, `git -c k=v push`)
        j = 0
        while j < len(args) and args[j].startswith("-"):
            j += 2 if args[j] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") and j + 1 < len(args) else 1
        args = args[j:]
    longs, shorts = set(a for a in args if a.startswith("--")), _short_flags(args)
    if verb == "rm" and ("r" in shorts or "R" in shorts or "--recursive" in longs) \
            and ("f" in shorts or "--force" in longs):
        return "irreversible_data_change"
    if verb == "git" and args:
        sub = args[0]
        if sub == "push" and ("f" in _short_flags(args[1:]) or "d" in _short_flags(args[1:])
                              or any(a.startswith(("--force", "--mirror", "--delete", "--prune")) for a in args)
                              or any(a.startswith("+") or a.startswith(":") for a in args[1:])):
            return "irreversible_data_change"
        if sub == "worktree" and args[1:2] == ["remove"] and ("--force" in longs or "f" in shorts):
            return "irreversible_data_change"
        if sub in ("reset", "clean") and ("--hard" in longs or ("f" in shorts and sub == "clean")):
            return "irreversible_data_change"
    if verb in ("kubectl", "terraform", "helm") and args[:1] and args[0] in ("apply", "destroy", "delete"):
        return "destructive_infra_change"
    if (verb in ("npm", "yarn", "pnpm") and args[:1] == ["publish"]) or (verb == "twine" and args[:1] == ["upload"]) \
            or (verb == "gh" and args[:2] == ["release", "create"]):
        return "unauthorized_external_publication"
    if (verb == "vercel" and "--prod" in longs) or (verb == "fly" and args[:1] == ["deploy"]) \
            or (verb == "npm" and args[:2] in (["run", "deploy"], ["run", "deploy:prod"])):
        return "production_deploy"
    if verb in SQL_CLIENTS and DROP_SQL.search(seg):   # verb position only (round 5, F4)
        return "irreversible_data_change"
    return None


def sensitive_op(cmd, raw_fallback=True):
    """Returns (operation, by_verb). by_verb=False means only the raw-text fallback matched."""
    for seg in segments(cmd):
        op = sensitive_segment(seg)
        if op:
            return op, True
    if not raw_fallback:   # strict uok-* commands cannot contain quotes; the raw scan would only add false asks
        return None, False
    # Main-session commands may hide the verb inside quotes or `bash -c`; scan once more with a
    # linear single-cluster rm pattern on the raw text (bounded by MAX_INSPECT_CMD).
    # Unquoted commands are fully covered by the per-segment verb check above; the raw-text
    # fallback is only needed when a verb can hide inside quotes or an interpreter's -c string.
    if RM_CLUSTER.search(cmd) or DROP_SQL.search(cmd):
        return "irreversible_data_change", False
    for m in re.finditer(r"\bgit\s+push\b", cmd):   # bounded window per occurrence: O(n * 400)
        window = re.split(r"[;&|\n'\"]", cmd[m.end():m.end() + 400], maxsplit=1)[0]
        if any(t.startswith("--force") or (t.startswith("-") and not t.startswith("--") and "f" in t)
               for t in window.split()):
            return "irreversible_data_change", False
    return None, False



WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
READ_TOOLS = ("Read", "Grep", "Glob")
PATH_TOOLS = READ_TOOLS + WRITE_TOOLS
PATH_KEYS = ("file_path", "notebook_path", "path")
CONTENT_KEYS = ("content", "new_string", "new_source", "edits")
# Guard controls that uok-* agents may never write, claims or not (M4).
# Compared case-insensitively (APFS is case-insensitive; NB3). The whole .orchestrator/ tree is
# protected (hooks, policy, claims, audit log; N6), and so is every directory holding an
# allowlisted script, so a writer cannot plant code that the restricted shell will run (NB4).
def _cfg(key, default):
    """Scalar `key: value` from .orchestrator/policy/adapter.yaml, or claude-code.yaml (no PyYAML dependency)."""
    for name in ("adapter.yaml", "claude-code.yaml"):
        try:
            for ln in open(os.path.join(ROOT, ".orchestrator", "policy", name)):
                m = re.match(r"\s*" + re.escape(key) + r":\s*\"?([^\"#\n]+?)\"?\s*(#.*)?$", ln)
                if m:
                    return m.group(1).strip()
        except OSError:
            continue
    return default


# enforcement: standard (default) = base protections for everyone + guard-control and claim checks
# for uok-* workers; strict = additionally sandboxes uok-* workers (exact shell allowlist, no
# Grep/Glob/MCP, no reads outside the root, ASCII paths, fail closed on any hook error).
STRICT = _cfg("enforcement", "standard").lower() == "strict"
# Where the kit lives relative to the project root (set by the installer); its code is write-protected.
KIT_DIR = _cfg("kit_dir", "UNIVERSAL-ORCHESTRATOR-KIT").strip("/").lower()
PROTECTED = (".claude/", ".qoder/", ".cursor/", ".codex/", ".git/", ".orchestrator/", "claude.md", "claude.local.md",
             "agents.md", "agents.local.md", ".mcp.json", ".gitignore") \
    + (() if os.path.isabs(KIT_DIR) or KIT_DIR.startswith("..") else
       (KIT_DIR + "/validation/", KIT_DIR + "/core/", KIT_DIR + "/adapters/"))
# File names protected at any depth (nested CLAUDE.md files are loaded as instructions; round 6, item 3).
PROTECTED_NAMES = ("claude.md", "claude.local.md", "agents.md", "agents.local.md", ".mcp.json", "settings.json",
                   "settings.local.json", "hooks.json")
NO_READ_FOR_UOK = (".orchestrator/audit/", ".orchestrator/claims/", ".git/")
# Roles whose AGENT-CAPABILITIES permissions say sensitive_ops: approval_required.
APPROVAL_ROLES = {"uok-senior-engineer", "uok-release-integration"}
SAFE_SHELL_FALLBACK = ["git status", "git diff", "git log", "git worktree list", "ls", "pwd"]
# Restricted shell (SEC-04): every segment must EQUAL an allowlist entry (no free arguments), and the
# command may contain only these characters. No quotes, backslashes, $, globs, parentheses, braces,
# redirection or tilde can appear, so shell parsing tricks have nothing to work with (NB1, NB2, N3).
ALLOWED_SHELL_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:@%+,= -&;|")
MAX_RESTRICTED_CMD = 2000


def restricted_chars_ok(cmd):
    """Linear-time charset check (no regex backtracking; security review round 3, B2)."""
    return len(cmd) <= MAX_RESTRICTED_CMD and all(c in ALLOWED_SHELL_CHARS for c in cmd)

CTX = {"agent": "main", "tool": ""}


def log(msg):
    try:
        os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
        with open(AUDIT, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def decide(decision, reason):
    """Emit a deny/ask decision in the host's format and exit."""
    if decision == "ask" and (FORMAT == "codex" or CTX.get("event") == "beforeReadFile"):
        # Codex PreToolUse cannot ask ("parsed but not supported"); Cursor beforeReadFile is allow/deny.
        # Fail safe: deny, and tell the agent a human must approve and run it.
        decision, reason = "deny", f"requires human approval; a hook cannot ask here, so the human must run it: {reason}"
    log(f"{decision}: [{CTX['agent']} {CTX['tool']}] {reason}")
    msg = f"[UOK G1] {reason}"
    if FORMAT == "cursor":
        print(json.dumps({"permission": decision, "user_message": msg, "agent_message": msg}))
    else:   # claude, qoder, codex share the PreToolUse hookSpecificOutput shape
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": msg}}))
    sys.exit(0)


def finish_allow():
    """Cursor permission hooks need an explicit allow; other hosts take silence as 'no objection'."""
    if FORMAT == "cursor":
        print(json.dumps({"permission": "allow"}))


def _patch_files(patch, cwd):
    """Paths and added text from a Codex apply_patch body (*** Add/Update/Delete File:, *** Move to:)."""
    paths, added = [], []
    for ln in patch.splitlines():
        m = re.match(r"\*\*\* (?:Add|Update|Delete) File: (.+)$|\*\*\* Move to: (.+)$", ln)
        if m:
            p = (m.group(1) or m.group(2)).strip()
            paths.append(p if os.path.isabs(p) else os.path.join(cwd, p))
        elif ln.startswith("+") and not ln.startswith("+++"):
            added.append(ln[1:])
    return paths, "\n".join(added)


def normalize(ev):
    """Map a host event to (tool, tool_input, agent) in the Claude Code vocabulary used below."""
    if FORMAT == "cursor":
        name = ev.get("hook_event_name") or ""
        if not name:   # infer from the documented fields
            name = ("beforeMCPExecution" if "mcp_server_name" in ev else
                    "beforeShellExecution" if "command" in ev and "tool_name" not in ev else
                    "beforeReadFile" if "file_path" in ev and "tool_name" not in ev else "preToolUse")
        CTX["event"] = name
        if name == "beforeShellExecution":
            return "Bash", {"command": ev.get("command", "")}, ""
        if name == "beforeMCPExecution":
            ti = ev.get("tool_input", {})
            if isinstance(ti, str):
                try:
                    ti = json.loads(ti)
                except ValueError:
                    ti = {"raw": ti}
            return f"mcp__{ev.get('mcp_server_name', 'server')}__{ev.get('tool_name', 'tool')}", ti, ""
        if name == "beforeReadFile":
            return "Read", {"file_path": ev.get("file_path", "")}, ""
        tool, ti = ev.get("tool_name", ""), ev.get("tool_input", {}) or {}
        if isinstance(ti, dict) and "target_file" in ti and "file_path" not in ti:
            ti = dict(ti, file_path=ti["target_file"])
        return tool, ti, ""
    tool, ti = ev.get("tool_name", ""), ev.get("tool_input", {}) or {}
    if FORMAT == "codex":
        if tool == "apply_patch" and isinstance(ti, dict):
            paths, added = _patch_files(str(ti.get("command", "")), str(ev.get("cwd") or ROOT))
            return "Write", {"_paths": paths, "content": added}, ""
        return tool, ti, ""   # Codex hook events carry no subagent identity
    return tool, ti, ev.get("agent_type") or ""


def string_leaves(obj):
    """Yield every string in a JSON-like value, iteratively (no recursion limit).
    Dict keys are yielded too, plus a synthetic "key=value" for string values (M2)."""
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            yield cur
        elif isinstance(cur, dict):
            for k, v in cur.items():
                k = str(k)
                yield k
                if isinstance(v, str):
                    yield f"{k}={v}"
                stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)


def has_secret(obj):
    return any(re.search(pat, leaf) for leaf in string_leaves(obj) for pat in SECRET_PATTERNS)


def _denied_name(p):
    parts = [x.lower() for x in re.split(r"[\\/]+", str(p)) if x]
    return any(fnmatch.fnmatch(part, g) for part in parts for g in DENIED_GLOBS)


def denied_path(p):
    """SEC-02: any path component (literal or symlink-resolved, N5) matching a secret-bearing name (L5)."""
    return _denied_name(p) or _denied_name(resolve(str(p)))


def canonical(real):
    """Rewrite each existing component of an absolute real path to its on-disk spelling.
    APFS/HFS+ fold case and Unicode (e.g. U+017F 'ſ' == 's'), and realpath() keeps the
    caller's spelling, so string checks must run on the names the filesystem really has
    (security review round 3, B1). Non-existing tail components are kept as given."""
    out = os.sep
    for comp in [c for c in real.split(os.sep) if c]:
        cand = os.path.join(out, comp)
        try:
            names = os.listdir(out)
        except OSError:
            names = []
        if comp not in names and os.path.lexists(cand):
            try:
                st = os.lstat(cand)
                for n in names:
                    st2 = os.lstat(os.path.join(out, n))
                    if (st2.st_dev, st2.st_ino) == (st.st_dev, st.st_ino):
                        cand = os.path.join(out, n)
                        break
            except OSError:
                pass
        out = cand
    return out


@functools.lru_cache(maxsize=64)
def resolve(p):
    p = os.path.expanduser(p) if p.startswith("~") else p
    return canonical(os.path.realpath(p if os.path.isabs(p) else os.path.join(ROOT, p)))


REAL_ROOT = canonical(REAL_ROOT)


def inside_root(p):
    real = resolve(p)
    return real == REAL_ROOT or real.startswith(REAL_ROOT + os.sep)


def rel(path):
    r = os.path.relpath(resolve(path), REAL_ROOT)
    # Worktree isolation: claims are written relative to the repo root, so a
    # path inside .claude/worktrees/<name>/ is matched as if it were at the root.
    m = re.match(r"\.claude/worktrees/[^/]+/(.+)$", r, re.IGNORECASE)
    return m.group(1) if m else r


def load_yaml_list(path, key):
    """Tiny parser: list items under `key:` in project.yaml (no PyYAML dependency)."""
    try:
        lines = open(path).read().splitlines()
    except OSError:
        return []
    out, on, indent = [], False, None
    for ln in lines:
        if re.match(r"\s+" + re.escape(key) + r":", ln):
            on, indent = True, len(ln) - len(ln.lstrip()); continue
        if on:
            m = re.match(r"\s+- \"?([^\"#]+?)\"?\s*(#.*)?$", ln)
            if m and len(ln) - len(ln.lstrip()) > indent:
                out.append(m.group(1).strip())
            elif ln.strip() and not ln.strip().startswith("#"):
                break
    return out


def active_claims():
    """Returns (claims, malformed). Malformed claim data makes uok-* writes fail closed (L1)."""
    try:
        data = json.load(open(os.path.join(ROOT, ".orchestrator", "claims", "active.json")))
    except OSError:
        return [], False
    except ValueError:
        log("fail-open: active.json is not valid JSON; claims ignored")
        return [], True
    if not isinstance(data, dict) or not isinstance(data.get("claims", []), list):
        log("fail-open: active.json is not an object with a claims list; claims ignored")
        return [], True
    raw = data.get("claims", [])
    valid = [c for c in raw if isinstance(c, dict) and isinstance(c.get("agent", ""), str)
             and isinstance(c.get("write", []), list)
             and all(isinstance(g, str) for g in c.get("write", []))]
    if len(valid) != len(raw):
        log("fail-open: malformed claim entries ignored")
    return [c for c in valid if not c.get("released")], len(valid) != len(raw)


def check_claims(agent, path):
    """LC-03/04: write paths must lie inside the caller's write claim and
    outside every other active writer's claim. Matching is case-insensitive (L2)."""
    claims, malformed = active_claims()
    if malformed and agent.startswith("uok-"):
        decide("deny", f"{agent}: claims ledger is malformed; writes blocked until fixed (LC-04)")
    if not claims:
        return
    r = rel(path).lower()

    def hit(c):
        return any(fnmatch.fnmatch(r, g.lower()) or r.startswith(g.lower().rstrip("*/") + "/")
                   for g in c.get("write", []))
    mine = [c for c in claims if c.get("agent") == agent] if agent else []
    others = [c for c in claims if c not in mine]
    if agent.startswith("uok-"):
        if not any(hit(c) for c in mine):
            decide("deny", f"write outside {agent}'s claimed paths (LC-04): {r!r}")
    for c in others:
        if hit(c):
            decide("deny", f"path claimed by {c.get('agent')!r} / {c.get('task_id')!r} (LC-04): {r!r}")


def check_path(tool, agent, path):
    strict_uok = STRICT and agent.startswith("uok-")
    if strict_uok and tool in ("Grep", "Glob"):
        decide("deny", f"{agent}: {tool} is not available to uok roles; use uok_search.py (SEC-04)")
    if strict_uok and not path.isascii():
        decide("deny", f"{agent}: non-ASCII path not allowed (SEC-04): {path[:60]!r}")
    if denied_path(path):
        decide("deny", f"{tool} on secret-bearing path blocked (SEC-02): {os.path.basename(str(path))!r}")
    if tool in READ_TOOLS and strict_uok and not inside_root(path):
        decide("deny", f"{agent}: read outside project root blocked (ISO-02): {resolve(path)!r}")
    if tool in READ_TOOLS and strict_uok and \
            any((rel(path).lower() + "/").startswith(p) for p in NO_READ_FOR_UOK):
        decide("deny", f"{agent}: read of audit log / claims ledger blocked (SEC-04): {rel(path)!r}")
    if tool in WRITE_TOOLS:
        if not inside_root(path):
            decide("deny", f"write outside project root blocked (ISO-02): {resolve(path)!r}")
        if agent.startswith("uok-") and (any((rel(path).lower() + "/").startswith(p) for p in PROTECTED)
                                        or os.path.basename(rel(path)).lower() in PROTECTED_NAMES):
            decide("deny", f"{agent}: write to guard controls blocked (SEC-04): {rel(path)!r}")
        check_claims(agent, path)


def segments(cmd):
    return [" ".join(x.split()) for x in re.split(r"&&|\|\||;|\||&|\n|\r", cmd) if x.strip()]


def allowlist():
    entries = load_yaml_list(os.path.join(ROOT, ".orchestrator", "policy", "project.yaml"), "shell_allowlist") \
        or SAFE_SHELL_FALLBACK
    return [a.replace("{root}", REAL_ROOT) for a in entries]   # portable: no machine paths in policy


def check_restricted_shell(agent, cmd, skip_sensitive=False):
    """SEC-04: uok-* shell = exact allowlisted commands only. With skip_sensitive, segments that match
    a sensitive operation by their leading verb are left for the human gate, but every other segment must still pass (N4)."""
    entries = [" ".join(a.split()) for a in allowlist()]
    exact = {a for a in entries if not a.endswith(" ...")}
    # "<command> ..." entries accept arguments, which RESTRICTED_CHARS has already limited to
    # plain characters; only use this for tools that validate their own arguments (uok_search.py).
    with_args = [a[:-4] for a in entries if a.endswith(" ...")]
    for seg in segments(cmd):
        if skip_sensitive and sensitive_segment(seg):
            continue
        if seg not in exact and not any(seg.startswith(w + " ") for w in with_args):
            decide("deny", f"{agent}: command not in shell_allowlist (exact match required) (SEC-04): {seg[:60]}")


def main():
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw)
    except RecursionError:
        CTX["tool"] = "?"
        decide("deny", "hook input nested too deeply; failing closed (SEC-03)")
    except Exception as e:
        log(f"fail-open: bad input {e}")
        return
    if not isinstance(ev, dict):
        log("fail-open: event is not a JSON object")
        return
    tool, inp, agent = normalize(ev)
    CTX.update(agent=str(agent) or "main", tool=str(tool))
    if not isinstance(tool, str) or not isinstance(agent, str):
        raise TypeError("tool_name/agent_type must be strings")
    if not isinstance(inp, dict):
        if tool in WRITE_TOOLS or tool.startswith("mcp__") or (tool == "Bash" and agent.startswith("uok-")):
            decide("deny", f"tool_input is not an object for a security-relevant tool; failing closed")
        log(f"fail-open: tool_input is not an object ({tool})")
        return
    paths = [inp[k] for k in PATH_KEYS if inp.get(k)] + list(inp.get("_paths", []) if isinstance(inp.get("_paths"), list) else [])
    for p in paths:   # bound all path work before it starts (round 5, P1); fail closed
        if isinstance(p, str) and (len(p) > MAX_PATH_LEN or p.count("/") > MAX_PATH_PARTS
                                   or any(ord(c) < 32 or ord(c) == 127 for c in p)):
            decide("deny", f"path too long, too deep or containing control characters (SEC-04): "
                           f"{len(p)} chars")
    if any(not isinstance(p, str) or "\x00" in p for p in paths):
        raise TypeError("path fields must be strings without NUL")
    if tool in WRITE_TOOLS and has_secret({k: v for k, v in inp.items() if k in CONTENT_KEYS}):
        decide("deny", "secret-like content in write payload blocked (SEC-03)")
    uok = agent.startswith("uok-")
    if tool in ("Grep", "Glob") and STRICT and uok and not paths:
        check_path(tool, agent, ".")   # path-less Grep/Glob would search the whole root (round 5, F2)
    if tool in PATH_TOOLS:
        for p in paths:  # every path key present is checked (M3)
            check_path(tool, agent, p)
    if tool.startswith("mcp__"):
        if STRICT and uok:  # before the scan, so no input shape can skip it (M1)
            decide("deny", f"{agent}: MCP tools are not in uok role allowlists (SEC-04)")
        if has_secret(inp):
            decide("deny", "secret-like content in MCP call payload blocked (SEC-03)")
    if tool == "Bash":
        cmd = inp.get("command", "")
        if not isinstance(cmd, str):
            raise TypeError("command must be a string")
        if STRICT and uok and not restricted_chars_ok(cmd):   # before any other parsing (N1)
            decide("deny", f"{agent}: shell expansion/quoting/redirection characters or overlong command "
                           f"not allowed in restricted mode (SEC-04)")
        if len(cmd) > MAX_INSPECT_CMD:
            decide("ask", f"command too long to inspect ({len(cmd)} chars) requires human approval (SEC-07)")
        sensitive, by_verb = sensitive_op(cmd, raw_fallback=not (STRICT and uok))
        if STRICT and uok:
            if sensitive and agent in APPROVAL_ROLES:
                # Approval roles reach the human gate (SEC-07), but only if every non-sensitive
                # segment is itself allowlisted (N4); the human sees the full command.
                check_restricted_shell(agent, cmd, skip_sensitive=True)
                decide("ask", f"sensitive operation '{sensitive}' requires human approval (SEC-07)")
            check_restricted_shell(agent, cmd)
        if sensitive and uok and agent not in APPROVAL_ROLES and by_verb:
            # Role permission sensitive_ops: never (AGENT-CAPABILITIES.yaml).
            decide("deny", f"{agent}: sensitive operation '{sensitive}' is not permitted for this role (SEC-07)")
        if sensitive:
            decide("ask", f"sensitive operation '{sensitive}' requires human approval (SEC-07)")
    log(f"allow: [{CTX['agent']}] {tool} {paths[0]!r}" if paths else f"allow: [{CTX['agent']}] {tool}")


def security_relevant():
    t, a = CTX["tool"], CTX["agent"]
    uok = a.startswith("uok-")
    return (STRICT and uok) or t in WRITE_TOOLS or t.startswith("mcp__") or (t == "Bash" and uok)


if __name__ == "__main__":
    try:
        main()
        finish_allow()
    except SystemExit:
        raise
    except Exception as e:
        if security_relevant():
            decide("deny", f"hook error {type(e).__name__} on a security-relevant tool; failing closed")
        log(f"fail-open: hook error {type(e).__name__}: {str(e)[:200]!r}")
        finish_allow()
