# G1 guard — the shared hook for all hosts

Kit version: 1.0.0 · Used by the Claude Code, Qoder, Cursor, and Codex adapters · Files: `g1_guard.py` (the hook), `uok_search.py` (safe search for agents), `test_g1_guard.py` (tests).

Installed by the adapter's installer: `python3 <kit>/adapters/<host>/install.py` (see the adapter's README). This description matches the current code.

## 0. Modes (`.orchestrator/policy/claude-code.yaml`, key `enforcement`)

- **`standard`** (default). For all callers: secret protection, no writes outside the project, secret checks on writes and MCP calls, human confirmation for dangerous operations (section 5). For `uok-*` workers additionally: writes to control files denied, write claims enforced, dangerous operations denied to roles with `sensitive_ops: never`. Ordinary tools (Bash, Grep, Glob, MCP) are available to workers.
- **`strict`**. Everything in `standard`, plus the `uok-*` sandbox from section 4 and the strict items of section 3: exact shell commands only, no Grep/Glob/MCP, no reads outside the project, ASCII paths only, blocking on any hook error. Enable it when workers cannot be trusted with the project's code or data.

The settings file is protected against writes by workers. If it is missing, `standard` applies. Live verification and six rounds of security review are recorded in `UNIVERSAL-ORCHESTRATOR-KIT/handoff/INSTALLATION-REPORT-claude-code-2026-11-17.md`.

## 0a. Hosts (`--format`)

| Host | Format | Where registered | Differences |
|---|---|---|---|
| Claude Code | `claude` (default) | `.claude/settings.json`, PreToolUse | the reference; `agent_type` distinguishes `uok-*` workers |
| Qoder | `qoder` | `.qoder/settings.json`, PreToolUse | the same scheme as Claude Code, including `agent_type` and `ask` |
| Cursor | `cursor` | `.cursor/hooks.json`: `beforeShellExecution`, `beforeMCPExecution`, `beforeReadFile`, `preToolUse` | response `{"permission": …}`, the hook always answers explicitly (including `allow`); `ask` becomes `deny` with the reason "the human must run it": the documentation promises a human prompt, but live (Cursor 3.27.22, 2026-11-17) the command executed with no prompt — fail-closed; `beforeReadFile` fires only for existing files; no agent identity |
| Codex | `codex` | `.codex/hooks.json`, PreToolUse | edits arrive as `apply_patch`: the hook extracts paths and added text; `ask` is not supported, so it becomes `deny` with the reason "the human must run it"; no agent identity |

The hook takes the project root from `UOK_PROJECT_DIR` / `CLAUDE_PROJECT_DIR` / `QODER_PROJECT_DIR` / `CURSOR_PROJECT_DIR`, else from its own location (`<root>/.orchestrator/hooks/`), else from the working directory. The hook command in the Qoder, Cursor, and Codex configurations locates the hook via `git rev-parse --show-toplevel`, so it works from any subfolder.

In hosts without agent identity (Cursor, Codex), the worker rules (protecting control files from workers, per-worker claims, denial of dangerous operations by role, strict mode) apply only as instructions. The baseline protections apply to everyone.

The hook reads mode settings from `.orchestrator/policy/adapter.yaml` (Qoder, Cursor, Codex) or `claude-code.yaml` (Claude Code).

## 1. Registration (Claude Code)

`.claude/settings.json`, event `PreToolUse`:

- matcher: `Read|Grep|Glob|Write|Edit|MultiEdit|NotebookEdit|Bash|mcp__.*`
- command: `python3 -I "$CLAUDE_PROJECT_DIR/.orchestrator/hooks/g1_guard.py"`, `timeout: 30`

The hook never returns `allow` explicitly. When all checks pass, it exits silently with code 0, and the decision is left to the `permissions` rules in `settings.json` and the session mode. `deny` blocks the call; `ask` shows a human prompt.

The hook identifies the caller by the event's `agent_type` field. If the field is present and starts with `uok-`, the caller is a worker subagent; otherwise it is the main session (the orchestrator, supervised by a human). For `uok-*` the hook acts as a sandbox; for the main session it checks secrets, writes outside the root, and dangerous operations.

## 2. Checks for all callers

| Check | Decision | Requirement |
|---|---|---|
| A path field longer than 4096 characters, with more than 256 `/`, or containing a control character | deny (before any path processing) | SEC-04 |
| A path component (as written or after symlink resolution) matches `DENIED_GLOBS`: `.env`, `.env.*`, `*credentials*`, `*secret*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `id_ecdsa*`, `id_dsa*`, `.ssh`, `.aws`, `.gnupg`, `.kube`, `.netrc`, `.npmrc`, `.pypirc`, `.docker`, `hosts.yml` | deny | SEC-02 |
| A write (Write/Edit/MultiEdit/NotebookEdit) outside the project root; exception for main — paths from `host_state_write_exceptions` (see below); no exceptions for `uok-*` | deny | ISO-02 |
| Secret-like text in any line of the `content`, `new_string`, `new_source`, `edits` fields | deny | SEC-03 |
| Secret-like text in any line, key, or `key=value` pair of an MCP call input | deny | SEC-03 |
| A write to a path held by another worker's claim | deny | LC-04 |
| A dangerous shell operation (section 5) | ask | SEC-07 |
| A Bash command longer than 20,000 characters | ask | SEC-07 |

Every path field present in the input is checked: `file_path`, `notebook_path`, `path`.

Paths are compared by their on-disk spelling. `canonical()` rewrites each existing component to the name under which it is recorded in the directory (by `st_dev`/`st_ino`). Therefore `.ORCHESTRATOR/…` or `.orcheſtrator/…` (U+017F) is recognized as `.orchestrator/…`: APFS folds case and Unicode.

Secret patterns: `sk-…` (16+), `AKIA…`, `gh[pousr]_…` (36+), `-----BEGIN … PRIVATE KEY-----`, and `api_key|token|password|secret` + `:`/`=` + 20+ characters from `[A-Za-z0-9_-]`.

**The ISO-02 exception (`host_state_write_exceptions`).** The host's own persistent state (agent memory, settings) lives outside the project root, and without the exception the host's memory stops working while the hook is active. The directory list (entries like `~/.claude/`, expanded via `expanduser`) is read from `adapter.yaml` (Qoder, Cursor, Codex) or `claude-code.yaml` (Claude Code); the installer adds its own host's directory. It applies to main only (not `uok-*`); SEC-02 is checked earlier, so secret-named paths such as `.env` remain denied inside the excluded directories as well. By default the list is empty — without an explicit entry in the policy, the behavior is unchanged. If `uok-*` workers in a particular project need to manage git worktrees, that is solved by extending `shell_allowlist` in `project.yaml` (by default they get only `git worktree list`; creating/removing worktrees is the orchestrator's job).

## 3. Additional checks for `uok-*`

In all modes: writes to control files denied, write claims enforced, dangerous operations denied to roles with `sensitive_ops: never` (`uok-*` except `uok-senior-engineer` and `uok-release-integration`). Items marked **strict** apply only in strict mode.

- **strict:** **ASCII-only paths** on all path tools → otherwise deny (SEC-04).
- **strict:** **Grep and Glob are denied** (deny SEC-04), including without `path`. They are also absent from the agents' tool lists. Search is provided by `uok_search.py`.
- **strict:** **Reads outside the root** → deny (ISO-02). Reads of `.orchestrator/audit/`, `.orchestrator/claims/`, `.git/` → deny (SEC-04).
- **Writes to control files** → deny (SEC-04). These are `.claude/`, `.qoder/`, `.cursor/`, `.codex/`, `.git/`, `.orchestrator/`, `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `AGENTS.local.md`, `.mcp.json`, `.gitignore`, `<kit>/validation/`, `<kit>/core/`, `<kit>/adapters/` (`<kit>` = `kit_dir` from `claude-code.yaml`), and, at any depth, files named `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `AGENTS.local.md`, `.mcp.json`, `settings.json`, `settings.local.json`, `hooks.json`. Comparison is case-insensitive.
- **Write claims**: if `active.json` holds active claims, an agent may write only inside its own. If the claim ledger is corrupted, every write by the agent is denied.
- **strict:** **MCP calls** → deny (SEC-04). This check runs before the secret scan.
- **strict:** **An error inside the hook** on any `uok-*` call → deny ("failing closed").

## 4. Restricted shell for `uok-*` (strict only)

1. The whole command is no longer than 2000 characters and consists only of the characters `A-Z a-z 0-9 _ . / : @ % + , = -`, the space, and the separators `& ; |`. No quotes, `\`, `` ` ``, `*?[]`, `(){}`, `~`, `<>`, or newlines are allowed, so shell-parsing tricks have nothing to work with. The check is linear and runs first.
2. The command is split into segments on `&&`, `||`, `;`, `|`, `&`, and newlines. **Every segment must match exactly** an item of `shell_allowlist` in `.orchestrator/policy/project.yaml` (spaces are normalized). An item ending in ` ...` accepts arguments that are already restricted by step 1. Only `uok_search.py` is marked this way, and it validates its own arguments.
3. The roles `uok-senior-engineer` and `uok-release-integration` (`sensitive_ops: approval_required`) get `ask` on a dangerous operation, but only if every other segment of the command is in the list. The other roles get deny.

Items may contain `{root}` — the hook substitutes the absolute root path, so the policy holds no machine-specific paths. The default list: `git status`, `git diff`, `git diff --stat`, `git log --oneline -20`, `git worktree list`, `ls`, `ls -la`, `pwd`, `python3 -I {root}/.orchestrator/hooks/uok_search.py ...`, `python3 -I {root}/.orchestrator/hooks/test_g1_guard.py`. `cat`, `grep`, and `pytest` are excluded deliberately: free-form arguments allowed bypassing the protection, and `pytest` executes arbitrary code.

## 5. Dangerous operations (SEC-07)

They are recognized by the verb at the start of each segment, without backtracking regular expressions. Before that, `( ) { }`, the keywords (`if then do else elif while until !`), `VAR=x` assignments, and the wrappers (`sudo env command exec nohup time xargs doas nice timeout`) together with their options are stripped. The following are treated as dangerous:

- `rm` with recursion (`-r`/`-R`/`--recursive`) and `-f`/`--force` in any order and spelling;
- `git push` with `-f`, `-d`, `--force*`, `--mirror`, `--delete`, `--prune`, `+refspec`, `:refspec` (global git options such as `-C dir` are skipped);
- `git worktree remove --force`, `git reset --hard`, `git clean -f`;
- `kubectl|terraform|helm apply|destroy|delete`, publishing via `npm|yarn|pnpm publish`, `twine upload`, `gh release create`;
- deployments: `vercel --prod`, `fly deploy`, `npm run deploy[:prod]`;
- `DROP TABLE|DATABASE` in SQL clients (`psql`, `mysql`, `sqlite3`, …).

For the main session there is also a fallback scan over the whole command text: `rm -rf` within one flag block, `DROP TABLE`, and `git push` with a force flag inside a 400-character window. It catches forms inside quotes and `bash -c`, and it is disabled for `uok-*`. False `ask` results are possible (for example, `echo rm -rf`); there are no misses in that direction.

## 6. Write claims

The file `.orchestrator/claims/active.json`:

```json
{"claims": [{"task_id": "T-1", "agent": "uok-implementation-engineer", "write": ["src/a/*"]}]}
```

- Matching: `fnmatch` on the root-relative path or the `glob/` prefix, case-insensitive. Paths inside `.claude/worktrees/<name>/` are matched as if they were at the root.
- Release: delete the entry or set `"released": true`.
- No file, or no active claims → the claim check does not apply. The other checks, including control files, root bounds, and secrets, still apply.
- Claims are distinguished by agent type (`agent`). Two instances of the same role are not isolated from each other.

## 7. Search for agents in strict: `uok_search.py`

```
python3 -I <project root>/.orchestrator/hooks/uok_search.py PATTERN [RELATIVE_DIR]
```

- Searches only inside the project root. The root is computed from the script's location; `CLAUDE_PROJECT_DIR` from the environment is ignored.
- Does not follow symlinks out of the root and skips secret-named files (the same `denied_path` as in the hook).
- Skips `.git`, `node_modules`, `__pycache__`, `.venv`, `.orchestrator/audit`, `.orchestrator/claims`. Refuses when the start directory is outside the root, secret-named, non-ASCII, or among these exclusions.
- `PATTERN` is a Python regular expression up to 200 characters long, with at most one `+`; the character set is limited by step 1 of section 4.
- Output: `path:line:text`, at most 200 matches; lines longer than 10,000 characters are not read.

## 8. Audit log

`.orchestrator/audit/g1.log`, one line per event: `<time> allow|deny|ask: [<agent> <tool>] <reason>` and `<time> fail-open: <description>`. Paths are written via `repr`, so a log line cannot be forged with a newline.

Fail-open with a log entry happens only for the main session and only for tools with no security role: invalid JSON, a non-object event, a non-object `tool_input` for `Read`. Writes, MCP, and any `uok-*` call are blocked on error. Excessively deep JSON nesting is blocked for all callers.

## 9. `permissions` rules in `settings.json` (second line of defense)

- `deny`: `Read(...)` for secret names at any depth and for `~/.ssh/**`, `~/.aws/**`; `Edit(...)` for `.env*`, `*credentials*`, `*secret*` (`Edit` rules cover all write tools; Claude Code does not apply `Write(...)`); `Bash(curl:*)`, `Bash(wget:*)`.
- `ask`: `Bash(git push:*)`, `Bash(rm -rf:*)`.

## 10. Known limitations

- If the hook file is deleted or renamed, Claude Code blocks every call the hook is configured for (verified: file not found → exit code 2). Do not move `.orchestrator/hooks/` while a session is open; reinstalling via `install.py` is safe.
- With no claims in place, `uok-*` can write to any unprotected location inside the root. Record claims before parallel work.
- WebFetch and WebSearch (available to `uok-research-analyst` and `uok-release-integration`) are not checked by the hook.
- `git diff` shows changed tracked files in full, so secret files must not be in git.
- A hook timeout, per available evidence (unverified), is a non-blocking error and the call proceeds. No known input comes anywhere near the 30 s timeout.
- In the main session, `eval`, indirect calls through variables, `find -delete`, `git branch -D`, `dd`, and `truncate` are not recognized. That responsibility belongs to the human running the orchestrator.
- In strict, roles without Bash (`uok-architect`, `uok-documentation-specialist`) have no search: the orchestrator passes them file paths.
- In standard, Bash arguments of workers are not checked: the hook does not parse `cat .env` inside Bash; only the `permissions` rules and the session mode remain.

## 11. How to verify

```bash
python3 -I .orchestrator/hooks/test_g1_guard.py
```

123 tests: the full suite in strict mode, a separate set for standard, and tests for the Cursor, Codex, and Qoder formats. They pass identically under unittest and pytest. Each test runs the hook in a separate process on a temporary root with its own policy and checks the decision, the requirement code, and the log line. Unicode-folding tests run only on volumes that support folding. There are time-limited tests against malicious inputs.
