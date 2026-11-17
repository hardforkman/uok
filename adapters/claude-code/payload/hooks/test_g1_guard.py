#!/usr/bin/env python3
"""Black-box tests for the G1 PreToolUse guard (g1_guard.py)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "g1_guard.py")

# Fixture policy (explicit, independent of the live project.yaml).
FIXTURE_POLICY = """\
project:
  shell_allowlist:
    - "ls"
    - "pwd"
    - "cat"
    - "head"
    - "tail"
    - "grep"
    - "wc"
    - "git status"
    - "git diff"
"""


class G1GuardTest(unittest.TestCase):
    """Full suite in `enforcement: strict` (worker sandbox on)."""
    MODE = "strict"

    def setUp(self):
        self.root = tempfile.mkdtemp()
        for d in ("claims", "audit", "policy"):
            os.makedirs(os.path.join(self.root, ".orchestrator", d))
        with open(os.path.join(self.root, ".orchestrator", "policy", "project.yaml"), "w") as f:
            f.write(FIXTURE_POLICY)
        with open(os.path.join(self.root, ".orchestrator", "policy", "claude-code.yaml"), "w") as f:
            f.write(f"enforcement: {self.MODE}\nkit_dir: \"UNIVERSAL-ORCHESTRATOR-KIT\"\n")
        self.addCleanup(shutil.rmtree, self.root, True)

    # helpers
    def run_full(self, stdin_text):
        """Run the hook; return (decision, reason). Crash => test failure (T1)."""
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.root)
        p = subprocess.run([sys.executable, "-I", HOOK], input=stdin_text, capture_output=True,
                           text=True, env=env, timeout=30)
        self.assertEqual(p.returncode, 0, f"hook exit {p.returncode}; stderr={p.stderr!r}")
        self.assertNotIn("Traceback", p.stderr)
        out = p.stdout.strip()
        if not out:
            return "allow", ""
        h = json.loads(out)["hookSpecificOutput"]
        return h["permissionDecision"], h["permissionDecisionReason"]

    def run_raw(self, stdin_text):
        return self.run_full(stdin_text)[0]

    def run_event(self, tool, tool_input, agent=None):
        return self.run_event_full(tool, tool_input, agent)[0]

    def run_event_full(self, tool, tool_input, agent=None):
        ev = {"tool_name": tool, "tool_input": tool_input}
        if agent:
            ev["agent_type"] = agent
        result = self.run_full(json.dumps(ev))
        if result[0] == "allow":
            # N-T1: a real allow is logged as "allow:"; a swallowed crash is "fail-open:".
            last = self.audit_log().strip().splitlines()[-1:] or [""]
            self.assertIn(" allow: ", last[0], f"expected allow log line, got {last[0]!r}")
        return result

    def set_claims(self, claims):
        with open(os.path.join(self.root, ".orchestrator", "claims", "active.json"), "w") as f:
            json.dump({"claims": claims}, f)

    def audit_log(self):
        path = os.path.join(self.root, ".orchestrator", "audit", "g1.log")
        if not os.path.exists(path):
            return ""
        with open(path) as f:
            return f.read()

    def p(self, rel):
        return os.path.join(self.root, rel)

    def outside(self, name="g1_outside_probe.txt"):
        return os.path.join(tempfile.gettempdir(), name)

    @staticmethod
    def secret():
        return "pass" + "word=" + "abcdefghij0123456789xyz"

    @staticmethod
    def sk_secret():
        return "sk" + "-" + "A1b2C3d4E5f6G7h8I9j0"

    def assertDecision(self, result, decision, code=None):
        got, reason = result
        self.assertEqual(got, decision, reason)
        if code:
            self.assertIn(code, reason)

    # secret paths / content / root
    def test_read_env_denied(self):
        self.assertDecision(self.run_event_full("Read", {"file_path": self.p(".env")}),
                            "deny", "SEC-02")

    def test_read_env_variant_denied(self):
        self.assertDecision(self.run_event_full("Read", {"file_path": self.p(".env.local")}),
                            "deny", "SEC-02")

    def test_path_key_env_denied(self):
        self.assertDecision(self.run_event_full("Read", {"path": self.p(".env")}),
                            "deny", "SEC-02")

    def test_path_key_outside_root_denied(self):
        self.assertDecision(
            self.run_event_full("Write", {"path": self.outside(), "content": "hi"}),
            "deny", "ISO-02")

    def test_read_outside_root_allowed(self):
        self.assertEqual(self.run_event("Read", {"file_path": self.outside("readme.txt")}),
                         "allow")

    def test_write_outside_root_denied(self):
        self.assertDecision(
            self.run_event_full("Write", {"file_path": self.outside(), "content": "hi"}),
            "deny", "ISO-02")

    def test_write_secret_content_denied(self):
        self.assertDecision(
            self.run_event_full("Write", {"file_path": self.p("notes.txt"),
                                          "content": self.secret()}),
            "deny", "SEC-03")

    def test_write_sk_secret_denied(self):
        self.assertDecision(
            self.run_event_full("Write", {"file_path": self.p("notes.txt"),
                                          "content": "k=" + self.sk_secret()}),
            "deny", "SEC-03")

    def test_edit_new_string_secret_denied(self):
        self.assertDecision(
            self.run_event_full("Edit", {"file_path": self.p("notes.txt"), "old_string": "a",
                                         "new_string": self.secret()}),
            "deny", "SEC-03")

    def test_multiedit_edits_secret_denied(self):
        edits = [{"old_string": "a", "new_string": "b"},
                 {"old_string": "c", "new_string": self.secret()}]
        self.assertDecision(
            self.run_event_full("MultiEdit", {"file_path": self.p("notes.txt"), "edits": edits}),
            "deny", "SEC-03")

    def test_write_benign_allowed(self):
        self.assertEqual(
            self.run_event("Write", {"file_path": self.p("notes.txt"), "content": "hello"}),
            "allow")

    # NotebookEdit (T2)
    def test_notebook_env_path_denied(self):
        self.assertDecision(
            self.run_event_full("NotebookEdit", {"notebook_path": self.p(".env"),
                                                 "new_source": "x = 1"}),
            "deny", "SEC-02")

    def test_notebook_outside_root_denied(self):
        self.assertDecision(
            self.run_event_full("NotebookEdit", {"notebook_path": self.outside("nb.ipynb"),
                                                 "new_source": "x = 1"}),
            "deny", "ISO-02")

    def test_notebook_secret_source_denied(self):
        self.assertDecision(
            self.run_event_full("NotebookEdit", {"notebook_path": self.p("nb.ipynb"),
                                                 "new_source": self.secret()}),
            "deny", "SEC-03")

    def test_notebook_benign_allowed(self):
        self.assertEqual(
            self.run_event("NotebookEdit", {"notebook_path": self.p("nb.ipynb"),
                                            "new_source": "print('hi')"}),
            "allow")

    # shell
    FORCE = "git push --force origin main"

    def test_main_force_push_asks(self):
        self.assertDecision(self.run_event_full("Bash", {"command": self.FORCE}), "ask", "SEC-07")

    def test_release_integration_force_push_asks(self):
        self.assertDecision(
            self.run_event_full("Bash", {"command": self.FORCE}, "uok-release-integration"),
            "ask", "SEC-07")

    def test_test_engineer_force_push_denied(self):
        self.assertDecision(
            self.run_event_full("Bash", {"command": self.FORCE}, "uok-test-engineer"),
            "deny", "SEC-04")

    def test_test_engineer_ls_allowed(self):
        self.assertEqual(self.run_event("Bash", {"command": "ls"}, "uok-test-engineer"), "allow")

    def test_test_engineer_redirect_denied(self):
        self.assertDecision(
            self.run_event_full("Bash", {"command": "ls > out"}, "uok-test-engineer"),
            "deny", "SEC-04")

    def test_test_engineer_pipe_to_rm_denied(self):
        self.assertDecision(
            self.run_event_full("Bash", {"command": "ls | rm x"}, "uok-test-engineer"),
            "deny", "SEC-04")

    def test_test_engineer_sensitive_with_args_denied(self):
        # exact-match policy: a non-approval role never reaches the ask gate with a free-form command
        self.assertDecision(
            self.run_event_full("Bash", {"command": 'grep "DROP TABLE" x'}, "uok-test-engineer"),
            "deny", "SEC-04")

    def test_senior_engineer_rm_rf_asks(self):
        self.assertDecision(
            self.run_event_full("Bash", {"command": "rm -rf build"}, "uok-senior-engineer"),
            "ask", "SEC-07")

    def test_main_rm_rf_asks(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "rm -rf build"}),
                            "ask", "SEC-07")

    # claims
    CLAIM = [{"task_id": "T1", "agent": "uok-implementation-engineer", "write": ["probe/a/*"]}]

    def test_claim_inside_allowed(self):
        self.set_claims(self.CLAIM)
        self.assertEqual(self.run_event("Write", {"file_path": self.p("probe/a/x.py"),
                                                  "content": "x = 1"},
                                        "uok-implementation-engineer"), "allow")

    def test_claim_outside_denied(self):
        self.set_claims(self.CLAIM)
        self.assertDecision(
            self.run_event_full("Write", {"file_path": self.p("src/y.py"), "content": "x = 1"},
                                "uok-implementation-engineer"),
            "deny", "LC-04")

    def test_main_write_in_others_claim_denied(self):
        self.set_claims(self.CLAIM)
        self.assertDecision(
            self.run_event_full("Write", {"file_path": self.p("probe/a/z.py"),
                                          "content": "x = 1"}),
            "deny", "LC-04")

    def test_claim_matched_in_worktree(self):
        self.set_claims(self.CLAIM)
        path = self.p(".claude/worktrees/w1/probe/a/x.py")
        self.assertEqual(self.run_event("Write", {"file_path": path, "content": "x = 1"},
                                        "uok-implementation-engineer"), "allow")

    def test_released_claim_ignored(self):
        claim = [dict(self.CLAIM[0], released=True)]
        self.set_claims(claim)
        self.assertEqual(self.run_event("Write", {"file_path": self.p("probe/a/z.py"),
                                                  "content": "x = 1"}), "allow")
        self.assertEqual(self.run_event("Write", {"file_path": self.p("src/y.py"),
                                                  "content": "x = 1"},
                                        "uok-implementation-engineer"), "allow")

    # MCP
    def test_mcp_secret_payload_denied(self):
        self.assertDecision(self.run_event_full("mcp__srv__tool", {"text": self.secret()}),
                            "deny", "SEC-03")

    def test_mcp_from_uok_agent_denied(self):
        self.assertDecision(
            self.run_event_full("mcp__srv__tool", {"q": "hello"}, "uok-research-analyst"),
            "deny", "SEC-04")

    # fail-open (T3, T4)
    def assertFailOpen(self, stdin_text, marker):
        self.assertEqual(self.run_raw(stdin_text), "allow")
        log = self.audit_log()
        self.assertIn("fail-open: " + marker, log)

    def test_malformed_stdin_allows(self):
        self.assertFailOpen("{not json", "bad input")

    def test_toplevel_list_fail_open(self):
        self.assertFailOpen("[]", "event is not a JSON object")

    def test_toplevel_string_fail_open(self):
        self.assertFailOpen('"x"', "event is not a JSON object")

    def test_toplevel_null_fail_open(self):
        self.assertFailOpen("null", "event is not a JSON object")

    def test_tool_input_string_fail_open(self):
        self.assertFailOpen(json.dumps({"tool_name": "Read", "tool_input": "x"}),
                            "tool_input is not an object")

    def test_tool_input_list_fail_open(self):
        self.assertFailOpen(json.dumps({"tool_name": "Read", "tool_input": [1]}),
                            "tool_input is not an object")

    def test_write_tool_input_not_object_fails_closed(self):
        for bad in ("x", [1]):
            self.assertDecision(self.run_full(json.dumps({"tool_name": "Write", "tool_input": bad})),
                                "deny", "failing closed")

    def test_tool_name_int_fail_open(self):
        self.assertFailOpen(json.dumps({"tool_name": 7, "tool_input": {}}), "hook error")

    def test_active_json_list_fail_open(self):
        with open(os.path.join(self.root, ".orchestrator", "claims", "active.json"), "w") as f:
            f.write("[]")
        self.assertFailOpen(json.dumps({"tool_name": "Write", "tool_input": {
            "file_path": self.p("notes.txt"), "content": "hello"}}), "active.json is not an object")

    def test_malformed_claim_entry_logged(self):
        self.set_claims([{"agent": "uok-x", "write": None}])
        self.assertFailOpen(json.dumps({"tool_name": "Write", "tool_input": {
            "file_path": self.p("notes.txt"), "content": "hello"}}), "malformed claim entries ignored")

    def test_secret_scanned_before_malformed_claims(self):
        self.set_claims([{"agent": "uok-x", "write": None}])
        self.assertDecision(self.run_event_full("Write", {"file_path": self.p("a.txt"),
                            "content": self.secret()}), "deny", "SEC-03")

    # single "&" separator (N-T3)
    def test_ampersand_segment_denied(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "ls & rm x"},
                            "uok-test-engineer"), "deny", "SEC-04")

    def test_ampersand_allowlisted_segments_allowed(self):
        self.assertEqual(self.run_event("Bash", {"command": "ls & pwd"}, "uok-test-engineer"), "allow")

    # quoted secret values inside nested payloads (N-C1)
    @staticmethod
    def quoted_secret():
        return "tok" + "en: \"" + "abcdefghij0123456789xyz" + "\""

    def test_mcp_quoted_secret_denied(self):
        self.assertDecision(self.run_event_full("mcp__srv__tool", {"body": {"x": [self.quoted_secret()]}}),
                            "deny", "SEC-03")

    def test_multiedit_quoted_secret_denied(self):
        self.assertDecision(self.run_event_full("MultiEdit", {"file_path": self.p("a.txt"), "edits": [
            {"old_string": "a", "new_string": self.quoted_secret()}]}), "deny", "SEC-03")

    # ---- security review round 2 (B1, B2, M1-M4, L1, L2, L5) ----
    def test_git_output_option_denied(self):
        for cmd in ("git diff --output=/tmp/x", "git log --output=notes.txt", "git diff --no-index a b",
                    "git diff -c x"):
            self.assertDecision(self.run_event_full("Bash", {"command": cmd}, "uok-test-engineer"),
                                "deny", "SEC-04")

    def test_shell_secret_path_argument_denied(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "cat .env"}, "uok-test-engineer"),
                            "deny", "SEC-04")

    def test_shell_outside_root_argument_denied(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "cat /etc/hosts"}, "uok-test-engineer"),
                            "deny", "SEC-04")

    def test_zsh_constructs_denied(self):
        for cmd in ("ls =(touch x)", "ls *(e:'touch x':)", "ls {a,b}", "cat .en?", "ls ~", "ls $HOME"):
            self.assertDecision(self.run_event_full("Bash", {"command": cmd}, "uok-test-engineer"),
                                "deny", "SEC-04")

    def test_quoted_pattern_denied(self):
        self.assertDecision(self.run_event_full("Bash", {"command": 'grep "a*b" notes.txt'},
                            "uok-test-engineer"), "deny", "SEC-04")

    def test_deep_nested_mcp_fails_closed(self):
        deep = "[" * 5000 + '"x"' + "]" * 5000
        stdin = '{"tool_name": "mcp__srv__tool", "tool_input": {"a": ' + deep + '}}'
        self.assertDecision(self.run_full(stdin), "deny", "SEC-03")

    def test_deep_nested_uok_mcp_denied(self):
        deep = "[" * 500 + '"x"' + "]" * 500
        stdin = ('{"tool_name": "mcp__srv__tool", "agent_type": "uok-research-analyst", '
                 '"tool_input": {"a": ' + deep + '}}')
        self.assertDecision(self.run_full(stdin), "deny", "SEC-04")

    def test_mcp_key_value_secret_denied(self):
        self.assertDecision(self.run_event_full("mcp__srv__tool",
                            {"api" + "_key": "abcdefghij0123456789xyz"}), "deny", "SEC-03")

    def test_mcp_secret_as_dict_key_denied(self):
        self.assertDecision(self.run_event_full("mcp__srv__tool", {self.sk_secret(): 1}), "deny", "SEC-03")

    def test_dual_path_keys_all_checked(self):
        self.assertDecision(self.run_event_full("NotebookEdit", {"file_path": self.p("ok.ipynb"),
                            "notebook_path": "/outside/x.ipynb", "new_source": "1"}), "deny", "ISO-02")

    def test_uok_write_to_guard_controls_denied(self):
        for rel_path in (".orchestrator/hooks/g1_guard.py", ".orchestrator/policy/project.yaml",
                         ".orchestrator/claims/active.json", ".claude/settings.json", ".git/config"):
            self.assertDecision(self.run_event_full("Write", {"file_path": self.p(rel_path), "content": "x"},
                                "uok-implementation-engineer"), "deny", "SEC-04")

    def test_uok_write_blocked_while_claims_malformed(self):
        self.set_claims([{"agent": "uok-implementation-engineer", "write": None}])
        self.assertDecision(self.run_event_full("Write", {"file_path": self.p("a.txt"), "content": "x"},
                            "uok-implementation-engineer"), "deny", "LC-04")

    def test_claim_match_case_insensitive(self):
        self.set_claims([{"task_id": "T", "agent": "uok-test-engineer", "write": ["src/*"]}])
        self.assertDecision(self.run_event_full("Write", {"file_path": self.p("SRC/x.py"), "content": "x"}),
                            "deny", "LC-04")

    def test_secret_directory_component_denied(self):
        self.assertDecision(self.run_event_full("Read", {"file_path": self.p("secrets/config.yaml")}),
                            "deny", "SEC-02")

    def test_grep_path_secret_denied(self):
        self.assertDecision(self.run_event_full("Grep", {"pattern": "x", "path": self.p(".env")}),
                            "deny", "SEC-02")

    def test_rm_split_flags_asks(self):
        for cmd in ("rm -r -f build", "rm --recursive --force build", "rm -Rf build"):
            self.assertDecision(self.run_event_full("Bash", {"command": cmd}), "ask", "SEC-07")

    def test_nonstring_command_fails_closed_for_uok(self):
        self.assertDecision(self.run_full(json.dumps({"tool_name": "Bash", "agent_type": "uok-test-engineer",
                            "tool_input": {"command": ["ls"]}})), "deny", "failing closed")

    # ---- security review round 3 (NB1-NB4, N1-N5) ----
    def test_recursive_grep_denied(self):
        for cmd in ("grep -r KEY .", "grep -rh x " + self.root, "grep -f.env x.txt", "git diff -O/etc/passwd",
                    "cat .env", "ls -R /"):
            self.assertDecision(self.run_event_full("Bash", {"command": cmd}, "uok-test-engineer"),
                                "deny", "SEC-04")

    def test_backslash_quote_tricks_denied(self):
        for cmd in ('ls \\" *(e:\'touch pwned\':) \\"', 'ls \\" =(touch x) \\"',
                    'cat \\" ' + self.root + '/.e* \\"'):
            self.assertDecision(self.run_event_full("Bash", {"command": cmd}, "uok-test-engineer"),
                                "deny", "SEC-04")

    def test_exact_allowlisted_commands_allowed(self):
        for cmd in ("ls", "git status", "ls && pwd", "git status ; ls"):
            self.assertEqual(self.run_event("Bash", {"command": cmd}, "uok-test-engineer"), "allow", cmd)

    def test_guard_controls_case_insensitive(self):
        for rel_path in (".Orchestrator/hooks/g1_guard.py", ".CLAUDE/settings.json",
                         ".orchestrator/Policy/project.yaml", ".GIT/hooks/pre-commit", "Claude.md",
                         ".claude/Worktrees/w1/.Orchestrator/hooks/g1_guard.py"):
            self.assertDecision(self.run_event_full("Write", {"file_path": self.p(rel_path), "content": "x"},
                                "uok-implementation-engineer"), "deny", "SEC-04")

    def test_allowlisted_script_dirs_protected(self):
        for rel_path in ("UNIVERSAL-ORCHESTRATOR-KIT/validation/self_test.py",
                         "UNIVERSAL-ORCHESTRATOR-KIT/validation/yaml.py", ".orchestrator/audit/g1.log"):
            self.assertDecision(self.run_event_full("Write", {"file_path": self.p(rel_path), "content": "x"},
                                "uok-implementation-engineer"), "deny", "SEC-04")

    def test_main_session_may_write_guard_controls(self):
        self.assertEqual(self.run_event("Write", {"file_path": self.p(".claude/settings.json"), "content": "{}"}),
                         "allow")

    def test_uok_read_outside_root_denied(self):
        self.assertDecision(self.run_event_full("Read", {"file_path": "/etc/hosts"}, "uok-research-analyst"),
                            "deny", "ISO-02")

    def test_extended_secret_names_denied(self):
        for name in (".netrc", ".npmrc", ".pypirc", "server.key", ".gnupg/x", ".kube/config", "id_ed25519"):
            self.assertDecision(self.run_event_full("Read", {"file_path": self.p(name)}), "deny", "SEC-02")

    def test_approval_role_cannot_smuggle_non_allowlisted_segment(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "cat .env && rm -rf build"},
                            "uok-senior-engineer"), "deny", "SEC-04")

    def test_approval_role_allowlisted_plus_sensitive_asks(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "ls && rm -rf build"},
                            "uok-senior-engineer"), "ask", "SEC-07")

    def test_symlink_to_secret_denied(self):
        with open(self.p(".env"), "w") as f:
            f.write("X=1\n")
        os.symlink(self.p(".env"), self.p("innocent.txt"))
        self.assertDecision(self.run_event_full("Read", {"file_path": self.p("innocent.txt")}), "deny", "SEC-02")

    # ---- uok_search.py (safe search replacing grep/cat for uok-* agents) ----
    def _search(self, *args):
        hooks = os.path.join(self.root, ".orchestrator", "hooks")
        os.makedirs(hooks, exist_ok=True)
        src = os.path.dirname(os.path.abspath(HOOK))
        for name in ("g1_guard.py", "uok_search.py"):
            shutil.copy(os.path.join(src, name), hooks)
        p = subprocess.run([sys.executable, "-I", os.path.join(hooks, "uok_search.py"), *args],
                           capture_output=True, text=True, timeout=30, cwd=tempfile.gettempdir())
        self.assertNotIn("Traceback", p.stderr)
        return p.stdout

    def test_search_finds_plain_files_and_skips_secrets(self):
        marker = "UOK" + "MARKER42"
        os.makedirs(self.p("src/conf"))
        for rel_path in ("src/a.py", "src/conf/.env", "src/conf/.env.local", "src/server.key",
                         "src/secrets/x.txt"):
            os.makedirs(os.path.dirname(self.p(rel_path)), exist_ok=True)
            with open(self.p(rel_path), "w") as f:
                f.write(marker + "\n")
        out = self._search(marker)
        self.assertIn("src/a.py:1:", out)
        for leaked in (".env", "server.key", "secrets/"):
            self.assertNotIn(leaked, out)

    def test_search_refuses_outside_root(self):
        self.assertIn("refused", self._search("x", ".."))
        self.assertIn("refused", self._search("x", "/etc"))

    def test_search_skips_symlink_out_of_root(self):
        outside = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside, True)
        marker = "UOK" + "OUTSIDE7"
        with open(os.path.join(outside, "o.txt"), "w") as f:
            f.write(marker + "\n")
        os.symlink(os.path.join(outside, "o.txt"), self.p("link.txt"))
        os.symlink(outside, self.p("linkdir"))
        self.assertIn("no matches", self._search(marker))

    def test_search_command_allowlist_shape(self):
        with open(os.path.join(self.root, ".orchestrator", "policy", "project.yaml"), "a") as f:
            f.write('    - "python3 -I /x/uok_search.py ..."\n')
        self.assertEqual(self.run_event("Bash", {"command": "python3 -I /x/uok_search.py def.main src"},
                                        "uok-research-analyst"), "allow")
        for cmd in ('python3 -I /x/uok_search.py "a b"', "python3 -I /x/uok_search.py x $HOME",
                    "python3 -I /x/uok_search.pyX x", "python3 -I /x/uok_search.py"):
            self.assertDecision(self.run_event_full("Bash", {"command": cmd}, "uok-research-analyst"),
                                "deny", "SEC-04")

    # ---- security review round 3, part 2 (Unicode/case folding B1, regex DoS B2) ----
    def _folds(self):
        """True if this volume folds U+017F to 's' (APFS/HFS+ case-insensitive)."""
        probe = self.p("fold_probe_s")
        open(probe, "w").close()
        return os.path.exists(self.p("fold_probe_ſ"))

    def test_unicode_folded_guard_controls_denied(self):
        os.makedirs(self.p(".orchestrator/hooks"), exist_ok=True)
        open(self.p(".orchestrator/hooks/g1_guard.py"), "w").close()
        for spelled in (".orcheſtrator/hooks/g1_guard.py", ".orchestrator/hooKs/g1_guard.py",
                        ".ORCHESTRATOR/hooks/g1_guard.py"):
            self.assertDecision(self.run_event_full("Write", {"file_path": self.p(spelled), "content": "x"},
                                "uok-implementation-engineer"), "deny", "SEC-04")

    def test_unicode_folded_secret_read_denied_main_session(self):
        if not self._folds():
            self.skipTest("volume does not fold Unicode")
        os.makedirs(self.p("conf"), exist_ok=True)
        with open(self.p("conf/db_secret.txt"), "w") as f:
            f.write("x\n")
        self.assertDecision(self.run_event_full("Read", {"file_path": self.p("conf/db_ſecret.txt")}),
                            "deny", "SEC-02")

    def test_unicode_folded_claim_still_matched(self):
        if not self._folds():
            self.skipTest("volume does not fold Unicode")
        os.makedirs(self.p("src"), exist_ok=True)
        self.set_claims([{"task_id": "T", "agent": "uok-test-engineer", "write": ["src/*"]}])
        self.assertDecision(self.run_event_full("Write", {"file_path": self.p("ſrc/x.py"), "content": "x"}),
                            "deny", "LC-04")

    def test_non_ascii_path_denied_for_uok(self):
        self.assertDecision(self.run_event_full("Read", {"file_path": self.p("café.txt")},
                            "uok-research-analyst"), "deny", "SEC-04")

    def test_restricted_charset_check_is_linear(self):
        import time as _t
        cmd = "ls" + " ; " * 600 + "\""
        t0 = _t.monotonic()
        self.assertDecision(self.run_event_full("Bash", {"command": cmd}, "uok-test-engineer"), "deny", "SEC-04")
        self.assertLess(_t.monotonic() - t0, 5.0)

    def test_overlong_restricted_command_denied(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "ls " + "a" * 3000}, "uok-test-engineer"),
                            "deny", "SEC-04")

    def test_search_skips_audit_log(self):
        os.makedirs(self.p(".orchestrator/audit"), exist_ok=True)
        marker = "UOK" + "AUDIT9"
        with open(self.p(".orchestrator/audit/g1.log"), "w") as f:
            f.write(marker + "\n")
        self.assertIn("no matches", self._search(marker))

    # ---- security review round 4 (N1 regex DoS, N2 audit/claims reads, N4 verb position) ----
    def _timed(self, cmd, agent=None, limit=5.0):
        import time as _t
        t0 = _t.monotonic()
        result = self.run_event_full("Bash", {"command": cmd}, agent)
        self.assertLess(_t.monotonic() - t0, limit, f"hook too slow on {len(cmd)}-char input")
        return result

    def test_rm_backtracking_input_is_fast(self):
        self.assertDecision(self._timed("rm -r " * 3000 + "; ls", "uok-test-engineer"), "deny", "SEC-04")
        self.assertEqual(self._timed("rm -r " * 3300 + "; ls")[0], "allow")

    def test_git_push_backtracking_input_is_fast(self):
        self.assertEqual(self._timed("git push x " * 1800 + "; ls")[0], "allow")
        self.assertEqual(self._timed("'" + "git push x " * 1800)[0], "allow")

    def test_overlong_main_command_asks(self):
        self.assertDecision(self._timed("ls " + "a" * 25000), "ask", "SEC-07")

    def test_token_based_sensitive_detection(self):
        for cmd in ("rm -r -f build", "rm --recursive --force build", "sudo rm -rf /x", "env X=1 rm -fr x",
                    "git push origin main --force-with-lease", "git push -fu origin x", "git reset --hard",
                    "git clean -fd", "bash -c 'rm -rf x'", "npm run deploy:prod", "terraform destroy"):
            self.assertDecision(self.run_event_full("Bash", {"command": cmd}), "ask", "SEC-07")
        for cmd in ("git push origin main", "rm -r build", "ls -rf", "git log --format=%f"):
            self.assertEqual(self.run_event("Bash", {"command": cmd}), "allow", cmd)

    def test_approval_role_sensitive_word_not_at_verb_position_denied(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "python3 /x/y.py rm -rf build"},
                            "uok-senior-engineer"), "deny", "SEC-04")

    def test_uok_cannot_read_audit_or_claims(self):
        for rel_path in (".orchestrator/audit/g1.log", ".orchestrator/claims/active.json", ".git/config",
                         ".Orchestrator/Audit/g1.log"):
            self.assertDecision(self.run_event_full("Read", {"file_path": self.p(rel_path)},
                                "uok-research-analyst"), "deny", "SEC-04")

    def test_search_refuses_audit_and_git_start_dirs(self):
        for d in (".orchestrator/audit", ".orchestrator/claims", ".git", ".orchestrator/audit/../audit"):
            os.makedirs(self.p(d.split("/..")[0]), exist_ok=True)
            self.assertIn("refused", self._search("x", d))

    def test_log_line_cannot_be_forged_with_newline(self):
        self.run_event_full("Read", {"file_path": self.p("a\nFAKE allow: [main] Write /x")}, None)
        self.assertNotIn("\nFAKE", self.audit_log())

    # ---- security review round 5 (P1 path DoS, F2 Grep/Glob, F3 log forging, F4 SQL verb, main forms) ----
    def test_huge_paths_denied_fast(self):
        for p in (self.root + "/" + "./" * 500000 + ".orchestrator/hooks/g1_guard.py",
                  self.root + "/" + "a/" * 500000 + "x", self.root + "/" + "a" * 5000):
            for agent in ("uok-implementation-engineer", None):
                result = self._timed_event("Write", {"file_path": p, "content": "x"}, agent)
                self.assertDecision(result, "deny", "SEC-04")

    def _timed_event(self, tool, inp, agent=None, limit=5.0):
        import time as _t
        t0 = _t.monotonic()
        result = self.run_event_full(tool, inp, agent)
        self.assertLess(_t.monotonic() - t0, limit)
        return result

    def test_control_chars_in_path_denied(self):
        self.assertDecision(self.run_event_full("Write", {"file_path": self.p("zz\n2026 allow: [main] Bash"),
                            "content": "x"}, "uok-implementation-engineer"), "deny", "SEC-04")

    def test_uok_grep_glob_denied_even_without_path(self):
        for tool, inp in (("Grep", {"pattern": "allow:"}), ("Glob", {"pattern": "**/*"}),
                          ("Grep", {"pattern": ".", "path": self.p(".orchestrator")})):
            self.assertDecision(self.run_event_full(tool, inp, "uok-research-analyst"), "deny", "SEC-04")

    def test_main_session_grep_still_allowed(self):
        self.assertEqual(self.run_event("Grep", {"pattern": "x", "path": self.p("src")}), "allow")

    def test_drop_table_only_for_sql_clients_in_approval_skip(self):
        self.assertDecision(self.run_event_full("Bash", {"command": "python3 /x/y.py DROP TABLE x"},
                            "uok-senior-engineer"), "deny", "SEC-04")

    def test_main_session_hidden_forms_ask(self):
        for cmd in ("cd x\nrm -rf y", "( rm -rf x )", "{ rm -rf x; }", "! rm -rf x", "if true; then rm -rf x; fi",
                    "env -i rm -rf x", "sudo -u root rm -rf x", "git -C dir push --force", "git push origin +main",
                    "git push --mirror", "git push --delete origin x", "psql -c 'DROP TABLE x'"):
            self.assertDecision(self.run_event_full("Bash", {"command": cmd}), "ask", "SEC-07")

    def test_rm_cluster_fallback_is_fast(self):
        self.assertEqual(self._timed("echo 'rm -" + "r" * 19000 + "'")[0], "allow")

    # ---- security review round 6 residuals ----
    def test_instruction_and_mcp_files_protected_at_any_depth(self):
        for rel_path in (".mcp.json", "src/CLAUDE.md", "docs/sub/claude.local.md", "pkg/.claude/settings.json",
                         ".gitignore", "UNIVERSAL-ORCHESTRATOR-KIT/core/routing-policy.yaml"):
            self.assertDecision(self.run_event_full("Write", {"file_path": self.p(rel_path), "content": "x"},
                                "uok-implementation-engineer"), "deny", "SEC-04")

    def test_uok_read_type_error_fails_closed(self):
        self.assertDecision(self.run_full(json.dumps({"tool_name": "Read", "agent_type": "uok-research-analyst",
                            "tool_input": {"file_path": 7}})), "deny", "failing closed")

    def test_uok_search_pattern_with_sensitive_words_no_false_ask(self):
        with open(os.path.join(self.root, ".orchestrator", "policy", "project.yaml"), "a") as f:
            f.write('    - "python3 -I /x/uok_search.py ..."\n')
        self.assertEqual(self.run_event("Bash", {"command": "python3 -I /x/uok_search.py rm -rf"},
                                        "uok-research-analyst"), "allow")

    def test_search_rejects_backtracking_pattern(self):
        self.assertIn("refused", self._search(".+.+.+.+@@"))


class StandardModeTest(G1GuardTest):
    """`enforcement: standard` (default): base protections only; workers keep normal tools."""
    MODE = "standard"

    def test_std_worker_normal_shell_allowed(self):
        for cmd in ("grep -rn foo src", "cat README.md", "python3 -m pytest -q", "ls -la | head"):
            self.assertEqual(self.run_event("Bash", {"command": cmd}, "uok-test-engineer"), "allow", cmd)

    def test_std_worker_grep_glob_allowed(self):
        self.assertEqual(self.run_event("Grep", {"pattern": "x", "path": self.p("src")}, "uok-research-analyst"),
                         "allow")
        self.assertEqual(self.run_event("Glob", {"pattern": "**/*.py"}, "uok-research-analyst"), "allow")

    def test_std_worker_read_outside_root_allowed(self):
        self.assertEqual(self.run_event("Read", {"file_path": "/etc/hosts"}, "uok-research-analyst"), "allow")

    def test_std_secrets_still_denied(self):
        self.assertDecision(self.run_event_full("Read", {"file_path": self.p(".env")}, "uok-research-analyst"),
                            "deny", "SEC-02")
        self.assertDecision(self.run_event_full("Write", {"file_path": self.p("a.txt"), "content": self.secret()},
                            "uok-implementation-engineer"), "deny", "SEC-03")

    def test_std_write_outside_root_denied(self):
        self.assertDecision(self.run_event_full("Write", {"file_path": "/tmp/x.txt", "content": "x"},
                            "uok-implementation-engineer"), "deny", "ISO-02")

    def test_std_guard_controls_still_protected(self):
        for rel_path in (".claude/settings.json", ".orchestrator/hooks/g1_guard.py", "CLAUDE.md", ".mcp.json",
                         "UNIVERSAL-ORCHESTRATOR-KIT/core/routing-policy.yaml", ".ORCHESTRATOR/policy/x.yaml"):
            self.assertDecision(self.run_event_full("Write", {"file_path": self.p(rel_path), "content": "x"},
                                "uok-implementation-engineer"), "deny", "SEC-04")

    def test_std_claims_enforced(self):
        self.set_claims([{"task_id": "T", "agent": "uok-test-engineer", "write": ["tests/*"]}])
        self.assertDecision(self.run_event_full("Write", {"file_path": self.p("src/a.py"), "content": "x"},
                            "uok-test-engineer"), "deny", "LC-04")

    def test_std_sensitive_ops_by_role(self):
        cmd = "git push --force origin main"
        self.assertDecision(self.run_event_full("Bash", {"command": cmd}), "ask", "SEC-07")
        self.assertDecision(self.run_event_full("Bash", {"command": cmd}, "uok-release-integration"), "ask", "SEC-07")
        self.assertDecision(self.run_event_full("Bash", {"command": cmd}, "uok-test-engineer"), "deny", "SEC-07")

    def test_std_mcp_secret_denied_but_mcp_allowed(self):
        self.assertEqual(self.run_event("mcp__srv__tool", {"q": "hello"}, "uok-research-analyst"), "allow")
        self.assertDecision(self.run_event_full("mcp__srv__tool", {"api" + "_key": "abcdefghij0123456789xyz"},
                            "uok-research-analyst"), "deny", "SEC-03")

    def test_std_missing_config_defaults_to_standard(self):
        os.remove(os.path.join(self.root, ".orchestrator", "policy", "claude-code.yaml"))
        self.assertEqual(self.run_event("Bash", {"command": "grep -rn foo ."}, "uok-test-engineer"), "allow")


# Standard mode runs only the tests written for it. Inherited strict-mode tests are removed from the
# class itself (not via load_tests), so unittest and pytest collect exactly the same 114 tests.
for _name in [n for n in dir(G1GuardTest) if n.startswith("test_")]:
    if not _name.startswith("test_std_"):
        setattr(StandardModeTest, _name, None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
