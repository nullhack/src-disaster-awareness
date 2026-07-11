from collections.abc import Callable
from datetime import datetime

import pytest
from disaster_report.config import Settings

@pytest.fixture
def db_url(tmp_path: str) -> str: ...
@pytest.fixture
def test_settings(db_url: str) -> Settings: ...
@pytest.fixture
def clock() -> Callable[[], datetime]: ...
