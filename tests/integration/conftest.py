from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sources"


@pytest.fixture
def load_fixture():
    def _load(name: str) -> bytes:
        return (_FIXTURES / name).read_bytes()

    return _load


@pytest.fixture
def mock_httpx(monkeypatch):
    registry: dict[str, tuple[bytes, str]] = {}

    def register(url: str, content: bytes | str, content_type: str = "application/json") -> None:
        registry[url] = (
            content.encode() if isinstance(content, str) else content,
            content_type,
        )

    def fake_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if url in registry:
            content, ct = registry[url]
            return httpx.Response(
                200, content=content, headers={"content-type": ct}, request=req
            )
        return httpx.Response(
            404,
            content=b"no fixture registered for " + url.encode(),
            request=req,
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    return SimpleNamespace(register=register)
