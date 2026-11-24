# INSTALLATION REPORT — Codex adapter (live)

Kit version: 1.0.0 · Spec version: 1.0.0 · Date: 2026-11-24
Environment: Codex CLI 0.171.0-alpha.13.2 (bundled with the ChatGPT desktop app, run headless as `codex exec`), macOS, scratch git project,
installed with `uok init --host codex`. The CLI was driven by the kit author's session; honesty rule: only what was executed is `verified_live`.

## Probes (actual executions)

| # | Probe | Result | Evidence |
|---|---|---|---|
| 1 | Install into a clean project | installer exit 0; hook suite OK; smoke event (secret file -> deny) PASS | installer output |
| 2 | Run with the project NOT trusted | **hook did not run**: Codex printed "Untrusted project-local configuration is disabled"; `git push --force origin no-such-branch` executed (failed only because the remote does not exist) and `apply_patch` wrote `../outside-probe.txt` outside the project | g1.log empty; file existed |
| 3 | Same task with the project trusted (`--trust`) and `--dangerously-bypass-hook-trust` | `ls` allowed; `apply_patch` of `../outside-probe.txt` **blocked** by the hook (ISO-02), file not created; `git push --force` **blocked** with "the human must run it" (SEC-07) | g1.log: `allow: [main] Bash`, `deny: [main Write] ... (ISO-02)`, `deny: [main Bash] ... human must run it ... (SEC-07)` |
| 4 | Agents and skill load | Codex listed all 10 `uok_*` custom agents and reported the `uok` skill available | Codex answer, read-only sandbox |

## Findings
1. **An untrusted project has no guard** (probe 2): documented behaviour of Codex, now observed. The install's "next steps" and README §11 say to trust the project and review the hook.
2. The workspace-write sandbox allows writing under `/tmp`, so the G1 root check is the only barrier for project-external writes there.
3. `-c 'projects."<path>".trust_level="trusted"'` did not enable trust for `codex exec`; `--trust` did (it records the project in `~/.codex/config.toml`; the probe's entries were removed afterwards).

## Not executed
- Interactive review of the hook with `/hooks` (the probes used `--dangerously-bypass-hook-trust` for one run of a scratch project).
- Delegation to a `uok_*` agent, `$uok` lifecycle, MCP hook, claims with parallel writers, subagent identity (not provided by Codex hook input).

## Maturity
`integration_tested` for hook, agents and skill loading; not `operationally_verified`.
