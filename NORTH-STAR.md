# NORTH-STAR — Universal Orchestrator Kit

Kit version: 1.0.0 · Spec version: 1.0.0 · Status: specification complete

## Vision

A single, portable orchestration standard that any AI coding agent — in any
supported development environment — can read, implement natively, and operate
without depending on the application that authored this kit.

The kit standardizes **how work is analyzed, routed, executed, isolated,
validated, and handed off**. It does not standardize which vendor, model, or
IDE an organization must use.

## What this kit is

- An executable engineering specification: layered architecture, routing
  policy, protocols, adapter requirements, configuration templates, and
  runnable validation.
- A reference implementation of the routing and lifecycle kernel
  (`validation/reference_router.py`) used to prove the specification's
  behavior with deterministic tests.
- A handoff package: a receiving agent follows
  [AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md](AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md)
  and produces an honest installation report.

## What this kit is not

- Not an application. There is no server, daemon, or UI to deploy.
- Not a model provider. It never ships credentials and never invents model
  capabilities, pricing, or availability.
- Not a replacement for native environment features. Adapters must prefer
  native subagents, hooks, permissions, and isolation over reinvention.
- Not unlimited autonomy. Human approval gates are mandatory and
  non-negotiable (see SEC requirements in
  [UNIVERSAL-ORCHESTRATION-SPEC.md](UNIVERSAL-ORCHESTRATION-SPEC.md)).

## Non-negotiable principles

| ID | Principle |
|----|-----------|
| NS-01 | The orchestration standard is application-independent. Provider and model names appear only as registry entries or examples, never as architectural dependencies. |
| NS-02 | Routing is per-task and multi-factor (category, complexity, risk, cost, availability, tools, verification), never per-project or per-model-name alone. |
| NS-03 | Strict project isolation by default. Cross-project context transfer is explicit, justified, logged, and never carries secrets. |
| NS-04 | Least privilege and human approval for sensitive operations. Autonomous execution is not unrestricted authority. |
| NS-05 | No uncontrolled concurrent writes. Parallelism requires dependency resolution and resource-claim safety. |
| NS-06 | Independent validation. High-impact work is reviewed by an agent/model instance that did not implement it. |
| NS-07 | Honesty of state. Every capability, adapter, and test result carries an explicit verification status: `unknown`, `unverified`, `verified_doc`, `verified_local`, `verified_live`. Nothing is claimed operational because its documentation exists. |
| NS-08 | Policy evolution is versioned, auditable, reversible, and may never silently weaken security gates. |
| NS-09 | Portability: plain Markdown + YAML + a dependency-light Python reference kernel. No language, vendor, or IDE lock-in. |
| NS-10 | Preserve existing user configuration and project behavior during installation. Extend, never blindly overwrite. |

## Success definition

A receiving agent in a different application can, using only this directory:

1. Understand the architecture and terminology.
2. Audit its environment and produce a capability matrix.
3. Implement the strongest native integration available.
4. Route, execute, isolate, and validate real tasks.
5. Report truthfully what is specification-ready vs operationally verified.

## Boundaries and explicit assumptions

- The kit assumes the receiving environment can read files and (ideally)
  execute shell commands. Environments without execution capability can still
  adopt the specification manually; validation scripts then cannot run and
  must be reported as `not_executed`.
- The kit assumes model access is configured by the user in their environment
  or provider accounts. The kit never provisions credentials.
- Live model behavior (quality, latency, price) is environment-specific and
  must be measured, not assumed. Registry defaults are `unverified`/`unknown`.
- The reference kernel is a specification conformance tool, not a production
  scheduler. Production execution uses the environment's native runtime.

## Document map

Start at [START-HERE.md](START-HERE.md). Architecture:
[UNIVERSAL-ORCHESTRATION-SPEC.md](UNIVERSAL-ORCHESTRATION-SPEC.md).
Implementation entry point for receiving agents:
[AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md](AUTONOMOUS-IMPLEMENTATION-DIRECTIVE.md).