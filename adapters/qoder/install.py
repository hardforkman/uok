#!/usr/bin/env python3
"""Universal Orchestrator Kit — Qoder adapter installer (kit 1.0.0).

  python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/qoder/install.py [--project DIR] [--mode standard|strict]
          [--models tier1=lite,tier2=efficient,tier3=performance,review=performance] [--dry-run]

Installs, additively and idempotently (backups in .orchestrator/backups/<ts>/):
  - .orchestrator/ working tree, policy files, shared G1 hook (copied before it is registered);
  - .qoder/agents/uok-<role>.md subagents (frontmatter name/description/tools/model/permissionMode);
  - .qoder/skills/uok/SKILL.md — user launcher: /uok <task> [verified_doc: docs.qoder.com/cli/Skills];
  - AGENTS.md marked section + .qoder/rules/uok.md (trigger: always_on);
  - PreToolUse hook in .qoder/settings.json (merged; user hooks and settings kept).
Qoder hook events use the Claude Code schema (tool_name, tool_input, agent_type,
hookSpecificOutput.permissionDecision allow/deny/ask) [verified_doc: docs.qoder.com/cli/hooks].
Model selectors are NOT probed: pass what your account shows.
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "shared"))
import uok_install as core  # noqa: E402

MATCHER = "Read|Grep|Glob|Write|Edit|MultiEdit|NotebookEdit|Bash|mcp__.*"


class QoderInstaller(core.BaseInstaller):
    HOST, FORMAT, INSTRUCTION_FILE = "qoder", "qoder", "AGENTS.md"
    SKILL_DIR, SKILL_INVOKE = ".qoder/skills/uok", "/uok"
    DEFAULT_MODELS = {"tier1": "lite", "tier2": "efficient", "tier3": "performance", "review": "performance"}

    def workers_line(self):
        return ("The main session is the **orchestrator**; workers are the subagents `uok-*` in `.qoder/agents/` "
                f"(one per role in `{self.kit_rel}/core/AGENT-CAPABILITIES.yaml`). Delegate with "
                "\"Use the uok-<role> subagent to …\".")

    def hook_line(self):
        return (super().hook_line() + " For `uok-*` workers it also blocks writes to the host config, `.orchestrator/`, "
                "`AGENTS.md` and the kit, enforces claims, and denies sensitive operations to roles with "
                "`sensitive_ops: never`." + (" Strict mode additionally sandboxes worker shell commands."
                                             if self.mode == "strict" else ""))

    def host_steps(self):
        for r in core.roles():
            p = r["permissions"]
            tools = ["Read", "Grep", "Glob"] + (["Write", "Edit"] if p["filesystem"] == "write" else []) \
                + (["Bash"] if p["shell"] != "none" else []) + (["WebSearch", "WebFetch"] if p["network"] != "none" else [])
            disallowed = [] if p["filesystem"] == "write" else ["Write", "Edit"]
            tier = "TIER-5" if r["id"] in ("code_reviewer", "security_reviewer") else r["default_tier"]
            rid = r["id"].replace("_", "-")
            front = [f"name: uok-{rid}",
                     f"description: \"{r['name']} {core.ROLE_MARK}. Use for: {'; '.join(r['responsibilities'][:2])}.\"",
                     f"tools: {', '.join(tools)}"]
            if disallowed:
                front.append(f"disallowedTools: {', '.join(disallowed)}")
            front += [f"model: {self.model_for(tier) or 'inherit'}", "permissionMode: default"]
            self.write_managed(self.p(".qoder", "agents", f"uok-{rid}.md"),
                               "---\n" + "\n".join(front) + "\n---\n\n" + core.role_rules(r), f"kit role {r['id']}")
        self.step_instruction_file()
        self.write_managed(self.p(".qoder", "rules", "uok.md"),
                           "---\ntrigger: always_on\n---\n\n<!-- " + core.ROLE_MARK + " -->\n"
                           + self.section(), "always-on kit rule", marker=core.ROLE_MARK)

    def register_hook(self):
        cmd = core.hook_command(self.FORMAT)

        def mutate(d):
            groups = d.setdefault("hooks", {}).setdefault("PreToolUse", [])
            ours = [g for g in groups if any("g1_guard.py" in h.get("command", "") for h in g.get("hooks", []))]
            entry = {"matcher": MATCHER, "hooks": [{"type": "command", "command": cmd, "timeout": 30}]}
            if ours:
                ours[0].clear(); ours[0].update(entry)
            else:
                groups.append(entry)
        self.merge_json(self.p(".qoder", "settings.json"), mutate, "PreToolUse G1 hook (merged)")


if __name__ == "__main__":
    core.cli(QoderInstaller, __doc__)
