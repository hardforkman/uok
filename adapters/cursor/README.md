# Adapter: Cursor (IDE / CLI)

Kit version: 1.0.0 · Spec version: 1.0.0 · Maturity: implementation_available
Research date: 2026-11-16 · Sources: cursor.com/docs (official)
Cursor's agent surface changes quickly; several items below are `unverified`
or `not_found`. Treat this adapter as discovery-heavy: audit before binding.

## 1. Environment discovery

- Detect: Cursor IDE installation; `command -v cursor-agent` (CLI binary
  name `unverified` — docs show `agent -p` usage); `.cursor/` directory;
  `AGENTS.md` in repo root.
- Inspect read-only: `.cursor/rules/`, `.cursor/hooks.json` (or user-level
  hooks config), IDE settings for model selection, MCP config.
- Modes: IDE agent chat, background/parallel agents (IDE feature,
  `unverified`), CLI headless. Verify each mode you use.

## 2. Native agent capabilities

- Custom subagent definition files: `not_found` in docs reviewed
  (agent overview, rules, hooks pages). Cursor historically exposes "modes"
  and custom prompts rather than file-defined subagents — `unverified`.
- Kit mapping: implement roles as **rule-scoped role prompts**
  (`.cursor/rules/uok-role-<role>.mdc`, `trigger: manual` / Agent Requested)
  plus orchestrator-driven sequential role sessions. If your Cursor version
  exposes native multi-agent features, re-audit and prefer them (ARCH-03).

## 3. Model selection

- IDE: user picks a model per task; Cursor handles optimizations
  [verified_doc: cursor.com/docs/agent/overview]. Per-agent model binding:
  `not_found`. CLI: `--model` flag [verified_doc: cursor.com/docs/cli/overview].
- Kit mapping: tier routing degrades to (a) CLI `--model` per role session
  where headless is used, or (b) human/orchestrator model switching between
  tasks in the IDE. Record the degradation (fallback ladder §4). Model ids
  use Cursor's `id[params]` style (secondary research, `unverified`) — probe
  the actual list; never hardcode.

## 4. Custom agent support

- No file-defined subagent format confirmed ⇒ install roles as rules:
  `.cursor/rules/uok-orchestrator.mdc` (`alwaysApply: true`) carrying kit
  obligations; per-role `.mdc` files with `description` triggers
  (Agent Requested) and role prompts (permissions expressed as instructions
  AND enforced via hooks where possible).
- Frontmatter fields: `description`, `globs`, `alwaysApply`
  [verified_doc: cursor.com/docs/context/rules]. Rule types: Always Apply,
  Apply Intelligently, Apply to Specific Files, Apply Manually.

## 5. Parallel execution

- Native parallel dispatch: `not_found` in reviewed pages. IDE background
  agents / worktrees: `unverified` (feature exists in product marketing;
  confirm in your version's docs/changelog).
- Kit mapping: sequential execution by default; if worktrees are available,
  run role sessions per worktree via CLI and coordinate merges
  (release_integration). Claim ledger still mandatory (LC-03/04).

## 6. Tool integration

- MCP supported (IDE settings; exact config path `unverified`).
- Tool allowlists per role: enforced via hooks (deny) + role instructions;
  no per-agent tool frontmatter confirmed ⇒ defense in depth required.

## 7. Context management

- Rules: `.cursor/rules/*.mdc` with frontmatter; `AGENTS.md` plain-markdown
  alternative with nested-directory support; User Rules global.
  [verified_doc: cursor.com/docs/context/rules]
- Kit binding: `AGENTS.md` marked section + `uok-orchestrator.mdc`
  (alwaysApply). Envelope discipline per task (ISO-03) since native subagent
  context isolation is unconfirmed.

## 8. Permissions

- IDE approval prompts for terminal/edit actions (`unverified` details).
- Headless caution: approval prompts in non-interactive runs are denied or
  rejected (secondary research, `unverified`) ⇒ sensitive tasks must
  ESCALATE in headless mode, never auto-proceed.
- Kit mapping: hooks deny rules + orchestrator G1 checks; SEC-07 gates
  enforced by blocking, not by prompts.

## 9. Hooks and events

- `hooks.json` at project or user level; hooks can block via exit code 2 or
  deny permissions [verified_doc: cursor.com/docs/agent/hooks]. Full event
  list and schema: `unverified` — read the page before registering.
- Kit G1: pre-tool-use-style hook (exact event name to confirm) denying
  out-of-claim writes and ungranted cross-project reads.

## 10. External API integration

- CLI headless: `agent -p "prompt"` with `--model`
  [verified_doc: cursor.com/docs/cli/overview]. Use for scripted role
  sessions and external-runtime fallback.
- Provider APIs per registry `auth_env` for tiers Cursor cannot select.

## 11. Limitations

- **Hook failure** [verified_doc 2026-11-17]: the hook entry sets `failClosed: true` (crash, timeout or no output blocks) and
  `timeout: 120`; the command also ends in `|| exit 2`. Live probes b, c and /uok are still open (see the Cursor report).
- Hook `ask` is documented but NOT honored live (Cursor 3.27.22, 2026-11-17):
  G1 returned the documented `{"permission": "ask"}` for `git push --force`,
  yet the host executed the command with no human prompt (twice). G1 therefore
  fails closed: on Cursor every `ask` becomes `deny` with "the human must run
  it" (same policy as Codex). SEC-07 is preserved as a block, not an interactive
  prompt; the human runs sensitive commands in their own terminal.
- `beforeReadFile` fires only for EXISTING files (the event carries file
  content). A Read of a missing secret-named path short-circuits in the host
  with "File not found" before any hook — nothing leaks, but there is no G1
  deny line. Probe SEC-02 reads with an existing (inert) fixture file.
- No confirmed file-defined subagents ⇒ multi-agent orchestration degrades
  to rule-scoped role sessions (record it).
- No confirmed per-agent model binding in IDE ⇒ tier routing degrades to
  session-level selection (record it).
- Parallelism unconfirmed ⇒ default sequential; worktree strategy only if
  verified in your version.
- Fast-moving product: every `unverified` item MUST be re-audited at
  installation time; this profile is a starting matrix, not a promise.

## 12. Installation procedure

Primary path: type `uok init` (or `/uok-init`) in the project session — the user-level `uok-init`
skill (registered once by `python3 UNIVERSAL-ORCHESTRATOR-KIT/uok bootstrap`; global skills live in
`~/.cursor/skills/` [verified_doc: cursor.com/docs/agent/chat/commands]) runs
`python3 UNIVERSAL-ORCHESTRATOR-KIT/uok init --host cursor`, which dispatches to this installer.

Direct invocation from the project root (additive, idempotent, backups in `.orchestrator/backups/`):

```bash
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/cursor/install.py --dry-run
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/cursor/install.py
```

It writes the marked section in `AGENTS.md`, `.cursor/rules/uok-orchestrator.mdc` (`alwaysApply: true`), and one `.cursor/rules/uok-role-<role>.mdc` per role (Agent Requested by description). It also writes the launcher skill `.cursor/skills/uok/SKILL.md` — invoke with `/uok` in Agent chat and put the task in the same message (Cursor does not expand arguments into the skill file) [verified_doc: cursor.com/docs/agent/chat/commands]. A user-authored `uok` skill is kept untouched. It also writes `.orchestrator/` with policy files and the shared G1 hook. In `.cursor/hooks.json` (version 1) it registers the hook for `beforeShellExecution`, `beforeMCPExecution`, `beforeReadFile` and `preToolUse` (file writes), with `--format cursor` and `failClosed: true` [verified_doc: cursor.com/docs/agent/hooks]. User hooks and rules are kept.

Degradations (the installer prints them): roles are rules run one at a time; hook input has no agent identity, so worker-only rules are instructions; there is no per-role model binding. The `preToolUse` input fields for file writes are `unverified` and are checked live (§13).

## 13. Verification procedure

- Level 2: rules load (check rule visibility in IDE settings); `/uok` appears in the chat
  command list; backups intact.
- Level 3 safe probes: a TIER-1 trivial task in a scratch dir; hook denial
  probe; approval-gate probe (simulated sensitive op must block); CLI
  `agent -p` read-only probe with `--model`. Tag `verified_live` per probe.
- Level 4: implement → test → review package with human or second-session
  review (independence degradation recorded).
- Canonical probes: ../validation/COMPATIBILITY-TESTS.md §3.