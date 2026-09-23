from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from phd_searcher.database.models.scheduled_job import ScheduledJob
from phd_searcher.database.models.university import University
from phd_searcher.service.expansion_service import REGISTRY_BASIS, ExpansionService, _candidate_statement, _pipeline
from phd_searcher.service.schedule_service import ScheduleService
from phd_searcher.typedef.expansion import ExpansionCreate


def test_expansion_requires_distinct_bounded_ids_and_source_budgets():
    for identifiers in ([], [0], [1, 1], list(range(1, 12))):
        with pytest.raises(ValidationError):
            ExpansionCreate(institution_ids=identifiers)
    with pytest.raises(ValidationError):
        ExpansionCreate(institution_ids=[1], max_pages=6)


def test_candidate_selection_balances_countries_without_reactivating_known_sources():
    sql = str(_candidate_statement("it", "100% Lab", 5).compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    assert "row_number() OVER (PARTITION BY universities.country" in sql
    assert "discovery_status = 'catalogued'" in sql
    assert "NOT (EXISTS" in sql
    assert "ESCAPE '/'" in sql
    assert "LIMIT 5" in sql


def test_expansion_publishes_each_institution_without_optional_review():
    body = _pipeline("One institute", ExpansionCreate(institution_ids=[1], max_sources=2))
    assert body.stages == ["discovery", "schema", "scrape", "quality", "index"]
    assert body.name == "One institute"
    assert body.limits.discovery == 1
    assert body.limits.schema_items == body.limits.scrape == body.limits.quality == 2
    assert body.limits.index == 150
    assert body.max_pages == 3


def setup_service(uni, *, previous=None, matches=None, source=None):
    session = AsyncMock()
    institutions = MagicMock()
    institutions.all.return_value = [uni]
    matching = MagicMock()
    matching.all.return_value = [uni.id] if matches is None else matches
    session.scalars.side_effect = [institutions, matching]
    session.scalar.side_effect = [previous, source]
    created = []

    def add(job):
        job.id = 50
        job.created_at = datetime(2026, 9, 22)
        created.append(job)

    session.add = MagicMock(side_effect=add)
    manager = MagicMock()
    manager.return_value.__aenter__ = AsyncMock(return_value=session)
    manager.return_value.__aexit__ = AsyncMock(return_value=False)
    return ExpansionService(manager), session, created


def institution(**kwargs):
    return University(id=1, name="Independent research institute", country="IT",
                      catalog_basis=REGISTRY_BASIS, discovery_status="catalogued", **kwargs)


async def test_activation_and_schedule_are_committed_together():
    uni = institution()
    service, session, created = setup_service(uni)
    response = await service.enqueue(ExpansionCreate(institution_ids=[1]))
    assert uni.discovery_status == "pending"
    assert created[0].payload["expansion_institution_id"] == 1
    assert response.schedules[0].id == 50
    session.commit.assert_awaited_once()


async def test_duplicate_request_returns_original_schedule_even_when_done():
    uni = institution()
    uni.discovery_status = "done"
    job = ScheduledJob(id=49, target="pipeline", state="done", run_at=datetime(2026, 9, 22),
                       payload={"name": uni.name}, created_at=datetime(2026, 9, 22), attempts=1)
    service, _session, created = setup_service(uni, previous=job)
    response = await service.enqueue(ExpansionCreate(institution_ids=[1]))
    assert response.schedules[0].id == 49
    assert not created
    assert uni.discovery_status == "done"


@pytest.mark.parametrize("issue", ["wildcard", "ambiguous", "existing_source", "already_done", "outside_scope"])
async def test_unsafe_or_redundant_activation_is_rejected_without_commit(issue):
    uni = institution()
    if issue == "wildcard":
        uni.name = "Lab_%"
    if issue == "already_done":
        uni.discovery_status = "done"
    if issue == "outside_scope":
        uni.country = "US"
    service, session, created = setup_service(uni, matches=[1, 2] if issue == "ambiguous" else None,
                                             source=10 if issue == "existing_source" else None)
    with pytest.raises(ValueError, match=r"scope|scoping|ambiguous|already|sources"):
        await service.enqueue(ExpansionCreate(institution_ids=[1]))
    assert not created
    session.commit.assert_not_awaited()


async def test_preview_rejects_unrequested_world_expansion():
    service = ExpansionService(MagicMock())
    with pytest.raises(ValueError, match="European"):
        await service.preview(country="US")


async def test_scheduler_holds_scope_that_became_ambiguous_while_waiting():
    session = AsyncMock()
    session.get.return_value = ScheduledJob(id=50, state="starting", target="pipeline", payload={
        "name": "Institute", "expansion_institution_id": 1,
    })
    matches = MagicMock()
    matches.all.return_value = [1, 2]
    session.scalars.return_value = matches
    maker = MagicMock()
    maker.return_value.__aenter__ = AsyncMock(return_value=session)
    maker.return_value.__aexit__ = AsyncMock(return_value=False)
    pipeline = AsyncMock()
    scheduler = ScheduleService(maker, pipeline, MagicMock())
    scheduler._fail = AsyncMock()
    await scheduler._dispatch(50)
    scheduler._fail.assert_awaited_once_with(50, "catalog expansion scope changed; inspect institution before retry")
    pipeline.ensure_scheduled.assert_not_awaited()
