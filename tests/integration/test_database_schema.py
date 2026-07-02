from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect

from disaster_report.models import Base


EXPECTED_DIMENSIONS = frozenset(
    {
        "dim_date",
        "dim_country",
        "dim_source",
        "dim_incident_type",
        "dim_disease",
        "dim_priority",
        "dim_severity_level",
        "dim_pandemic_potential",
    }
)
EXPECTED_FACTS = frozenset(
    {
        "fact_incident",
        "fact_gdacs_event",
        "fact_who_don",
        "fact_healthmap_alert",
        "fact_usgs_earthquake",
        "fact_news_article",
    }
)
CHILD_FACT_NATURAL_KEY = {
    "fact_gdacs_event": "gdacs_eventid",
    "fact_who_don": "don_id",
    "fact_healthmap_alert": "alert_id",
    "fact_usgs_earthquake": "usgs_id",
    "fact_news_article": "url",
}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "disaster.db"


@pytest.fixture
def inspector(db_path):
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return inspect(engine)


def _unique_columns(insp, table):
    cols = set()
    for uc in insp.get_unique_constraints(table):
        cols.update(uc["column_names"])
    for idx in insp.get_indexes(table):
        if idx["unique"]:
            cols.update(idx["column_names"])
    return cols


def _fk_targets(insp, table):
    return {fk["referred_table"] for fk in insp.get_foreign_keys(table)}


def _fk_columns_to(insp, table, target):
    return {
        fk["constrained_columns"][0]
        for fk in insp.get_foreign_keys(table)
        if fk["referred_table"] == target
    }


def test_given_no_database_when_create_all_then_galaxy_tables_created(db_path):
    assert not db_path.exists()

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    assert db_path.exists()
    tables = set(inspect(engine).get_table_names())
    assert tables == EXPECTED_DIMENSIONS | EXPECTED_FACTS


def test_given_galaxy_when_inspected_then_every_dimension_has_surrogate_key(inspector):
    for dim_table in EXPECTED_DIMENSIONS:
        pk = inspector.get_pk_constraint(dim_table)["constrained_columns"]
        assert len(pk) == 1, f"{dim_table} must have a single surrogate primary key"
        assert pk[0].endswith("_key"), f"{dim_table} primary key must be a surrogate *_key"

        columns = {c["name"]: c for c in inspector.get_columns(dim_table)}
        assert columns[pk[0]]["type"].python_type is int, f"{dim_table}.{pk[0]} must be integer"
        assert columns[pk[0]]["nullable"] is False


def test_given_galaxy_when_inspected_then_fact_incident_is_parent_referencing_conformed_dims(
    inspector,
):
    assert inspector.get_pk_constraint("fact_incident")["constrained_columns"] == ["incident_key"]
    assert "incident_id" in _unique_columns(inspector, "fact_incident")

    columns = {c["name"]: c for c in inspector.get_columns("fact_incident")}
    assert columns["incident_key"]["type"].python_type is int
    assert columns["incident_id"]["type"].python_type is str
    assert columns["summary"]["type"].python_type is str

    referenced = _fk_targets(inspector, "fact_incident")
    assert referenced == {
        "dim_date",
        "dim_country",
        "dim_incident_type",
        "dim_priority",
        "dim_severity_level",
        "dim_disease",
        "dim_pandemic_potential",
    }

    date_fk_columns = _fk_columns_to(inspector, "fact_incident", "dim_date")
    assert {"first_reported_date_key", "last_updated_date_key", "event_date_key"} <= date_fk_columns

    assert columns["disease_key"]["nullable"] is True
    assert columns["should_report"]["type"].python_type is bool
    assert columns["pandemic_potential_key"]["nullable"] is True, (
        "pandemic_potential_key must be nullable (physical incident or not yet digested)"
    )
    assert columns["event_status"]["nullable"] is True


def test_given_galaxy_when_inspected_then_child_facts_link_to_parent_and_share_conformed_dims(
    inspector,
):
    for child, natural_key in CHILD_FACT_NATURAL_KEY.items():
        targets = _fk_targets(inspector, child)
        assert "fact_incident" in targets, f"{child} must link to parent fact_incident"
        assert "dim_source" in targets, f"{child} must reference conformed dim_source"
        assert "dim_date" in targets, f"{child} must reference conformed dim_date"
        assert natural_key in _unique_columns(inspector, child)

        incident_fk_cols = _fk_columns_to(inspector, child, "fact_incident")
        assert incident_fk_cols == {"incident_key"}

    for child in CHILD_FACT_NATURAL_KEY:
        if child == "fact_news_article":
            continue
        columns = {c["name"]: c for c in inspector.get_columns(child)}
        assert columns["incident_key"]["nullable"] is False, (
            f"{child}.incident_key must be NOT NULL (feed-source observation always resolves)"
        )

    news_columns = {c["name"]: c for c in inspector.get_columns("fact_news_article")}
    assert news_columns["incident_key"]["nullable"] is True
    assert "country_key" not in news_columns


def test_given_galaxy_when_inspected_then_fact_incident_has_search_keys_and_ai_digest_date(
    inspector,
):
    columns = {c["name"]: c for c in inspector.get_columns("fact_incident")}

    assert "search_keys" in columns, "fact_incident must persist AI search_keys"
    assert columns["ai_digest_date_key"]["nullable"] is True, (
        "ai_digest_date_key must be nullable (incident may not have been digested yet)"
    )

    date_fk_columns = _fk_columns_to(inspector, "fact_incident", "dim_date")
    assert "ai_digest_date_key" in date_fk_columns
