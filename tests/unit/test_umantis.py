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


def test_detail_repair_uses_observed_title_link_and_preserves_input():
    from phd_searcher.pipeline.umantis import repair_umantis_detail_urls
    item = {"title": "Guest Researcher", "url": "/Vacancies/490/Application/CheckLogin/2"}
    html = '<a href="/Vacancies/490/Description/2">Guest Researcher</a>'
    result = repair_umantis_detail_urls([item], html, URL)
    assert result[0]["url"] == "https://recruitingapp-5034.de.umantis.com/Vacancies/490/Description/2"
    assert item["url"] == "/Vacancies/490/Application/CheckLogin/2"


@pytest.mark.parametrize("html", [
    '<a href="/Vacancies/491/Description/2">Guest Researcher</a>',
    '<a href="/Vacancies/490/Description/1">Guest Researcher</a>',
    '<a href="/Vacancies/490/Description/2">Another post</a>',
    '<a href="https://other.example/Vacancies/490/Description/2">Guest Researcher</a>',
    '<p>No detail link</p>',
])
def test_detail_repair_abstains_on_identity_or_language_mismatch(html):
    from phd_searcher.pipeline.umantis import repair_umantis_detail_urls
    items = [{"title": "Guest Researcher", "url": "/Vacancies/490/Application/CheckLogin/2"}]
    assert repair_umantis_detail_urls(items, html, URL) == items


def test_detail_repair_preserves_existing_detail_and_unrelated_sources():
    from phd_searcher.pipeline.umantis import repair_umantis_detail_urls
    html = '<a href="/Vacancies/490/Description/2">Guest Researcher</a>'
    items = [{"title": "Guest Researcher", "url": "/Vacancies/490/Description/2"}]
    assert repair_umantis_detail_urls(items, html, URL) == items
    assert repair_umantis_detail_urls(items, html, "https://other.example/jobs") is items


def test_detail_cleaner_retains_offer_and_application_sections_together():
    from phd_searcher.pipeline.enrich import _clean_detail_document
    url = "https://recruitingapp-5034.de.umantis.com/Vacancies/490/Description/2"
    offer = "Visiting researchers are self-funded. " * 15
    contact = "Please submit your application electronically. " * 25
    html = ('<div class="container"><div class="header">Unrelated header</div>'
            '<div class="content">Guest researcher programme</div>'
            f'<div class="content">Our Offer {offer}</div>'
            f'<div class="content">Contact {contact}</div></div><footer>Other jobs</footer>')
    text = _clean_detail_document(html, "fallback", expected_url=url)
    assert "Our Offer" in text
    assert "self-funded" in text
    assert "Contact" in text
    assert "Other jobs" not in text
    assert "Unrelated header" not in text


@pytest.mark.parametrize("url", [None, "https://other.example/Vacancies/490/Description/2", URL])
def test_detail_sections_are_scoped_to_recognized_detail_url(url):
    from phd_searcher.pipeline.umantis import umantis_detail_content
    assert umantis_detail_content('<div class="container"><div class="content">A</div><div class="content">B</div></div>', url) is None


def test_multiple_vacancy_containers_are_not_combined():
    from phd_searcher.pipeline.umantis import umantis_detail_content
    html = '<div class="container"><div class="content">A</div><div class="content">B</div></div>'
    url = "https://recruitingapp-5034.de.umantis.com/Vacancies/490/Description/2"
    assert umantis_detail_content(html + html, url) is None
