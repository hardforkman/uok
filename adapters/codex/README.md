# Adapter: Codex (OpenAI — CLI / IDE / cloud)

Kit version: 1.0.0 · Spec version: 1.0.0 · Maturity: implementation_available
Research date: 2026-11-16 · Sources: developers.openai.com/codex (308-redirects
to learn.chatgpt.com/docs — both are official; cite the final URL).

## 1. Environment discovery

- Detect: `command -v codex`; `~/.codex/` (user), `.codex/` (project);
  `AGENTS.md` in repo root.
- Inspect read-only: `~/.codex/config.toml`, `.codex/config.toml`,
  `$CODEX_HOME/*.config.toml` profiles, `hooks.json` if present, `AGENTS.md`.
- Modes: interactive TUI, IDE extension, cloud tasks, `codex exec`
  (non-interactive). Capabilities differ per mode — verify each.
- Note: docs moved (308) from developers.openai.com/codex/* to
  learn.chatgpt.com/docs/* during research; older links may 404 at the new
  host if paths changed — navigate from the CLI docs root.

## 2. Native agent capabilities

- Subagents: supported. Users can delegate focused work to specialized
  agents; `/subagents` command; parallel execution for e.g. codebase
  exploration; local clients allow agents with different model
  configurations. [verified_doc: learn.chatgpt.com/docs/agent-configuration/subagents]
- Definition file format/location: `not_found` in the reviewed page —
  inspect `config.toml` `agents.*` keys and current docs at installation.
- Nesting limits: `not_found` (`unknown`) — flatten hierarchies.
- Concurrency control: `agents.max_concurrent_threads_per_session`.
  [verified_doc: config reference]

## 3. Model selection

- `model` key in config.toml (value must be available to your account);
  `/model` interactive command chooses model + reasoning effort.
  [verified_doc: CLI page, config reference]
- Subagent defaults: `agents.default_subagent_model`,
  `agents.default_subagent_reasoning_effort`. [verified_doc: config reference]
- Per-subagent model configuration exists in local clients
  [verified_doc: subagents page]; exact mechanism `unverified` — probe.
- Kit tier mapping: TIER-1 → fast/mini model + low effort; TIER-2 → standard
  model; TIER-3 → flagship + high effort; TIER-4/5 → strongest available.
  Bind via profiles (§7) or subagent config after probing actual model names.
  `model_reasoning_effort` top-level key: widely used historically but
  `not_found` in the reviewed excerpt — confirm exact key before writing.

## 4. Custom agent support

- `agents.enabled` toggles the subsystem. [verified_doc: config reference]
- Kit mapping: define role agents through the CURRENT subagent definition
  mechanism (audit step 4 of the directive); until confirmed, fall back to
  profile-scoped role sessions: one `$CODEX_HOME/uok-<role>.config.toml`
  profile per role with model/effort/sandbox settings, invoked via
  `codex exec --profile uok-<role>`. Profiles live next to config.toml as
  `$CODEX_HOME/profile-name.config.toml`, selected with `--profile`.
  [verified_doc: config reference]

## 5. Parallel execution

- Subagents run in parallel [verified_doc: subagents page]; bounded by
  `agents.max_concurrent_threads_per_session` [verified_doc: config reference].
- Kit rule: dependencies satisfied + disjoint write claims; use git
  worktrees per writer (Codex cloud has worktree-style task isolation
  `unverified`); claim ledger mandatory.

## 6. Tool integration

- MCP: `codex mcp` adds/inspects local or remote servers.
  [verified_doc: CLI page]
- Tool permissions: sandbox + approval policy (§8); per-agent tool
  allowlists `unverified` — enforce via hooks + sandbox where unavailable.

## 7. Context management

- `AGENTS.md` supported; `/init` generates it. [verified_doc: CLI page]
  Discovery locations/precedence: `not_found` in reviewed excerpt — confirm
  at `learn.chatgpt.com/docs/agent-configuration/agents-md` (navigate from
  docs root). Common convention: repo root + nested dirs (`unverified`).
- Kit binding: marked section in `AGENTS.md`; per-task envelopes; subagent
  contexts consume their own model/tool work (token cost grows — record in
  metrics). [verified_doc: subagents page]

## 8. Permissions

- `approval_policy`: `on-request | never` (plus granular keys
  `sandbox_approval`, `rules`, `mcp_elicitations`, `request_permissions`,
  `skill_approval`); `untrusted` unsupported; `on-failure` deprecated.
  [verified_doc: config reference]
- `codex exec` defaults to a **read-only sandbox**; flags `--sandbox`,
  `--json`, `--skip-git-repo-check`; `--full-auto` is NO LONGER supported.
  [verified_doc: learn.chatgpt.com/docs/non-interactive-mode]
- Sandbox modes (`sandbox_mode` values) `not_found` in reviewed excerpt —
  read the sandboxing page before configuring writes.
- Kit mapping: workers get workspace-write sandbox scoped to claimed paths
  where supported; sensitive ops (SEC-07) never auto-approved — orchestrator
  blocks and escalates; `approval_policy: never` is forbidden for
  kit-managed mutating tasks.
- Project-local `.codex/config.toml` ignores `model_provider`/`model_providers`
  keys [verified_doc: config reference] — provider config stays user-level.

## 9. Hooks and events

- `features.hooks` enables lifecycle hooks from `hooks.json` or inline
  `[hooks]`. [verified_doc: config reference] Event names/schema:
  `unverified` — read the hooks page before registering.
- Kit G1: blocking pre-tool hook denying out-of-claim writes / ungranted
  cross-project reads, once the event schema is confirmed.

## 10. External API integration

- `codex exec` for pipelines and scripted role sessions (read-only default;
  explicit `--sandbox` for writes). [verified_doc: non-interactive-mode]
- OpenAI-compatible provider APIs per registry `auth_env`; cross-family
  review models via external runtime when only one provider is configured.

## 11. Limitations

- Subagent definition format not confirmed in reviewed docs ⇒ profile-based
  role sessions are the reliable fallback (record degradation if used).
- `--full-auto` removed; older tutorials are stale — do not follow them.
- exec default read-only: implementation tasks need explicit sandbox config;
  forgetting it yields silent no-op "successes" — G2 evidence checks catch this.
- Nesting depth unknown; reasoning-effort key name must be confirmed.
- Cloud vs CLI vs IDE capability drift: verify per mode.

## 12. Installation procedure

Run the installer from the project root (additive, idempotent, backups in `.orchestrator/backups/`):

```bash
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/codex/install.py --dry-run
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/codex/install.py --models tier1=<model>,tier2=<model>,tier3=<model>,review=<model>
```

It writes `.codex/agents/uok_<role>.toml` (`name`, `description`, `developer_instructions`, and an optional `model`; `[features] shell_tool = false` for shell-less roles) [verified_doc: learn.chatgpt.com/docs/agent-configuration/subagents]. It also writes the marked section in `AGENTS.md`, `.orchestrator/` with policy files, and the shared G1 hook. It registers PreToolUse in `.codex/hooks.json` with `--format codex` [verified_doc: learn.chatgpt.com/docs/hooks]. Without `--models` the agents inherit the session model.

After installing, trust the project `.codex/` layer and review/trust the hook with `/hooks`: Codex skips untrusted hooks.

Degradations: PreToolUse cannot ask, so SEC-07 operations are denied with a "human must run it" reason. Hook input has no subagent identity. Sandbox and approval settings cannot be set per agent.

## 13. Verification procedure

- Level 2: profiles parse (`codex --profile uok-orchestrator` dry check);
  backups intact.
- Level 3 safe probes: `codex exec --json "list files in ."` (read-only
  default) as TIER-1 probe; subagent dispatch probe if enabled; hook denial
  probe in scratch dir; approval-gate probe (simulated sensitive op must
  block). Tag `verified_live` per executed probe.
- Level 4: implement → test → review package with worktree isolation and
  recorded evidence.
- Canonical probes: ../validation/COMPATIBILITY-TESTS.md §3.