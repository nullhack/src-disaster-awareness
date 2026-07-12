#!/usr/bin/env python3
"""Regenerate dashboard JSON from the DB and push to the gh-pages branch.

Workflow:
1. Run generate_dashboard_data.py -> temp dir
2. Checkout gh-pages branch
3. Replace data/ with the fresh JSON
4. Commit + push

Usage:
    uv run python scripts/publish_dashboard_data.py [--db disaster_report.db]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = REPO_ROOT / ".cache" / "dashboard-build"


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or REPO_ROOT, check=True, capture_output=True, text=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate + push dashboard data to gh-pages")
    parser.add_argument("--db", default="disaster_report.db")
    parser.add_argument("--as-of", default=None, help="Override as-of date (YYYY-MM-DD)")
    args = parser.parse_args()

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)

    gen_args = [
        "uv", "run", "python", "scripts/generate_dashboard_data.py",
        "--db", args.db,
        "--output", str(TMP_DIR),
    ]
    if args.as_of:
        gen_args += ["--as-of", args.as_of]
    print("Generating dashboard JSON...")
    run(gen_args)

    print("Stashing any working tree changes...")
    stash_result = subprocess.run(
        ["git", "stash", "list"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )

    current_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()

    has_changes = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    ).stdout.strip()

    stashed = False
    if has_changes:
        run(["git", "stash", "--include-untracked"])
        stashed = True

    try:
        print("Checking out gh-pages...")
        run(["git", "checkout", "gh-pages"])

        print("Replacing data/...")
        data_dir = REPO_ROOT / "data"
        if data_dir.exists():
            shutil.rmtree(data_dir)
        shutil.copytree(TMP_DIR, data_dir)

        run(["git", "add", "data/"])
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=REPO_ROOT,
        )
        if diff.returncode == 0:
            print("No changes to publish.")
            return

        ts = subprocess.run(
            ["git", "show", "-s", "--format=%ci", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()[:10]
        run(["git", "commit", "-m", f"chore(data): regenerate dashboard JSON ({ts})"])

        print("Pushing gh-pages...")
        run(["git", "push", "origin", "gh-pages"])
        print("Done. GitHub Pages will rebuild automatically.")

    finally:
        print(f"Returning to {current_branch}...")
        run(["git", "checkout", current_branch])
        if stashed:
            run(["git", "stash", "pop"])
        shutil.rmtree(TMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
