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
                self.assertIn("cat ~/.uok/location", body)   # path is read from the pointer, not embedded
                self.assertNotIn(KIT, body)
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

    def test_bootstrap_mirrors_dsh_skills(self):
        (Path(self.home) / ".dsh" / "skills").mkdir(parents=True)   # DSH installed on the machine
        r = run_uok(["bootstrap", "--host", "all"], self.home, self.proj)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for name in ("uok-init", "uok"):
            with self.subTest(skill=name):
                p = Path(self.home, ".dsh/skills", name, "SKILL.md")
                self.assertTrue(p.exists(), f"{p} missing")
                fm, body = frontmatter(p.read_text(encoding="utf-8"))
                self.assertEqual(fm["name"], name)
                self.assertIn(MARK, fm["description"])
                self.assertIn("cat ~/.uok/location", body)
                self.assertNotIn(KIT, body)
        r2 = run_uok(["bootstrap", "--host", "all"], self.home, self.proj)
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(r2.stdout.count("(unchanged)"), 6)   # 4 hosts + 2 dsh skills
        self.assertIn(".dsh/skills/uok/SKILL.md", r.stdout)
        # no ~/.dsh -> no mirror lines, hosts-only behaviour unchanged
        home2 = tempfile.mkdtemp(prefix="uok-cli-home2-")
        self.addCleanup(shutil.rmtree, home2, ignore_errors=True)
        r3 = run_uok(["bootstrap", "--host", "all"], home2, self.proj)
        self.assertEqual(r3.returncode, 0)
        self.assertNotIn(".dsh", r3.stdout)

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


class SharedKitRelocationTest(unittest.TestCase):
    """Kit in a shared folder: projects store <kit>, the real path lives in ~/.uok/location only."""

    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.shared = Path(os.path.realpath(self.tmp / "shared" / "UNIVERSAL-ORCHESTRATOR-KIT"))
        shutil.copytree(KIT, self.shared, ignore=shutil.ignore_patterns("__pycache__", "backups"))
        self.proj = Path(os.path.realpath(self.tmp)) / "proj"
        self.proj.mkdir()
        (self.proj / "src").mkdir()
        (self.proj / "src" / "app.py").write_text("x = 1\n")
        self.env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE="1")

    def run_kit(self, kit, args, cwd):
        return subprocess.run([sys.executable, str(kit / "uok"), *args], capture_output=True, text=True,
                              env=self.env, cwd=str(cwd), timeout=900)

    def pointer(self):
        return (self.home / ".uok" / "location").read_text().strip()

    def test_project_stores_placeholder_not_path(self):
        r = self.run_kit(self.shared, ["init", "--host", "claude-code", "--project", str(self.proj)], self.proj)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.pointer(), str(self.shared))
        claude = (self.proj / "CLAUDE.md").read_text()
        self.assertIn("`<kit>/core/", claude)
        self.assertNotIn(str(self.shared), claude)
        self.assertIn('kit_dir: "<kit>"', (self.proj / ".orchestrator" / "policy" / "claude-code.yaml").read_text())
        self.assertNotIn(str(self.shared), (self.proj / ".orchestrator" / "policy" / "claude-code.yaml").read_text())

    def test_move_then_locate_updates_only_pointer(self):
        self.run_kit(self.shared, ["init", "--host", "claude-code", "--project", str(self.proj)], self.proj)
        before = (self.proj / "CLAUDE.md").read_text()
        moved = Path(os.path.realpath(self.tmp)) / "elsewhere" / "UNIVERSAL-ORCHESTRATOR-KIT"
        moved.parent.mkdir()
        shutil.move(str(self.shared), str(moved))
        r = self.run_kit(moved, ["locate"], moved)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.pointer(), str(moved))
        self.assertEqual((self.proj / "CLAUDE.md").read_text(), before, "project files must not change on locate")

    def test_bootstrap_skill_reads_pointer_not_path(self):
        self.run_kit(self.shared, ["bootstrap", "--host", "claude-code"], self.shared)
        skill = (self.home / ".claude" / "skills" / "uok-init" / "SKILL.md").read_text()
        self.assertIn("cat ~/.uok/location", skill)
        self.assertNotIn(str(self.shared), skill)


class RefreshAndUpdaterTest(unittest.TestCase):
    """One kit folder, many projects: init records a project, refresh/updater.sh propagate kit changes."""

    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE="1",
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        self.upstream = self.tmp / "upstream"
        shutil.copytree(KIT, self.upstream, ignore=shutil.ignore_patterns("__pycache__", "backups", ".git"))
        self.git(self.upstream, "init", "-q", "-b", "main")
        self.git(self.upstream, "add", "-A")
        self.git(self.upstream, "commit", "-q", "-m", "v1")
        self.git(self.upstream, "tag", "v1.0.0")
        self.kit = self.tmp / "shared" / "kit"
        self.kit.parent.mkdir()
        self.git(self.tmp, "clone", "-q", str(self.upstream), str(self.kit))
        self.proj = self.tmp / "proj"
        self.proj.mkdir()

    def git(self, cwd, *args):
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def kit_run(self, args):
        return subprocess.run([sys.executable, str(self.kit / "uok"), *args], capture_output=True, text=True,
                              env=self.env, cwd=str(self.proj), timeout=900)

    def registry(self):
        import json
        return json.loads((self.home / ".uok" / "projects.json").read_text())["projects"]

    def test_init_records_project_with_models(self):
        r = self.kit_run(["init", "--host", "claude-code", "--project", str(self.proj), "--models", "review=fable"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        reg = self.registry()
        self.assertEqual(len(reg), 1)
        self.assertEqual(reg[0]["project"], os.path.realpath(self.proj))
        self.assertEqual(reg[0]["host"], "claude-code")
        self.assertEqual(reg[0]["models"], "review=fable")

    def test_dry_run_init_records_nothing(self):
        self.kit_run(["init", "--host", "qoder", "--project", str(self.proj), "--dry-run"])
        self.assertFalse((self.home / ".uok" / "projects.json").exists())

    def test_reinit_without_models_keeps_recorded_models(self):
        self.kit_run(["init", "--host", "claude-code", "--project", str(self.proj), "--models", "review=fable"])
        r = self.kit_run(["init", "--host", "claude-code", "--project", str(self.proj)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("reusing models", r.stdout)
        agent = (self.proj / ".claude" / "agents" / "uok-code-reviewer.md").read_text()
        self.assertIn("model: fable", agent)
        self.assertEqual(len(self.registry()), 1)

    def test_updater_pulls_kit_and_refreshes_projects(self):
        self.kit_run(["init", "--host", "claude-code", "--project", str(self.proj), "--models", "review=fable"])
        skill = self.proj / ".claude" / "skills" / "uok" / "SKILL.md"
        before = skill.read_text()
        # upstream ships a new kit version: a changed launcher skill text
        inst = self.upstream / "adapters" / "claude-code" / "install.py"
        text = inst.read_text()
        self.assertIn("Report results with actual command output", text)
        inst.write_text(text.replace("Report results with actual command output",
                                     "Report results with actual command output (UPDATED-MARKER)"))
        self.git(self.upstream, "commit", "-q", "-am", "v2")
        self.git(self.upstream, "tag", "v1.1.0")
        r = subprocess.run(["bash", str(self.kit / "updater.sh")], capture_output=True, text=True,
                           env=self.env, cwd=str(self.tmp), timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("refresh", r.stdout)
        after = skill.read_text()
        self.assertNotEqual(before, after)
        self.assertIn("UPDATED-MARKER", after)
        self.assertIn("model: fable", (self.proj / ".claude" / "agents" / "uok-code-reviewer.md").read_text())

    def test_updater_no_refresh_flag_leaves_projects(self):
        self.kit_run(["init", "--host", "claude-code", "--project", str(self.proj)])
        skill = self.proj / ".claude" / "skills" / "uok" / "SKILL.md"
        inst = self.upstream / "adapters" / "claude-code" / "install.py"
        inst.write_text(inst.read_text().replace("Report results with actual command output",
                                                 "Report results with actual command output (UPDATED-MARKER)"))
        self.git(self.upstream, "commit", "-q", "-am", "v2")
        self.git(self.upstream, "tag", "v1.1.0")
        r = subprocess.run(["bash", str(self.kit / "updater.sh"), "--no-refresh"], capture_output=True, text=True,
                           env=self.env, cwd=str(self.tmp), timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("UPDATED-MARKER", skill.read_text())

    def test_refresh_skips_missing_project(self):
        self.kit_run(["init", "--host", "qoder", "--project", str(self.proj)])
        shutil.rmtree(self.proj)
        r = self.kit_run(["refresh"]) if self.proj.exists() else subprocess.run(
            [sys.executable, str(self.kit / "uok"), "refresh"], capture_output=True, text=True,
            env=self.env, cwd=str(self.tmp), timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("skipping", r.stdout)

    def test_refresh_with_empty_registry(self):
        r = self.kit_run(["refresh"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("no projects recorded", r.stdout)


    def updater(self, *args):
        return subprocess.run(["bash", str(self.kit / "updater.sh"), *args], capture_output=True, text=True,
                              env=self.env, cwd=str(self.tmp), timeout=900)

    def upstream_commit(self, name, tag=None):
        (self.upstream / f"{name}.txt").write_text(name + "\n")
        self.git(self.upstream, "add", "-A")
        self.git(self.upstream, "commit", "-q", "-m", name)
        if tag:
            self.git(self.upstream, "tag", tag)

    def kit_head(self):
        return self.git(self.kit, "rev-parse", "HEAD").strip()

    def test_updater_default_follows_release_tag_not_main(self):
        self.upstream_commit("released", tag="v1.1.0")
        self.upstream_commit("unreleased-work")
        r = self.updater("--no-refresh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("release v1.1.0", r.stdout)
        self.assertTrue((self.kit / "released.txt").exists())
        self.assertFalse((self.kit / "unreleased-work.txt").exists())

    def test_updater_edge_follows_main(self):
        self.upstream_commit("released", tag="v1.1.0")
        self.upstream_commit("unreleased-work")
        r = self.updater("--edge", "--no-refresh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.kit / "unreleased-work.txt").exists())

    def test_updater_picks_highest_semver_tag(self):
        self.upstream_commit("a", tag="v1.9.0")
        self.upstream_commit("b", tag="v1.10.0")
        r = self.updater("--no-refresh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("release v1.10.0", r.stdout)
        self.assertTrue((self.kit / "b.txt").exists())

    def test_updater_ignores_non_release_tags(self):
        self.upstream_commit("c", tag="v2.0.0-rc1")
        r = self.updater("--no-refresh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("already up to date", r.stdout)
        self.assertFalse((self.kit / "c.txt").exists())

    def test_updater_check_changes_nothing(self):
        self.upstream_commit("released", tag="v1.1.0")
        before = self.kit_head()
        r = self.updater("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("release v1.1.0", r.stdout)
        self.assertEqual(self.kit_head(), before)

    def test_updater_ahead_of_latest_release_is_up_to_date(self):
        self.upstream_commit("work")
        self.updater("--edge", "--no-refresh")
        head = self.kit_head()
        r = self.updater("--no-refresh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("already up to date", r.stdout)
        self.assertEqual(self.kit_head(), head)

    def test_updater_without_any_release_tag_points_to_edge(self):
        self.git(self.upstream, "tag", "-d", "v1.0.0")
        self.git(self.kit, "tag", "-d", "v1.0.0")
        r = self.updater("--no-refresh")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--edge", r.stderr)

    def test_version_flag_reads_version_file(self):
        (self.kit / "VERSION").write_text("9.8.7\n")
        r = self.kit_run(["--version"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("9.8.7", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)