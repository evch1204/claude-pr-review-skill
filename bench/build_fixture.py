#!/usr/bin/env python3
"""Build a throwaway git repo for one benchmark fixture.

A fixture directory looks like:

    fixtures/<name>/
        fixture.json      # branches, commit list, PR title/body
        answer_key.json   # seeded issues + decoys (never copied into the repo)
        base/             # files committed on the base branch
        commits/<dir>/    # overlay for each PR commit; optional `.delete` lists paths to remove

Usage: build_fixture.py <fixture_dir> <dest_dir>
The dest repo ends up checked out on the PR branch, with the base branch intact,
so a reviewer can run `git diff main...HEAD`, `git log`, etc.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def git(dest, *args):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Dev",
        "GIT_AUTHOR_EMAIL": "dev@example.com",
        "GIT_COMMITTER_NAME": "Dev",
        "GIT_COMMITTER_EMAIL": "dev@example.com",
        "GIT_AUTHOR_DATE": "2026-10-01T12:00:00Z",
        "GIT_COMMITTER_DATE": "2026-10-01T12:00:00Z",
    }
    subprocess.run(["git", *args], cwd=dest, check=True, env=env, stdout=subprocess.DEVNULL)


def overlay(src: Path, dest: Path):
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if rel.name == ".delete" and path.parent == src:
            continue
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    delete_list = src / ".delete"
    if delete_list.exists():
        for line in delete_list.read_text().splitlines():
            if line.strip():
                (dest / line.strip()).unlink(missing_ok=True)


def main():
    fixture, dest = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    spec = json.loads((fixture / "fixture.json").read_text())
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    git(dest, "init", "-q", "-b", spec.get("base_branch", "main"))
    overlay(fixture / "base", dest)
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", spec.get("base_message", "Initial commit"))
    git(dest, "checkout", "-q", "-b", spec["pr_branch"])
    for c in spec["commits"]:
        overlay(fixture / "commits" / c["dir"], dest)
        git(dest, "add", "-A")
        git(dest, "commit", "-q", "--allow-empty", "-m", c["message"])
    print(dest)


if __name__ == "__main__":
    main()
