from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from pathlib import Path

    from disaster_report.config import Settings


@pytest.fixture
def tree_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def test_settings(tree_root: Path) -> Settings:
    from disaster_report.config import Settings

    return Settings(
        tree_root=str(tree_root),
        openrouter_api_key="test-key",
        openrouter_model="test-model",
        active_window_days=7,
    )


@pytest.fixture
def clock() -> Callable[[], datetime]:
    import datetime

    fixed = datetime.datetime(2026, 7, 4, 12, 0, 0, 0, tzinfo=datetime.timezone.utc)
    return lambda: fixed
