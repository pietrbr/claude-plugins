"""Tests for bin/coordination-ledger (black-box, via the CLI + temp git fixtures)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CL = str(Path(__file__).resolve().parent.parent / "bin" / "coordination-ledger")
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def cl(*args, cwd, stdin=None):
    return subprocess.run(
        [sys.executable, CL, *args, "--cwd", str(cwd)],
        capture_output=True,
        text=True,
        input=stdin,
        env=ENV,
    )


def git(cwd, *args):
    subprocess.run(
        ["git", "-C", str(cwd), *args], env=ENV, capture_output=True, text=True, check=True
    )


def make_repo(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "commit", "-q", "--allow-empty", "-m", "init")


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "root"
        self.root.mkdir()
        make_repo(self.root / "evaluation")
        make_repo(self.root / "paper")
        self.assertEqual(cl("init", cwd=self.root).returncode, 0)
        self.assertEqual(
            cl("register", "--path", "evaluation", "--label", "code", cwd=self.root).returncode, 0
        )
        self.assertEqual(
            cl("register", "--path", "paper", "--label", "paper", cwd=self.root).returncode, 0
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def index(self):
        return json.loads((self.root / "index.json").read_text())

    def next_num(self):
        # next_number is derived, not stored; read it via context.
        return json.loads(cl("context", cwd=self.root).stdout)["next_number"]

    # --- context / resolution ---------------------------------------------
    def test_context_resolves_party_from_cwd(self):
        out = json.loads(cl("context", cwd=self.root / "evaluation").stdout)
        self.assertEqual(out["party_label"], "code")
        self.assertEqual(out["party_abspath"], str((self.root / "evaluation").resolve()))
        self.assertEqual(out["next_number"], 1)

    def test_deepest_party_wins(self):
        make_repo(self.root / "evaluation" / "vendor" / "lib")
        cl("register", "--path", "evaluation/vendor/lib", "--label", "lib", cwd=self.root)
        deep = self.root / "evaluation" / "vendor" / "lib" / "src"
        deep.mkdir(parents=True)
        self.assertEqual(json.loads(cl("context", cwd=deep).stdout)["party_label"], "lib")
        self.assertEqual(
            json.loads(cl("context", cwd=self.root / "evaluation" / "vendor").stdout)[
                "party_label"
            ],
            "code",
        )

    # --- open / reply / schema --------------------------------------------
    def test_open_writes_issue_and_index(self):
        r = cl(
            "open",
            "--author",
            "code",
            "--description",
            "eta anchoring pending",
            cwd=self.root / "evaluation",
            stdin="the body",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        issue = self.index()["issues"][0]
        self.assertEqual(issue["number"], 1)
        self.assertEqual(issue["author"], "code")
        self.assertEqual(issue["actors"], ["paper"])
        self.assertEqual(issue["status"], "open")
        self.assertIsNone(issue["date_resolved"])
        self.assertEqual(self.next_num(), 2)
        body = (self.root / "issues" / f"0001-{issue['slug']}.md").read_text()
        self.assertIn("### code", body)
        self.assertRegex(body, r"ref: code@[0-9a-f]+")
        self.assertIn("the body", body)

    def test_reply_resolves_and_appends(self):
        cl(
            "open",
            "--author",
            "code",
            "--description",
            "x",
            cwd=self.root / "evaluation",
            stdin="req",
        )
        r = cl(
            "reply",
            "--number",
            "1",
            "--status",
            "done",
            "--description",
            "handled",
            cwd=self.root / "paper",
            stdin="resolution",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        issue = self.index()["issues"][0]
        self.assertEqual(issue["status"], "done")
        self.assertEqual(issue["actors"], [])
        self.assertIsNotNone(issue["date_resolved"])
        self.assertEqual(issue["description"], "handled")
        body = (self.root / "issues" / f"0001-{issue['slug']}.md").read_text()
        self.assertIn("### paper", body)
        self.assertIn("resolution", body)

    def test_check_filters_by_actor_and_status(self):
        cl(
            "open",
            "--author",
            "code",
            "--description",
            "x",
            cwd=self.root / "evaluation",
            stdin="b",
        )
        self.assertIn("0001", cl("check", "--party", "paper", cwd=self.root).stdout)
        self.assertIn("(none)", cl("check", "--party", "code", cwd=self.root).stdout)
        cl("reply", "--number", "1", "--status", "done", cwd=self.root / "paper", stdin="d")
        self.assertIn("(none)", cl("check", "--party", "paper", cwd=self.root).stdout)

    def test_numbers_monotonic_never_recycled(self):
        cl(
            "open",
            "--author",
            "code",
            "--description",
            "a",
            cwd=self.root / "evaluation",
            stdin="b",
        )
        cl("reply", "--number", "1", "--status", "done", cwd=self.root / "paper", stdin="d")
        cl(
            "open",
            "--author",
            "code",
            "--description",
            "b",
            cwd=self.root / "evaluation",
            stdin="b",
        )
        nums = sorted(i["number"] for i in self.index()["issues"])
        self.assertEqual(nums, [1, 2])
        self.assertEqual(self.next_num(), 3)

    # --- git model ---------------------------------------------------------
    def test_index_tracked_and_parties_excluded(self):
        tracked = subprocess.run(
            ["git", "-C", str(self.root), "ls-files"], capture_output=True, text=True, env=ENV
        ).stdout.split()
        self.assertIn("index.json", tracked)
        self.assertIn(".gitignore", tracked)
        self.assertFalse(
            any(t.startswith("evaluation/") or t.startswith("paper/") for t in tracked)
        )

    # --- guards ------------------------------------------------------------
    def test_reinit_refused(self):
        self.assertEqual(cl("init", cwd=self.root).returncode, 1)

    def test_init_inside_enclosing_repo_refused(self):
        outer = self.tmp / "outer"
        make_repo(outer)
        (outer / "sub").mkdir()
        r = cl("init", cwd=outer / "sub")
        self.assertEqual(r.returncode, 1)
        self.assertIn("inside an existing git repo", r.stderr)

    def test_register_rejects_duplicates(self):
        self.assertEqual(
            cl("register", "--path", "evaluation", "--label", "other", cwd=self.root).returncode, 1
        )
        self.assertEqual(
            cl("register", "--path", "paper", "--label", "code", cwd=self.root).returncode, 1
        )

    # --- concurrency -------------------------------------------------------
    def test_concurrent_opens_do_not_collide(self):
        # Two parallel `open`s must serialize on the lock: distinct numbers, no
        # lost update, two body files. Body comes from a file so both run at once.
        bodyf = self.tmp / "body.txt"
        bodyf.write_text("body")
        procs = [
            subprocess.Popen(
                [
                    sys.executable,
                    CL,
                    "open",
                    "--author",
                    "code",
                    "--description",
                    f"concurrent {i}",
                    "--cwd",
                    str(self.root / "evaluation"),
                ],
                stdin=bodyf.open(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=ENV,
            )
            for i in range(2)
        ]
        results = [p.communicate() for p in procs]
        for p, (_out, err) in zip(procs, results):
            self.assertEqual(p.returncode, 0, err)
        nums = sorted(i["number"] for i in self.index()["issues"])
        self.assertEqual(nums, [1, 2])
        self.assertEqual(self.next_num(), 3)
        self.assertEqual(len(list((self.root / "issues").glob("0*.md"))), 2)

    # --- guards added after code review -----------------------------------
    def test_reply_refuses_already_resolved(self):
        cl(
            "open",
            "--author",
            "code",
            "--description",
            "x",
            cwd=self.root / "evaluation",
            stdin="b",
        )
        self.assertEqual(
            cl(
                "reply", "--number", "1", "--status", "done", cwd=self.root / "paper", stdin="d"
            ).returncode,
            0,
        )
        r = cl(
            "reply",
            "--number",
            "1",
            "--status",
            "divergent",
            cwd=self.root / "paper",
            stdin="again",
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("already", r.stderr)
        self.assertEqual(self.index()["issues"][0]["status"], "done")  # unchanged

    def test_register_rejects_unsafe_paths(self):
        for bad in ("../x", "/abs", "/"):
            self.assertEqual(
                cl("register", "--path", bad, "--label", "bad", cwd=self.root).returncode, 1, bad
            )
        self.assertEqual(sorted(p["label"] for p in self.index()["parties"]), ["code", "paper"])

    def test_slugify_long_description_no_crash(self):
        r = cl(
            "open",
            "--author",
            "code",
            "--description",
            "x" * 300,
            cwd=self.root / "evaluation",
            stdin="b",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        slug = self.index()["issues"][0]["slug"]
        self.assertLessEqual(len(slug), 40)
        self.assertTrue((self.root / "issues" / f"0001-{slug}.md").is_file())

    def test_reply_pass_the_ball_stays_open(self):
        cl(
            "open",
            "--author",
            "code",
            "--description",
            "x",
            cwd=self.root / "evaluation",
            stdin="req",
        )
        r = cl(
            "reply", "--number", "1", "--to", "code", cwd=self.root / "paper", stdin="over to you"
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        issue = self.index()["issues"][0]
        self.assertEqual(issue["status"], "open")
        self.assertEqual(issue["actors"], ["code"])
        self.assertIsNone(issue["date_resolved"])
        self.assertIn("0001", cl("check", "--party", "code", cwd=self.root).stdout)
        self.assertIn("(none)", cl("check", "--party", "paper", cwd=self.root).stdout)
        body = (self.root / "issues" / f"0001-{issue['slug']}.md").read_text()
        self.assertIn("### code", body)
        self.assertIn("### paper", body)
        self.assertIn("over to you", body)

    def test_reply_requires_exactly_one_mode(self):
        cl(
            "open",
            "--author",
            "code",
            "--description",
            "x",
            cwd=self.root / "evaluation",
            stdin="b",
        )
        self.assertEqual(
            cl("reply", "--number", "1", cwd=self.root / "paper", stdin="b").returncode, 1
        )
        self.assertEqual(
            cl(
                "reply",
                "--number",
                "1",
                "--to",
                "code",
                "--status",
                "done",
                cwd=self.root / "paper",
                stdin="b",
            ).returncode,
            1,
        )

    def test_open_rejects_author_only_actor(self):
        r = cl(
            "open",
            "--author",
            "code",
            "--actor",
            "code",
            "--description",
            "x",
            cwd=self.root / "evaluation",
            stdin="b",
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("other than the author", r.stderr)

    def test_reply_to_invalid_label_leaves_no_orphan_entry(self):
        cl(
            "open",
            "--author",
            "code",
            "--description",
            "x",
            cwd=self.root / "evaluation",
            stdin="req",
        )
        slug = self.index()["issues"][0]["slug"]
        r = cl("reply", "--number", "1", "--to", "bogus", cwd=self.root / "paper", stdin="oops")
        self.assertEqual(r.returncode, 1)
        body = (self.root / "issues" / f"0001-{slug}.md").read_text()
        self.assertNotIn("oops", body)  # no orphan entry written before the die
        self.assertEqual(body.count("### "), 1)  # only the original author entry

    def test_open_requires_another_party(self):
        solo = self.tmp / "solo"
        make_repo(solo / "only")
        cl("init", cwd=solo)
        cl("register", "--path", "only", "--label", "solo", cwd=solo)
        r = cl("open", "--author", "solo", "--description", "x", cwd=solo / "only", stdin="b")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no other party", r.stderr)


if __name__ == "__main__":
    unittest.main()
