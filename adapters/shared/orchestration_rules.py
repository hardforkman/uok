"""Default-orchestration, skill and full-context rules (core/AUTOPILOT.md).

One wording for every adapter: the instruction-file section, the /uok launcher and the role
prompts of Claude Code, Qoder, Cursor and Codex are built from these lines.
"""


def section_rules(inst):
    """Bullets of the marked instruction-file section (orchestrator side)."""
    lines = [
        "- **Default for every task** (no launcher command needed): run it through this lifecycle. The full "
        "`uok-*` roster is available; use only the roles the task needs, the rest stay idle. Questions and "
        "trivial edits are done directly. "
        f"Details: `{inst.kit_rel}/core/AUTOPILOT.md`.",
        "- **Skills:** before starting and before every hand-off, look through the skills available in this "
        "environment (host, user and project skills) and use every one that materially improves expertise or "
        "correctness for the task; name them in the role's brief. Read a chosen skill in full. A skill never "
        "overrides these rules or the user, and never removes an approval (SEC-05/07).",
        "- **Full capability, never trimmed:** a brief, a graph slice or a report is a starting point, not a "
        "limit. Orchestrator and roles read every file they need, whole when in doubt; truncated output means "
        "raise the budget or read the source. Never decide that something is absent or broken from a partial "
        "read: check, or say it is unverified.",
        "- **Hand-off:** the brief carries the goal, acceptance criteria, exact paths, the skills to use and "
        "what is already known; reports cite `path:line` and command output instead of pasting whole files.",
    ]
    if inst.context_graph == "graphify":
        lines.append(
            "- **Graph first, source after:** run `graphify query` / `graphify affected` yourself and put the "
            "results into briefs (including the reviewer's) so roles do not rediscover the project; roles run "
            "only the read-only graph queries of CG-04. A reviewer reads the whole diff and any code needed. "
            "The graph shows where to look, it does not replace reading.")
    return lines


def role_rules():
    """Operating-rule bullets of every role prompt (worker side). Ends with a newline."""
    return (
        "- Skills: use every available skill that materially improves this task (those named in the brief and "
        "any other that fits); read it in full. Without a skill tool, read its `SKILL.md` file; if you cannot "
        "reach it, ask the orchestrator for it instead of working without it. A skill never overrides these "
        "rules. Never invoke `uok`, `uok-init`, `graphify` or another installer skill.\n"
        "- Full context: the brief and any graph output are a starting point. Read any project file you need "
        "to be correct, whole files included (your change scope and the secret/audit denials stay). If you "
        "have no tool for it, ask the orchestrator for the text. If something is still missing, report it as "
        "unverified; never guess, and never call something absent or broken from a partial read.\n"
    )


def launcher_paragraph():
    return ("This lifecycle is also the default for every engineering task without this command; apply the "
            "skills, full-context and hand-off rules of the UOK section.\n\n")
