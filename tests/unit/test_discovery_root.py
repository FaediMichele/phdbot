from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from phd_searcher.pipeline.discovery import DiscoverySourceUnavailableError, _crawl_institution_root, _root_identity


def response(status, html, url=None):
    return SimpleNamespace(status_code=status, redirected_status_code=None, html=html,
                           success=status < 400, redirected_url=url, error_message="HTTP failure")


async def test_obsolete_registry_subpath_recovers_only_identity_verified_root():
    crawler = SimpleNamespace(arun=AsyncMock(side_effect=[
        response(404, '<h1>Page not found</h1>'),
        response(200, '<title>Homepage | Example Foundation</title>', 'https://example.org/'),
    ]))
    _, root = await _crawl_institution_root(crawler, None, 'http://example.org/en/about/', 'Example Foundation')
    assert root == 'https://example.org/'
    assert crawler.arun.await_count == 2


@pytest.mark.parametrize(('html', 'target'), [
    ('<title>Parent University</title><p>Partner: Example Foundation</p>', 'https://example.org/'),
    ('<title>Example Foundation</title>', 'https://other.org/'),
])
async def test_parent_or_foreign_homepage_does_not_take_over_subpath_identity(html, target):
    crawler = SimpleNamespace(arun=AsyncMock(side_effect=[response(404, ''), response(200, html, target)]))
    with pytest.raises(DiscoverySourceUnavailableError, match='unavailable'):
        await _crawl_institution_root(crawler, None, 'https://example.org/lab/', 'Example Foundation')


@pytest.mark.parametrize('status', [401, 403])
async def test_access_denial_never_tries_alternative_path(status):
    crawler = SimpleNamespace(arun=AsyncMock(return_value=response(status, 'Access denied')))
    with pytest.raises(DiscoverySourceUnavailableError, match=f'HTTP {status}'):
        await _crawl_institution_root(crawler, None, 'https://example.org/lab/', 'Example Foundation')
    assert crawler.arun.await_count == 1


async def test_transient_server_failure_remains_retryable_without_root_fallback():
    crawler = SimpleNamespace(arun=AsyncMock(return_value=response(503, 'Temporary failure')))
    with pytest.raises(RuntimeError, match='HTTP failure') as error:
        await _crawl_institution_root(crawler, None, 'https://example.org/lab/', 'Example Foundation')
    assert not isinstance(error.value, DiscoverySourceUnavailableError)
    assert crawler.arun.await_count == 1


def test_root_identity_requires_full_title_segment_or_heading_not_body_mention():
    assert _root_identity('<h1>Example Foundation</h1>', 'Example Foundation')
    assert not _root_identity('<title>Examples</title><p>Example Foundation</p>', 'Example Foundation')
    assert not _root_identity('<title>Example Foundation partners</title>', 'Example Foundation')
