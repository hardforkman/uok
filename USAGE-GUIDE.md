# USAGE GUIDE — Universal Orchestrator Kit

Kit version: 1.0.0 · Spec version: 1.0.0 · Updated: 2026-11-17

A practical guide: how to verify, install, and use the kit in your project.
The kit's normative documents are in English (for portability across agents);
this guide is navigation and step-by-step procedure for a human. On any
conflict, the normative documents take precedence
([UNIVERSAL-ORCHESTRATION-SPEC.md](UNIVERSAL-ORCHESTRATION-SPEC.md)).

---

## 1. What it is

The kit is a portable standard for orchestrating AI agents and models: a task
routing policy, 11 agent roles, a task lifecycle, project isolation, security
and quality gates, an executable reference core, and tests. It is NOT a running
service: "installing the kit" means integrating its adapter into your
environment (Claude Code, Qoder, Cursor, Codex, or another) and honestly
recording what actually works.

Three layers:

- **Layer A — universal core** (`core/`, `protocols/`): rules independent of
  any application.
- **Layer B — adapters** (`adapters/`): translate the rules into the native
  mechanisms of a specific environment (subagents, hooks, rules, models).
- **Layer C — execution**: the real agents/models/tools of your environment.

### Current readiness (2026-11-17)

| Component | Status | Evidence |
|---|---|---|
| Specification + protocols (16 schemas) | specification_complete | self_test 16/16 |
| Reference core + 13 scenarios | integration_tested | behavior_tests 63/63 (after an independent audit, all 12 findings closed) |
| G1 security hook | verified_local | 123/123 tests; checked live in Claude Code |
| Skill shortcut `/uok` + `uok init` CLI | verified_local; `uok init` — verified_live in Qoder | test_install_skill 7/7, test_uok_cli 32/32; live chain bootstrap → skill → install → `/uok <task>` → worker dispatch → G1 denials (SEC-04 worker write, SEC-02 reading .env), Qoder Desktop 2026-11-17 ([report](handoff/INSTALLATION-REPORT-qoder-2026-11-17.md)); the full SEC-07 cycle (hook ask → human refusal) confirmed live in default mode; claims and two parallel workers with disjoint claims also confirmed live (report step 16); the read-only probe `uok-research-analyst` passed (step 17) — all LIVE-CHECKS items a–e closed; other environments — not yet |
| Claude Code adapter | integration_tested | live install and checks 1–12 ([report](handoff/INSTALLATION-REPORT-claude-code-2026-11-17.md)) |
| Qoder adapter | integration_tested | live checks in Qoder Desktop 2026-11-17: install via `uok init`, `/uok`, worker dispatch (read-only and writer), SEC-02/04 denials, the full SEC-07 cycle, claims and parallel workers (LC-04) — all items a–e verified_live ([report](handoff/INSTALLATION-REPORT-qoder-2026-11-17.md)); model selectors not verified (configuration gap) |
| Cursor / Codex adapters | implementation_available | Cursor: live checks 2026-11-17 partially done — ISO-02 and SEC-02 (Write) verified_live; 2 defects found (the host does not execute the hook `ask`; `beforeReadFile` only for existing files), the kit patched fail-closed (ask→deny), re-probes pending ([report](handoff/INSTALLATION-REPORT-cursor-2026-11-17.md)). Codex: CLI not installed, live checks still ahead ([prompts](handoff/LIVE-CHECKS.md)) |
| Universal adapter | specification_complete | fallback path for environments without native support |
| Real-model registry | unverified | entries are illustrative; prices/availability must be confirmed in your own environment |

No adapter is declared `operationally_verified`. A human remains mandatory for
sensitive operations.

## 2. Requirements

- Python ≥ 3.10 and PyYAML (`pip install pyyaml`) — for tests and installers.
- Target environment: Claude Code, Qoder, Cursor, Codex CLI, or any agent that
  can read files and run commands (the universal profile).
- Network and API keys are NOT needed for the tests themselves.
- Optional: the Graphify CLI (`graphifyy`, Python ≥ 3.11 via uv/pipx) for the
  context graph — see `core/CONTEXT-GRAPH.md`. Without it, the kit works in
  full.

## 3. Step 1 — verify the kit (before installation)

```bash
cd UNIVERSAL-ORCHESTRATOR-KIT
python3 validation/self_test.py        # 16 structural checks CHK-01…16
python3 validation/behavior_tests.py   # 63 behavioral checks TS-01…13
python3 adapters/shared/hooks/test_g1_guard.py   # 123 G1 hook tests
python3 adapters/shared/test_install_skill.py    # 7 installer skill-shortcut tests
python3 adapters/shared/test_uok_cli.py          # 32 uok CLI tests (init, bootstrap, updater)
```

All five commands must exit with code 0. If PyYAML is unavailable, the tests
count as `not_executed`, not "passed". After ANY change to the kit, rerun all
five suites.

## 4. Step 2 — install into a project

**Primary path — `uok init` in a project session.** Once per machine,
register the global `uok-init` skill (it works in all projects):

```bash
python3 UNIVERSAL-ORCHESTRATOR-KIT/uok bootstrap            # environments with configs in ~
python3 UNIVERSAL-ORCHESTRATOR-KIT/uok bootstrap --host all # or all four at once
```

Bootstrap creates the user-level `uok-init` skill (`~/.claude/skills/`,
`~/.qoder/skills/`, `~/.cursor/skills/`, `~/.agents/skills/` — paths checked
against the official documentation). Your own skills are not overwritten.

After a session restart, open any project and type in the agent chat:

```text
uok init
```

(or explicitly `/uok-init`; in Codex — `$uok-init`). The agent shows the plan
(`--dry-run`), performs the installation, reports the checks honestly, and
asks you to restart the session. From then on, tasks are issued via
`/uok <task>` (§6.1).

The same CLI also works in a terminal:

```bash
python3 UNIVERSAL-ORCHESTRATOR-KIT/uok init --host qoder --project /path/to/project \
    --models tier1=lite,tier2=efficient,tier3=performance,review=performance
```

`--host auto` (the default) detects the environment heuristically (environment
variables → project config directories → directories under ~); on ambiguity it
asks you to pass `--host` explicitly. The in-session skill always passes
`--host` itself.

**Fallback path — call an installer directly** (the same thing init does):

The installers are additive and idempotent: existing configs are preserved,
backups go to `.orchestrator/backups/<timestamp>/`.

```bash
# from the project root (the kit sits next to it or inside it):
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/qoder/install.py --dry-run   # preview first
python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/qoder/install.py \
    --models tier1=lite,tier2=efficient,tier3=performance,review=performance
```

Replace `qoder` with `claude-code`, `cursor`, or `codex` per your environment.

Flags (identical for all installers):

- `--project DIR` — project root (default: the parent of the kit directory);
- `--mode standard|strict` — strict additionally restricts worker shells to
  an allowlist and forbids redirections/substitutions;
- `--models tier1=…,tier2=…,tier3=…,review=…` — the real model selectors of
  YOUR account. The installer does not validate them: pass what you see in
  your environment's interface;
- `--dry-run` — show the changes without writing;
- `--graphify auto|install|off` — the Graphify context graph: `auto` (the
  default) enables the integration only if the CLI is already on PATH (no
  network); `install` additionally installs the CLI via uv/pipx (this is what
  the `/uok-init` skill does); `off` — skip. Rules CG-01…07:
  `core/CONTEXT-GRAPH.md`.

What gets created:

- `.orchestrator/` — the working tree: `policy/` (project.yaml, models.yaml,
  agents.yaml), `tasks/`, `audit/`, `claims/`, `hooks/g1_guard.py`;
- native subagents `uok-<role>` (10 roles; the orchestrator is the main
  session);
- the `uok` skill shortcut for launching orchestration (`/uok <task>`; in
  Codex — `$uok`, see §6.1);
- a marked UOK section in the instructions file (`CLAUDE.md` / `AGENTS.md`);
- the G1 PreToolUse hook in the environment settings (merged with existing
  hooks).

**After installation, restart the agent session** — subagent registries are
usually loaded at startup. Then run the live checks: for Qoder/Cursor/Codex
paste the prompt from [handoff/LIVE-CHECKS.md](handoff/LIVE-CHECKS.md) into
the chat of the corresponding app. Record the result as a report using the
[template](handoff/INSTALLATION-REPORT-TEMPLATE.md).

For environments without an installer: the agent follows
[AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md](AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md)
(13 steps) with the fallback profile
[adapters/universal/README.md](adapters/universal/README.md).

## 5. Step 3 — human review of the G1 hook

The G1 hook is the only programmatic barrier between workers and dangerous
actions. Before trusting it, complete
[handoff/HUMAN-REVIEW-G1.md](handoff/HUMAN-REVIEW-G1.md): read the code,
check deny/ask/allow on synthetic events, record the result.

What G1 does (in brief):

- denies reads of secret paths (`.env`, keys, etc.) and secret-looking
  content in writes;
- denies writes outside the task's declared resource claims (LC-04);
- protects environment configs, `.orchestrator/`, the instructions file, and
  the kit itself from worker writes;
- turns sensitive operations (`git push --force` etc.) into `ask` — a human
  decides;
- in strict mode, restricts worker shells to an allowlist.

## 6. Everyday operation

### 6.1 How to issue tasks

The main agent session is the **orchestrator**. State the task in plain
language; the orchestrator must carry it through the lifecycle:

```
RECEIVED → ANALYZED → CLASSIFIED → DECOMPOSED → DEPENDENCIES_RESOLVED
→ ROUTED → APPROVED_IF_REQUIRED → EXECUTING → VALIDATING
→ COMPLETED / FAILED / ESCALATED
```

**Quick launch — the `/uok` skill shortcut.** The installer creates it
automatically:

| Environment | Skill file | Invocation |
|---|---|---|
| Claude Code | `.claude/skills/uok/SKILL.md` | `/uok <task>` |
| Qoder | `.qoder/skills/uok/SKILL.md` | `/uok <task>` |
| Cursor | `.cursor/skills/uok/SKILL.md` | `/uok` + the task in the same message |
| Codex | `.agents/skills/uok/SKILL.md` | `$uok` + the task in the same message (not a slash) |

Example:

> `/uok Figure out how module X works (read-only), then fix Y
> in `src/y/*` and run an independent review. Report — with test output.`

The skill expands into the orchestrator prompt and carries the task through
the same cycle (classification → routing → claims → approvals → validation →
report with evidence). In Claude Code the skill is tagged
`disable-model-invocation: true` — only a human can launch it; `$ARGUMENTS`
substitutes the task text. In Cursor and Codex, arguments are not substituted
into the skill file — put the task in the same message. If the name `uok` is
already taken by one of your skills, the installer leaves it untouched and
reports this. After installation, restart the session.

**`/uok` argument routing (the first word of the task):**

| First argument | What happens |
|---|---|
| `<role>` (e.g. `/uok research-analyst …`) | Launches **only that role**, `uok-<role>`, with the task text; kit rules (claims, the G1 hook, approvals, evidence) still apply, no decomposition into subtasks. Roles: `architect`, `senior-engineer`, `implementation-engineer`, `research-analyst`, `debugging-specialist`, `test-engineer`, `security-reviewer`, `code-reviewer`, `documentation-specialist`, `release-integration` |
| `all` (e.g. `/uok all <task>`) | **All roles at once**: the orchestrator verifies that every `uok-*` role is registered, prints the roster with tiers and models, and runs the task through the full cycle with the full roster |
| `roles` | Just the list of roles with tiers and models; no task is started |
| anything else | The full orchestration cycle over the entire task text |

**Reviewer model.** The reviewer tier (TIER-5) always gets the strongest model
of the environment the kit runs in: in Claude Code that is `fable`; in the
other environments — the most capable model in the environment's list (Qoder
defaults to `performance`; Cursor and Codex are set via
`--models review=<model>`; those environments' selectors are not verified
live). If that model is unavailable (for example, credits ran out), the
orchestrator takes the next strongest available model of the environment (in
Claude Code — `opus`) and honestly flags the degradation
(`degraded_review_independence` / `degraded_model_routing`) in the report.

The skill is optional — a plain instruction works too:

> "Use uok-research-analyst to figure out how module X works (read-only).
> Then have uok-implementation-engineer fix Y, claiming `src/y/*`.
> After that, uok-code-reviewer runs an independent review. Report — with
> evidence (test output)."

### 6.2 Roles and routing

11 roles (`core/AGENT-CAPABILITIES.yaml`): orchestrator, architect,
senior_engineer, implementation_engineer, research_analyst,
debugging_specialist, test_engineer, security_reviewer, code_reviewer,
documentation_specialist, release_integration. A role ≠ a model: one model
can play several roles.

Routing is deterministic (`core/ROUTING-POLICY.md` + `routing-policy.yaml`):
task category (CAT-01…08) → base tier → complexity/reasoning/error-cost
modifiers (capped at TIER-3) → hard floors (architecture and security ≥
TIER-3, specialized ≥ TIER-4) → capability filter → ranking (reliability ↓,
cost ↑, latency, id). TIER-5 — independent review only. Candidate exhaustion
→ escalation to a human, never a silent swap to a weaker model.

### 6.3 Project configuration

After installation, edit `.orchestrator/policy/`:

- `project.yaml` — isolation, sensitive operations, the shell allowlist,
  parallelism, budget;
- `models.yaml` — real models: availability, context, prices. Fill in ONLY
  verified data (the provider's pricing page, probes); every value needs
  `evidence` and `verified_at`. Leave anything unknown as `unknown`;
- `agents.yaml` — roles, tools, tiers. Reviewer independence (a different
  model/instance) cannot be removed.

Commented templates: [templates/](templates/). The defaults are conservative:
strict isolation, auto-approval off, all six sensitive operations gated.

### 6.4 Approvals (a human is mandatory)

Explicit human approval is required for: production deploys, financial
operations, irreversible data changes, destructive infrastructure changes,
access/credential changes, unauthorized external publication. Plus CAT-07
(security) with any write.

An approval is an `approval_record` (protocols/TASK-CONTRACT.md): a specific
task, specific operations, a human's name, an expiry. An empty operation list
approves nothing; an expired approval is invalid both at execution and at
final acceptance (G4).

### 6.5 Parallel work

Only tasks without dependencies and with compatible resource claims run in
parallel: write–write and write–read overlaps are blocked (the claims
registry in `.orchestrator/claims/`). Strategies: a lock registry (the
default), a git worktree per writer, merge coordination by the
release_integration role. If no safe strategy exists, tasks are serialized,
and the report says so.

### 6.6 Project isolation

Every task belongs to one project and gets a minimal context (the context
envelope). Cross-project access happens only via an explicit grant with a
scope (specific paths, not the whole project), an expiry, and a reason; a
grant is valid ONLY from the recipient's registry, not from the envelope
itself. Secrets are never passed — redaction before every transfer.

### 6.7 Failures, waivers, acceptance

- Dependency cycles are rejected at DECOMPOSED.
- An unfinished dependency, a failed child task, or a missing review blocks
  acceptance. The ONLY way around is an explicit human waiver
  (`dependency`, `partial_acceptance`, `review`) with a name and an expiry; a
  waiver cannot disable isolation, secret redaction, or the
  sensitive-operations list.
- COMPLETED requires a result with evidence; for high-impact/security tasks —
  a G3 independent-review verdict with evidence.

### 6.8 Context graph (Graphify)

If `.orchestrator/policy/graphify.yaml` contains `enabled: true`, the
orchestrator and roles orient themselves with `graphify query/path/explain`
requests before bulk file reads (CG-01), claims are derived from the impact
subgraph (CG-02), and a stale graph is updated by the main session
(`graphify update .`) or the task is honestly tagged
`degraded_context_graph` (CG-03). Workers only read the graph: G1 forbids
them to rebuild it or write into `graphify-out/` (CG-04); in strict mode,
queries go through `.orchestrator/hooks/uok_graph.py`. Secrets never enter
the graph: `.graphifyignore` mirrors the G1 denials, and the build is
code-only and offline (CG-05).

## 7. Quality and policy improvement

Metrics (core/QUALITY-GATES.md): completion rate, first-try success, retry
frequency, validation failures, time, tokens, cost estimate, model/role
reliability, frequency of human intervention, regressions. Policy changes
are only versioned, audited, reversible proposals based on measured
results; silently rewriting the core or weakening the gates is forbidden.

## 8. If the environment has no native support

The universal profile (`adapters/universal/README.md`): role sessions in a
single agent, a claims registry kept by the orchestrator, headless CLI /
external APIs / manual mode down the degradation ladder. Degradation
decisions are flagged (`degraded_multi_agent`, `degraded_parallelism`,
`degraded_model_routing`, `doc_only_verification`) and land in the
installation report. Every degradation decision is recorded explicitly.

## 9. Honesty boundaries

- Every claim about an environment's capabilities carries a verification
  status: `unknown` / `unverified` / `verified_doc` / `verified_local` /
  `verified_live`. Documentation ≠ a working integration.
- Real-model entries in the registry are illustrations (`example: true`,
  `availability: unverified`, prices `unknown`). Test mock models
  (`test_only: true`) are used only by tests.
- Never call a test passed if it did not run; never pass a plan off as an
  implementation.

## 10. File map (where to look)

| Question | Document |
|---|---|
| Where a receiving agent starts | [START-HERE.md](START-HERE.md) → [AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md](AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md) |
| Principles and boundaries | [NORTH-STAR.md](NORTH-STAR.md) |
| Normative architecture, requirement IDs | [UNIVERSAL-ORCHESTRATION-SPEC.md](UNIVERSAL-ORCHESTRATION-SPEC.md) |
| Task categories / routing | [core/TASK-CLASSIFICATION.md](core/TASK-CLASSIFICATION.md), [core/ROUTING-POLICY.md](core/ROUTING-POLICY.md) |
| Lifecycle, waivers, acceptance gates | [core/EXECUTION-LIFECYCLE.md](core/EXECUTION-LIFECYCLE.md) |
| Task/agent/envelope schemas | [protocols/](protocols/) |
| Your environment | `adapters/<environment>/README.md` + `PROFILE.yaml` + `install.py` |
| Initial installation (`uok init`) | `uok` (the CLI at the kit root): `init` + `bootstrap`, §4 |
| Checks and scenarios | [validation/SELF-TEST.md](validation/SELF-TEST.md), [validation/COMPATIBILITY-TESTS.md](validation/COMPATIBILITY-TESTS.md) |
| Live checks for Qoder/Cursor/Codex | [handoff/LIVE-CHECKS.md](handoff/LIVE-CHECKS.md) |
| Human review of the G1 hook | [handoff/HUMAN-REVIEW-G1.md](handoff/HUMAN-REVIEW-G1.md) |
| The author's final report | [handoff/INSTALLATION-REPORT-2026-11-16.md](handoff/INSTALLATION-REPORT-2026-11-16.md) |

### 6.9 Statistics (`uok stats`)

What the kit actually did in this project — derived only from recorded
artifacts, never estimated:

```bash
python3 "$(cat ~/.uok/location)/uok" stats            # this project, human-readable
python3 "$(cat ~/.uok/location)/uok" stats --json    # the same numbers for tooling
```

- **Safety** — every allow/deny/ask the G1 hook decided, from
  `.orchestrator/audit/g1.log`: secret reads blocked (SEC-02), secret-like
  payloads blocked (SEC-03), reads/writes outside the project (ISO-02),
  guard-control violations (SEC-04), claim violations (LC-04), approvals that
  waited for a human (SEC-07), and how many `uok-*` worker roles ran.
- **Context graph** — enabled state, CLI version, nodes and edges, build time
  and CG-03 freshness (a stale graph is reported loudly, not silently used).
- **Orchestration ledger** — routing records, task ledger entries, audit
  notes, active claims, and the project registry.
- **Not measured** — stated explicitly: graph-query usage (the CLI keeps no
  query log) and token/time savings versus a no-kit baseline (that needs an
  A/B run). The command never invents a benefit number (CG-07).
