#!/usr/bin/env python3
"""uok launcher tests (kit 1.0.0): init dispatch + bootstrap user-level skill.

Runs the real CLI on scratch projects and a scratch HOME. No host application
is involved; this is verified_local evidence for the launcher, not live skill
invocation inside a host.

Run: python3 adapters/shared/test_uok_cli.py   (exit 0 = all pass)
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = os.path.dirname(os.path.realpath(__file__))
KIT = os.path.dirname(os.path.dirname(HERE))
UOK = os.path.join(KIT, "uok")
HOSTS = ("claude-code", "qoder", "cursor", "codex")
GLOBAL_DIR = {"claude-code": ".claude/skills", "qoder": ".qoder/skills",
              "cursor": ".cursor/skills", "codex": ".agents/skills"}
MARK = "(Universal Orchestrator Kit bootstrap)"


def run_uok(args, home, cwd, env_extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CLAUDE", "QODER", "CURSOR", "CODEX"))}
    env.update(HOME=home, PYTHONDONTWRITEBYTECODE="1")
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, UOK] + args, capture_output=True, text=True,
                          cwd=cwd, env=env, timeout=600)


def frontmatter(text):
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = text.index("\n---\n", 4)
    return yaml.safe_load(text[4:end]), text[end + 5:]


class UokCliTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="uok-cli-home-")
        self.proj = tempfile.mkdtemp(prefix="uok-cli-proj-")
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.proj, ignore_errors=True)

    def skill_path(self, host):
        return Path(self.home, GLOBAL_DIR[host], "uok-init", "SKILL.md")

    def test_init_dry_run_dispatch_all_hosts(self):
        for host in HOSTS:
            with self.subTest(host=host):
                r = run_uok(["init", "--host", host, "--dry-run"], self.home, self.proj)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn(f"host={host}", r.stdout)
                self.assertIn("DRY RUN", r.stdout)
                self.assertIn("orchestrator launcher skill", r.stdout)
                self.assertFalse(any(Path(self.proj).iterdir()), "dry run wrote files")

    def test_init_real_install_one_host(self):
        r = run_uok(["init", "--host", "qoder"], self.home, self.proj)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(Path(self.proj, ".qoder/skills/uok/SKILL.md").exists())
        self.assertTrue(Path(self.proj, ".orchestrator/hooks/g1_guard.py").exists())
        self.assertIn("PASS", r.stdout)

    def test_init_unknown_host_rejected(self):
        r = run_uok(["init", "--host", "emacs"], self.home, self.proj)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid choice", r.stderr)

    def test_init_auto_detects_host_from_env(self):
        r = run_uok(["init", "--dry-run"], self.home, self.proj, env_extra={"CLAUDECODE": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("host=claude-code", r.stdout)

    def test_init_auto_ambiguous_requires_host(self):
        Path(self.proj, ".claude").mkdir()
        Path(self.proj, ".qoder").mkdir()
        r = run_uok(["init", "--dry-run"], self.home, self.proj)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--host", r.stderr)

    def test_bootstrap_all_hosts_valid_skill(self):
        r = run_uok(["bootstrap", "--host", "all"], self.home, self.proj)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for host in HOSTS:
            with self.subTest(host=host):
                p = self.skill_path(host)
                self.assertTrue(p.exists(), f"{host}: {p} missing")
                fm, body = frontmatter(p.read_text(encoding="utf-8"))
                self.assertEqual(fm["name"], "uok-init")
                self.assertIn("uok init", fm["description"])
                self.assertIn(MARK, fm["description"])
                self.assertIn(f"--host {host}", body)
                self.assertIn(KIT, body)
                self.assertIn("--dry-run", body)

    def test_bootstrap_idempotent(self):
        run_uok(["bootstrap", "--host", "all"], self.home, self.proj)
        r = run_uok(["bootstrap", "--host", "all"], self.home, self.proj)
        self.assertEqual(r.returncode, 0)
        self.assertIn("(none)", r.stdout)
        self.assertEqual(r.stdout.count("(unchanged)"), 4)

    def test_bootstrap_update_backs_up(self):
        run_uok(["bootstrap", "--host", "qoder"], self.home, self.proj)
        p = self.skill_path("qoder")
        p.write_text(p.read_text(encoding="utf-8") + "\nextra line\n", encoding="utf-8")
        r = run_uok(["bootstrap", "--host", "qoder"], self.home, self.proj)
        self.assertEqual(r.returncode, 0)
        self.assertIn("update", r.stdout)
        backups = list(Path(self.home, ".uok/backups").rglob("SKILL.md"))
        self.assertEqual(len(backups), 1)
        self.assertIn("extra line", backups[0].read_text(encoding="utf-8"))
        self.assertNotIn("extra line", p.read_text(encoding="utf-8"))

    def test_bootstrap_preserves_user_skill(self):
        p = self.skill_path("qoder")
        p.parent.mkdir(parents=True)
        mine = "---\nname: uok-init\ndescription: my own\n---\n\nMine.\n"
        p.write_text(mine, encoding="utf-8")
        r = run_uok(["bootstrap", "--host", "qoder"], self.home, self.proj)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(p.read_text(encoding="utf-8"), mine)
        self.assertIn("user-authored", r.stdout)

    def test_bootstrap_dry_run_writes_nothing(self):
        r = run_uok(["bootstrap", "--host", "all", "--dry-run"], self.home, self.proj)
        self.assertEqual(r.returncode, 0)
        for host in HOSTS:
            self.assertFalse(self.skill_path(host).exists())

    def test_bootstrap_auto_uses_home_markers(self):
        Path(self.home, ".qoder").mkdir()
        r = run_uok(["bootstrap"], self.home, self.proj)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.skill_path("qoder").exists())
        for host in ("claude-code", "cursor", "codex"):
            self.assertFalse(self.skill_path(host).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)