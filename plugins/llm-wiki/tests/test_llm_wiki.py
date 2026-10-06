"""Tests for bin/llm-wiki and bin/llm-wiki-hook (black-box, via subprocess in a sandbox)."""

import datetime
import enum
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
BIN = PLUGIN / "bin"
CLI = str(BIN / "llm-wiki")
HOOK = str(BIN / "llm-wiki-hook")
NO_JQ_PATH = "/bin:/usr/sbin"
ANY = ...
MAX_PLAIN_PROMPT_SECONDS = 0.3
PLAIN_PROMPT_RUNS = 10


class Streams(enum.Enum):
    MERGED = "merged"
    STDOUT_ONLY = "stdout"
    STDERR_ONLY = "stderr"


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")


def read_lines(path):
    return Path(path).read_text(encoding="utf8").splitlines()


def today():
    return datetime.date.today().isoformat()


def sidecar(path, source_file, uri, title, compiled):
    write(
        path,
        f"---\nsource-uri: {uri}\nsource-file: {source_file}\n"
        f"title: {title}\ncompiled: {compiled}\n---\n",
    )


def sed_range(text, start, end):
    picked = []
    inside = False
    for line in text.splitlines():
        if not inside:
            if re.search(start, line):
                inside = True
                picked.append(line)
            continue
        picked.append(line)
        if re.search(end, line):
            inside = False
    return "\n".join(picked)


def jq_r(text, *keys):
    if not text:
        return ""
    value = json.loads(text)
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    return json.dumps(value)


class Sandbox(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.t = Path(os.path.realpath(tmp.name))
        self.home = self.t / "home"
        self.config_dir = self.home / ".config" / "llm-wiki"
        self.config_dir.mkdir(parents=True)
        self.work = self.t / "work"
        self.work.mkdir()
        self.vault = self.t / "vault"
        tools = self.t / "tools"
        tools.mkdir()
        for tool in ("jq", "git"):
            found = shutil.which(tool)
            if found:
                (tools / tool).symlink_to(found)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{BIN}:{tools}:/usr/bin:/bin",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        }
        self.rc = None

    @property
    def topics_path(self):
        return self.config_dir / "topics.json"

    def topics_text(self):
        if not self.topics_path.exists():
            return ""
        return self.topics_path.read_text(encoding="utf8")

    def run_cmd(self, argv, *, env=None, stdin=None, cwd=None, streams=Streams.MERGED):
        stderr = subprocess.STDOUT if streams is Streams.MERGED else subprocess.PIPE
        proc = subprocess.run(
            argv,
            input=stdin if stdin is not None else "",
            stdout=subprocess.PIPE,
            stderr=stderr,
            cwd=cwd or self.t,
            env=env or self.env,
            text=True,
            errors="replace",
            check=False,
        )
        self.rc = proc.returncode
        text = proc.stderr if streams is Streams.STDERR_ONLY else proc.stdout
        return text.rstrip("\n")

    def cli(self, *args, **kwargs):
        return self.run_cmd([CLI, *(str(a) for a in args)], **kwargs)

    def git(self, *args):
        proc = subprocess.run(
            ["git", "-C", str(self.vault), *args],
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )
        return proc.stdout

    def write_config(self):
        write(self.config_dir / "config.json", json.dumps({"vault_path": str(self.vault)}))

    def init_repo(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")
        self.write_config()

    def fresh(self, *topics):
        shutil.rmtree(self.vault, ignore_errors=True)
        self.vault.mkdir(parents=True)
        for topic in topics:
            for sub in ("wiki", "raw/documents", "raw/attachments", "outputs/reports"):
                (self.vault / topic / sub).mkdir(parents=True)
            write(self.vault / topic / "log.md", f"# {topic} Wiki Log\n\n<!-- header -->\n")
            write(self.vault / topic / "wiki" / "index.md", f"# {topic} Wiki Index\n")
        self.init_repo()

    def bind(self, directory, topic):
        self.cli("set-topic", "--", directory, topic)

    def assertLike(self, text, *parts):
        pattern = "".join(".*" if part is ANY else re.escape(part) for part in parts)
        self.assertIsNotNone(re.fullmatch(pattern, text, re.DOTALL), text)

    def porcelain(self):
        return self.git("status", "--porcelain")


class TestRemove(Sandbox):
    def setUp(self):
        super().setUp()
        self.vault = self.t / "my vault"
        for topic in ("foo", "bar", "baz"):
            write(self.vault / topic / "wiki" / "p.md", "x\n")
        self.init_repo()

    def ignore(self, *patterns):
        with open(self.vault / ".gitignore", "a", encoding="utf8") as handle:
            handle.write("".join(f"{p}\n" for p in patterns))
        self.git("add", ".gitignore")
        self.git("commit", "-qm", "ign")

    def with_caches(self):
        self.ignore("*.pdf")
        (self.vault / "foo" / ".DS_Store").touch()
        (self.vault / "foo" / "x.sqlite").touch()
        self.ignore(".DS_Store", "*.sqlite")

    def removed_foo(self):
        self.bind(self.work, "foo")
        self.with_caches()
        with open(self.vault / "bar" / "wiki" / "p.md", "a", encoding="utf8") as handle:
            handle.write("wip\n")
        self.git("add", "bar/wiki/p.md")
        return self.cli("remove", "--", "foo")

    def test_set_topic_binds(self):
        out = self.cli("set-topic", "--", self.work, "foo")
        self.assertIn("bound to topic 'foo'", out)

    def test_set_topic_unknown_lists_topics(self):
        out = self.cli("set-topic", "--", self.work, "zz")
        self.assertLike(out, ANY, "no topic", ANY, "bar, baz, foo", ANY)

    def test_list_marks_current(self):
        self.bind(self.work, "foo")
        self.assertIn("* foo", self.cli("list", self.work))

    def test_wrong_case_refused(self):
        out = self.cli("remove", "--", "Foo")
        self.assertIn("no such topic: Foo", out)
        self.assertTrue((self.vault / "foo").is_dir())

    def test_glob_refused(self):
        out = self.cli("remove", "--", "*", cwd=self.vault)
        self.assertIn("no such topic", out)
        self.assertTrue((self.vault / "foo").is_dir())

    def test_escape_refused(self):
        self.assertIn("no such topic", self.cli("remove", "--", "../work"))

    def test_symlink_alias_refused(self):
        (self.vault / "alias").symlink_to("foo")
        out = self.cli("remove", "--", "alias")
        self.assertIn("no such topic", out)
        self.assertTrue((self.vault / "foo").is_dir())

    def test_untracked_refused(self):
        write(self.vault / "foo" / "wiki" / "new.md", "new\n")
        out = self.cli("remove", "--", "foo")
        self.assertIn("new.md", out)
        self.assertTrue((self.vault / "foo").is_dir())

    def test_ignored_file_refused(self):
        self.ignore("*.pdf")
        write(self.vault / "foo" / "wiki" / "a.pdf", "p\n")
        out = self.cli("remove", "--", "foo")
        self.assertIn("a.pdf", out)
        self.assertTrue((self.vault / "foo" / "wiki" / "a.pdf").is_file())

    def test_git_status_failure_refused(self):
        self.with_caches()
        index = self.vault / ".git" / "index"
        backup = self.t / "index.bak"
        shutil.copy2(index, backup)
        write(index, "junk\n")
        out = self.cli("remove", "--", "foo")
        shutil.copy2(backup, index)
        self.assertIn("git status failed", out)
        self.assertTrue((self.vault / "foo").is_dir())

    def test_remove_with_caches_present(self):
        out = self.removed_foo()
        self.assertTrue(out.startswith("Removed:"), out)
        self.assertFalse((self.vault / "foo").exists())

    def test_commit_has_only_foo(self):
        self.removed_foo()
        names = self.git("show", "--name-only", "--format=", "HEAD").splitlines()
        self.assertEqual(sum(1 for n in names if not n.startswith("foo/")), 0)

    def test_bar_stays_staged(self):
        self.removed_foo()
        self.assertTrue(self.git("diff", "--cached", "--name-only", "--", "bar").strip())

    def test_binding_removed(self):
        self.removed_foo()
        self.assertNotIn("foo", self.topics_text())

    def recover_and_restore(self, out):
        match = re.search(r"^Recover with: (.*)$", out, re.MULTILINE)
        self.assertIsNotNone(match, out)
        subprocess.run(
            ["bash", "-c", match.group(1)],
            cwd=self.t,
            env=self.env,
            capture_output=True,
            check=False,
        )

    def test_recovery_command_works_with_spaces(self):
        out = self.removed_foo()
        self.recover_and_restore(out)
        self.assertTrue((self.vault / "foo" / "wiki" / "p.md").is_file())

    def test_remove_two(self):
        out = self.removed_foo()
        self.recover_and_restore(out)
        self.git("reset", "-q")
        self.git("checkout", "-q", "--", ".")
        self.git("add", "-A")
        self.git("commit", "-qm", "restore")
        out = self.cli("remove", "--", "foo", "baz")
        self.assertLike(out, "Removed: baz, foo", ANY)
        self.assertFalse((self.vault / "baz").exists())

    def test_set_vault_inits_nested_vault(self):
        outer = self.t / "outer"
        write(outer / "wiki-vault" / "t" / "wiki" / "p.md", "x\n")
        subprocess.run(["git", "-C", str(outer), "init", "-q"], env=self.env, check=False)
        subprocess.run(["git", "-C", str(outer), "add", "-A"], env=self.env, check=False)
        subprocess.run(
            ["git", "-C", str(outer), "commit", "-qm", "o"],
            env=self.env,
            capture_output=True,
            check=False,
        )
        self.cli("set-vault", "--", self.work, outer / "wiki-vault")
        self.assertTrue((outer / "wiki-vault" / ".git").is_dir())

    def test_no_shell_in_args(self):
        marker = self.t / "pwned"
        out = self.cli("remove", "--", f"zz; touch {marker}")
        self.assertFalse(marker.exists())
        self.assertIn("no such topic", out)

    def test_os_error_is_a_clean_message(self):
        outer = self.t / "outer"
        write(outer / "wiki-vault" / "t" / "wiki" / "p.md", "x\n")
        self.bind(self.work, "foo")
        self.cli("set-vault", "--", self.work, outer / "wiki-vault")
        self.topics_path.chmod(0o400)
        self.addCleanup(self.topics_path.chmod, 0o600)
        out = self.cli("set-topic", "--", self.work, "t")
        self.assertLike(out, "llm-wiki: ", ANY, "Permission denied", ANY)

    def test_doctor_runs(self):
        self.assertIn("vault is a git repo", self.cli("doctor", self.work))

    def test_context_with_conventions(self):
        out = self.cli("context", "--conventions", self.work)
        self.assertLike(
            out, "cwd=", ANY, "vault_path=", ANY, "--- conventions ---", ANY, "Output policy", ANY
        )

    def test_resolve_is_gone(self):
        self.assertIn("Subcommands:", self.cli("resolve"))


class TestLogCommit(Sandbox):
    def setUp(self):
        super().setUp()
        self.fresh("a", "b")
        self.bind(self.work, "a")
        write(self.vault / "a" / "wiki" / "p.md", "page\n")
        with open(self.vault / "b" / "log.md", "a", encoding="utf8") as handle:
            handle.write("wip\n")
        self.git("add", "b/log.md")
        self.log = self.vault / "a" / "log.md"

    def commit_first(self):
        return self.cli("log-commit", self.work, "query", "what is x", "used [[p]]")

    def test_log_commit_commits(self):
        out = self.commit_first()
        self.assertLike(out, "committed", ANY, "query: what is x")

    def test_only_topic_a_in_commit(self):
        self.commit_first()
        names = sorted(self.git("show", "--name-only", "--format=", "HEAD").split())
        self.assertEqual(names, ["a/log.md", "a/wiki/p.md"])

    def test_b_stays_staged(self):
        self.commit_first()
        self.assertTrue(self.git("diff", "--cached", "--name-only", "--", "b").strip())

    def test_log_entry_appended(self):
        self.commit_first()
        lines = read_lines(self.log)
        self.assertEqual(lines[-2], f"## [{today()}] query | what is x")
        self.assertIn("used [[p]]", lines[-1])

    def test_body_optional(self):
        self.commit_first()
        out = self.cli("log-commit", self.work, "lint", "t")
        self.assertTrue(out.startswith("committed"), out)
        self.assertLike(read_lines(self.log)[-1], "## [", ANY, "] lint | t")

    def test_bad_op_rejected(self):
        self.commit_first()
        self.assertIn("invalid choice", self.cli("log-commit", self.work, "dance", "t"))

    def test_unbound_directory_rejected(self):
        self.commit_first()
        out = self.cli("log-commit", self.t / "nowhere", "query", "t")
        self.assertIn("no topic is bound", out)

    def test_dash_title_with_double_dash(self):
        self.commit_first()
        out = self.cli("log-commit", self.work, "query", "--", "-3dB beamwidth?", "x")
        self.assertLike(out, ANY, "query: -3dB beamwidth?")

    def locked_attempt(self):
        self.commit_first()
        write(self.vault / "a" / "wiki" / "p.md", "more\n")
        (self.vault / ".git" / "index.lock").touch()
        before = self.log.read_text(encoding="utf8")
        out = self.cli("log-commit", self.work, "query", "locked")
        return out, before

    def test_lock_fails_loudly(self):
        out, _ = self.locked_attempt()
        self.assertIn("git add failed", out)

    def test_log_rolled_back(self):
        _, before = self.locked_attempt()
        self.assertEqual(self.log.read_text(encoding="utf8"), before)

    def test_body_forced_to_one_line(self):
        self.commit_first()
        self.cli("log-commit", self.work, "compile", "multi", "line one\nline two")
        self.assertEqual(read_lines(self.log)[-1], "line one line two")

    def test_context_still_works(self):
        self.commit_first()
        self.assertLike(self.cli("context", self.work), "cwd=", ANY, "vault_path=", ANY)

    def test_unknown_subcommand(self):
        self.assertIn("Subcommands:", self.cli("nope"))


class TestIngest(Sandbox):
    def setUp(self):
        super().setUp()
        self.fresh("a")
        self.bind(self.work, "a")
        self.docs = self.vault / "a" / "raw" / "documents"
        self.today = today()
        self.paper = self.t / "paper.pdf"
        self.paper.write_bytes(os.urandom(4096))

    def ingest(self, *args, source=None):
        return self.cli("ingest", self.work, *args, "--", source or self.paper)

    def ingest_paper(self):
        return self.ingest("--type", "paper", "--title=Opt Density: A Study")

    def sidecar_lines(self, name):
        return read_lines(self.docs / name)

    def commit_raw(self, path, data):
        Path(path).write_bytes(data)
        self.git("add", "-A")
        self.git("commit", "-qm", "raw")

    def clipped(self):
        self.commit_raw(self.docs / "clipped.pdf", self.paper.read_bytes())
        return self.docs / "clipped.pdf"

    def test_ingest_commits(self):
        out = self.ingest_paper()
        self.assertLike(out, "committed", ANY, "ingest: Opt Density: A Study")

    def test_byte_copy(self):
        self.ingest_paper()
        copied = self.docs / f"{self.today}-paper.pdf"
        self.assertEqual(copied.read_bytes(), self.paper.read_bytes())

    def test_sidecar_fields(self):
        self.ingest_paper()
        lines = self.sidecar_lines(f"{self.today}-paper.meta.md")
        self.assertIn('title: "Opt Density: A Study"', lines)
        self.assertIn(f'source-uri: "{self.paper}"', lines)
        self.assertIn("compiled: false", lines)
        self.assertIn(f"source-file: {self.today}-paper.pdf", lines)

    def test_log_entry(self):
        self.ingest_paper()
        last = read_lines(self.vault / "a" / "log.md")[-1]
        self.assertEqual(last, f"paper -> raw/documents/{self.today}-paper.pdf")

    def test_collision_suffix(self):
        self.ingest_paper()
        self.ingest("--type", "paper", "--title=Again")
        self.assertTrue((self.docs / f"{self.today}-paper-2.pdf").is_file())
        self.assertTrue((self.docs / f"{self.today}-paper-2.meta.md").is_file())

    def test_slug_and_uri(self):
        self.ingest(
            "--type", "article", "--title=X", "--slug=My Slug!!", "--uri=https://ex.com/a"
        )
        self.assertTrue((self.docs / f"{self.today}-my-slug.pdf").is_file())
        lines = self.sidecar_lines(f"{self.today}-my-slug.meta.md")
        self.assertIn('source-uri: "https://ex.com/a"', lines)

    def test_dash_title(self):
        out = self.ingest("--type", "paper", "--title=-3dB beam")
        self.assertLike(out, ANY, "ingest: -3dB beam")

    def test_file_already_in_raw(self):
        clipped = self.clipped()
        self.ingest("--type", "article", "--title=Clip", source=clipped)
        self.assertTrue((self.docs / "clipped.meta.md").is_file())
        self.assertFalse((self.docs / f"{self.today}-clipped.pdf").exists())
        self.assertIn("source-uri: ", self.sidecar_lines("clipped.meta.md"))

    def test_second_sidecar_refused(self):
        clipped = self.clipped()
        self.ingest("--type", "article", "--title=Clip", source=clipped)
        out = self.ingest("--type", "article", "--title=Clip", source=clipped)
        self.assertIn("already has a sidecar", out)

    def test_bad_type_refused(self):
        out = self.ingest("--type", "blog", "--title=X")
        self.assertIn("invalid choice", out)

    def test_missing_file_refused(self):
        out = self.ingest("--type", "paper", "--title=X", source=self.t / "missing.pdf")
        self.assertIn("no such file", out)

    def test_failure_cleans_up(self):
        before = len(list(self.docs.iterdir()))
        (self.vault / ".git" / "index.lock").touch()
        out = self.ingest("--type", "paper", "--title=Locked")
        self.assertIn("git add failed", out)
        self.assertEqual(len(list(self.docs.iterdir())), before)

    def test_colon_title_quoted(self):
        self.ingest("--type", "paper", "--title=Overview:", "--slug=ov")
        lines = self.sidecar_lines(f"{self.today}-ov.meta.md")
        self.assertIn('title: "Overview:"', lines)

    def test_slug_on_in_place_refused(self):
        clipped = self.clipped()
        out = self.ingest("--type", "paper", "--title=X", "--slug=new", source=clipped)
        self.assertIn("--slug cannot rename", out)

    def test_other_raw_folder_refused(self):
        fig = self.vault / "a" / "raw" / "attachments" / "fig.pdf"
        self.commit_raw(fig, self.paper.read_bytes())
        out = self.ingest("--type", "paper", "--title=X", source=fig)
        self.assertIn("not in raw/documents", out)

    def test_hook_failure_leaves_no_trace(self):
        before = len(list(self.docs.iterdir()))
        hook = self.vault / ".git" / "hooks" / "pre-commit"
        write(hook, "#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        out = self.ingest("--type", "paper", "--title=Hooked")
        self.assertIn("git commit failed", out)
        self.assertEqual(len(list(self.docs.iterdir())), before)
        self.assertEqual(self.porcelain(), "")

    def test_tree_clean_after_all(self):
        self.ingest_paper()
        self.ingest("--type", "paper", "--title=Again")
        self.ingest("--type", "article", "--title=X", "--slug=My Slug!!")
        clipped = self.clipped()
        self.ingest("--type", "article", "--title=Clip", source=clipped)
        lock = self.vault / ".git" / "index.lock"
        lock.touch()
        self.ingest("--type", "paper", "--title=Locked")
        lock.unlink()
        hook = self.vault / ".git" / "hooks" / "pre-commit"
        write(hook, "#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.ingest("--type", "paper", "--title=Hooked")
        hook.unlink()
        self.assertEqual(self.porcelain(), "")


class TestInit(Sandbox):
    def setUp(self):
        super().setUp()
        self.write_config()
        self.out = self.cli("init", "--description=Conformal risk: control.", "--", self.work, "crc")
        self.topic = self.vault / "crc"

    def test_init_creates_vault_repo_and_topic(self):
        self.assertTrue((self.vault / ".git").is_dir())
        for sub in ("raw/documents", "raw/attachments", "wiki/queries", "outputs/reports"):
            self.assertTrue((self.topic / sub).is_dir(), sub)

    def test_init_commit(self):
        self.assertEqual(self.git("log", "-1", "--format=%s").strip(), "init: crc wiki")

    def test_tree_clean(self):
        self.assertEqual(self.porcelain(), "")

    def test_templates_filled(self):
        index = read_lines(self.topic / "wiki" / "index.md")
        log = read_lines(self.topic / "log.md")
        self.assertTrue(any(line.startswith("# crc Wiki Index") for line in index))
        self.assertTrue(any(f"Last updated: {today()}" in line for line in index))
        self.assertTrue(any(line.startswith("# crc Wiki Log") for line in log))

    def test_log_entry(self):
        self.assertIn(f"## [{today()}] init | crc wiki", read_lines(self.topic / "log.md"))

    def test_description_in_claude_md(self):
        self.assertIn("Conformal risk: control.", read_lines(self.topic / "CLAUDE.md"))

    def test_qmd_yml(self):
        lines = read_lines(self.topic / "qmd.yml")
        self.assertTrue(any(line.startswith("  crc:") for line in lines))

    def test_bound(self):
        self.assertIn('"crc"', self.topics_text())

    def test_existing_refused(self):
        self.assertIn("already exists", self.cli("init", "--", self.work, "crc"))

    def test_bad_name_refused(self):
        out = self.cli("init", "--", self.work, "Bad_Name")
        self.assertIn("kebab-case", out)
        self.assertFalse((self.vault / "Bad_Name").exists())

    def test_placeholder_when_no_description(self):
        out = self.cli("init", "--", self.work, "nodesc")
        self.assertIn("needs a domain description", out)
        claude_md = (self.vault / "nodesc" / "CLAUDE.md").read_text(encoding="utf8")
        self.assertIn("domain description: one paragraph", claude_md)

    def failing_init(self):
        hook = self.vault / ".git" / "hooks" / "pre-commit"
        write(hook, "#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        out = self.cli("init", "--", self.work, "failing")
        hook.unlink()
        return out

    def test_commit_failure_removes_topic(self):
        out = self.failing_init()
        self.assertIn("git commit failed", out)
        self.assertFalse((self.vault / "failing").exists())
        self.assertEqual(self.porcelain(), "")

    def test_failed_init_not_bound(self):
        self.failing_init()
        self.assertNotIn('"failing"', self.topics_text())

    def test_template_comments_keep_placeholders(self):
        log = (self.topic / "log.md").read_text(encoding="utf8")
        self.assertIn("## [YYYY-MM-DD] <op> | <title>", log)

    def test_newline_in_name_refused(self):
        self.assertIn("kebab-case", self.cli("init", "--", self.work, "bad\n"))


@unittest.skipUnless(shutil.which("jq"), "jq is required by llm-wiki-hook")
class TestHook(Sandbox):
    def setUp(self):
        super().setUp()
        self.fresh("a")
        self.bind(self.work, "a")

    def hk(self, prompt, cwd, *, env=None, streams=Streams.STDOUT_ONLY):
        payload = json.dumps({"prompt": prompt, "cwd": str(cwd)})
        return self.run_cmd([HOOK], stdin=payload, env=env, streams=streams)

    def no_jq_env(self):
        return {**self.env, "PATH": NO_JQ_PATH}

    def context_of(self, out):
        return jq_r(out, "hookSpecificOutput", "additionalContext")

    def test_plain_prompt_passes_silently(self):
        self.assertEqual(self.hk("hello there", self.work), "")

    def test_bound_context_injected(self):
        out = self.hk("/llm-wiki:query what is x", self.work)
        self.assertLike(
            self.context_of(out), ANY, "topic=a", ANY, "--- conventions ---", ANY,
            "Output policy", ANY,
        )

    def test_valid_json(self):
        out = self.hk("/llm-wiki:query what is x", self.work)
        self.assertIsInstance(json.loads(out), dict)

    def test_unbound_blocked(self):
        out = self.hk("/llm-wiki:query what is x", self.t / "elsewhere")
        self.assertEqual(jq_r(out, "decision"), "block")
        self.assertIn("No llm-wiki topic is set", jq_r(out, "reason"))

    def test_unbound_setup_command_injected(self):
        out = self.hk("/llm-wiki:init new", self.t / "elsewhere")
        self.assertIn("topic=", self.context_of(out))

    def test_mention_of_setup_command_passes(self):
        out = self.hk("how do I use /llm-wiki:set-topic?", self.t / "elsewhere")
        self.assertNotEqual(jq_r(out, "decision"), "block")

    def test_special_characters_safe(self):
        marker = self.t / "pwned2"
        prompt = f'tricky "quotes" and \\\\ and $(touch {marker}) /llm-wiki:query'
        out = self.hk(prompt, self.work)
        self.assertFalse(marker.exists())
        self.assertNotIn(json.loads(out).get("hookSpecificOutput"), (None, False))

    def test_multi_line_prompt(self):
        out = self.hk("line one\n/llm-wiki:lint", self.work)
        self.assertNotIn(json.loads(out).get("hookSpecificOutput"), (None, False))

    def test_no_jq_blocks_with_hint(self):
        out = self.hk(
            "/llm-wiki:query x", self.work, env=self.no_jq_env(), streams=Streams.MERGED
        )
        self.assertIn("needs jq", out)

    def test_corrupt_topics_json_blocks_as_unbound(self):
        write(self.topics_path, "[1]\n")
        out = self.hk("/llm-wiki:query x", self.work)
        self.assertEqual(jq_r(out, "decision"), "block")

    def test_fast_on_plain_prompts(self):
        start = time.perf_counter()
        for _ in range(PLAIN_PROMPT_RUNS):
            self.hk("hello", self.work)
        mean = (time.perf_counter() - start) / PLAIN_PROMPT_RUNS
        self.assertLess(mean, MAX_PLAIN_PROMPT_SECONDS)

    def test_hook_injects_cwd(self):
        out = self.hk("/llm-wiki:query x", self.work)
        self.assertLike(
            self.context_of(out), "llm-wiki active context", ANY, f"cwd={self.work}", ANY
        )

    def test_context_prints_cwd(self):
        out = self.cli("context", self.work)
        self.assertLike(out, f"cwd={self.work}", ANY)

    def test_trailing_slash_cwd_still_bound(self):
        out = self.hk("/llm-wiki:query x", f"{self.work}/")
        self.assertIn("topic=a", self.context_of(out))

    def test_missing_conventions_still_injects(self):
        fake = self.t / "fake" / "bin"
        fake.mkdir(parents=True)
        shutil.copy2(HOOK, fake)
        payload = json.dumps({"prompt": "/llm-wiki:query x", "cwd": str(self.work)})
        out = self.run_cmd(
            [str(fake / "llm-wiki-hook")], stdin=payload, streams=Streams.STDOUT_ONLY
        )
        self.assertEqual(self.rc, 0)
        self.assertIn("conventions file unreadable", self.context_of(out))

    def test_doctor_not_blocked_without_jq(self):
        out = self.hk(
            "/llm-wiki:doctor", self.work, env=self.no_jq_env(), streams=Streams.MERGED
        )
        self.assertEqual(out, "")

    def test_doctor_reports_jq(self):
        self.assertIn("OK      jq", self.cli("doctor", self.work))


class TestCompile(Sandbox):
    def setUp(self):
        super().setUp()
        self.fresh("a")
        self.bind(self.work, "a")
        self.docs = self.vault / "a" / "raw" / "documents"
        self.wiki = self.vault / "a" / "wiki"
        self.today = today()
        write(self.t / "p1.pdf", "p1\n")
        write(self.t / "p2.pdf", "p2\n")
        self.cli(
            "ingest", self.work, "--type", "paper", "--title=Paper One", "--slug=one",
            "--", self.t / "p1.pdf",
        )
        self.cli(
            "ingest", self.work, "--type", "article", "--title=Paper: Two", "--slug=two",
            "--", self.t / "p2.pdf",
        )
        self.one = f"{self.today}-one.pdf"
        self.two = f"{self.today}-two.pdf"

    def mark_both(self):
        return self.cli("mark-compiled", self.work, self.one, self.two)

    def page(self, name, body, kind="concept"):
        write(self.wiki / name, f"---\ntype: {kind}\n---\n{body}")

    def write_backlink_pages(self):
        self.page("conformal-risk-control.md", "# Conformal Risk Control\n\nBody.\n")
        self.page("a-page.md", "# A\n\nWe use conformal risk control here.\n")
        self.page("b-page.md", "# B\n\nSee [[conformal-risk-control]] for conformal risk control.\n")
        self.page(
            "c-page.md",
            "# C\n\n`conformal risk control` in code only. <!-- conformal risk control -->\n",
        )

    def test_scan_lists_uncompiled(self):
        out = self.cli("compile-scan", self.work)
        self.assertIn("2 sources, 2 selected", out)
        self.assertIn(f"## {self.one}", out)
        self.assertIn('title: "Paper: Two"', out)
        self.assertIn(f"source-file: {self.two}", out)

    def test_scan_one_source_with_summary(self):
        write(
            self.wiki / "summary-one.md",
            f'---\ntype: source-summary\nsource-file: "{self.one}"\n---\n# Paper One\n',
        )
        out = self.cli("compile-scan", self.work, self.docs / self.one)
        self.assertIn("1 selected", out)
        self.assertIn("Summary pages: `summary-one.md`", out)

    def test_scan_unknown_source(self):
        self.assertIn("no source nope.pdf", self.cli("compile-scan", self.work, "nope.pdf"))

    def test_mark_compiled(self):
        out = self.mark_both()
        self.assertTrue(out.startswith("marked compiled:"), out)
        self.assertIn("compiled: true", read_lines(self.docs / f"{self.today}-one.meta.md"))
        two_meta = (self.docs / f"{self.today}-two.meta.md").read_text(encoding="utf8")
        self.assertNotIn("compiled: false", two_meta)

    def test_sidecar_keeps_other_fields(self):
        self.mark_both()
        lines = read_lines(self.docs / f"{self.today}-two.meta.md")
        self.assertIn('title: "Paper: Two"', lines)

    def test_scan_reports_all_compiled(self):
        self.mark_both()
        out = self.cli("compile-scan", self.work)
        self.assertIn("All sources are already compiled.", out)

    def test_mark_unknown_refused(self):
        self.mark_both()
        self.assertIn("no sidecar", self.cli("mark-compiled", self.work, "missing.pdf"))

    def test_backlinks_finds_unlinked_mention_only(self):
        self.write_backlink_pages()
        out = self.cli("backlinks", self.work, "conformal-risk-control")
        self.assertEqual(out, "conformal-risk-control: a-page.md")

    def test_backlinks_unknown_page(self):
        self.write_backlink_pages()
        self.assertIn("no page", self.cli("backlinks", self.work, "nope"))

    def test_unbound_refused(self):
        out = self.cli("compile-scan", self.t / "nowhere")
        self.assertIn("no topic is bound", out)

    def test_scan_several_named(self):
        self.mark_both()
        out = self.cli("compile-scan", self.work, self.one, self.two)
        self.assertIn("2 selected", out)

    def test_orphan_listed_not_selected(self):
        self.mark_both()
        write(self.docs / "orphan.pdf", "x\n")
        out = self.cli("compile-scan", self.work)
        self.assertIn("0 selected", out)
        self.assertLike(out, ANY, "without a sidecar", ANY, "orphan.pdf", ANY)

    def test_backlinks_case_dots_frontmatter(self):
        self.write_backlink_pages()
        self.page("ieee-802.11.md", "# IEEE 802.11\n")
        self.page("d-page.md", "# D\n\nLinked as [[Conformal-Risk-Control]] and [[ieee-802.11]].\n")
        write(
            self.wiki / "e-page.md",
            "---\ntype: concept\ntags: [conformal risk control]\n---\n# E\n\nNothing here.\n",
        )
        out = self.cli("backlinks", self.work, "conformal-risk-control", "ieee-802.11")
        self.assertEqual(out, "conformal-risk-control: a-page.md\nieee-802.11: none")

    def test_mark_is_all_or_nothing(self):
        self.mark_both()
        meta = self.docs / f"{self.today}-one.meta.md"
        meta.write_text(
            meta.read_text(encoding="utf8").replace("compiled: true", "compiled: false"),
            encoding="utf8",
        )
        out = self.cli("mark-compiled", self.work, self.one, "typo.pdf")
        self.assertIn("nothing marked", out)
        self.assertIn("compiled: false", read_lines(meta))


class TestLint(Sandbox):
    def setUp(self):
        super().setUp()
        self.fresh("a")
        self.bind(self.work, "a")
        self.wiki = self.vault / "a" / "wiki"
        (self.wiki / "queries").mkdir()
        write(self.wiki / "index.md", "# a Wiki Index\n\n- [[good]] -- ok\n- [[gone]] -- missing page\n")
        write(
            self.wiki / "good.md",
            '---\ntype: concept\ninformed-by:\n  - "[[other]]"\n---\n# Good\n\nx\n\n'
            "## Details\n\n## See Also\n\n## Counter-Arguments and Gaps\n",
        )
        write(
            self.wiki / "other.md",
            "---\ntype: concept\n---\n# Other\n\nSee [[good]] and [[Good|alias]] and [[nowhere]]"
            " and ![[fig.png]] and [[ieee-802.11]].\n`[[in-code]]` <!-- [[in-comment]] -->\n\n## Details\n",
        )
        write(self.wiki / "ieee-802.11.md", "---\ntype: concept\n---\n# IEEE 802.11\n")
        write(self.wiki / "queries" / "q.md", "no frontmatter\n")
        write(self.wiki / "dup.md", "---\ntype: person\n---\n# Dup\n")
        write(self.wiki / "queries" / "dup.md", "---\ntype: query\n---\n# Dup\n")
        (self.vault / "a" / "raw" / "attachments" / "fig.png").touch()
        self.report = self.cli("lint-scan", self.work)

    def add_extra_pages(self):
        write(
            self.wiki / "f-page.md",
            "---\ntype: concept\n---\n# F\n\n```\n## Details\n## See Also\n"
            "## Counter-Arguments and Gaps\n```\n| [[good\\|Good]] | [[Index]] |\n",
        )
        (self.vault / "a" / "raw" / "documents" / "2026-01-01-src.md").touch()
        write(
            self.wiki / "g-page.md",
            "---\ntype: concept\n---\n# G\n\n[[2026-01-01-src.md]]\n",
        )
        return self.cli("lint-scan", self.work)

    def orphans(self, out):
        return sed_range(out, r"^## Orphan", r"^## Pages missing")

    def test_dead_links_page_and_index(self):
        self.assertIn("[[nowhere]]` in `other.md`", self.report)
        self.assertIn("[[gone]]` in `index.md`", self.report)

    def test_code_comments_attachments_dots_not_dead(self):
        for text in ("in-code", "in-comment", "[[fig.png]]", "[[ieee-802.11]]"):
            self.assertNotIn(text, self.report)

    def test_frontmatter_link_counts_as_inbound(self):
        section = sed_range(self.report, r"^## Orphan", r"^## ")
        self.assertNotIn("other.md", section)

    def test_orphans(self):
        self.assertIn("dup.md", self.orphans(self.report))

    def test_missing_from_index(self):
        section = sed_range(self.report, r"^## Pages missing", r"^## Missing")
        self.assertTrue(
            re.search(r"other\.md.*dup\.md|dup\.md.*other\.md", section, re.DOTALL), section
        )

    def test_missing_headers(self):
        self.assertIn("`other.md` (concept): `## See Also`", self.report)
        self.assertIn("`dup.md` (person): `## Key Contributions`", self.report)

    def test_good_page_complete(self):
        self.assertNotIn("`good.md` (concept)", self.report)

    def test_untyped_page(self):
        self.assertIn("`queries/q.md`: `(none)`", self.report)

    def test_ambiguous_names(self):
        self.assertIn("`dup`: `dup.md`, `queries/dup.md`", self.report)

    def test_unbound_refused(self):
        out = self.cli("lint-scan", self.t / "nowhere")
        self.assertIn("no topic is bound", out)

    def test_no_warnings_on_stderr(self):
        out = self.cli("lint-scan", self.work, streams=Streams.STDERR_ONLY)
        self.assertEqual(out, "")

    def test_header_in_code_fence_is_missing(self):
        out = self.add_extra_pages()
        self.assertIn("`f-page.md` (concept): `## Details`", out)

    def test_escaped_table_link_not_dead(self):
        out = self.add_extra_pages()
        self.assertNotIn("[[good\\", out)
        self.assertNotIn("[[good]]` in `f-page.md`", out)

    def test_link_to_raw_md_source_not_dead(self):
        out = self.add_extra_pages()
        self.assertNotIn("2026-01-01-src.md]]` in", out)

    def test_index_link_not_counted_as_inbound(self):
        out = self.add_extra_pages()
        self.assertNotIn("- `index.md`", self.orphans(out))
        self.assertIn("9 pages, 5 links", out)

    def test_ambiguous_name_credits_root_page_only(self):
        section = self.orphans(self.add_extra_pages())
        self.assertTrue("queries/dup.md" in section or "dup.md" in section, section)


class TestMerge(Sandbox):
    def scenario_one(self):
        self.fresh("f", "i")
        self.fd = self.vault / "f" / "raw" / "documents"
        self.id = self.vault / "i" / "raw" / "documents"
        self.fw = self.vault / "f" / "wiki"
        self.iw = self.vault / "i" / "wiki"
        fd, id_, fw, iw, v = self.fd, self.id, self.fw, self.iw, self.vault
        write(fd / "dupx.pdf", "same\n")
        sidecar(fd / "dupx.meta.md", "dupx.pdf", "", '"Dup X"', "true")
        write(id_ / "dupy.pdf", "same\n")
        sidecar(id_ / "dupy.meta.md", "dupy.pdf", "", '"Dup Y"', "false")
        write(fd / "solo.pdf", "solo\n")
        sidecar(fd / "solo.meta.md", "solo.pdf", '"https://x.org/solo"', '"Solo"', "true")
        write(id_ / "soloi.pdf", "soloi\n")
        sidecar(id_ / "soloi.meta.md", "soloi.pdf", "", '"Solo I"', "false")
        shutil.copy2(fd / "solo.pdf", id_ / "solo-copy.pdf")
        sidecar(id_ / "solo-copy.meta.md", "solo-copy.pdf", "", '"Solo copy"', "false")
        write(fd / "clash.pdf", "f-clash\n")
        sidecar(fd / "clash.meta.md", "clash.pdf", "", '"Clash F"', "true")
        write(id_ / "clash.pdf", "i-clash\n")
        sidecar(id_ / "clash.meta.md", "clash.pdf", "", '"Clash I"', "true")
        write(fd / "pre.pdf", "v1\n")
        sidecar(fd / "pre.meta.md", "pre.pdf", "", '"Same Title"', "true")
        write(id_ / "pub.pdf", "v2\n")
        sidecar(id_ / "pub.meta.md", "pub.pdf", "", '"Same Title"', "true")
        write(v / "f/raw/attachments/same.png", "img\n")
        write(v / "i/raw/attachments/same.png", "img\n")
        write(v / "f/raw/attachments/fig.png", "f\n")
        write(v / "i/raw/attachments/fig.png", "i\n")
        write(
            fw / "sum-x.md",
            "---\ntype: source-summary\nsource-file: dupx.pdf\n---\n# Dup\n\n## Overview -- frame: f\n",
        )
        write(
            iw / "sum-y.md",
            "---\ntype: source-summary\nsource-file: dupy.pdf\n---\n# Dup\n\n## Overview -- frame: i\n",
        )
        write(fw / "sum-clash.md", "---\ntype: source-summary\nsource-file: clash.pdf\n---\n# Clash F\n")
        write(fw / "sum-solo.md", "---\ntype: source-summary\nsource-file: solo.pdf\n---\n# Solo\n")
        write(
            fw / "new-page.md",
            "---\ntype: concept\n---\n# New\n\nSee [[sum-x]], [[shared]], [[bank]], ![[fig.png]].\n",
        )
        write(fw / "shared.md", "---\ntype: concept\n---\n# Shared F\n")
        write(iw / "shared.md", "---\ntype: concept\n---\n# Shared I\n\nLinks [[bank]].\n")
        write(fw / "bank.md", "---\ntype: concept\n---\n# River bank\n")
        write(iw / "bank.md", "---\ntype: concept\n---\n# Money bank\n")
        write(v / "f/outputs/reports/2026-01-01-lint.md", "report\n")
        write(v / "i/outputs/reports/2026-01-01-lint.md", "report\n")
        write(v / "f/extra/notes.txt", "n\n")
        with open(v / "f" / "log.md", "a", encoding="utf8") as handle:
            handle.write("\n## [2026-01-01] ingest | f source\nline\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "setup")
        self.bind(self.work, "f")
        self.bind(self.t / "work2", "f")
        self.bind(self.t / "other", "i")

    def move_one(self):
        out = self.cli("merge-move", "f", "i", "--distinct", "pre.pdf")
        return json.loads(out)

    def finish_one(self):
        self.move_one()
        self.cli("merge-finish", "f", "i")
        write(
            self.iw / "shared.md",
            "---\ntype: concept\n---\n# Shared\n\nMerged. Links [[bank]].\n",
        )
        (self.fw / "shared.md").unlink()
        (self.fw / "sum-x.md").unlink()
        shutil.move(str(self.fw / "bank.md"), str(self.iw / "river-bank.md"))
        return self.cli(
            "merge-finish", "f", "i", "--rename", "bank=river-bank", "--summary=test merge"
        )

    def scenario_two(self):
        self.fresh("g", "h")
        self.gd = self.vault / "g" / "raw" / "documents"
        self.hd = self.vault / "h" / "raw" / "documents"
        self.gw = self.vault / "g" / "wiki"
        self.hw = self.vault / "h" / "wiki"
        v = self.vault
        write(self.gd / "doc.pdf", "g1\n")
        sidecar(self.gd / "doc.meta.md", "doc.pdf", "", '"Doc G"', "true")
        write(self.hd / "doc.pdf", "h1\n")
        sidecar(self.hd / "doc.meta.md", "doc.pdf", "", '"Doc H"', "true")
        write(self.gd / "s.pdf", "same\n")
        sidecar(self.gd / "s.meta.md", "s.pdf", "", '"S"', "true")
        write(self.hd / "s2.pdf", "same\n")
        sidecar(self.hd / "s2.meta.md", "s2.pdf", "", '"S2"', "true")
        write(v / "g/raw/attachments/a.png", "a\n")
        write(v / "h/raw/attachments/a.png", "b\n")
        write(self.gw / "topic.md", "---\ntype: source-summary\nsource-file: s.pdf\n---\n# S\n")
        write(self.hw / "topic.md", "---\ntype: concept\n---\n# Topic H\n")
        write(
            self.hw / "s2-summary.md",
            "---\ntype: source-summary\nsource-file: s2.pdf\n---\n# S2\n",
        )
        write(
            self.gw / "p.md",
            "---\ntype: concept\n---\n# P\n\n[[doc.pdf]] ![](../raw/attachments/a.png)"
            " | [[topic\\|T]] |\n```\n[[doc.pdf]]\n```\n",
        )
        write(self.gw / "diagram.canvas", "x")
        write(self.gw / "people" / "index.md", "# nested index\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "setup2")

    def move_two(self):
        out = self.cli("merge-move", "g", "h")
        return json.loads(out)

    def fail_commit_hook(self):
        hook = self.vault / ".git" / "hooks" / "pre-commit"
        write(hook, "#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        return hook

    def prepare_finish_two(self):
        self.move_two()
        self.cli("merge-finish", "g", "h")
        shutil.move(str(self.gw / "people" / "index.md"), str(self.hw / "people-index.md"))
        (self.gw / "people").rmdir()
        (self.gw / "topic.md").unlink()

    def test_undecided_possible_duplicate_refused(self):
        self.scenario_one()
        out = self.cli("merge-move", "f", "i")
        self.assertLike(out, ANY, "decide each possible duplicate", ANY, "pre.pdf", ANY)
        self.assertTrue((self.fd / "pre.pdf").is_file())

    def test_dirty_tree_refused(self):
        self.scenario_one()
        write(self.fw / "dirty.md", "dirty\n")
        out = self.cli("merge-move", "f", "i", "--distinct", "pre.pdf")
        self.assertIn("commit or discard", out)

    def test_move_ran(self):
        self.scenario_one()
        self.assertNotIn(self.move_one().get("to_reconcile"), (None, False))

    def test_duplicate_deleted_kept_copy_compiled(self):
        self.scenario_one()
        self.move_one()
        self.assertFalse((self.fd / "dupx.pdf").exists())
        self.assertIn("compiled: true", read_lines(self.id / "dupy.meta.md"))

    def test_empty_title_filled_kept_existing(self):
        self.scenario_one()
        self.move_one()
        self.assertIn('title: "Dup Y"', read_lines(self.id / "dupy.meta.md"))

    def test_solo_dedup_with_uri_filled(self):
        self.scenario_one()
        self.move_one()
        self.assertFalse((self.fd / "solo.pdf").exists())
        self.assertIn(
            'source-uri: "https://x.org/solo"', read_lines(self.id / "solo-copy.meta.md")
        )

    def test_summary_retargeted_and_moved(self):
        self.scenario_one()
        self.move_one()
        self.assertIn("source-file: solo-copy.pdf", read_lines(self.iw / "sum-solo.md"))

    def test_clash_renamed_with_sidecar(self):
        self.scenario_one()
        self.move_one()
        self.assertTrue((self.id / "clash-2.pdf").is_file())
        self.assertTrue((self.id / "clash-2.meta.md").is_file())
        self.assertIn("source-file: clash-2.pdf", read_lines(self.id / "clash-2.meta.md"))
        self.assertIn("source-file: clash-2.pdf", read_lines(self.iw / "sum-clash.md"))

    def test_distinct_moved(self):
        self.scenario_one()
        self.move_one()
        self.assertTrue((self.id / "pre.pdf").is_file())

    def test_attachments(self):
        self.scenario_one()
        self.move_one()
        self.assertFalse((self.vault / "f/raw/attachments/same.png").exists())
        self.assertTrue((self.vault / "i/raw/attachments/fig-2.png").is_file())
        page = (self.iw / "new-page.md").read_text(encoding="utf8")
        self.assertIn("![[fig-2.png]]", page)

    def test_reconcile_list(self):
        self.scenario_one()
        state = self.move_one()
        got = ",".join(
            sorted(f"{e['kind']}:{e['from']}>{e['into']}" for e in state["to_reconcile"])
        )
        self.assertEqual(
            got,
            "same-name:bank.md>bank.md,same-name:shared.md>shared.md,"
            "same-source:sum-x.md>sum-y.md",
        )

    def test_finish_refuses_with_pages_left(self):
        self.scenario_one()
        self.move_one()
        out = self.cli("merge-finish", "f", "i")
        self.assertIn("reconcile or move these pages first", out)

    def test_finish_commits(self):
        self.scenario_one()
        out = self.finish_one()
        self.assertIn("Merged f into i", out)
        self.assertEqual(self.git("log", "-1", "--format=%s").strip(), "merge: f into i")
        self.assertEqual(self.porcelain(), "")

    def test_from_topic_gone(self):
        self.scenario_one()
        self.finish_one()
        self.assertFalse((self.vault / "f").exists())

    def test_summary_link_rewritten_everywhere(self):
        self.scenario_one()
        self.finish_one()
        self.assertIn("[[sum-y]]", (self.iw / "new-page.md").read_text(encoding="utf8"))

    def test_homonym_link_rewritten_in_f_pages_only(self):
        self.scenario_one()
        self.finish_one()
        self.assertIn("[[river-bank]]", (self.iw / "new-page.md").read_text(encoding="utf8"))
        self.assertIn("[[bank]]", (self.iw / "shared.md").read_text(encoding="utf8"))

    def test_reports_and_extra_files_moved(self):
        self.scenario_one()
        self.finish_one()
        reports = self.vault / "i" / "outputs" / "reports"
        self.assertTrue((reports / "f-2026-01-01-lint.md").is_file())
        self.assertTrue((self.vault / "i" / "extra" / "notes.txt").is_file())

    def test_log_merged(self):
        self.scenario_one()
        self.finish_one()
        lines = read_lines(self.vault / "i" / "log.md")
        self.assertTrue(any("ingest | f source" in line for line in lines))
        self.assertIn("merge | f into i", lines[-2])

    def test_rebound(self):
        self.scenario_one()
        self.finish_one()
        topics = json.loads(self.topics_text())
        self.assertEqual(topics.get(str(self.work)), "i")
        self.assertEqual(topics.get(str(self.t / "work2")), "i")

    def test_no_dead_links_after_merge(self):
        self.scenario_one()
        self.finish_one()
        out = self.cli("lint-scan", self.t / "other", "--topic", "i")
        self.assertIn("## Dead links (0)", out)

    def test_same_on_a_non_candidate_refused(self):
        self.scenario_two()
        out = self.cli("merge-move", "g", "h", "--same", "doc.pdf")
        self.assertIn("take only possible duplicates", out)
        self.assertTrue((self.gd / "doc.pdf").is_file())

    def test_raw_rename_rewritten_code_kept(self):
        self.scenario_two()
        self.move_two()
        lines = read_lines(self.hw / "p.md")
        self.assertTrue(any("[[doc-2.pdf]]" in line for line in lines))
        fenced = [
            lines[i : i + 2] for i, line in enumerate(lines) if line.startswith("```")
        ]
        self.assertTrue(any("[[doc.pdf]]" in line for pair in fenced for line in pair))

    def test_markdown_image_rewritten(self):
        self.scenario_two()
        self.move_two()
        self.assertIn("attachments/a-2.png)", (self.hw / "p.md").read_text(encoding="utf8"))

    def test_summary_name_colliding_with_i_page_local_rename(self):
        self.scenario_two()
        state = self.move_two()
        self.assertEqual(state["local_renames"]["topic"], "s2-summary")
        link_renames = state.get("link_renames") or {}
        self.assertEqual(link_renames.get("topic") or "none", "none")
        self.assertIn("[[s2-summary\\|T]]", (self.hw / "p.md").read_text(encoding="utf8"))

    def test_one_reconcile_entry_for_the_summary(self):
        self.scenario_two()
        state = self.move_two()
        entries = [e for e in state["to_reconcile"] if e["from"] == "topic.md"]
        self.assertEqual(len(entries), 1)

    def test_nested_page_blocks_finish(self):
        self.scenario_two()
        self.move_two()
        self.assertIn("wiki/people/index.md", self.cli("merge-finish", "g", "h"))

    def test_failed_commit_restores_the_old_topic(self):
        self.scenario_two()
        self.prepare_finish_two()
        self.fail_commit_hook()
        out = self.cli("merge-finish", "g", "h")
        self.assertIn("merge-finish failed", out)
        self.assertTrue((self.vault / "g").is_dir())
        self.assertTrue((self.vault / "g" / "merge-state.json").is_file())

    def test_failed_finish_restored_leftovers_and_log(self):
        self.scenario_two()
        self.prepare_finish_two()
        self.fail_commit_hook()
        self.cli("merge-finish", "g", "h")
        self.assertTrue((self.gw / "diagram.canvas").is_file())
        log = read_lines(self.vault / "h" / "log.md")
        self.assertEqual(sum("merge | g into h" in line for line in log), 0)

    def finish_two_after_fix(self):
        self.prepare_finish_two()
        hook = self.fail_commit_hook()
        self.cli("merge-finish", "g", "h")
        hook.unlink()
        return self.cli("merge-finish", "g", "h")

    def test_finish_after_fix(self):
        self.scenario_two()
        out = self.finish_two_after_fix()
        self.assertIn("Merged g into h", out)
        self.assertFalse((self.vault / "g").exists())

    def test_non_md_wiki_file_moved(self):
        self.scenario_two()
        self.finish_two_after_fix()
        self.assertTrue((self.hw / "diagram.canvas").is_file())

    def test_i_page_link_to_its_own_topic_untouched(self):
        self.scenario_two()
        self.finish_two_after_fix()
        self.assertIn("Topic H", (self.hw / "topic.md").read_text(encoding="utf8"))


    def test_merged_log_skips_template_comment(self):
        self.vault.mkdir(parents=True)
        self.git("init", "-q")
        self.write_config()
        self.cli("init", "--description=from", "--", self.work / "f", "zf")
        self.cli("init", "--description=into", "--", self.work / "i", "zi")
        self.cli("log-commit", self.work / "f", "query", "from question")
        self.cli("merge-move", "zf", "zi")
        out = self.cli("merge-finish", "zf", "zi", "--summary=regression")
        self.assertIn("Merged zf into zi", out)
        log = (self.vault / "zi" / "log.md").read_text(encoding="utf8")
        self.assertEqual(log.count("## [YYYY-MM-DD] <op> | <title>"), 1)
        self.assertEqual(log.count("-->"), 1)
        self.assertIn("query | from question", log)
        self.assertIn("init | zf wiki", log)


if __name__ == "__main__":
    unittest.main()
