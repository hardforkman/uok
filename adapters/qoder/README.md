# Adapter: Qoder (CLI / Desktop)

Kit version: 1.0.0 · Spec version: 1.0.0 · Maturity: integration_tested (live, 2026-11-17)
Research date: 2026-11-16 · Sources: docs.qoder.com (official)
Status tags as in ADAPTER-IMPLEMENTATION-SPEC §1.

## 1. Environment discovery

- Detect: `command -v qoder`; `.qoder/` (project) or `~/.qoder/` (user);
  `AGENTS.md` in repo root. Qoder Desktop exposes the same agent concepts
  through its UI; CLI and Desktop capabilities can differ — verify per mode.
- Inspect read-only: `~/.qoder/settings.json`, project `.qoder/`,
  `.qoder/agents/`, `.qoder/rules/`, MCP config. WARNING: settings files may
  contain plaintext API keys — never copy them into notes, logs, or reports
  (observed locally on the authoring machine, 2026-11-16).

## 2. Native agent capabilities

Subagents [verified_doc: docs.qoder.com/cli/subagent]:
- Files: `.qoder/agents/*.md` (project), `~/.qoder/agents/*.md` (user);
  temporary injection via `--agents` JSON flag (process-scoped, highest
  priority). Markdown + YAML frontmatter; `name` field defines the name.
- Required frontmatter: `name`, `description`. Optional: `tools` (allowlist),
  `disallowedTools` (denylist), `model` (`inherit` default, or `auto`, `lite`,
  `efficient`, `performance`, or a model name), `permissionMode` (`default`,
  `acceptEdits`, `bypassPermissions`, `dontAsk`, `auto`, `plan`), `maxTurns`,
  `timeoutMins`, `isolation: worktree`, `background: true`, scoped `hooks`
  (e.g. `PreToolUse`, `Stop`), `mcpServers`.
- Invocation: natural language ("Use the X subagent…"), `@name` mention,
  `--agent <name>` to make an agent the main session agent; headless
  `qoder -p "Use the X subagent…"`.
- Each subagent has isolated conversation context, system prompt, tool
  registry, and transcript → native ISO-03 support.
- Nesting: a subagent can call another if the `Agent` tool is available;
  `Agent(name)` syntax restricts callees. Hard depth limit: not found in docs
  (`unknown`) — kit policy: flatten hierarchies at the orchestrator anyway.

## 3. Model selection

- Per-agent `model` frontmatter with tier-style selectors: `auto`, `lite`,
  `efficient`, `performance` (plus `inherit`). [verified_doc: subagent page]
- Kit tier mapping (default proposal; confirm available tiers in your
  account via the model selector): TIER-1 → `lite`/`efficient`; TIER-2 →
  `efficient`/`auto`; TIER-3 → `performance`; TIER-4/TIER-5 → `performance`
  or a named specialist model where exposed. These are environment
  selectors, not architectural dependencies (RT-04).
- Tier names/availability change over time (retirement notices exist in
  docs) — probe before binding; record `unverified` until probed.

## 4. Custom agent support

Map kit roles → `.qoder/agents/uok-<role>.md`:
- `tools`/`disallowedTools` = role allowlist (reviewers: `[Read, Grep, Glob]`,
  disallow Write/Edit) — native SEC-04.
- `permissionMode: default` for workers; NEVER `bypassPermissions` for
  kit-managed agents (SEC-01/10).
- `maxTurns`/`timeoutMins` = lifecycle timeouts (EXECUTION-LIFECYCLE §3).
- `isolation: worktree` for parallel writers (LC-04 native_isolation).
- Body = role prompt + envelope checks + evidence-based result semantics.

## 5. Parallel execution

- "Qoder CLI can dispatch independent Subagents in parallel."
  [verified_doc: subagent page] Background agents (`background: true`,
  feature must be enabled) notify the main session on completion.
- Kit rule: parallel only with satisfied dependencies + disjoint write
  claims; prefer `isolation: worktree` per writer + release_integration
  merge coordination.

## 6. Tool integration

- Per-agent tool allow/deny lists (frontmatter) and per-agent `mcpServers`.
  [verified_doc] MCP servers also configurable globally
  (`docs.qoder.com/cli/mcp-servers`). Skills extend capabilities
  (`docs.qoder.com/cli/Skills`).
- Map `required_tools` onto agent allowlist ∩ project permission config.

## 7. Context management

Instruction/memory files [verified_doc: docs.qoder.com/cli/memory]:
- Default context file: `AGENTS.md` (NOT QODER.md); rename via
  `context.fileName` setting. Locations: `~/.qoder/AGENTS.md` (user),
  `<project>/AGENTS.md` (team), `<project>/AGENTS.local.md` (private),
  `.qoder/rules/**/*.md` (project rules), `~/.qoder/rules/**/*.md` (user).
- Loading: user level first; project search upwards from cwd, stops at the
  `.git` directory; subdirectory memory loads on demand.
- Rules frontmatter `trigger`: `always_on` (default), `manual`,
  `model_decision`, `glob`/`paths`.
- Imports: `@path/to/file`, relative to the importing file; project memory
  imports are restricted to project boundaries by default (native ISO-02
  support); recursion depth-limited.
- Kit binding: marked section in `AGENTS.md` + a `.qoder/rules/uok.md`
  (`trigger: always_on`) carrying lifecycle/routing/gate obligations.

## 8. Permissions

- `permissionMode` per agent (values in §2). [verified_doc]
- Global permission configuration and hooks can strictly block
  commands/tools/paths (`docs.qoder.com/cli/permissions`). [verified_doc:
  existence; exact rule syntax unverified — read the page before writing]
- Headless caution: in non-interactive runs, `ask`-style prompts cannot be
  answered and resolve to deny (secondary research finding, `unverified` —
  confirm in permissions docs). Design G1 so denials are the safe default.
- SEC-07 gates: orchestrator blocks sensitive tasks and asks the human in
  the interactive session; in headless runs such tasks must ESCALATE, never
  auto-proceed.

## 9. Hooks and events

- CLI hooks: `docs.qoder.com/cli/hooks` + `/cli/hooks-reference`; Desktop
  hooks: `/qoder/hooks`. Scoped per-agent hooks in frontmatter (`PreToolUse`,
  `Stop` observed). [verified_doc: existence + these event names; full event
  list unverified — read hooks-reference]
- Kit G1: `PreToolUse` hook denying out-of-claim writes and cross-project
  reads without grants; register additively, back up existing hook config.

## 10. External API integration

- Headless: `qoder -p "<prompt>"` [verified_doc: subagent page]; scripts/
  automation pages exist (`cli/run-in-scripts`, `cli/loop`). Agent SDK with
  permission controls (`cli/sdk/permissions`). [verified_doc: existence]
- External role sessions: spawn `qoder -p` per role with `--agent` when
  native in-session dispatch is unavailable; provider APIs per registry
  `auth_env` for cross-family review models.

## 11. Limitations

- **Hook failure is non-blocking in Qoder** [verified_doc 2026-11-24: docs.qoder.com/cli/hooks, hooks-reference]: exit
  codes other than 2 are "non-blocking error; the main flow continues", the timeout outcome is not documented, default timeout 600 s,
  and there is no fail-closed setting. The installer therefore registers the command as `python3 -I <guard> --format qoder || exit 2`
  (a crash or missing python3 blocks the call) and sets `timeout: 120`. A guard that merely hangs past the timeout is not
  covered: keep the machine's load in mind. `agent_type` is not documented for PreToolUse (worker-only rules stay instructions
  unless a live probe shows it).
- Nesting depth limit: unknown (not in docs) — flatten.
- Model tiers are abstract selectors; exact underlying models are not
  exposed → registry cost/latency metadata stays `unknown` unless measured;
  cross-family G3 independence may be unachievable natively ⇒ second
  instance or human review, recorded as degradation.
- OS-level sandbox: not found in CLI docs (`unknown`) — rely on permission
  config + hooks, and do not claim sandboxing.
- Desktop vs CLI vs headless capability drift: verify each mode used.
- Background agents require the feature to be enabled.
- Auto permission mode: the host classifier may block sensitive commands
  before the G1 `ask` reaches the human (observed live 2026-11-17,
  `git push --force` probe). To verify the human-approval round-trip, run
  the session in a prompt-surfacing mode (default), not Auto.

## 12. Installation procedure

Primary path: type `uok init` (or `/uok-init`) in the project session — the user-level `uok-init`
skill (registered once by `python3 UNIVERSAL-ORCHESTRATOR-KIT/uok bootstrap`; user skills live in
`~/.qoder/skills/` and apply to all projects [verified_doc: docs.qoder.com/cli/Skills]) runs
`python3 UNIVERSAL-ORCHESTRATOR-KIT/uok init --host qoder`, which dispatches to this installer.

Direct invocation from the project root (additive, idempotent, backups in `.orchestrator/backups/`):

```bash
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/qoder/install.py --dry-run
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/qoder/install.py --models tier1=lite,tier2=efficient,tier3=performance,review=performance
```

It writes `.qoder/agents/uok-<role>.md` (name, description, tools, `disallowedTools` for read-only roles, `model`, `permissionMode: default`). It also writes the marked section in `AGENTS.md`, `.qoder/rules/uok.md` (`trigger: always_on`), the launcher skill `.qoder/skills/uok/SKILL.md` (invoke with `/uok <task>` [verified_doc: docs.qoder.com/cli/Skills]), `.orchestrator/` with policy files, and the shared G1 hook. It registers PreToolUse in `.qoder/settings.json` with `--format qoder`. User agents and user skills with the same name are left untouched and reported. The hook uses Qoder's Claude-compatible event schema [verified_doc: docs.qoder.com/cli/hooks]; the root is resolved via `git rev-parse` at run time. Probe your model selectors before passing `--models`. Restart the Qoder session afterwards.

## 13. Verification procedure

- Level 2: files re-read; subagent visible (`@uok-…` mention resolves);
  `/uok` appears in the skill list and expands the orchestrator prompt;
  user config intact (diff backups).
- Level 3 safe probes: dispatch read-only `uok-research_analyst` via
  `qoder -p`; verify isolated result; probe hook denial with a scratch
  out-of-claim write; probe approval gate with a simulated
  `production_deploy` task (must block/escalate); parallel probe: two
  read-only agents concurrently. Tag `verified_live` per executed probe.
- Level 4: real implement → test → review package with worktree isolation.
- Canonical probes: ../validation/COMPATIBILITY-TESTS.md §3.