# Adapter: Claude Code

Kit version: 1.0.0 · Spec version: 1.0.0 · Maturity: integration_tested
Research date: 2026-11-16 · Live verification: 2026-11-17, Claude Code 2.1.325 (desktop app + CLI), macOS
Status tags: `verified_doc` = read in official docs; `verified_live` = executed and observed in a
real Claude Code session; `unverified` = plausible, not confirmed. Re-verify in your version.

**Quick install** (from the project root that contains the kit):

```bash
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/claude-code/install.py --dry-run
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/claude-code/install.py --models tier1=haiku,tier2=sonnet,tier3=opus,review=opus
```

Then restart the session: agents load at session start. See §12 for options and §13 for the
live checks to run afterwards.

## 1. Environment discovery

- Detect: a `.claude/` dir or `CLAUDE.md` in the project, `~/.claude/` for the user, the agent's
  own tool inventory (Agent/Task tool, `mcp__*` tools). The `claude` binary may not be on PATH:
  the desktop app ships it under `~/Library/Application Support/Claude/claude-code/<version>/`
  [verified_live].
- Runtime modes: desktop app / TUI, IDE extension, headless (`claude -p`), SDK. Headless needs
  the CLI to be logged in separately (`claude /login`) [verified_live].
- Inspect read-only: `.claude/settings.json`, `.claude/settings.local.json`,
  `~/.claude/settings.json`, `.claude/agents/`, `.mcp.json`, `CLAUDE.md`. Never copy secrets.

## 2. Native agent capabilities

- Subagents are markdown files with YAML frontmatter (`name`, `description`, `tools`, `model`)
  in `.claude/agents/` [verified_doc, verified_live].
- The agent registry loads at **session start**: agents created mid-session are not dispatchable
  until a new session [verified_live].
- Each subagent has its own context window (ISO-03) [verified_doc]. Hook events from subagents
  carry `agent_id` and `agent_type` [verified_live], which the G1 guard uses to tell workers
  from the orchestrator.
- The tools a subagent really gets can differ from its `tools:` line. In 2.1.325 subagents had
  no Grep/Glob tools [verified_live]. Probe with a trivial dispatch.

## 3. Model selection

- `model` frontmatter accepts aliases or full IDs. `haiku`, `sonnet`, `opus`, `fable` resolved
  on the verification account [verified_live]; your account may differ.
- Tier mapping (installer `--models`): TIER-1 → `tier1`, TIER-2 → `tier2`, TIER-3/4 → `tier3`,
  reviewers (TIER-5) → `review` (default `fable`, the most capable model of this host; fallback `opus` when unavailable). Give reviewers a model different from the implementers
  (QA-01). Same provider family remains a documented degradation: human review for critical work.
- Aliases are environment conveniences, not architectural dependencies (RT-04).

## 4. Custom agent support

`install.py` generates `.claude/agents/uok-<role>.md` from `core/AGENT-CAPABILITIES.yaml`:
- `name` = role id, `description` = responsibilities + "(Universal Orchestrator Kit role)" marker;
- `tools` from role permissions (read-only roles get no Write/Edit; `shell: none` → no Bash; standard mode adds `Skill`, checked by G1);
- `model` from the tier binding; the body holds responsibilities, outputs, validation and
  operating rules (envelope scope, SEC-05 injection resistance, evidence).
A file of the same name without the marker is user-authored: the installer leaves it alone and
reports it (NS-10).

## 5. Parallel execution

- Background subagents run concurrently [verified_live: two writers in parallel on disjoint files].
- Kit rule: dispatch parallel writers only with satisfied dependencies and disjoint write claims
  (LC-03/04). The orchestrator records claims in `.orchestrator/claims/active.json`; the G1 hook
  denies writes outside the caller's claim or inside another's [verified_live].
- Worktree isolation: subagent `isolation: worktree` creates `.claude/worktrees/<name>/` on its
  own branch; claims map worktree paths back to repo-relative paths [verified_live]. It needs a
  git repository with at least one commit.

## 6. Tool integration

- `tools` frontmatter allowlists per agent [verified_doc].
- MCP tools appear as `mcp__<server>__<tool>`; the hook matcher `mcp__.*` sees them
  [verified_live]. Kit agents do not list MCP tools.

## 7. Context management

- `CLAUDE.md` (project root), `CLAUDE.local.md`, `~/.claude/CLAUDE.md` [verified_doc].
- The installer writes a section between `<!-- UOK:BEGIN … -->` and `<!-- UOK:END -->`.
  User text outside the markers is preserved, and a rerun replaces only the section.

## 8. Permissions

- `permissions.deny` / `permissions.ask` rules in `.claude/settings.json` apply [verified_live:
  a `Bash(curl:*)` deny blocked a command the hook allowed].
- `Read(path)` and `Edit(path)` rules apply to file tools; **`Write(path)` rules are ignored**
  (the CLI warns: "only Edit(path) rules are") [verified_live]. The installer writes only Read and
  Edit path rules.
- Never write bypass modes for kit agents (SEC-01/10).

## 9. Hooks and events

- `PreToolUse` hooks in `settings.json`; decision via JSON `permissionDecision`:
  `deny` / `ask` [verified_live]; `timeout` per hook.
- **A missing hook script blocks every matched tool call** (python exits 2 → blocking error)
  [verified_live]. The installer copies the hook before it registers it. Never move
  `.orchestrator/hooks/` while a session is open.
- In headless mode an `ask` has no human, so the call is not run [verified_live].
- The kit's G1 guard: `payload/hooks/g1_guard.py`, documented in `payload/hooks/README.md`
  (modes `standard` / `strict`, 123 tests).

## 10. External API integration

- Headless `claude -p "<prompt>"` for scripted role sessions [verified_live]; it loads project
  hooks and settings and prints settings warnings [verified_live].
- Provider APIs for routing outside the session: registry `auth_env` names only; the kit never
  stores keys.

## 11. Limitations

- The subagent nesting depth is limited, but the exact default is unverified:
  published sources conflict (docs describe no nested dispatch; changelog
  entries mention deeper nesting) [unverified]. The orchestrator is the main
  session and workers do not spawn orchestrators.
- WebFetch/WebSearch are not covered by the hook matcher.
- A hook timeout is believed to be a non-blocking error (the call proceeds) [unverified]; no
  known input brings the G1 guard near its 30 s timeout.
- Per-role tool lists may be reduced at runtime (§2); `strict` mode workers without Bash cannot
  search and need exact paths in their brief.

## 12. Installation procedure

Primary path: `uok init` in the session (user-level `uok-init` skill, registered once by
`python3 UNIVERSAL-ORCHESTRATOR-KIT/uok bootstrap`; personal skills live in `~/.claude/skills/`
[verified_doc: code.claude.com/docs/en/skills]). The CLI dispatches to this installer:
`python3 UNIVERSAL-ORCHESTRATOR-KIT/uok init --host claude-code [--project DIR] [flags]`.

Direct invocation:

`install.py [--project DIR] [--mode standard|strict] [--models tier1=…,tier2=…,tier3=…,review=…] [--dry-run]`

1. Discover and audit (directive steps 1-7). Probe which model aliases your account really has
   (`/model`) and pass them with `--models`.
2. Run with `--dry-run` and read the plan. Every modified file is backed up to
   `.orchestrator/backups/<timestamp>/`.
3. Run for real. The installer:
   - copies the G1 hook to `.orchestrator/hooks/` before registering it;
   - writes the policy files (`.orchestrator/policy/project.yaml`, `models.yaml`, `agents.yaml`,
     `claude-code.yaml`), keeping existing ones;
   - writes the `uok-*` agents and the CLAUDE.md section;
   - writes the launcher skill `.claude/skills/uok/SKILL.md` — the user runs `/uok <task>`
     (`argument-hint: "[task]"`, `disable-model-invocation: true`, `$ARGUMENTS` carries the task)
     [verified_doc: code.claude.com/docs/en/skills]; a user-authored `uok` skill is kept untouched;
   - merges `.claude/settings.json`: adds the hook and the deny/ask rules, keeps everything else;
   - adds the ignore entries;
   - runs the hook test suite and a smoke event.
4. Restart the session. Re-running is idempotent; it is also the upgrade path.

Default mode is `standard`. Use `strict` only when workers must be sandboxed.

## 13. Verification procedure

- Level 2: the installer's summary shows `hook test suite: OK` and `smoke event … PASS`.
- Level 3 (new session):
  - `/uok <small read-only task>` expands the skill and runs the kit lifecycle;
  - dispatch `uok-research-analyst` read-only and confirm the result;
  - have a worker attempt a write to `.claude/settings.json` (must be denied);
  - with a claims file, a write outside the claim must be denied;
  - a sensitive command from `uok-release-integration` must produce a prompt;
  - in headless mode, `claude -p` must answer.
  Record each probe as `verified_live`.
- Level 4: a real task package (implement → test → independent review) end to end.
- Canonical probe list: ../../validation/COMPATIBILITY-TESTS.md §3.
