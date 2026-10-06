"""Tests for bin/comment-deslop (black-box, via the CLI + temp git fixtures)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
ENGINE = str(PLUGIN / "bin" / "comment-deslop")
WRAPPER = str(PLUGIN / "bin" / "comment-deslop-hook.sh")
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def run(*args, stdin=None, cwd=None):
    return subprocess.run(
        [sys.executable, ENGINE, *args],
        capture_output=True,
        text=True,
        input=stdin,
        cwd=cwd,
        env=ENV,
        check=False,
    )


def wrapped(*args, stdin=None, cwd=None):
    """Drive the engine through the hook wrapper, which provisions tree-sitter."""
    return subprocess.run(
        [WRAPPER, *args],
        capture_output=True,
        text=True,
        input=stdin,
        cwd=cwd,
        env=ENV,
        check=False,
    )


def has_ast():
    for line in wrapped("doctor").stdout.splitlines():
        if line.startswith("tree-sitter"):
            return "available" in line
    return False


def rules_of(output):
    """The primary rule of each finding line; extras are appended as `+rule`."""
    return [
        line.split("[", 1)[1].split("]", 1)[0].split()[0]
        for line in output.splitlines()
        if "[" in line and line.startswith("  L")
    ]


class Fixture:
    def __init__(self, stack):
        self.dir = stack.enter_context(tempfile.TemporaryDirectory())

    def write(self, name, text):
        path = Path(self.dir) / name
        path.write_text(text, encoding="utf8")
        return str(path)

    def git(self, *args):
        subprocess.run(
            ["git", *args], cwd=self.dir, env=ENV, capture_output=True, check=False
        )

    def init(self):
        self.git("init", "-q")


class ScopeTest(unittest.TestCase):
    def setUp(self):
        from contextlib import ExitStack

        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.fixture = Fixture(self.stack)

    def test_untouched_slop_is_out_of_scope(self):
        self.fixture.init()
        path = self.fixture.write(
            "app.py",
            "def f(counter):\n    # increment the counter\n    counter += 1\n    return counter\n",
        )
        self.fixture.git("add", "app.py")
        self.fixture.git("commit", "-qm", "seed")
        done = run(path, cwd=self.fixture.dir)
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_all_overrides_scope(self):
        self.fixture.init()
        path = self.fixture.write(
            "app.py",
            "def f(counter):\n    # increment the counter\n    counter += 1\n    return counter\n",
        )
        self.fixture.git("add", "app.py")
        self.fixture.git("commit", "-qm", "seed")
        done = run("--all", path, cwd=self.fixture.dir)
        self.assertEqual(done.returncode, 2)
        self.assertIn("restatement", rules_of(done.stdout))

    def test_changed_line_is_in_scope(self):
        self.fixture.init()
        self.fixture.write(
            "app.py", "def f(counter):\n    counter += 1\n    return counter\n"
        )
        self.fixture.git("add", "app.py")
        self.fixture.git("commit", "-qm", "seed")
        path = self.fixture.write(
            "app.py",
            "def f(counter):\n    # increment the counter\n    counter += 1\n    return counter\n",
        )
        done = run(path, cwd=self.fixture.dir)
        self.assertEqual(done.returncode, 2)
        self.assertIn("restatement", rules_of(done.stdout))

    def test_untracked_file_is_fully_in_scope(self):
        self.fixture.init()
        path = self.fixture.write(
            "new.py",
            "def f(counter):\n    # increment the counter\n    counter += 1\n    return counter\n",
        )
        done = run(path, cwd=self.fixture.dir)
        self.assertEqual(done.returncode, 2)

    def test_no_repo_is_fully_in_scope(self):
        path = self.fixture.write(
            "loose.py",
            "def f(counter):\n    # increment the counter\n    counter += 1\n    return counter\n",
        )
        done = run(path)
        self.assertEqual(done.returncode, 2)

    def test_since_moves_the_base(self):
        self.fixture.init()
        self.fixture.write(
            "app.py", "def f(counter):\n    counter += 1\n    return counter\n"
        )
        self.fixture.git("add", "app.py")
        self.fixture.git("commit", "-qm", "seed")
        self.fixture.git("branch", "base")
        path = self.fixture.write(
            "app.py",
            "def f(counter):\n    # increment the counter\n    counter += 1\n    return counter\n",
        )
        self.fixture.git("add", "app.py")
        self.fixture.git("commit", "-qm", "slop")
        self.assertEqual(run(path, cwd=self.fixture.dir).returncode, 0)
        self.assertEqual(
            run("--since", "base", path, cwd=self.fixture.dir).returncode, 2
        )


class AllowlistTest(unittest.TestCase):
    def check(self, source, name="probe.py"):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_text(source, encoding="utf8")
            return run("--all", str(path))

    def test_directive_is_allowed(self):
        self.assertEqual(
            self.check("import os  # noqa: F401\n\nprint(os)\n").returncode, 0
        )

    def test_shouted_todo_is_allowed(self):
        self.assertEqual(
            self.check("def f():\n    # TODO: fix later\n    return 1\n").returncode, 0
        )

    def test_deferral_defeats_the_marker(self):
        done = self.check(
            "def f():\n    # TODO: revisit once the codec lands\n    return 1\n"
        )
        self.assertEqual(done.returncode, 2)
        self.assertIn("history", rules_of(done.stdout))

    def test_spec_citation_is_allowed(self):
        self.assertEqual(
            self.check(
                "def f(frame):\n    # 3GPP TS 38.211 fixes the order\n    return frame\n"
            ).returncode,
            0,
        )

    def test_lowercase_marker_is_not_allowed(self):
        done = self.check(
            "def f(job):\n    # obviously we note that the fast path wins\n    return fast(job)\n"
        )
        self.assertEqual(done.returncode, 2)

    def test_shebang_and_license_are_allowed(self):
        source = (
            '#!/usr/bin/env bash\n# SPDX-License-Identifier: MIT\nset -eu\nmain "$@"\n'
        )
        self.assertEqual(self.check(source, name="run.sh").returncode, 0)


class LexerTest(unittest.TestCase):
    def check(self, source, name):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_text(source, encoding="utf8")
            return run("--all", str(path))

    def test_string_is_not_a_comment(self):
        done = self.check(
            'def f():\n    prefix = "# increment the counter"\n    return prefix\n',
            "a.py",
        )
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_shell_word_boundary_hash(self):
        source = '#!/usr/bin/env bash\nname="${path#prefix}"\nmask=$((16#ff))\necho "$name$mask"\n'
        self.assertEqual(self.check(source, "a.sh").returncode, 0)

    def test_trailing_comment_is_exempt(self):
        done = self.check(
            "def f():\n    timeout = 5  # seconds\n    limit = 10  # limit\n    return timeout, limit\n",
            "a.py",
        )
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_run_reports_verbose_once(self):
        source = (
            "def f(payload):\n"
            "    # This function takes the raw payload and, after validating every field\n"
            "    # against the schema, normalises the units and returns a dictionary that\n"
            "    # the caller can feed straight into the renderer without further work.\n"
            "    return shape(payload)\n"
        )
        done = self.check(source, "a.py")
        self.assertEqual(rules_of(done.stdout).count("verbose"), 1)

    def test_unsupported_extension_is_skipped(self):
        done = self.check("# increment the counter\n", "notes.txt")
        self.assertEqual(done.returncode, 0)


class OutputTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.path = str(Path(self.directory) / "app.py")
        Path(self.path).write_text(
            "def f(counter):\n    # increment the counter\n    counter += 1\n    return counter\n",
            encoding="utf8",
        )

    def test_json_output(self):
        done = run("--all", "--json", self.path)
        self.assertEqual(done.returncode, 2)
        payload = json.loads(done.stdout)
        self.assertEqual(payload["findings"][0]["rule"], "restatement")
        self.assertEqual(payload["findings"][0]["line"], 2)

    def test_evidence_is_cited(self):
        done = run("--all", self.path)
        self.assertIn("shares", done.stdout)
        self.assertIn("counter", done.stdout)

    def test_no_rules_drops_a_rule(self):
        done = run("--all", "--no-rules", "restatement", self.path)
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_rules_narrows_to_a_rule(self):
        done = run("--all", "--rules", "history", self.path)
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_one_finding_per_line(self):
        done = run("--all", self.path)
        lines = [hit for hit in rules_of(done.stdout)]
        self.assertEqual(len(lines), len(set(lines)))

    def test_list_rules(self):
        done = run("--list-rules")
        self.assertIn("restatement", done.stdout.split())
        self.assertIn("budget", done.stdout.split())


class HookTest(unittest.TestCase):
    def test_hook_reads_the_payload_and_writes_to_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "app.py")
            Path(path).write_text(
                "def f(counter):\n    # increment the counter\n    counter += 1\n    return counter\n",
                encoding="utf8",
            )
            payload = json.dumps(
                {"tool_name": "Edit", "tool_input": {"file_path": path}}
            )
            done = run("--hook", "--all", stdin=payload)
        self.assertEqual(done.returncode, 2)
        self.assertIn("restatement", done.stderr)
        self.assertEqual(done.stdout, "")

    def test_hook_ignores_other_tools(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        done = run("--hook", stdin=payload)
        self.assertEqual(done.returncode, 0)

    def test_hook_fails_open_on_garbage(self):
        done = run("--hook", stdin="not json at all")
        self.assertEqual(done.returncode, 0)

    def test_wrapper_fails_open_without_payload(self):
        done = subprocess.run(
            [WRAPPER, "--hook"],
            input="",
            capture_output=True,
            text=True,
            env=ENV,
            check=False,
        )
        self.assertEqual(done.returncode, 0)


class CorpusTest(unittest.TestCase):
    def test_corpus_meets_the_per_kind_floors(self):
        done = run("eval")
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_corpus_covers_every_rule(self):
        corpus = json.loads(
            (PLUGIN / "eval" / "corpus.json").read_text(encoding="utf8")
        )
        rules, advisories = set(), set()
        for line in run("--list-rules").stdout.splitlines():
            name = line.split()[0]
            (advisories if "(advisory)" in line else rules).add(name)
        self.assertEqual(
            rules - {case["expect"] for case in corpus if case["expect"]}, set()
        )
        self.assertEqual(
            advisories
            - {case.get("advisory") for case in corpus if case.get("advisory")},
            {"unreviewed"},
        )


@unittest.skipUnless(has_ast(), "no tree-sitter parser available")
class AstTest(unittest.TestCase):
    def check(self, source):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.py"
            path.write_text(source, encoding="utf8")
            return wrapped("--all", str(path))

    def test_budget_zero_in_a_small_function(self):
        done = self.check(
            "def tiny(value):\n    # clamp it\n    return min(value, 255)\n"
        )
        self.assertIn("budget", rules_of(done.stdout))

    def test_redundant_docstring(self):
        done = self.check(
            'def add_one(counter):\n    """Add one to counter."""\n    return counter + 1\n'
        )
        self.assertIn("redundant-docstring", rules_of(done.stdout))


if __name__ == "__main__":
    unittest.main()


class AdvisoryTest(unittest.TestCase):
    SOURCE = (
        "def probe(value):\n"
        "    # --- collection ----------------\n"
        '    # print("debug", value)\n'
        "    # TODO: fix later\n"
        "    # TODO(alice): tracked, so silent\n"
        "    return value\n"
    )

    def check(self, *args, name="app.py"):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_text(self.SOURCE, encoding="utf8")
            return wrapped("--all", "--json", *args, str(path))

    def payload(self, *args):
        return json.loads(self.check(*args).stdout)

    def test_default_advisories_are_noted(self):
        noted = {x["rule"] for x in self.payload()["advisories"]}
        self.assertEqual(noted, {"banner", "dead-code", "untracked-todo"})

    def test_tracked_todo_is_silent(self):
        lines = {x["line"] for x in self.payload()["advisories"]}
        self.assertNotIn(5, lines)

    def test_no_advisory_silences_them(self):
        self.assertEqual(self.payload("--no-advisory")["advisories"], [])

    def test_unreviewed_is_never_reported(self):
        for args in ((), ("--advisory", "all")):
            rules = {x["rule"] for x in self.payload(*args)["advisories"]}
            self.assertNotIn("unreviewed", rules)

    def test_advisories_alone_do_not_fail(self):
        done = self.check("--no-rules", "budget")
        self.assertEqual(json.loads(done.stdout)["findings"], [])
        self.assertEqual(done.returncode, 0)

    def test_commented_out_code_is_not_a_finding(self):
        rules = {x["rule"] for x in self.payload("--no-rules", "budget")["findings"]}
        self.assertEqual(rules, set())

    def test_hook_splits_the_channels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.py"
            path.write_text(
                "def f(counter):\n"
                "    # increment the counter\n"
                "    # TODO: fix later\n"
                "    counter += 1\n"
                "    return counter\n",
                encoding="utf8",
            )
            stdin = json.dumps(
                {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}
            )
            done = wrapped("--hook", "--all", "--no-rules", "budget", stdin=stdin)
        self.assertEqual(done.returncode, 2)
        self.assertIn("restatement", done.stderr)
        self.assertNotIn("untracked-todo", done.stderr)
        self.assertIn("untracked-todo", json.loads(done.stdout)["systemMessage"])


class TriageTest(unittest.TestCase):
    SOURCE = (
        "def probe(value):\n"
        "    # --- collection ----------------\n"
        "    # TODO: fix later\n"
        "    # TODO(alice): tracked, so no advisory\n"
        "    # increment the value\n"
        "    value += 1\n"
        "    return value\n"
    )

    def candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.py"
            path.write_text(self.SOURCE, encoding="utf8")
            done = wrapped("--all", "--llm", str(path))
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)["candidates"]

    def test_only_unmatched_comments_are_candidates(self):
        lines = {row["line"] for row in self.candidates()}
        self.assertEqual(lines, {4})

    def test_candidates_carry_the_adjacent_code(self):
        rows = self.candidates()
        self.assertTrue(all(row["code"] for row in rows))

    def test_triage_never_reports_findings(self):
        payload = json.loads(wrapped("--all", "--llm", ".").stdout)
        self.assertEqual(set(payload), {"candidates"})


class ProvisioningTest(unittest.TestCase):
    def test_doctor_reports_the_venv_path(self):
        lines = wrapped("doctor").stdout.splitlines()
        venv = next(line for line in lines if line.startswith("venv"))
        self.assertIn("comment-deslop", venv)
        self.assertRegex(venv, r"\((present|absent)\)$")

    def test_explicit_interpreter_is_honoured(self):
        env = {**ENV, "COMMENT_DESLOP_PYTHON": sys.executable}
        done = subprocess.run(
            [WRAPPER, "doctor"], capture_output=True, text=True, env=env, check=False
        )
        self.assertIn(sys.executable, done.stdout)

    def test_wrapper_runs_without_uv(self):
        env = {**ENV, "COMMENT_DESLOP_NO_UV": "1"}
        done = subprocess.run(
            [WRAPPER, "--list-rules"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(done.returncode, 0)
        self.assertIn("restatement", done.stdout)


class FallThroughTest(unittest.TestCase):
    """A venv without the parsers must not cost the AST rules silently."""

    def setUp(self):
        self.cache = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.cache, ignore_errors=True)
        target = Path(self.cache) / "comment-deslop" / "venv"
        target.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(
            [sys.executable, "-m", "venv", str(target)],
            capture_output=True,
            check=False,
        )
        if done.returncode != 0:
            self.skipTest("could not create a venv")

    def wrapped_with(self, *args, **extra):
        env = {**ENV, "XDG_CACHE_HOME": self.cache, **extra}
        return subprocess.run(
            [WRAPPER, *args], capture_output=True, text=True, env=env, check=False
        )

    def test_require_ast_exits_three(self):
        venv = Path(self.cache) / "comment-deslop" / "venv" / "bin" / "python"
        done = subprocess.run(
            [str(venv), ENGINE, "--list-rules"],
            capture_output=True,
            text=True,
            env={**ENV, "COMMENT_DESLOP_REQUIRE_AST": "1"},
            check=False,
        )
        self.assertEqual(done.returncode, 3)

    def test_parserless_venv_degrades_without_failing(self):
        done = self.wrapped_with("eval", COMMENT_DESLOP_NO_UV="1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("AST-only case(s) skipped", done.stdout)


class StopTest(unittest.TestCase):
    """The Stop hook: one report per turn, each finding reported once per session."""

    SLOP = (
        "def handle(item):\n"
        "    # increment the counter\n"
        "    counter = item + 1\n"
        "    # TODO: fix later\n"
        "    return counter\n"
    )

    def setUp(self):
        self.cache = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.cache, ignore_errors=True)
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self.app = Path(self.repo) / "app.py"
        self.git("init", "-q")
        self.app.write_text("def handle(item):\n    return item\n", encoding="utf8")
        self.git("add", "app.py")
        self.git("commit", "-qm", "seed")
        self.app.write_text(self.SLOP, encoding="utf8")

    def git(self, *args):
        subprocess.run(
            ["git", *args], cwd=self.repo, env=ENV, capture_output=True, check=False
        )

    def stop(self, session="s1", event="Stop"):
        payload = json.dumps(
            {"hook_event_name": event, "session_id": session, "cwd": self.repo}
        )
        env = {**ENV, "XDG_CACHE_HOME": self.cache}
        return subprocess.run(
            [WRAPPER, "--hook"],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def test_stop_reports_git_changed_files(self):
        done = self.stop()
        self.assertEqual(done.returncode, 2)
        self.assertIn("restatement", rules_of(done.stderr))

    def test_structural_rules_are_excluded(self):
        done = self.stop()
        for line in done.stderr.splitlines():
            self.assertNotIn("budget", line)
            self.assertNotIn("density", line)

    def test_second_stop_suppresses_the_same_finding(self):
        self.assertEqual(self.stop().returncode, 2)
        again = self.stop()
        self.assertEqual(again.returncode, 0)
        self.assertEqual(rules_of(again.stderr), [])

    def test_suppression_survives_an_unrelated_edit(self):
        self.stop()
        self.app.write_text(
            self.SLOP + "\n\ndef extra():\n    return 7\n", encoding="utf8"
        )
        self.assertEqual(self.stop().returncode, 0)

    def test_editing_the_comment_reports_again(self):
        self.stop()
        self.app.write_text(
            self.SLOP.replace("increment the counter", "bump the counter by one"),
            encoding="utf8",
        )
        self.assertEqual(self.stop().returncode, 2)

    def test_changed_adjacent_code_reports_again(self):
        self.stop()
        self.app.write_text(
            self.SLOP.replace("counter = item + 1", "counter += 1"), encoding="utf8"
        )
        self.assertEqual(self.stop().returncode, 2)

    def test_a_separate_session_is_not_suppressed(self):
        self.stop(session="s1")
        self.assertEqual(self.stop(session="s2").returncode, 2)

    def test_suppressed_count_reaches_the_user(self):
        self.stop()
        again = self.stop()
        message = json.loads(again.stdout)["systemMessage"]
        self.assertIn("not repeated", message)

    def test_session_end_clears_the_cache(self):
        self.stop()
        self.stop(event="SessionEnd")
        self.assertEqual(self.stop().returncode, 2)
