from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


class UpdateError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


class AppUpdater:
    def __init__(
        self,
        project_root: str | Path | None = None,
        runner: Runner = subprocess.run,
        python_executable: str | None = None,
        branch: str | None = None,
    ):
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self.runner = runner
        self.python_executable = python_executable or sys.executable
        self.branch = branch or os.environ.get("CLASSROOM_UPDATE_BRANCH", "stable")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}", self.branch):
            raise UpdateError("업데이트 브랜치 이름이 올바르지 않습니다.")
        if ".." in self.branch or self.branch.endswith(("/", ".")):
            raise UpdateError("업데이트 브랜치 이름이 올바르지 않습니다.")

    def _run(self, command: list[str], timeout: int = 60) -> str:
        try:
            result = self.runner(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise UpdateError(f"업데이트 명령을 실행하지 못했습니다: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "알 수 없는 오류").strip()
            raise UpdateError(detail[-500:])
        return result.stdout.strip()

    def _git(self, *arguments: str, timeout: int = 60) -> str:
        return self._run(["git", *arguments], timeout=timeout)

    def check(self, fetch: bool = True) -> dict[str, Any]:
        if not (self.project_root / ".git").exists():
            raise UpdateError("Git으로 설치된 앱에서만 자동 업데이트할 수 있습니다.")

        dirty = bool(self._git("status", "--porcelain"))
        current = self._git("rev-parse", "--short", "HEAD")
        if fetch:
            self._git("fetch", "--quiet", "origin", self.branch, timeout=120)
        remote_ref = f"origin/{self.branch}"
        latest = self._git("rev-parse", "--short", remote_ref)
        counts = self._git(
            "rev-list", "--left-right", "--count", f"HEAD...{remote_ref}"
        ).split()
        if len(counts) != 2:
            raise UpdateError("Git 버전 상태를 확인하지 못했습니다.")
        ahead, behind = map(int, counts)

        if dirty:
            message = "수정된 파일이 있어 자동 업데이트할 수 없습니다."
        elif ahead and behind:
            message = "로컬과 원격 이력이 갈라져 자동 업데이트할 수 없습니다."
        elif ahead:
            message = "원격에 없는 로컬 커밋이 있어 자동 업데이트하지 않습니다."
        elif behind:
            message = f"새 업데이트 {behind}개를 설치할 수 있습니다."
        else:
            message = "이미 최신 버전입니다."

        return {
            "current": current,
            "latest": latest,
            "channel": self.branch,
            "ahead": ahead,
            "behind": behind,
            "dirty": dirty,
            "available": behind > 0,
            "can_update": behind > 0 and ahead == 0 and not dirty,
            "message": message,
        }

    def apply(self) -> dict[str, Any]:
        status = self.check(fetch=True)
        if not status["available"]:
            return {**status, "updated": False}
        if not status["can_update"]:
            raise UpdateError(status["message"])

        self._git("merge", "--ff-only", f"origin/{self.branch}", timeout=120)
        requirements = self.project_root / "requirements.txt"
        if requirements.exists():
            self._run(
                [
                    self.python_executable,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "-r",
                    str(requirements),
                ],
                timeout=600,
            )

        current = self._git("rev-parse", "--short", "HEAD")
        return {
            **status,
            "current": current,
            "latest": current,
            "behind": 0,
            "available": False,
            "can_update": False,
            "updated": True,
            "message": "업데이트를 설치했습니다. 서버를 다시 시작합니다.",
        }
