from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest
from disaster_report.config import Settings

@pytest.fixture
def tree_root(tmp_path: Path) -> Path: ...
@pytest.fixture
def test_settings(tree_root: Path) -> Settings: ...
@pytest.fixture
def clock() -> Callable[[], datetime]: ...
