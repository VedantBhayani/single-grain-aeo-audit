"""Guardrails on the workflow files (stdlib has no YAML parser, so these read the text).
Each one pins a security or reliability fix, so undoing it fails here instead of in production."""
import re
import unittest
from pathlib import Path

WF = Path(__file__).resolve().parent.parent / ".github" / "workflows"


def text(name):
    return (WF / name).read_text(encoding="utf-8")


def top_level(src):
    """The part of a workflow before `jobs:`."""
    return src.split("\njobs:", 1)[0]


def job(src, name):
    """One job's block: from `  name:` to the next job at the same indent."""
    m = re.search(rf"(?ms)^  {name}:\n(.*?)(?=^  [a-z][\w-]*:\n|\Z)", src.split("\njobs:", 1)[1])
    return m.group(1)


class AeoWatchWorkflow(unittest.TestCase):
    src = text("aeo-watch.yml")

    def test_no_rights_by_default_and_pages_only_in_deploy(self):
        self.assertRegex(top_level(self.src), r"(?m)^permissions: \{\}")
        watch, deploy = job(self.src, "watch"), job(self.src, "deploy")
        self.assertNotIn("pages: write", watch)
        self.assertNotIn("id-token", watch)
        self.assertIn("pages: write", deploy)
        self.assertNotIn("actions/checkout", deploy)  # deploy never touches the repo or scraped content

    def test_the_box_key_only_reaches_box_steps(self):
        code = "\n".join(line.split("#", 1)[0] for line in top_level(self.src).splitlines())  # comments out
        self.assertNotIn("INSTABOX_API_KEY", code)
        steps = re.split(r"(?m)^      - ", job(self.src, "watch"))
        with_key = [s.splitlines()[0] for s in steps if "secrets.INSTABOX_API_KEY" in s]
        self.assertEqual(len(with_key), 3, with_key)
        self.assertNotIn("INSTABOX", job(self.src, "issues"))
        self.assertNotIn("INSTABOX", job(self.src, "deploy"))

    def test_issue_rights_only_in_the_issues_job_and_it_cannot_block_the_dashboard(self):
        self.assertNotIn("issues: write", job(self.src, "watch"))
        self.assertIn("issues: write", job(self.src, "issues"))
        self.assertIn("issues.py", job(self.src, "issues"))
        self.assertNotIn("issues.py", job(self.src, "watch"))
        self.assertRegex(job(self.src, "deploy"), r"needs: watch\n")

    def test_no_expressions_pasted_into_shell(self):
        for block in re.findall(r"(?ms)run: \|\n(.*?)(?=\n      - |\Z)", self.src):
            self.assertNotIn("${{", block)

    def test_wake_step_waits_for_the_box_lock_before_touching_code(self):
        wake = [s for s in re.split(r"(?m)^      - ", job(self.src, "watch")) if "Wake the box" in s][0]
        self.assertLess(wake.index("flock -n 9"), wake.index("git reset"))

    def test_one_results_folder_per_run(self):
        self.assertIn('RUN=$(date -u +%Y-%m-%dT%H%MZ)', self.src)


class AllWorkflows(unittest.TestCase):
    def test_every_action_is_pinned_to_a_commit(self):
        # Jobs here can push, write issues and deploy Pages: a moved tag must not change what runs.
        for f in WF.glob("*.yml"):
            for ref in re.findall(r"uses:\s*(\S+)", f.read_text(encoding="utf-8")):
                self.assertRegex(ref, r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$", f"{f.name}: {ref}")


class OtherWorkflows(unittest.TestCase):
    def test_tests_workflow_is_read_only(self):
        self.assertRegex(text("tests.yml"), r"(?m)^permissions:\n  contents: read")

    def test_tracking_guard_rebases_and_alerts_even_if_commit_fails(self):
        src = text("tracking-guard.yml")
        self.assertIn("git pull -q --rebase && git push", src)
        self.assertRegex(src, r"if: always\(\) && steps\.guard\.outputs\.exit != '0'")


if __name__ == "__main__":
    unittest.main()
