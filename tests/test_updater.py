import subprocess
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from classroom_lite.updater import AppUpdater, UpdateError


class FakeRunner:
    def __init__(self):
        self.responses = defaultdict(list)
        self.calls = []

    def add(self, command, stdout="", returncode=0, stderr=""):
        self.responses[tuple(command)].append(
            subprocess.CompletedProcess(command, returncode, stdout, stderr)
        )

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        responses = self.responses[tuple(command)]
        if not responses:
            raise AssertionError(f"예상하지 않은 명령: {command}")
        return responses.pop(0)


class AppUpdaterTests(unittest.TestCase):
    def make_project(self, directory):
        root = Path(directory)
        (root / ".git").mkdir()
        (root / "requirements.txt").write_text("Flask\n", encoding="utf-8")
        return root

    def prepare_check(self, runner, *, dirty="", ahead=0, behind=1):
        runner.add(["git", "status", "--porcelain"], dirty)
        runner.add(["git", "rev-parse", "--short", "HEAD"], "aaaaaaa")
        runner.add(["git", "fetch", "--quiet", "origin", "stable"])
        runner.add(["git", "rev-parse", "--short", "origin/stable"], "bbbbbbb")
        runner.add(
            ["git", "rev-list", "--left-right", "--count", "HEAD...origin/stable"],
            f"{ahead}\t{behind}",
        )

    def test_check_reports_fast_forward_update(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeRunner()
            self.prepare_check(runner, behind=2)
            status = AppUpdater(self.make_project(directory), runner).check()
        self.assertTrue(status["available"])
        self.assertTrue(status["can_update"])
        self.assertEqual(status["behind"], 2)

    def test_rejects_unsafe_branch_name(self):
        with self.assertRaisesRegex(UpdateError, "브랜치 이름"):
            AppUpdater(branch="--upload-pack=bad")

    def test_apply_refuses_dirty_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeRunner()
            self.prepare_check(runner, dirty=" M app.py")
            updater = AppUpdater(self.make_project(directory), runner)
            with self.assertRaisesRegex(UpdateError, "수정된 파일"):
                updater.apply()

    def test_apply_fast_forwards_and_installs_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeRunner()
            root = self.make_project(directory)
            self.prepare_check(runner)
            runner.add(["git", "merge", "--ff-only", "origin/stable"])
            runner.add(
                [
                    "/test/python",
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "-r",
                    str(root / "requirements.txt"),
                ]
            )
            runner.add(["git", "rev-parse", "--short", "HEAD"], "bbbbbbb")
            result = AppUpdater(
                root, runner, python_executable="/test/python"
            ).apply()

        self.assertTrue(result["updated"])
        self.assertEqual(result["current"], "bbbbbbb")
        self.assertIn(
            ["git", "merge", "--ff-only", "origin/stable"], runner.calls
        )


if __name__ == "__main__":
    unittest.main()
