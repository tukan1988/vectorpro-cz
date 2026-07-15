#!/usr/bin/env python3
"""Build and push gh-pages branch for GitHub Pages."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "https://github.com/tukan1988/vectorpro-cz.git"
BASE = "/vectorpro-cz"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def main() -> None:
    token_file = ROOT / ".edit-github-token"
    if token_file.exists() or os.environ.get("VP_GITHUB_TOKEN"):
        run([sys.executable, "setup_gh_edit.py"])
    run([sys.executable, "build_pages.py", "--out", "_site", "--base", BASE])

    tmp = Path(tempfile.mkdtemp(prefix="vp-pages-"))
    try:
        pages = tmp / "pages"
        shutil.copytree(ROOT / "_site", pages)

        run(["git", "init"], cwd=pages)
        run(["git", "checkout", "-b", "gh-pages"], cwd=pages)
        run(["git", "add", "-A"], cwd=pages)
        run(["git", "commit", "-m", "Deploy VectorPro CZ site"], cwd=pages)
        run(["git", "remote", "add", "origin", REPO], cwd=pages)
        run(["git", "push", "-f", "origin", "gh-pages"], cwd=pages)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    subprocess.run(
        [
            "gh", "api", "repos/tukan1988/vectorpro-cz/pages", "-X", "POST",
            "-f", "build_type=legacy",
            "-f", "source[branch]=gh-pages",
            "-f", "source[path]=/",
        ],
        check=False,
    )
    print("\nHotovo: https://tukan1988.github.io/vectorpro-cz/")


if __name__ == "__main__":
    main()
