# INSTALLATION REPORT — Claude Code adapter (UNIORK)

Kit version: 1.0.0 · Spec version: 1.0.0 · Date: 2026-11-17

## Environment
Claude Code (desktop app, Code tab), macOS, Python 3.12.2, PyYAML 6.0.2. Project root `/Users/snm/UNIORK` (not a git repo). No pre-existing `.claude/`, `CLAUDE.md`, or project settings → nothing to back up or merge. `claude` CLI not on PATH (headless mode not probed).

## Changes
- Kit fix: `validation/behavior_tests.py` TS-10 `granted_cross_project` now passes the grant through a receiver-held registry (kernel correctly ignores envelope-embedded grants, ISO-04); added negative check that an embedded-only grant is rejected. Kernel unchanged.
- Created `.claude/agents/uok-*.md` (10 roles; orchestrator = main session, per nesting policy). Model aliases: T1 haiku, T2 sonnet, T3/T5 opus (**unverified**, aliases not probed).
- Created `.claude/settings.json` with one `PreToolUse` hook → `.orchestrator/hooks/g1_guard.py`.
- Created `CLAUDE.md` (marked UOK section), `.orchestrator/{tasks,audit,claims,hooks,policy,routing}`, policy copies (`project.yaml`, `agents.yaml`, `models.yaml`).

## Validation (actually executed)
- `self_test.py`: 16/16 pass. `behavior_tests.py`: 29/29 pass.
- G1 hook run standalone with synthetic events: secret path read → deny; write outside root → deny; secret-like payload → deny; `git push --force` → ask; normal write → allow; malformed input → fail-open. Tag: `verified_local` (script behavior), NOT `verified_live` for Claude Code integration.
- Hook logged real session tool calls, so it is loaded in a live session (indirect evidence).

## Update (same day): gaps addressed
- Claim-ledger enforcement: implemented in G1 (`.orchestrator/claims/active.json`); tested locally (in-claim allow; out-of-claim / other's claim deny). Live: a real subagent PreToolUse event carries `agent_type` (observed in hook log, `verified_live`), so enforcement keys on it.
- Restricted shell: `uok-*` agents limited to `policy/project.yaml` `shell_allowlist`, no redirection/substitution/chaining outside allowlist; tested locally.
- Reviewer independence: code/security reviewers now `fable` vs implementers haiku/sonnet/opus (model-level). Same provider family remains; human review for critical work is stated in CLAUDE.md.
- Live dispatch of `uok-*` agents: BLOCKED in the installing session (agent registry loads at session start; `uok-research-analyst` not found). Needs a new session in /Users/snm/UNIORK, then `/agents` check and one read-only dispatch. Alias `fable` also unverified.

## Remaining
Live dispatch of uok-* (restart required), permission rules, worktrees, MCP, headless not configured. Maturity stays `implementation_available` until the live dispatch passes.

## Live verification

Date: 2026-11-17, fresh Claude Code session in /Users/snm/UNIORK (orchestrator model: Sonnet 5.5). All results below were observed by dispatching the `uok-*` subagents and reading `.orchestrator/audit/g1.log`.

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Agents registered; model aliases resolve | verified_live | Agent tool accepted `uok-research-analyst`, `uok-implementation-engineer`, `uok-code-reviewer` (all 10 listed). Dispatched runs reported: `sonnet` -> Sonnet 5.5 (research, test, implementation), `fable` -> Fable 5.2 (`claude-fable-5-2`, code-reviewer). No alias failed. `opus`/`haiku` aliases not exercised. |
| 2 | Read-only research dispatch | verified_live | `uok-research-analyst` listed `.orchestrator/policy`: agents.yaml, models.yaml, project.yaml. Nothing modified. |
| 3 | Restricted shell | verified_live | `uok-test-engineer`: `ls .orchestrator/policy` allowed; `curl https://example.com` -> `[UOK G1] ... command not in shell_allowlist (SEC-04)`; `ls > probe/out.txt` -> `[UOK G1] ... shell redirection/substitution not allowed in restricted mode (SEC-04)`. g1.log shows matching `allow`/`deny` lines. |
| 4 | Write claims | verified_live | With claims T-live-1 (impl, `probe/a/*`) and T-live-2 (test, `probe/b/*`): impl-engineer Write `probe/a/x.txt` succeeded; `probe/b/x.txt` -> `[UOK G1] write outside uok-implementation-engineer's claimed paths (LC-04)`. g1.log: `allow: Write .../probe/a/x.txt`, `deny: ... probe/b/x.txt`. File `probe/b/x.txt` was not created. |
| 5 | Independent review on different model | verified_live | `uok-code-reviewer` (Fable 5.2) read `probe/a/x.txt` read-only, verdict approve; implementer was Sonnet 5.5, so models differ. |
| 6 | Kit tests | verified_live | `self_test.py`: 16 PASS, 0 FAIL. `behavior_tests.py`: "29 checks passed, 0 failed", exit 0. |

Notes / caveats (no false deny/allow observed):
- Subagents self-report their model from their system prompt; this is not independently verified beyond that.
- The two probe Writes in check 4 were issued in parallel by the agent; the hook handled each correctly.
- Not covered: `opus`/`haiku` alias resolution, security-reviewer, other roles, permission rules, worktrees, MCP, headless.
- Cleanup: `probe/` and `.orchestrator/claims/active.json` deleted.

Maturity verdict: `integration_tested` (checks 1-5 all passed; not production-hardened, human review still required for CAT-07/production work).

## Live verification, part 2

Date: 2026-11-17, same session. Remaining roles and aliases dispatched with trivial read-only tasks; models are as self-reported by each subagent from its system prompt.

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 7 | `uok-architect` (opus) | verified_live | Reports Opus 5.5 (`claude-opus-5-5`); summarized CLAUDE.md. |
| 8 | `uok-senior-engineer` (opus) | verified_live | Reports Opus 5.5 (`claude-opus-5-5`). |
| 9 | `uok-debugging-specialist` (opus) | verified_live | Reports Opus 5.5; listed agents.yaml, models.yaml, project.yaml. |
| 10 | `uok-documentation-specialist` (haiku) | verified_live | Reports Haiku 5.5 (`claude-haiku-5-5`); summarized CLAUDE.md. |
| 11 | `uok-release-integration` (sonnet) | verified_live | Reports Sonnet 5.5 (`claude-sonnet-5-5`). |
| 12 | `uok-security-reviewer` (fable) | verified_live | Reports Fable 5.2 (`claude-fable-5-2`). |
| 13 | Aliases opus/haiku/fable | verified_live | No resolution error; every alias resolved to a current model. |
| 14 | security-reviewer cannot write | verified_live (tool-level) | Its tool set is Read, Bash, SubagentHandback: no Write tool exists. Write was not attempted, so G1 was not exercised for this; block is by tool provisioning. Note it does have (restricted) Bash. |
| 15 | documentation-specialist has no Bash | verified_live | Tools: Read, Write, Edit, Grep, Glob, SubagentHandback. No Bash. |
| 16 | senior-engineer secret payload denied | verified_live | Write `probe/n.txt` with `password=abcdefghij0123456789xyz` (claim `probe/n.txt` was set for it) -> `[UOK G1] secret-like content in write payload blocked (SEC-03)`; g1.log has matching deny; file not created. |
| 17 | release-integration `git push --force origin main` returns `ask` | FAILED as specified (still blocked) | Actual: hard deny `[UOK G1] uok-release-integration: command not in shell_allowlist (SEC-04): git push --force origin main`; no prompt shown. Expected: `ask` (SEC-07). The command was blocked, so the safety outcome holds, but the ask path was not exercised. |
| 18 | Kit tests re-run | verified_live | self_test.py 16 PASS; behavior_tests.py "29 checks passed, 0 failed". |

Deviation detail (check 17): `project.yaml` shell_allowlist contains no `git push`, and `g1_guard.py` evaluates the allowlist (deny) before the sensitive-operation check that emits `ask` (guard line ~152). Hence for restricted `uok-*` agents the SEC-07 `ask` is unreachable for non-allowlisted commands like `git push`; it only fires for allowlisted commands matching a sensitive pattern, or for the unrestricted main session. This is a design/ordering question rather than a false allow. To exercise `ask`, either add `git push` to the release role's allowlist (so the sensitive check can fire) or test from the main session. No files were changed.

Updated coverage gaps: not covered: security-reviewer attempted Write through G1 (only tool absence seen), the `ask` outcome of G1, permission rules, worktrees, MCP, headless, real (non-probe) parallel writer workflows. Cleanup: `probe/` and `.orchestrator/claims/active.json` deleted.

Maturity verdict unchanged: `integration_tested`.

## Fix for check 17 (2026-11-17)

`g1_guard.py`: for roles with `sensitive_ops: approval_required` (`uok-senior-engineer`, `uok-release-integration`, matching AGENT-CAPABILITIES.yaml; orchestrator = main session) a sensitive shell operation now returns `ask` (SEC-07) before the allowlist check. Redirection/substitution is still denied first for every `uok-*` agent; roles with `sensitive_ops: never` still get a hard deny.

Local hook test (synthetic events, `verified_local`):

| Event | Expected | Actual |
|---|---|---|
| release-integration `git push --force origin main` | ask | ask |
| senior-engineer `rm -rf build` | ask | ask |
| test-engineer `git push --force origin main` | deny | deny |
| release-integration `git push -f x > log` | deny | deny |
| release-integration `curl https://x` | deny | deny |
| release-integration `git status` | allow | allow |
| main session `git push --force origin main` | ask | ask |
| main session `curl https://x` | allow | allow |

Kit tests after the fix: self_test 16/16, behavior_tests 29/29. The `ask` path has not yet been exercised by a live subagent (it shows a permission prompt to the user; needs the user to decline it).

## Live verification, part 3

Date: 2026-11-17. G1 `ask` path after the hook fix. Command in both cases: `rm -rf probe/ask-test-nonexistent` (target does not exist; nothing was executed in either case).

| Event | Expected | Actual | Prompt shown / user choice |
|-------|----------|--------|----------------------------|
| `uok-release-integration` runs the command | G1 `ask` (SEC-07, irreversible_data_change) | g1.log `2026-11-17T01:38:15 ask: sensitive operation 'irreversible_data_change' requires human approval (SEC-07)`. The harness then reported the agent as stopped by the user; the command did not run and the agent sent no final report. | Prompt was raised; user declined (inferred from the agent being stopped by the user, not from a verbatim message). No retry. verified_live (ask fired), user choice inferred. |
| `uok-test-engineer` runs the command | hard deny, no prompt | Hook error `[UOK G1] uok-test-engineer: command not in shell_allowlist (SEC-04): rm -rf probe/ask-test-nonexistent`; g1.log `01:38:15 deny: ... (SEC-04)`. | No prompt. verified_live. |

Notes:
- g1.log contains a second, earlier `ask` line (`01:37:19`, same operation) that was not produced by this part's dispatch (probably from the dispatching session's own test). `ask` entries carry no agent name, so the 01:38:15 line is attributed to the release agent by timing (same second as the test-engineer deny) rather than by identity. Suggest adding the agent name to `ask` log lines.
- This resolves the check-17 deviation from part 2: after the fix the `ask` path is reachable for `uok-release-integration`.
- No files other than this report were changed; `probe/` does not exist.

## Follow-up after part 3

- g1.log lines now carry the caller (`[uok-<role> Bash]` or `[main ...]`), so `ask`/`deny` entries are attributable by identity, not by timing (`verified_local`).
- Known limitation: sensitive patterns match anywhere in the command text, so a main-session command that merely contains e.g. `rm -rf ...` inside a heredoc also triggers `ask` (likely the source of the extra `ask` lines). This errs on the safe side (a prompt, never a silent allow).

Final maturity: claude-code adapter `integration_tested`; all 10 roles, aliases haiku/sonnet/opus/fable, claims ledger, restricted shell, secret-payload deny, and the SEC-07 `ask` gate verified live. Not covered: permission rules, worktrees, MCP, headless, real multi-writer parallel workflows.

## Headless / worktree / MCP probe (partial, 2026-11-17)

- CLI found (not on PATH): `~/Library/Application Support/Claude/claude-code/2.1.325/.../claude`, version 2.1.325. `--help` lists `-p/--print`, `--agent`, `--agents`, `--mcp-config`, `-w/--worktree` (`verified_local`, help text only).
- Headless run `claude -p ... --model haiku`: binary starts, but returns "Not logged in · Please run /login" (the desktop app manages auth for its own sessions). Headless NOT verified; needs the user to log the CLI in.
- Worktree: `/Users/snm/UNIORK` is not a git repo, so `--worktree` / subagent worktree isolation cannot run here without `git init` (needs user approval). Not tested.
- MCP: uok-* agents have explicit `tools:` allowlists without MCP tools (by design, SEC-04); G1 matcher does not cover `mcp__*` tools in the main session. Not live-tested.

## MCP / worktree / headless (continued, 2026-11-17)

| Area | Change | Result |
|---|---|---|
| MCP | Hook matcher now includes `mcp__.*`; G1 denies MCP payloads with secret-like content (SEC-03) and any MCP call from a `uok-*` agent (SEC-04). | Local: secret payload deny, clean call allow, uok MCP call deny (`verified_local`). Live: real main-session MCP call `mcp__ccd_turn__update_plan` logged by G1 as `allow: [main]` (`verified_live`). Registry listing of `uok-*` agents shows no MCP tools (`verified_live`). |
| Worktree | Claim matching treats `.claude/worktrees/<name>/…` as repo-relative, so claims hold inside worktrees. | Scratch git repo + `git worktree add .claude/worktrees/w1`: claimed path allow; unclaimed deny; main into worker claim deny; outside repo deny (`verified_local`). Native Claude Code worktree isolation (`--worktree` / subagent isolation) NOT run: `/Users/snm/UNIORK` is not a git repo. |
| Headless | none | `claude -p` (CLI 2.1.325) returns "Not logged in · Please run /login". NOT verified; needs the CLI to be logged in. |

Kit tests after these changes: self_test 16/16, behavior_tests 29/29.

Remaining: native worktree run (needs `git init` in UNIORK or a git project), headless (needs CLI login), Claude Code permission rules, real multi-writer parallel workflow.
