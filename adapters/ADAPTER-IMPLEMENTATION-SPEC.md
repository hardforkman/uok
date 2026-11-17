# ADAPTER IMPLEMENTATION SPECIFICATION

Kit version: 1.0.0 · Spec version: 1.0.0 · Requirements: ADP-01…ADP-03, ARCH-03, NS-07, NS-10

An adapter translates the universal specification (Layer A) into one
environment's native mechanisms (Layer B) and documents the actual execution
mechanisms (Layer C). Adapters never modify Layer A semantics; they map them.

## 1. Required documentation (ADP-01)

Every adapter directory MUST contain a `README.md` with ALL thirteen sections
(exact headings, checked by self_test.py):

1. Environment discovery
2. Native agent capabilities
3. Model selection
4. Custom agent support
5. Parallel execution
6. Tool integration
7. Context management
8. Permissions
9. Hooks and events
10. External API integration
11. Limitations
12. Installation procedure
13. Verification procedure

Every factual claim about the environment MUST carry a verification status
(spec §6) and, for `verified_doc`, a source URL and research date. Anything
not confirmed is `unverified`/`unknown`/`not_found` — never stated as fact.
Each adapter SHOULD also ship a `PROFILE.yaml` capability matrix (format §3).

## 2. Environment discovery procedure (generic)

The receiving agent performs, read-only:

1. Identify the product and runtime mode (TUI / IDE / headless / SDK / cloud).
   Capabilities differ per mode; verify each mode you intend to use.
2. Locate config: project dirs (`.claude/`, `.qoder/`, `.cursor/`, `.codex/`),
   user dirs (`~/.claude/`, `~/.qoder/`, `~/.cursor/`, `~/.codex/`), instruction
   files (CLAUDE.md / AGENTS.md / rules).
3. Inventory your own tool surface: is there an Agent/Task dispatch tool?
   Model selection mechanism? Hook registration? Permission prompts?
4. Probe CLIs with `--help` only (no mutating commands).
5. Record findings in the capability matrix with evidence. Never copy secrets
   from config files into notes or reports.

## 3. Capability matrix format (PROFILE.yaml)

```yaml
schema: adapter_profile
schema_version: 1
adapter: <id>
researched_at: <date>
capabilities:
  <capability_key>:
    status: unknown | unverified | verified_doc | verified_local | verified_live | not_found
    native_mechanism: <string or null>
    evidence: <source URL / local path / command>
    fallback: <strategy id from §4 or null>
```

Standard capability keys: `instruction_files`, `custom_agents`,
`per_agent_model_selection`, `parallel_dispatch`, `background_execution`,
`worktree_isolation`, `blocking_hooks`, `permission_modes`, `mcp`,
`headless_invocation`, `context_isolation`, `nesting`.

## 4. Fallback ladder (ARCH-03, ADP-02)

When a native capability is missing, implement the strongest supported
alternative, in this order, and RECORD the degradation:

| Universal need | Fallback ladder (strongest → weakest) |
|----------------|----------------------------------------|
| Multi-agent execution | native subagents → role-scoped separate sessions (headless CLI per role) → sequential role-switching in one session with explicit role headers → human-executed steps |
| Per-task model routing | per-agent model config → session-level model switch between tasks → single model + role routing (tiers degrade to roles; record it) |
| Parallel execution | native parallel dispatch → worktree-isolated sequential batches → fully sequential execution |
| Blocking enforcement (G1) | blocking hooks → permission deny rules → orchestrator-side pre-dispatch checks (envelope validation before invoking the agent) |
| Context isolation | native isolated subagent contexts → envelope discipline + scoped prompts (never paste unrelated project context) |
| Independent review (G3) | second model family → second instance same model → human review (never silent self-review) |
| Task ledger | native task system → `.orchestrator/` YAML/JSON ledger files |
| Approval gates | native approval prompts → orchestrator blocks and asks the human explicitly → task ESCALATED |

A fallback is legitimate only if it actually works with the environment's
real permissions. Otherwise mark `not_implemented` with the reason.

## 5. Installation requirements (NS-10)

1. Read existing config first; back up every file before modification.
2. Add kit artifacts additively: new agent files, new rule files, appended
   instruction sections clearly marked `<!-- UNIVERSAL-ORCHESTRATOR-KIT -->`.
3. Never delete or rewrite user-authored agents/rules/hooks. On conflict of
   intent, user instructions win; record the deviation.
4. Keep secrets out of all created files; reference env vars only.
5. Create `.orchestrator/` (tasks/, audit/, claims/) and add it to
   `.gitignore` unless the user wants it committed.
6. Adapters SHOULD ship an idempotent installer (`install.py`) that applies
   rules 1-5, supports `--dry-run`, never embeds machine-specific absolute
   paths in committed policy, installs any hook script before registering it,
   and runs the adapter's self-checks. Re-running it is the upgrade path.
7. Where the host has a native skill/command mechanism, the installer SHOULD
   create a launcher skill (`uok`) that starts the orchestration lifecycle
   (`/uok <task>`; Codex: `$uok` mention). Record the mechanism's verification
   status in PROFILE.yaml; never overwrite a user-authored skill of the same
   name; protect the skill file from worker writes like other host config.
8. The kit SHOULD offer a primary installation command (`uok init`) usable
   from a project session: a one-time bootstrap registers a user-level
   `uok-init` skill in the host's global skills directory (verified_doc per
   host), which runs the installer for the current project. Bootstrap obeys
   rules 1-4 as well (additive, backups, user files preserved).
9. Installation itself obeys SEC-07: modifying credential/access-control
   config or anything production-affecting needs explicit human approval.

## 6. Verification requirements (ADP-03)

Verification proceeds in levels; report the highest level actually reached:

1. **specification_complete** — README + PROFILE exist, self_test passes.
2. **implementation_available** — artifacts installed; re-read them and diff
   against intent; existing config still intact.
3. **integration_tested** — execute the safe compatibility checks
   (../validation/COMPATIBILITY-TESTS.md §3): agent registration visible to
   the runtime, a TIER-1 dry-run task, an approval-gate probe, a parallel
   dispatch probe with disjoint claims. Tag `verified_live` per check.
4. **operationally_verified** — a real multi-task work package routed,
   executed, validated, and accepted end-to-end with evidence.

Never report a level without its evidence. Headless/TUI/SDK differences MUST
be noted per check (a capability verified in TUI is not verified headless).

## 7. Adapter inventory

| Adapter | Target | Profile |
|---------|--------|---------|
| claude-code | Claude Code (CLI/IDE) | [claude-code/README.md](claude-code/README.md) |
| qoder | Qoder CLI / Qoder Desktop | [qoder/README.md](qoder/README.md) |
| cursor | Cursor IDE / Cursor CLI | [cursor/README.md](cursor/README.md) |
| codex | OpenAI Codex CLI / IDE / cloud | [codex/README.md](codex/README.md) |
| universal | any other compatible environment | [universal/README.md](universal/README.md) |

All five ship at `specification_complete`. Higher levels are achieved by the
receiving agent during installation, per §6, and recorded in the installation
report.