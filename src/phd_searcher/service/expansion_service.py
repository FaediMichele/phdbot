"""Activate small registry cohorts and publish one institution per durable job.

No registry reimport, new crawler, bulk review, or background recurring expansion.
Existing schedule locking/recovery serializes runs and preserves failures for repair.
"""

from datetime import timedelta

from injector import inject
from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from phd_searcher.database.models.listing_page import ListingPage
from phd_searcher.database.models.position import Position
from phd_searcher.database.models.scheduled_job import ScheduledJob
from phd_searcher.database.models.university import University
from phd_searcher.pipeline.registry_catalog import EUROPE
from phd_searcher.service.schedule_service import ScheduleService, _utcnow
from phd_searcher.typedef.expansion import ExpansionCandidate, ExpansionCreate, ExpansionPreview, ExpansionQueued
from phd_searcher.typedef.pipeline import PipelineLimits, PipelineStartBody

REGISTRY_BASIS = "ror:active-research-registry"


def _candidate_statement(country: str | None, query: str | None, limit: int) -> Select[tuple[University]]:
    # Round-robin countries, with a stable registry-ID hash within each country.
    # This is an exploration order, not an estimated probability of hiring.
    has_source = select(ListingPage.id).where(ListingPage.university_id == University.id).exists()
    stmt = select(
        University.id,
        func.row_number().over(
            partition_by=University.country,
            order_by=func.md5(University.ror_id),
        ).label("country_rank"),
    ).where(
        University.catalog_basis == REGISTRY_BASIS,
        University.catalog_tier == "research",
        University.discovery_status == "catalogued",
        University.country.in_(EUROPE),
        ~has_source,
    )
    if country:
        stmt = stmt.where(University.country == country.upper())
    if query:
        stmt = stmt.where(University.name.icontains(query, autoescape=True))
    ranked = stmt.subquery()
    return (
        select(University).join(ranked, University.id == ranked.c.id)
        .order_by(ranked.c.country_rank, University.country, University.id).limit(limit)
    )


def _pipeline(name: str, request: ExpansionCreate) -> PipelineStartBody:
    return PipelineStartBody(
        stages=["discovery", "schema", "scrape", "quality", "index"],
        name=name,
        limits=PipelineLimits(discovery=1, schema_items=request.max_sources,
                              scrape=request.max_sources, quality=request.max_sources, index=150),
        max_pages=request.max_pages,
    )


@inject
class ExpansionService:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def preview(self, *, country: str | None = None, query: str | None = None,
                      limit: int = 5) -> ExpansionPreview:
        if country and country.upper() not in EUROPE:
            raise ValueError("country must be within the configured European scope")
        sources = select(ListingPage.university_id).group_by(ListingPage.university_id).subquery()
        positions = select(
            Position.university_id,
            func.count().filter(Position.indexed_at.is_not(None)).label("indexed"),
        ).group_by(Position.university_id).subquery()
        async with self._session_maker() as session:
            counts = (await session.execute(select(
                func.count(),
                func.count().filter(University.discovery_status == "catalogued"),
                func.count().filter(sources.c.university_id.is_not(None)),
                func.count().filter(positions.c.university_id.is_not(None)),
                func.count().filter(positions.c.indexed > 0),
            ).select_from(University)
                .outerjoin(sources, sources.c.university_id == University.id)
                .outerjoin(positions, positions.c.university_id == University.id)
                .where(University.catalog_basis == REGISTRY_BASIS))).one()
            candidates = (await session.scalars(_candidate_statement(country, query, limit))).all()
            return ExpansionPreview(
                total=counts[0], catalog_only=counts[1], with_sources=counts[2],
                with_positions=counts[3], with_indexed_markers=counts[4],
                candidates=[ExpansionCandidate(id=u.id, name=u.name, country=u.country,
                                               website_url=u.website_url, catalog_tier=u.catalog_tier)
                            for u in candidates],
            )

    async def enqueue(self, request: ExpansionCreate) -> ExpansionQueued:
        async with self._session_maker() as session:
            # One transaction for activation + queue. Same ordered row locks make
            # repeated/concurrent requests return the existing job, not a second run.
            await session.execute(text("SET LOCAL lock_timeout = '5s'"))
            institutions = (await session.scalars(
                select(University).where(University.id.in_(request.institution_ids))
                .order_by(University.id).with_for_update()
            )).all()
            if len(institutions) != len(request.institution_ids):
                raise ValueError("one or more institutions no longer exist; refresh the preview")
            jobs: list[ScheduledJob] = []
            for uni in institutions:
                previous = await session.scalar(
                    select(ScheduledJob).where(
                        ScheduledJob.target == "pipeline",
                        ScheduledJob.payload["expansion_institution_id"].as_integer() == uni.id,
                    ).order_by(ScheduledJob.id.desc()).limit(1)
                )
                if previous is not None and previous.state != "cancelled":
                    jobs.append(previous)
                    continue
                if uni.catalog_basis != REGISTRY_BASIS or uni.country not in EUROPE:
                    raise ValueError("only imported institutions in the European scope can be activated")
                allowed = {"catalogued", "pending"} if previous is not None else {"catalogued"}
                if uni.discovery_status not in allowed:
                    raise ValueError(f"{uni.name}: already processed; inspect its existing run/sources")
                # Existing pipeline scope is ILIKE. Refuse ambiguous names and SQL
                # wildcards instead of accidentally collecting another institution.
                if any(character in uni.name for character in ("%", "_", "\\")):
                    raise ValueError(f"{uni.name}: name requires explicit ID scoping")
                matches = (await session.scalars(
                    select(University.id).where(University.name.ilike(f"%{uni.name}%")),
                )).all()
                if list(matches) != [uni.id]:
                    raise ValueError(f"{uni.name}: ambiguous pipeline name scope")
                existing_source = await session.scalar(
                    select(ListingPage.id).where(ListingPage.university_id == uni.id).limit(1),
                )
                if existing_source is not None:
                    raise ValueError(f"{uni.name}: sources already exist; use a scoped collection run")
                body = _pipeline(uni.name, request)
                payload = body.model_dump(mode="json", by_alias=True, exclude_none=True)
                payload["expansion_institution_id"] = uni.id
                job = ScheduledJob(target="pipeline", state="scheduled", run_at=_utcnow() + timedelta(seconds=10),
                                   timezone="Europe/Rome", payload=payload, attempts=0)
                uni.discovery_status = "pending"
                session.add(job)
                jobs.append(job)
            await session.flush()
            views = [ScheduleService._view(job) for job in jobs]
            await session.commit()
            return ExpansionQueued(schedules=views)
