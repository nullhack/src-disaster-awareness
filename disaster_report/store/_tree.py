from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

import yaml

NAMESPACE = uuid.UUID("746d6665-6e61-626c-6521-000000000001")
_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def safe_part(value: str) -> str:
    return _SAFE.sub("_", value) or "_"


def report_uuid(source: str, source_id: str) -> str:
    return uuid.uuid5(NAMESPACE, f"report:{source}:{source_id}").hex


def news_uuid(url: str) -> str:
    return uuid.uuid5(NAMESPACE, f"news:{url}").hex


def report_staging_path(root: Path, source: str, ruuid: str) -> Path:
    return root / "reports" / f"source={safe_part(source)}" / f"{ruuid}.yaml"


def news_staging_path(root: Path, nuuid: str) -> Path:
    return root / "news" / f"{nuuid}.yaml"


def incident_dir(root: Path, iuuid: str) -> Path:
    return root / "incidents" / iuuid


def incident_manifest_path(root: Path, iuuid: str) -> Path:
    return incident_dir(root, iuuid) / "incident.yaml"


def incident_report_path(root: Path, iuuid: str, source: str, ruuid: str) -> Path:
    return incident_dir(root, iuuid) / "reports" / f"source={safe_part(source)}" / f"{ruuid}.yaml"


def incident_news_path(root: Path, iuuid: str, nuuid: str) -> Path:
    return incident_dir(root, iuuid) / "news" / f"{nuuid}.yaml"


def log_dir(root: Path, iuuid: str, log_date: str) -> Path:
    return incident_dir(root, iuuid) / "logs" / log_date


def log_path(root: Path, iuuid: str, log_date: str) -> Path:
    return log_dir(root, iuuid, log_date) / "log.yaml"


def log_news_path(root: Path, iuuid: str, log_date: str, nuuid: str) -> Path:
    return log_dir(root, iuuid, log_date) / "news" / f"{nuuid}.yaml"


def _str_block(dumper: yaml.Dumper, data: str) -> Any:
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


class _StoreDumper(yaml.Dumper):
    def ignore_aliases(self, data: Any) -> bool:  # noqa: ARG002
        return True


_StoreDumper.add_representer(str, _str_block)


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.dump(
        data,
        Dumper=_StoreDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    )
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    return loaded if isinstance(loaded, dict) else {}
