# Human review of the G1 hook

Kit version: 1.0.0 · Requirement: CLAUDE.md / AGENTS.md ("critical work also needs human review"), QA-01, SEC-07

The G1 hook is the only mechanism that actually stops an agent in practice. Six rounds of
automated security review approved it, but by the kit's rules code of this level must be
reviewed by a human. This page tells you exactly what to look at and how to record the
result. Time: 1–2 hours.

## 1. What to read

| File | What it contains | What to look at |
|---|---|---|
| `adapters/shared/hooks/g1_guard.py` | the hook itself (≈500 lines) | `main()` — the order of checks; `check_path()`; `decide()`; error handling in `__main__` |
| `adapters/shared/hooks/README.md` | behavior description | does it match the code; are you comfortable with the known limitations (§10) |
| `adapters/<host>/install.py`, `adapters/shared/uok_install.py` | the installers | what they change in a project; that user content is left untouched |
| `.claude/settings.json` / `.qoder/settings.json` / `.cursor/hooks.json` / `.codex/hooks.json` | registration in your project | the hook command, the `deny`/`ask` rules |

## 2. Review questions

Answer "yes / no / don't know" and record your notes.

1. **Secrets.** Are the `DENIED_GLOBS` and `SECRET_PATTERNS` lists enough for your projects?
   Do you keep secrets under other names (for example `*.tfvars`, `service-account*.json`)?
   Those need to be added.
2. **Project boundary.** Are you comfortable with the main session being able to read files
   outside the project but never write them?
3. **Approvals.** The dangerous-operations list (README section 5): what is missing for your
   infrastructure (for example `kubectl rollout`, `aws s3 rm`, `psql -c "DELETE…"`)?
4. **Failure behavior.** On its own error the hook lets a call through for the main session
   (except writes and MCP) and blocks it for workers. Do you agree?
5. **Missing hook.** If the hook file disappears, Claude Code blocks every call (verified).
   Cursor with `failClosed: true` does the same. Is that the right trade-off for you, or do
   you need a different compromise?
6. **Modes.** Is `standard` enough for your projects, or do you need `strict`?
7. **Hosts without agent identity** (Cursor, Codex): there the worker rules are instructions
   only. Is that acceptable?
8. **False positives.** Do the `ask` on `echo rm -rf`, the `curl` deny from the `permissions`
   rule and the like get in your way?

## 3. How to check it yourself

```bash
python3 -I UNIVERSAL-ORCHESTRATOR-KIT/adapters/shared/hooks/test_g1_guard.py
```

Manual probe of a single event (substitute your own path):

```bash
echo '{"tool_name":"Read","tool_input":{"file_path":"'"$PWD"'/.env"}}' | python3 -I .orchestrator/hooks/g1_guard.py
```

Expect JSON with `"permissionDecision": "deny"`. Decision log: `.orchestrator/audit/g1.log`.

## 4. Recording the result

Add to the installation report (`handoff/INSTALLATION-REPORT-*.md`) a section:

```markdown
## Human review of G1 (YYYY-MM-DD)
Reviewer: <name>
Version reviewed: <git commit>
Verdict: approved | approved with changes | rejected
Findings: <list or "none">
Changes requested: <list or "none">
```

Until such a record exists, adapter maturity does not rise above `integration_tested`.
