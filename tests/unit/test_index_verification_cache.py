from datetime import date, timedelta

import pytest

from phd_searcher.database.models.listing_page import ListingPage
from phd_searcher.database.models.position import Position
from phd_searcher.pipeline.index import _verification_metadata, _VerificationCache

TODAY = date(2026, 10, 4)


def sample(position_id: int = 1) -> tuple[Position, ListingPage]:
    return Position(
        id=position_id, listing_page_id=1, title="PhD researcher in physics",
        url=f"https://example.org/jobs/{position_id}", description="Funded PhD position",
        position_type="phd", opportunity_kind="unknown", screening_status="pending",
        is_active=True, deadline=TODAY,
    ), ListingPage(id=1, url="https://example.org/jobs", quality_status="healthy")


def test_reuses_equal_reloaded_records_and_rechecks_after_midnight():
    cache = _VerificationCache()
    position, source = sample()
    expected = _verification_metadata(position, TODAY, listing_page=source)
    assert expected is not None
    assert cache.assess(position, TODAY, listing_page=source) == expected
    reloaded, reloaded_source = sample()
    assert cache.assess(reloaded, TODAY, listing_page=reloaded_source) == expected
    assert (cache.hits, cache.misses) == (1, 1)
    assert cache.assess(reloaded, TODAY + timedelta(days=1), listing_page=reloaded_source) is None
    assert cache.misses == 2
    assert len(cache.entries) == 1


@pytest.mark.parametrize(("field", "value"), [
    ("is_active", False), ("deadline", TODAY - timedelta(days=1)),
    ("screening_status", "rejected"), ("review_state", "source_broken"),
    ("full_description", "Applications are closed. This vacancy has expired."),
    ("routing_reason", "evidence:unsupported_document"),
])
def test_position_changes_never_reuse_an_old_positive(field, value):
    cache = _VerificationCache()
    position, source = sample()
    assert cache.assess(position, TODAY, listing_page=source) is not None
    setattr(position, field, value)
    expected = _verification_metadata(position, TODAY, listing_page=source)
    assert expected is None
    assert cache.assess(position, TODAY, listing_page=source) == expected
    assert cache.misses == 2


def test_source_health_and_repaired_negative_are_rechecked():
    cache = _VerificationCache()
    position, source = sample()
    assert cache.assess(position, TODAY, listing_page=source) is not None
    source.quality_status = "quarantine"
    assert cache.assess(position, TODAY, listing_page=source) is None
    source.quality_status = "healthy"
    source.quality_reason = "repaired extraction"
    assert cache.assess(position, TODAY, listing_page=source) is not None
    assert cache.misses == 3


def test_cache_is_bounded_and_does_not_merge_neighbouring_records():
    cache = _VerificationCache(max_entries=2)
    for position_id in (1, 2, 3, 1):
        position, source = sample(position_id)
        assert cache.assess(position, TODAY, listing_page=source) is not None
    assert len(cache.entries) == 2
    assert cache.hits == 0
    assert cache.misses == 4
