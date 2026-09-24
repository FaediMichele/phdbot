from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from phd_searcher.pipeline.umantis import verified_umantis_link

URL = 'https://recruitingapp-5034.de.umantis.com/Jobs/2?lang=eng'
REF = 'https://institute.example/123/career'


def crawler(html, *, url=REF, status=200, success=True):
    return SimpleNamespace(arun=AsyncMock(return_value=SimpleNamespace(
        html=html, redirected_url=url, status_code=status, redirected_status_code=None, success=success,
    )))


async def test_current_official_board_link_is_ownership_evidence():
    client = crawler(f'<a href="{URL}">Vacancies</a>')
    assert await verified_umantis_link(client, None, REF, 'https://institute.example/en', URL)
    client.arun.assert_awaited_once()


@pytest.mark.parametrize('html', [
    '<main>Link removed</main>',
    f'<a href="{URL.replace("5034", "9999")}">Vacancies</a>',
    f'<a href="{URL.replace("lang=eng", "lang=ger")}">Vacancies</a>',
    f'<a href="{URL}">Funding partners</a>',
])
async def test_stale_or_different_scope_does_not_verify(html):
    assert not await verified_umantis_link(crawler(html), None, REF, 'https://institute.example', URL)


@pytest.mark.parametrize(('final', 'status'), [
    ('https://other.example/career', 200),
    ('https://institute.example/about', 200),
    (REF, 403),
    (REF, 404),
])
async def test_redirect_or_denial_does_not_authorize(final, status):
    assert not await verified_umantis_link(
        crawler(f'<a href="{URL}">Jobs</a>', url=final, status=status), None, REF,
        'https://institute.example', URL,
    )


@pytest.mark.parametrize('ref', [None, '', 'https://partner.example/career', 'https://institute.example/about'])
async def test_untrusted_provenance_does_not_fetch(ref):
    client = crawler('')
    assert not await verified_umantis_link(client, None, ref, 'https://institute.example', URL)
    client.arun.assert_not_called()
