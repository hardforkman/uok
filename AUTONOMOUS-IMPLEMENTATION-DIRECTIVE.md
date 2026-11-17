# AUTONOMOUS IMPLEMENTATION DIRECTIVE

Kit version: 1.0.0 · Spec version: 1.0.0
Audience: the receiving AI coding agent, in ANY environment.
This directive is independently executable. No knowledge of the authoring
application or conversation is required.

## Operating rules

- Continue from inspection into implementation. Do NOT stop after producing a
  plan unless blocked by a missing permission, unavailable dependency, or an
  explicit safety restriction — and then state the exact blocker.
- Never fabricate completed integrations, successful tests, or capabilities.
  Every claim carries a verification status (spec §6).
- Preserve existing user configuration and project behavior (NS-10). Read
  before writing; extend or merge, never blindly overwrite. Back up any file
  you modify.
- Human approval gates (SEC-07) apply to YOUR installation work too: no
  production changes, credential changes, or destructive operations without
  explicit approval.
- Work in the phases below, in order. Record evidence as you go; you will need
  it for the installation report.

## Step 1 — Identify your environment

Determine which product/runtime you are running in (e.g. Claude Code, Qoder
CLI/Desktop, Cursor, Codex CLI/IDE, or other). Evidence: your own tool
inventory, config directories present (`.claude/`, `.qoder/`, `.cursor/`,
`.codex/`), CLI availability (`command -v claude qoder cursor-agent codex`),
environment variables. If none matches, use
[adapters/universal/README.md](adapters/universal/README.md).

## Step 2 — Inspect existing configuration

Read (do not modify yet): project instruction files, agent definitions,
settings/permission files, hook configs, MCP configs, model selection state.
The adapter README for your environment lists exact paths to inspect.
Record what exists, what is user-authored, and what must be preserved.
NEVER copy secrets into notes, logs, or the report.

## Step 3 — Read the complete universal specification

Read, in order: NORTH-STAR.md → UNIVERSAL-ORCHESTRATION-SPEC.md → all of
core/ → all of protocols/ → adapters/ADAPTER-IMPLEMENTATION-SPEC.md → your
adapter → templates/ → validation/. Do not implement from summaries.

## Step 4 — Audit current orchestration capabilities

For each capability in the adapter's capability matrix, determine the actual
state in THIS environment: native subagents? per-agent model selection?
parallel dispatch? hooks that can block? permission modes? worktree
isolation? headless invocation? MCP? Probe safely (read-only checks, `--help`,
config inspection). Tag each: `verified_local`, `verified_doc`, `unverified`,
`unknown`, or `not_found`.

## Step 5 — Produce the capability matrix

Fill a copy of your adapter's `PROFILE.yaml` with observed statuses and
evidence (file paths, command outputs — redacted). This matrix is the source
of truth for gap analysis; do not assume doc claims hold in your runtime
version (TUI vs headless vs SDK can differ).

## Step 6 — Identify implementation gaps

Map each universal requirement (ARCH/RT/LC/ISO/SEC/QA/PROT) to: fully
supported natively / supported with adaptation / unsupported. For each gap
choose the strongest supported alternative per
[adapters/ADAPTER-IMPLEMENTATION-SPEC.md](adapters/ADAPTER-IMPLEMENTATION-SPEC.md)
§4 (fallback ladder). Record degradations explicitly (e.g. "no native
per-agent model selection ⇒ single session model; tier routing degrades to
role routing").

## Step 7 — Prepare the implementation plan

A short ordered plan: files to create/modify (with backups), native features
to configure, fallback mechanisms to implement, validation to run. If the
environment requires approval for config changes, request it here.

## Step 8 — Implement the native adapter

If your adapter ships an installer (`adapters/<env>/install.py`), run it with
`--dry-run`, review the plan, then run it; it covers steps 8-12 and prints what
it changed and verified. Otherwise create the adapter artifacts manually.

Create the adapter artifacts in the target project/user config:
- instruction-file section or rules that bind the agent to this kit's
  lifecycle, routing, isolation, and gates;
- native agent definitions for the roles in AGENT-CAPABILITIES.yaml that your
  environment supports (map tier → environment model selector; map
  permissions → native tool allowlists);
- hooks/permission rules enforcing G1 checks where supported;
- the kit's `orchestrator/` working directory (task ledger, audit log,
  routing history) in a location that does not pollute the user's source tree
  (default: `.orchestrator/` at project root, git-ignored).

## Step 9 — Configure models and agents where supported

Copy templates/ into the project config location your adapter specifies.
Fill MODEL-CONFIG.yaml from ACTUAL available models (probe the environment's
model list; mark anything unconfirmed `unverified`). Never invent model ids,
pricing, or capabilities. Bind roles to tiers, not to hardcoded model names.

## Step 10 — Implement missing orchestration mechanisms where feasible

For gaps without native support, implement the documented fallback:
file-based task ledger + claim ledger (universal adapter), sequential
execution with role switching, human-review substitution for independent
review, etc. Feasible means: works with your actual tool permissions. If not
feasible, record `not_implemented` with the reason — do not fake it.

## Step 11 — Preserve existing configuration

Diff every touched file against its backup. User-authored agents, rules,
hooks, and settings must remain functional. If a merge conflict of intent
exists (user rule vs kit rule), the user's explicit instruction wins; record
the deviation.

## Step 12 — Run validation and compatibility tests

1. `python3 validation/self_test.py` — kit integrity (must pass).
2. `python3 validation/behavior_tests.py` — reference-kernel behavior (must pass).
3. Live compatibility checks from
   [validation/COMPATIBILITY-TESTS.md](validation/COMPATIBILITY-TESTS.md) §3
   for your environment: execute the safe subset (read-only routing dry-runs,
   a trivial TIER-1 task, an approval-gate probe). Tag results
   `verified_live` only when actually executed. Never run destructive or
   production-affecting probes without approval.

## Step 13 — Produce the installation report

Fill [handoff/INSTALLATION-REPORT-TEMPLATE.md](handoff/INSTALLATION-REPORT-TEMPLATE.md)
completely: capability matrix, gaps, degradations, files changed, test
results (actual outputs), maturity level per adapter
(`specification_complete` / `implementation_available` / `integration_tested`
/ `operationally_verified`), known limitations, next steps. Report incomplete
functionality honestly. An honest partial installation is a success; a
fabricated complete one is a failure.

## Blocker protocol

If blocked at any step: record the step, the exact blocker (permission
denied / dependency missing / safety restriction), the smallest action needed
to unblock (e.g. "user must approve writing `.claude/agents/`"), and continue
with any non-blocked steps. Do not retry denied actions unchanged; do not
switch identity or channels to bypass a denial.