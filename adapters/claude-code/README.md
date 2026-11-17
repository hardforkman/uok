# Adapter: Claude Code

Kit version: 1.0.0 · Spec version: 1.0.0 · Maturity: specification_complete
Research date: 2026-11-16 · Sources: code.claude.com/docs (official)
Status tags: `verified_doc` = read in official docs on the research date;
`unverified` = plausible but not confirmed this session; re-verify locally.

## 1. Environment discovery

- Detect: `command -v claude`; presence of `.claude/` (project) or
  `~/.claude/` (user); `CLAUDE.md` in repo root. [unverified: exact binary
  name/flags — confirm with `claude --help`]
- Runtime modes: interactive TUI, IDE extension, headless (`-p` print mode),
  SDK. Verify capabilities per mode; headless still runs project hooks and
  `.mcp.json` servers with no interactive trust dialog. [unverified — confirm
  in docs `code.claude.com/docs/en/headless` and locally]
- Inspect read-only: `.claude/settings.json`, `.claude/settings.local.json`,
  `~/.claude/settings.json`, `.claude/agents/`, `.mcp.json`, `CLAUDE.md`.
  Never copy secrets found there into notes.

## 2. Native agent capabilities

- Subagents: markdown files with YAML frontmatter in `.claude/agents/`
  (project) and `~/.claude/agents/` (user). Frontmatter fields: `name`,
  `description`, `tools`, `model`. [verified_doc: code.claude.com/docs/en/sub-agents]
- Invocation: natural-language delegation, `@`-mention, or `--agent` flag.
  [verified_doc: same]
- Each subagent runs in its own context window; intermediate output does not
  clutter the main conversation → maps to ISO-03 context isolation.
  [verified_doc: same]
- Nesting: permitted up to three layers by default. [verified_doc: same —
  re-verify for your version; kit policy: orchestrator spawns workers;
  workers do not spawn further orchestrators]

## 3. Model selection

- Per-agent `model` frontmatter: aliases (e.g. `sonnet`, `opus`, `haiku`,
  `fable`) or full model IDs. [verified_doc: sub-agents page]
- Tier mapping (configure in MODEL-CONFIG.yaml after probing your account):
  TIER-1 → fast alias; TIER-2/TIER-3 → standard/advanced alias; TIER-5 →
  strongest available reasoning model, ideally a different family than the
  implementer. Aliases are environment conveniences, NOT architectural
  dependencies (RT-04): the registry binds tiers to whatever your account
  exposes.
- Session-level model switching exists (`/model`); exact behavior `unverified`.

## 4. Custom agent support

Map kit roles → `.claude/agents/<role>.md`:
- `name` = role id; `description` = role responsibilities + "use for …"
  triggers (drives implicit delegation).
- `tools` = role allowlist (SEC-04): reviewers get read-only tools;
  implementation roles get edit/write + restricted shell.
- `model` = tier binding from MODEL-CONFIG.yaml.
- Body = role prompt: responsibilities, expected outputs, validation rules,
  envelope checks (HANDOFF-CONTRACT §1), injection resistance (SEC-05),
  and "report via result_submit semantics with evidence".
Install additively; never overwrite user-authored agent files (NS-10).

## 5. Parallel execution

- Background subagents run concurrently. [verified_doc: sub-agents page]
- Kit rule: dispatch parallel workers only with satisfied dependencies and
  disjoint write claims (LC-03/04). Use the `.orchestrator/claims/` ledger or
  git worktrees per writer; Claude Code worktree conventions exist
  [unverified — confirm docs]. Merge via release_integration role.

## 6. Tool integration

- `tools` frontmatter allowlists per agent. [verified_doc]
- MCP servers via `.mcp.json` (project) and user config. [unverified: exact
  schema — confirm `code.claude.com/docs/en/mcp`]
- Map `required_tools` (tool plane) onto the union of agent allowlist ∩
  project permission rules; deny-by-default for anything undeclared.

## 7. Context management

- Instruction files: `CLAUDE.md` (project root or `.claude/`),
  `CLAUDE.local.md`, `~/.claude/CLAUDE.md`, enterprise-managed locations;
  loaded broadest→most-specific; `@path` imports (≤4 hops).
  [verified_doc: code.claude.com/docs/en/memory]
- Kit binding: append a marked section to project `CLAUDE.md` pointing to
  the kit and `.orchestrator/` ledger; keep per-task context in envelopes,
  not in global memory (ISO-03). Subagent context isolation is native (§2).

## 8. Permissions

- Settings files: `~/.claude/settings.json`, `.claude/settings.json`
  (+ `.local`). `permissions.deny` and
  `permissions.blockReadsOutsideWorkingDirectories` observed in docs;
  full allow/ask rule syntax `unverified` — confirm
  `code.claude.com/docs/en/settings` / `iam` before writing rules.
- Kit mapping: project grants → permission rules; sensitive operations
  (SEC-07) → deny rules + orchestrator approval gate (never auto-approve).
- Plan mode exists as a behavioral mode. [verified_doc: memory page mention]

## 9. Hooks and events

- Config: `~/.claude/settings.json`, `.claude/settings.json`. Events include
  `PreToolUse`, `PostToolUse`, `SessionStart` (full list `unverified` — see
  `code.claude.com/docs/en/hooks`). Matchers: exact strings, `|`, regex.
  Hooks block via exit code 2 or JSON `permissionDecision: "deny"`.
  [verified_doc: hooks page]
- Kit G1 enforcement: `PreToolUse` hook denying (a) writes outside claimed
  paths, (b) reads of other projects without a grant, (c) secret-pattern
  content in outbound payloads where feasible. Hook scripts live in
  `.orchestrator/hooks/` and are registered additively.

## 10. External API integration

- Headless mode (`claude -p`) for scripted role sessions [unverified: exact
  flags]; SDK for programmatic orchestration [unverified].
- Provider APIs for TIER routing outside the session: use registry
  `auth_env` references; the kit never stores keys.
- Use external runtimes only when native subagents cannot satisfy a plane
  (fallback ladder, ADAPTER-IMPLEMENTATION-SPEC §4).

## 11. Limitations

- Nesting depth capped (3 by default, verified_doc) — deep hierarchies must
  be flattened by the orchestrator.
- Per-agent model selection is alias/ID-based; cross-family independence for
  G3 requires a second provider configured — if unavailable, degrade to
  second instance or human review and record it.
- Headless mode has no interactive trust dialog: approval gates MUST be
  enforced by hooks/permission rules + orchestrator blocking, not by prompts.
- Anything tagged `unverified` above is a research gap, not a product claim.

## 12. Installation procedure

1. Follow AUTONOMOUS-IMPLEMENTATION-DIRECTIVE steps 1–7 (discover, audit,
   matrix, gaps, plan).
2. Back up `.claude/settings.json`, `CLAUDE.md`, existing agents.
3. Create `.claude/agents/uok-*.md` for enabled roles (prefix avoids
   collisions with user agents).
4. Append marked kit section to `CLAUDE.md`; create `.orchestrator/`
   (tasks/, audit/, claims/, hooks/) + `.gitignore` entry.
5. Register G1 `PreToolUse` hook additively; verify it blocks a deliberate
   out-of-claim write probe in a scratch directory.
6. Fill templates → project config (MODEL-CONFIG from probed model list).
7. Run validation (step 12 of the directive).

## 13. Verification procedure

- Level 2: re-read installed files; `claude` lists the new agents
  [unverified: exact command — check `/agents` in TUI]; existing agents intact.
- Level 3 (safe probes): dispatch a read-only research subagent (TIER-1/2);
  verify isolated context returns a result; trigger the G1 hook with a
  harmless denied write; confirm approval gate blocks a simulated
  `production_deploy` task. Record `verified_live` per probe.
- Level 4: run a real 3-task package (implement → test → independent review)
  end-to-end; archive evidence in the installation report.
- See ../validation/COMPATIBILITY-TESTS.md §3 for the canonical probe list.