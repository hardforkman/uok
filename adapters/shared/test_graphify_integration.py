#!/usr/bin/env python3
"""Graphify context-graph integration tests (release 1.1.0).

Runs the real installers on scratch projects with a FAKE graphify CLI on PATH
(no network, no real Graphify). verified_local evidence for CG-01..07 wiring;
live host behaviour is checked separately (core/CONTEXT-GRAPH.md, Live checks).

Run: python3 adapters/shared/test_graphify_integration.py   (exit 0 = all pass)
"""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
KIT = os.path.dirname(os.path.dirname(HERE))
UOK = os.path.join(KIT, "uok")

FAKE = """#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
if a[:1] == ["--version"]:
    print("graphify 0.9.112"); sys.exit(0)
if a[:1] == ["install"] or (len(a) >= 2 and a[1] == "install"):
    plat = a[0] if a[0] != "install" else "agents"
    if "--platform" in a: plat = a[a.index("--platform") + 1]
    if plat == "cursor" and os.environ.get("FAKE_FAIL_CURSOR"): sys.exit(1)
    dirs = {"claude": ".claude/skills", "codex": ".agents/skills", "agents": ".agents/skills",
            "cursor": ".cursor/skills"}
    d = os.path.join(dirs.get(plat, ".agents/skills"), "graphify")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "SKILL.md"), "w").write("---\\nname: graphify\\n---\\nfake skill\\n")
    sys.exit(0)
if a[:1] in (["extract"], ["update"]):
    os.makedirs("graphify-out", exist_ok=True)
    json.dump({"graph": {"schema_version": 48, "graphify_version": "0.9.112"},
               "nodes": [{"id": "A"}, {"id": "B"}], "edges": []},
              open("graphify-out/graph.json", "w"))
    print("built"); sys.exit(0)
if a[:1] == ["query"]:
    print("QUERY:" + " ".join(a[1:])); sys.exit(0)
print("fake-graphify " + " ".join(a)); sys.exit(0)
"""


class GraphifyIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix="uok-gx-")))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"; self.home.mkdir()
        self.proj = self.tmp / "proj"; self.proj.mkdir()
        (self.proj / "src").mkdir(); (self.proj / "src" / "app.py").write_text("x = 1\n")
        self.bin = self.tmp / "bin"; self.bin.mkdir()
        fake = self.bin / "graphify"; fake.write_text(FAKE); fake.chmod(0o755)

    def env(self, with_cli=True, extra=None):
        e = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "QODER", "CURSOR", "CODEX"))}
        e.update(HOME=str(self.home), PYTHONDONTWRITEBYTECODE="1")
        if with_cli:
            e["PATH"] = str(self.bin) + os.pathsep + e.get("PATH", "")
        if extra: e.update(extra)
        return e

    def init(self, host="qoder", extra=(), with_cli=True, env_extra=None, proj=None):
        return subprocess.run([sys.executable, UOK, "init", "--host", host,
                               "--project", str(proj or self.proj), *extra],
                              capture_output=True, text=True, cwd=str(self.tmp),
                              env=self.env(with_cli, env_extra), timeout=900)

    def g1(self, event, fmt="qoder"):
        return subprocess.run([sys.executable, "-I", str(self.proj / ".orchestrator/hooks/g1_guard.py"),
                               "--format", fmt], input=json.dumps(event), capture_output=True, text=True,
                              env=dict(self.env(), UOK_PROJECT_DIR=str(self.proj)), timeout=60)

    def read(self, rel):
        return (self.proj / rel).read_text(encoding="utf-8")

    def test_auto_without_cli_degrades_honestly(self):
        r = self.init(with_cli=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("degraded_context_graph", r.stdout)
        self.assertIn("enabled: false", self.read(".orchestrator/policy/graphify.yaml"))
        self.assertIn('context_graph: "none"', self.read(".orchestrator/policy/adapter.yaml"))

    def test_install_with_cli_qoder(self):
        r = self.init()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.proj / ".qoder/skills/graphify/SKILL.md").exists())
        self.assertTrue((self.proj / "graphify-out/graph.json").exists())
        self.assertIn("): PASS", r.stdout)
        self.assertIn('context_graph: "graphify"', self.read(".orchestrator/policy/adapter.yaml"))
        self.assertIn(".env", self.read(".graphifyignore"))
        self.assertIn("graphify-out/", self.read(".gitignore"))
        self.assertIn("CG-01", self.read("AGENTS.md"))

    def test_idempotent_ignore_and_second_run(self):
        self.init()
        r = self.init()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(".graphifyignore (unchanged)", r.stdout)
        self.assertEqual(self.read(".graphifyignore").count("# UOK:BEGIN graphify"), 1)

    def test_dry_run_writes_nothing(self):
        empty = self.tmp / "empty"; empty.mkdir()
        r = self.init(extra=("--dry-run",), proj=empty)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(any(empty.iterdir()), "dry run wrote files")

    def test_off_skips_everything(self):
        r = self.init(extra=("--graphify", "off"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.proj / ".graphifyignore").exists())
        self.assertIn('context_graph: "none"', self.read(".orchestrator/policy/adapter.yaml"))

    def test_claude_code_host_and_cursor_fallback(self):
        r = self.init(host="claude-code")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.proj / ".claude/skills/graphify/SKILL.md").exists())
        self.assertIn("CG-01", self.read("CLAUDE.md"))
        p2 = self.tmp / "proj2"; p2.mkdir()
        r = self.init(host="cursor", proj=p2, env_extra={"FAKE_FAIL_CURSOR": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((p2 / ".cursor/skills/graphify/SKILL.md").exists())   # agents fallback + copy

    def test_g1_graph_is_read_only_for_workers(self):
        self.init()
        w = {"tool_name": "Write", "tool_input": {"file_path": str(self.proj / "graphify-out/graph.json"),
                                                  "content": "{}"}, "agent_type": "uok-implementation-engineer"}
        self.assertIn('"deny"', self.g1(w).stdout)
        w2 = {"tool_name": "Write", "tool_input": {"file_path": str(self.proj / ".graphifyignore"),
                                                   "content": "x"}, "agent_type": "uok-implementation-engineer"}
        self.assertIn('"deny"', self.g1(w2).stdout)
        main = dict(w, agent_type="")
        self.assertNotIn('"deny"', self.g1(main).stdout)
        b = {"tool_name": "Bash", "tool_input": {"command": "graphify extract ."},
             "agent_type": "uok-implementation-engineer"}
        self.assertIn("CG-04", self.g1(b).stdout)
        q = {"tool_name": "Bash", "tool_input": {"command": "graphify query auth"},
             "agent_type": "uok-research-analyst"}
        self.assertNotIn('"deny"', self.g1(q).stdout)

    def test_wrapper_finds_cli_in_local_bin(self):
        """uv/pipx put graphify in ~/.local/bin, which GUI-session PATHs often lack —
        the wrapper must fall back there (same as the installer's find_cli)."""
        r = self.init(extra=("--mode", "strict"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        local = self.home / ".local" / "bin"
        local.mkdir(parents=True)
        shutil.copy2(self.bin / "graphify", local / "graphify")
        hook = str(self.proj / ".orchestrator/hooks/uok_graph.py")
        r = subprocess.run([sys.executable, "-I", hook, "query", "auth"], capture_output=True,
                           text=True, env=self.env(with_cli=False), cwd=str(self.proj), timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("QUERY:auth", r.stdout)

    def test_strict_mode_wrapper(self):
        r = self.init(extra=("--mode", "strict"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wrap = f"python3 -I {self.proj}/.orchestrator/hooks/uok_graph.py query auth flow"
        ok = {"tool_name": "Bash", "tool_input": {"command": wrap}, "agent_type": "uok-research-analyst"}
        self.assertNotIn('"deny"', self.g1(ok).stdout)
        bad = {"tool_name": "Bash", "tool_input": {"command": 'graphify query "auth"'},
               "agent_type": "uok-research-analyst"}
        self.assertIn('"deny"', self.g1(bad).stdout)
        hook = str(self.proj / ".orchestrator/hooks/uok_graph.py")
        run = lambda *a: subprocess.run([sys.executable, "-I", hook, *a], capture_output=True,
                                        text=True, env=self.env(), cwd=str(self.proj), timeout=60)
        r = run("query", "auth", "flow")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("QUERY:auth flow", r.stdout)
        self.assertEqual(run("query", "--graph", "/elsewhere").returncode, 2)
        self.assertEqual(run("extract", ".").returncode, 2)

    def test_registry_and_refresh_keep_integration(self):
        self.init()
        reg = json.loads((self.home / ".uok/projects.json").read_text())["projects"]
        self.assertEqual(reg[0]["graphify"], "auto")
        r = subprocess.run([sys.executable, UOK, "refresh"], capture_output=True, text=True,
                           cwd=str(self.tmp), env=self.env(), timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("enabled: true", self.read(".orchestrator/policy/graphify.yaml"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
