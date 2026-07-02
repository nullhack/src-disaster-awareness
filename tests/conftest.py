from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from disaster_report.store import SqliteIncidentStore


@pytest.fixture(scope="session")
def _db_template(tmp_path_factory):
    tpl = tmp_path_factory.mktemp("tpl") / "template.db"
    SqliteIncidentStore(f"sqlite:///{tpl}")
    return tpl


@pytest.fixture
def db_url(_db_template, tmp_path):
    dst = Path(tmp_path) / "store.db"
    shutil.copy(_db_template, dst)
    return f"sqlite:///{dst}"
