#!/usr/bin/env python3
"""Installer skill-launcher tests (kit 1.0.0).

Verifies the /uok (Codex: $uok) skill step of every adapter installer on
scratch projects: creation, frontmatter validity, idempotency, dry-run,
and preservation of user-authored skills. No host application is involved;
this is verified_local evidence for the installer, not live skill invocation.

Run: python3 adapters/shared/test_install_skill.py   (exit 0 = all pass)
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = os.path.dirname(os.path.realpath(__file__))
ADAPTERS = os.path.dirname(HERE)
sys.path.insert(0, HERE)

HOSTS = {
    "claude-code": (".claude/skills/uok/SKILL.md", "/uok"),
    "qoder": (".qoder/skills/uok/SKILL.md", "/uok"),
    "cursor": (".cursor/skills/uok/SKILL.md", "/uok"),
    "codex": (".agents/skills/uok/SKILL.md", "$uok"),
}


def load_installer(host):
    path = os.path.join(ADAPTERS, host, "install.py")
    spec = importlib.util.spec_from_file_location(f"uok_install_{host.replace('-', '_')}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if host == "claude-code":
        return mod.Installer, {"tier1": "haiku", "tier2": "sonnet", "tier3": "opus", "review": "opus"}
    cls = getattr(mod, {"qoder": "QoderInstaller", "cursor": "CursorInstaller", "codex": "CodexInstaller"}[host])
    return cls, dict(cls.DEFAULT_MODELS)


def frontmatter(text):
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = text.index("\n---\n", 4)
    return yaml.safe_load(text[4:end]), text[end + 5:]


class SkillStepTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="uok-skill-test-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def installer(self, host, dry=False):
        cls, models = load_installer(host)
        return cls(self.root, "standard", models, dry)

    def test_skill_created_with_valid_frontmatter(self):
        for host, (rel, invoke) in HOSTS.items():
            with self.subTest(host=host):
                inst = self.installer(host)
                inst.step_skill()
                path = os.path.join(self.root, rel)
                self.assertTrue(os.path.exists(path), f"{host}: {rel} not created")
                fm, body = frontmatter(Path(path).read_text(encoding="utf-8"))
                self.assertEqual(fm["name"], "uok")
                self.assertTrue(fm.get("description"))
                self.assertIn("(Universal Orchestrator Kit skill)", Path(path).read_text(encoding="utf-8"))
                self.assertIn("EXECUTION-LIFECYCLE.md", body)
                self.assertIn("human approval", body)
                self.assertIn(invoke, fm["description"])

    def test_claude_skill_is_user_only_with_arguments(self):
        inst = self.installer("claude-code")
        inst.step_skill()
        text = Path(self.root, HOSTS["claude-code"][0]).read_text(encoding="utf-8")
        fm, body = frontmatter(text)
        self.assertIs(fm.get("disable-model-invocation"), True)
        self.assertEqual(fm.get("argument-hint"), "[task]")
        self.assertIn("$ARGUMENTS", body)

    def test_idempotent_rerun(self):
        for host in HOSTS:
            with self.subTest(host=host):
                inst = self.installer(host)
                inst.step_skill()
                again = self.installer(host)
                again.step_skill()
                self.assertFalse(again.changes, f"{host}: rerun changed files: {again.changes}")
                self.assertTrue(any("unchanged" in k for k in again.kept))

    def test_dry_run_writes_nothing(self):
        for host, (rel, _) in HOSTS.items():
            with self.subTest(host=host):
                inst = self.installer(host, dry=True)
                inst.step_skill()
                self.assertTrue(inst.changes)
                self.assertFalse(os.path.exists(os.path.join(self.root, rel)))

    def test_user_skill_preserved(self):
        for host, (rel, _) in HOSTS.items():
            with self.subTest(host=host):
                path = os.path.join(self.root, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                mine = "---\nname: uok\ndescription: my own skill\n---\n\nMine.\n"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(mine)
                inst = self.installer(host)
                inst.step_skill()
                self.assertEqual(Path(path).read_text(encoding="utf-8"), mine)
                self.assertTrue(inst.warnings)
                self.assertFalse(inst.changes)


if __name__ == "__main__":
    unittest.main(verbosity=2)