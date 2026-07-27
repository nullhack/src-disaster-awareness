"""Shared GitHub issue helpers for bot scripts."""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def gh(args: list[str]) -> str:

    proc = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def add_label(number: int, label: str) -> None:

    gh(["issue", "edit", str(number), "--add-label", label])


def remove_label(number: int, label: str) -> None:

    try:
        gh(["issue", "edit", str(number), "--remove-label", label])
    except RuntimeError as exc:
        logger.warning("issue %s: remove-label %s failed: %s", number, label, exc)


def close(number: int, reason: str) -> None:

    gh(["issue", "close", str(number), "--reason", "not planned", "--comment", reason])


def comment(number: int, body: str) -> None:

    gh(["issue", "comment", str(number), "--body", body])
