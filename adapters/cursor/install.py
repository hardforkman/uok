#!/usr/bin/env python3
"""Universal Orchestrator Kit — Cursor adapter installer (kit 1.0.0).

  python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/cursor/install.py [--project DIR] [--dry-run]

Installs, additively and idempotently (backups in .orchestrator/backups/<ts>/):
  - .orchestrator/ working tree, policy files, shared G1 hook (copied before it is registered);
  - AGENTS.md marked section + .cursor/rules/uok-orchestrator.mdc (alwaysApply) and one
    .cursor/rules/uok-role-<role>.mdc per role (Agent Requested by description);
  - .cursor/skills/uok/SKILL.md — user launcher: /uok in chat [verified_doc: cursor.com/docs/agent/chat/commands];
  - .cursor/hooks.json (version 1): beforeShellExecution, beforeMCPExecution, beforeReadFile and
    preToolUse (file writes) -> G1 guard with --format cursor, failClosed (merged; user hooks kept).
Cursor has no file-defined subagents and its hook input carries no agent identity, so roles are
rule-scoped prompts and the hook applies the base protections to every caller (degradation recorded).
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "shared"))
import uok_install as core  # noqa: E402

EVENTS = {"beforeShellExecution": None, "beforeMCPExecution": None, "beforeReadFile": None,
          "preToolUse": "Write|Edit|MultiEdit|StrReplace|Delete|NotebookEdit|EditNotebook"}


class CursorInstaller(core.BaseInstaller):
    HOST, FORMAT, INSTRUCTION_FILE = "cursor", "cursor", "AGENTS.md"
    SKILL_DIR, SKILL_INVOKE = ".cursor/skills/uok", "/uok"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.degradations += [
            "no file-defined subagents: roles are rule-scoped prompts (.cursor/rules/uok-role-*.mdc), run sequentially",
            "hook input has no agent identity: worker-only rules (claims per worker, guard files, role sensitive_ops) "
            "are instructions, not hook-enforced",
            "per-role model binding not available: switch models per task manually",
        ]
        if self.mode == "strict":
            self.warnings.append("strict mode has no effect on Cursor (no worker identity in hook input)")

    def workers_line(self):
        return ("You are the **orchestrator**. Cursor has no file-defined subagents: the kit roles are rules "
                "`.cursor/rules/uok-role-<role>.mdc`. To work as a role, apply that rule explicitly "
                "(`@uok-role-<role>`) and follow it; switch roles between tasks, one role at a time.")

    def host_steps(self):
        self.step_instruction_file()
        self.write_managed(self.p(".cursor", "rules", "uok-orchestrator.mdc"),
                           "---\ndescription: Universal Orchestrator Kit orchestration rules\nalwaysApply: true\n---\n\n"
                           f"<!-- {core.ROLE_MARK} -->\n" + self.section(), "always-apply kit rule")
        for r in core.roles():
            rid = r["id"].replace("_", "-")
            self.write_managed(self.p(".cursor", "rules", f"uok-role-{rid}.mdc"),
                               f"---\ndescription: \"{r['name']} {core.ROLE_MARK}: {'; '.join(r['responsibilities'][:2])}\"\n"
                               "alwaysApply: false\n---\n\n" + core.role_rules(r), f"kit role {r['id']}")

    def register_hook(self):
        cmd = core.hook_command(self.FORMAT)

        def mutate(d):
            d.setdefault("version", 1)
            hooks = d.setdefault("hooks", {})
            for event, matcher in EVENTS.items():
                lst = hooks.setdefault(event, [])
                lst[:] = [h for h in lst if "g1_guard.py" not in h.get("command", "")]
                entry = {"command": cmd, "timeout": 120, "failClosed": True}
                if matcher:
                    entry["matcher"] = matcher
                lst.append(entry)
        self.merge_json(self.p(".cursor", "hooks.json"), mutate, "G1 hooks for 4 events (merged)")

    def smoke_event(self):
        return {"hook_event_name": "beforeReadFile", "file_path": self.p(".env"), "content": ""}, '"deny"'


if __name__ == "__main__":
    core.cli(CursorInstaller, __doc__)
