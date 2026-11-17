# Adapter: Universal (fallback for any other environment)

Kit version: 1.0.0 · Spec version: 1.0.0 · Maturity: specification_complete
Requirements: ADP-02, ARCH-03

For environments without a dedicated adapter (other IDE agents, custom
agent frameworks, bare LLM API loops, or restricted runtimes). This profile
is also the degradation target when a dedicated adapter's native features
are unavailable. It assumes only: file read/write, and optionally shell
execution and/or a model API. Everything else is optional and probed.

**Reference implementations:** when building an adapter for your environment,
use `adapters/claude-code` and `adapters/qoder` (both `integration_tested`,
live 2026-11-17) as the working example of structure, installer, hook wiring
and PROFILE evidence; their handoff reports are the evidence bar. Copy the
pattern, not host-specific facts — probe your own environment per §1 and
record only what you actually verified.

## 1. Environment discovery

1. Inventory actual capabilities: Can you dispatch a second agent/session?
   Select models per call? Run shell commands? Register hooks? If unknown,
   probe read-only (`--help`, config inspection, one trivial API call if
   credentials exist).
2. Locate the environment's instruction mechanism (system prompt file,
   rules file, repo markdown convention). If none exists, the orchestrator
   injects the kit obligations into every role prompt directly.
3. Fill `PROFILE.yaml` (copy this directory's file) with observed statuses.
   Default everything to `unknown` until probed — never assume parity with
   the dedicated adapters.

## 2. Native agent capabilities

Assume NONE until proven. The universal implementation of multi-agent
behavior is the **role-session pattern**:

- One orchestrator session owns the task ledger.
- Each worker is a fresh session (or API call sequence) given: role prompt
  (from AGENT-CAPABILITIES.yaml) + context envelope (HANDOFF-CONTRACT §1)
  + nothing else. Fresh context per role = enforced ISO-03.
- Results return only as `result_submit` payloads written to
  `.orchestrator/tasks/<task_id>/result.yaml`.

## 3. Model selection

- If the environment exposes model choice per session/call: bind tiers via
  MODEL-CONFIG.yaml to probed model ids.
- If only one model is available: tiers degrade to role routing; record
  `degraded_model_routing` in every routing decision's flags. G3
  independence then requires a second instance (different session/prompt)
  or human review — never silent self-review.
- If no model choice exists at all: the current session model serves all
  roles; record it; cost/latency metadata stays `unknown`.

## 4. Custom agent support

Roles are prompt artifacts, not native objects:
- `.orchestrator/roles/<role>.md` — generated from AGENT-CAPABILITIES.yaml
  (responsibilities, permissions, outputs, validation) + envelope checks +
  injection resistance + evidence requirements.
- The orchestrator composes: role prompt + envelope → worker session.
- Permissions are enforced by (a) whatever native tool controls exist,
  (b) orchestrator-side G1 checks before dispatch, (c) post-hoc diff audit
  of worker changes against claimed paths.

## 5. Parallel execution

- If the environment can run concurrent sessions/processes: parallelize only
  dependency-ready tasks with disjoint write claims; prefer git worktrees
  (`git worktree add`) per writer when the repo is git; merge via
  release_integration.
- Otherwise: strict sequential execution. Record `degraded_parallelism`.
- The claim ledger (`.orchestrator/claims/claims.yaml`) is mandatory in all
  cases — it is the universal LC-04 mechanism (reference kernel implements
  it; see validation/reference_router.py `ClaimLedger`).

## 6. Tool integration

- Map `required_tools` to whatever the environment exposes; deny-by-default.
- MCP if available; otherwise direct tool/function calling or shell.
- No native allowlist ⇒ orchestrator validates the worker's tool plan
  before dispatch and audits actual usage afterwards (logs/diffs).

## 7. Context management

- Instruction mechanism: repo markdown file if one exists (AGENTS.md is the
  de-facto cross-product convention); otherwise per-prompt injection.
- Envelope discipline is the isolation boundary: project-scoped artifacts
  only, redaction pass before every transfer, cross-project grants recorded
  (ISO-04/05). The orchestrator MUST refuse to paste unrelated project
  context into worker prompts.
- Ledger layout:

```
.orchestrator/
├── tasks/<task_id>/task.yaml        # TASK-CONTRACT object
├── tasks/<task_id>/envelope.yaml    # last context envelope sent
├── tasks/<task_id>/result.yaml      # result_submit payload
├── audit/events.yaml                # append-only SEC-06 log
├── claims/claims.yaml               # resource claim ledger
├── roles/<role>.md                  # role prompts
└── policy/                          # installed policy + config copies
```

## 8. Permissions

- Least privilege via role prompts + G1 pre-dispatch checks + post-hoc audit.
- Sensitive operations (SEC-07): orchestrator STOPS and asks the human
  directly (chat, terminal prompt, or escalation file
  `.orchestrator/audit/approvals_pending.yaml`); execution resumes only after
  an `approval_record` is written. No approval mechanism ⇒ such tasks stay
  ESCALATED. Never auto-proceed.
- Untrusted input: worker prompts include the SEC-05 data-vs-instructions
  rule; suspected injection freezes the task.

## 9. Hooks and events

- Assume none. G1/G2 enforcement is orchestrator-side: envelope validation
  before dispatch; evidence validation after results; claim checks before
  state transitions. If the environment later reveals hook support, upgrade
  to native enforcement and update PROFILE.yaml.

## 10. External API integration

- **Headless CLI runner**: if any compatible agent CLI exists (claude,
  qoder, cursor-agent, codex, aider, …), the orchestrator may spawn
  `cli -p/--exec` role sessions. Probe exact flags first; respect each
  product's headless approval behavior (prompts denied ⇒ sensitive tasks
  escalate).
- **Direct provider API**: OpenAI-compatible or native SDK calls per
  registry `auth_env`; the orchestrator implements the message contracts
  itself. This is the strongest fallback for per-task model routing.
- **Manual mode**: no execution capability at all ⇒ the kit operates as a
  planning/routing standard; a human executes steps and records results.
  Report maturity honestly (never above integration_tested without probes).

## 11. Limitations

- No native enforcement: all gates are orchestrator-discipline + audit.
  A misbehaving worker can violate claims; post-hoc audit + rollback
  (SEC-08) is the mitigation. Record this residual risk.
- Parallelism, model routing, and independence may all degrade; every
  degradation is flagged in routing decisions and the installation report.
- Token overhead: role sessions re-send context; keep envelopes minimal.

## 12. Installation procedure

1. Directive steps 1–7; fill the capability matrix by probing.
2. Create `.orchestrator/` layout (§7) + `.gitignore` entry.
3. Generate `.orchestrator/roles/*.md` from AGENT-CAPABILITIES.yaml.
4. Install instruction binding (repo markdown section or per-prompt header).
5. Copy templates → `.orchestrator/policy/`; fill MODEL-CONFIG from probed
   endpoints; conservative defaults (sequential, strict isolation).
6. Choose execution mechanism per §10 (native > headless CLI > API > manual)
   and record the choice.
7. Run validation (self_test + behavior_tests always; live probes where
   execution exists).

## 13. Verification procedure

- Level 2: ledger layout exists; role prompts generated; config parses.
- Level 3: run the reference kernel scenarios as dry-runs
  (`python3 validation/behavior_tests.py`); if execution exists, run one
  real TIER-1 task end-to-end through the ledger (task.yaml → envelope →
  result.yaml → gate_results) and one approval-gate probe.
- Level 4: a real multi-task package with sequential or worktree-parallel
  execution, independent review (or recorded human-review substitution),
  and complete audit trail.
- Canonical probes: ../validation/COMPATIBILITY-TESTS.md §3.