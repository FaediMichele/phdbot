from types import SimpleNamespace

import pytest

from phd_searcher.pipeline.bite import _matching_response, bite_items, bite_listing, fetch_bite_page
from phd_searcher.pipeline.source_adapters import source_adapter_name

LOADER = '<script src="https://static.b-ite.com/jobs-api/loader-v1/api-loader-v1.min.js"></script>'
WIDGET = '<div data-bite-jobs-api-listing="research-institute:main-listing-en"></div>'
URL = 'https://jobs.example.org/jobposting/abcdef1230'


def payload(**changes):
    job = {'title': 'Research group leader', 'url': URL, 'locale': 'en',
           'endsOn': '2026-10-19T21:59:00+00:00', 'startsOn': '2026-08-27',
           'keywords': ['PhD', 'student'], 'applyUrl': URL + '/apply'}
    job.update(changes)
    return {'jobPostings': [job], 'page': {'total': 1, 'offset': 0}}


def test_recognizes_single_official_embed_only():
    assert bite_listing(LOADER + WIDGET) == 'research-institute:main-listing-en'
    for html in [WIDGET, LOADER, LOADER + WIDGET * 2, (LOADER + WIDGET).replace(':main-listing-en', ':../other')]:
        assert bite_listing(html) is None
    assert source_adapter_name({'adapter': 'bite'}) == 'bite'


def test_display_windows_and_keywords_do_not_become_application_facts():
    assert bite_items(payload()) == [{'title': 'Research group leader', 'url': URL, 'language': 'en'}]


def test_confirmed_empty_is_valid():
    assert bite_items({'jobPostings': [], 'page': {'offset': 0, 'total': 0}}) == []
    assert bite_items({'fields': [], 'page': {'offset': 0, 'total': 0}}) == []
    with pytest.raises(RuntimeError):
        bite_items({'fields': [], 'page': {'offset': 0, 'total': 1}})


@pytest.mark.parametrize('page', [{'offset': 0, 'total': 2}, {'offset': 1, 'total': 1},
                                  {'offset': 0, 'total': True}, {'total': 1}, {'offset': 0, 'total': -1}])
def test_incomplete_pages_are_failures_not_empty_boards(page):
    data = payload()
    data['page'] = page
    with pytest.raises(RuntimeError):
        bite_items(data)


@pytest.mark.parametrize('changes', [{'title': ''}, {'url': URL + '/apply'}, {'url': 'javascript:foo'},
                                     {'url': URL.replace('https:', 'http:')}, {'url': URL + '#apply'},
                                     {'url': URL.replace('jobs.example.org', 'user@jobs.example.org')}])
def test_rejects_invalid_details(changes):
    with pytest.raises(RuntimeError):
        bite_items(payload(**changes))


def test_duplicates_are_contract_failure():
    data = payload()
    data['jobPostings'] *= 2
    data['page']['total'] = 2
    with pytest.raises(RuntimeError):
        bite_items(data)


def test_network_response_must_belong_to_exact_official_page():
    source = 'https://institute.example.org/jobs?area=research'
    req = SimpleNamespace(method='POST', post_data_json={'origin': source}, frame=SimpleNamespace(url=source))
    response = SimpleNamespace(url='https://jobs.b-ite.com/api/v1/postings/search', request=req)
    assert _matching_response(response, source)
    assert not _matching_response(response, source.split('?')[0])
    req.frame.url = 'https://other.example.org/jobs'
    assert not _matching_response(response, source)


@pytest.mark.asyncio
async def test_no_extra_browser_page_after_complete_feed():
    assert await fetch_bite_page('https://institute.example.org/jobs', 'institute:main', 1) == []
    with pytest.raises(RuntimeError):
        await fetch_bite_page('https://institute.example.org/jobs', '../bad', 0)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [None, 'marker', 'script', 'redirect', 'denied', 'partial', 'timeout'])
async def test_browser_revalidates_live_widget_and_never_turns_failure_into_empty(monkeypatch, failure):
    import asyncio

    from phd_searcher.pipeline import bite

    source = 'https://institute.example.org/jobs?area=research'
    marker = 'research-institute:main-listing-en'
    script = '<script src="https://cs-assets.b-ite.com/research-institute/jobs-api/main-listing-en.min.js"></script>'
    closed = []
    data = payload()
    if failure == 'partial':
        data['page']['total'] = 2

    class Response:
        url = bite._API
        request = SimpleNamespace(method='POST', post_data_json={'origin': source}, frame=SimpleNamespace(url=source))
        status = 403 if failure == 'denied' else 200

        async def json(self):
            return data

    class Pending:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        @property
        async def value(self):
            if failure == 'timeout':
                raise TimeoutError('no public API response')
            return Response()

    class Page:
        url = 'https://other.example.org/jobs' if failure == 'redirect' else source

        def expect_response(self, predicate, **kwargs):
            assert predicate(Response())
            return Pending()

        async def goto(self, url, **kwargs):
            assert url == source  # Preserve all publisher filters.
            return SimpleNamespace(status=200)

        async def content(self):
            html = LOADER + WIDGET + script
            if failure == 'marker':
                return html.replace('main-listing-en', 'main-listing-de')
            if failure == 'script':
                return LOADER + WIDGET
            return html

    class Browser:
        async def new_page(self):
            return Page()

        async def close(self):
            closed.append(True)

    class Driver:
        chromium = None

        async def __aenter__(self):
            self.chromium = self
            return self

        async def __aexit__(self, *args):
            pass

        async def launch(self, **kwargs):
            return Browser()

    monkeypatch.setattr(bite, 'async_playwright', Driver)
    if failure:
        with pytest.raises((RuntimeError, asyncio.TimeoutError)):
            await fetch_bite_page(source, marker, 0)
    else:
        assert (await fetch_bite_page(source, marker, 0))[0]['url'] == URL
    assert closed == [True]
