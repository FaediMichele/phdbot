from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from phd_searcher.config.search import SearchConfig
from phd_searcher.engine import search_helper
from phd_searcher.pipeline import discovery


def _xml(kind, urls):
    entry = "sitemap" if kind == "sitemapindex" else "url"
    return (
        f'<{kind} xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<{entry}><loc>{url}</loc></{entry}>" for url in urls)
        + f"</{kind}>"
    )


def _responses(monkeypatch, responses):
    original = httpx.AsyncClient
    requested = []

    def respond(request):
        url = str(request.url)
        requested.append(url)
        value = responses.get(url, (404, "missing"))
        if isinstance(value, Exception):
            raise value
        return httpx.Response(value[0], text=value[1], headers=value[2] if len(value) > 2 else {})

    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        return original(**kwargs, transport=httpx.MockTransport(respond))

    monkeypatch.setattr(discovery.httpx, "AsyncClient", client)
    return requested


async def test_index_reaches_department_jobs_without_curated_source(monkeypatch):
    requested = _responses(
        monkeypatch,
        {
            "https://www.example.edu/sitemap.xml": (
                200,
                _xml("sitemapindex", ["https://www.example.edu/page-sitemap.xml"]),
            ),
            "https://www.example.edu/page-sitemap.xml": (
                200,
                _xml(
                    "urlset",
                    [
                        "https://lab.example.edu/jobs/",
                        "https://www.example.edu/events/",
                        "https://other.edu/jobs/",
                        "https://www.example.edu/phd/document.pdf",
                    ],
                ),
            ),
        },
    )
    candidates = await discovery._sitemap_candidates("https://www.example.edu/en/")
    assert [c.href for c in candidates] == ["https://lab.example.edu/jobs/"]
    assert len(requested) == 2


async def test_nested_indexes_are_bounded_deduplicated_and_same_site(monkeypatch):
    root = "https://example.edu/sitemap.xml"
    children = [f"https://example.edu/jobs-{n}.xml" for n in range(10)]
    requested = _responses(
        monkeypatch,
        {
            root: (200, _xml("sitemapindex", ["https://evil.example/jobs.xml", root, *children])),
            **{child: (200, _xml("sitemapindex", [root, *children])) for child in children},
        },
    )
    assert await discovery._sitemap_candidates("https://example.edu/") == []
    assert len(requested) == 4
    assert len(set(requested)) == 4
    assert not any("evil.example" in url for url in requested)


async def test_broken_child_does_not_discard_other_sitemap_candidates(monkeypatch):
    _responses(
        monkeypatch,
        {
            "https://example.edu/sitemap.xml": (
                200,
                _xml("sitemapindex", ["https://example.edu/first.xml", "https://example.edu/second.xml"]),
            ),
            "https://example.edu/first.xml": (200, "not XML"),
            "https://example.edu/second.xml": (200, _xml("urlset", ["https://example.edu/doctoral/openings"])),
        },
    )
    assert len(await discovery._sitemap_candidates("https://example.edu/")) == 1


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (403, "Access denied"),
        (302, "redirect"),
        (200, '<!DOCTYPE urlset [<!ENTITY a "expanded">]><urlset/>'),
        (200, "x" * 101),
    ],
)
async def test_redirect_denial_doctype_and_size_limit_are_not_bypassed(monkeypatch, status, body):
    monkeypatch.setattr(discovery, "_MAX_SITEMAP_BYTES", 100)
    requested = _responses(monkeypatch, {"https://example.edu/sitemap.xml": (status, body)})
    assert await discovery._sitemap_candidates("https://example.edu/") == []
    assert len(requested) == 1


@pytest.mark.parametrize(
    "url", ["https://evil.example/jobs.xml", "file:///jobs.xml", "https://user:pass@example.edu/jobs.xml"]
)
def test_sitemap_urls_need_official_host_and_no_credentials(url):
    assert not discovery._public_sitemap_url(url, "https://example.edu/")


async def test_search_includes_sibling_job_subdomains(monkeypatch):
    queries = []

    async def brave(query, maximum, api_key):
        queries.append((query, maximum))
        return ["https://jobs.example.edu/vacancies/"]

    monkeypatch.setattr(search_helper, "_brave_search", brave)
    assert await search_helper.search_listing_candidates(
        SearchConfig(provider="brave", api_key="test"), "www.example.edu"
    ) == ["https://jobs.example.edu/vacancies/"]
    assert queries[0][0].startswith("site:example.edu ")
    assert queries[0][1] == 10


def test_plain_jobs_and_careers_labels_are_not_lost_before_selection():
    links = [
        {"href": "https://example.edu/openings", "text": "Jobs"},
        {"href": "https://example.edu/work", "text": "Careers"},
        {"href": "https://example.edu/?page_id=3435", "text": "Job Opportunities"},
        {"href": "https://example.edu/membres-fondateurs/", "text": "Nous rejoindre"},
    ]
    assert len(discovery._candidates(links)) == len(links)


def test_share_actions_do_not_consume_jobs_candidates_or_hub_budget():
    share = [
        "http://www.facebook.com/sharer.php?u=https://institute.example/jobs",
        "https://www.linkedin.com/sharing/share-offsite/?url=https://institute.example/jobs",
        "https://reddit.com/submit?url=https://institute.example/jobs",
        "https://twitter.com/intent/tweet?url=https://institute.example/jobs",
        "https://www.xing.com/spi/shares/new?url=https://institute.example/jobs",
        "mailto:?body=https://institute.example/jobs",
        "whatsapp://send?text=https://institute.example/jobs",
    ]
    pages = ["https://employer.ats.example/jobs?department=research",
             "https://www.linkedin.com/jobs/view/123", "https://institute.example/?page_id=123"]
    links = [{"href": url, "text": "Jobs"} for url in [*share, *pages]]
    assert [c.href for c in discovery._candidates(links)] == pages
    assert set(discovery._hub_links(links)) == set(pages)


def test_recruitment_is_not_crowded_out_by_short_research_hubs():
    links = [{"href": f"https://example.edu/research/{n}", "text": "Research"} for n in range(6)]
    jobs = "https://example.edu/about-us/work-with-us/jobs-and-careers"
    links.append({"href": jobs, "text": "Jobs"})
    assert discovery._hub_links(links)[0] == jobs
    assert len(discovery._hub_links(links)) == 4


async def test_jobs_subsection_and_external_board_share_four_fetch_budget(monkeypatch):
    root = "https://example.edu/"
    career = root + "careers"
    jobs = root + "careers/jobs"
    external = "https://employer.ats.example/jobs"
    vacancy = external + "/phd-123"
    responses = {
        career: [{"href": jobs, "text": "Vacancies"}],
        jobs: [{"href": external, "text": "Jobs portal"}],
        external: [{"href": vacancy, "text": "PhD position"}],
    }
    requested = []

    async def fetch(url, **kwargs):
        requested.append(url)
        return SimpleNamespace(success=True, redirected_url=None, links={"internal": responses.get(url, [])})

    monkeypatch.setattr(discovery, "_sitemap_candidates", AsyncMock(return_value=[]))
    crawler = SimpleNamespace(arun=fetch)
    candidates = await discovery._collect_candidates(crawler, None, root, [{"href": career, "text": "Careers"}])
    assert requested[:3] == [career, jobs, external]
    assert len(requested) <= 4
    assert any(c.href == vacancy and c.referrer == external for c in candidates)


async def test_sitemap_and_jobs_hub_overlap_without_losing_candidates(monkeypatch):
    import asyncio

    root = "https://example.edu/"
    both_started = asyncio.Event()
    started = set()

    async def wait_for_other(kind):
        started.add(kind)
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=1)

    async def sitemap(url):
        await wait_for_other("sitemap")
        return [discovery._Link(root + "doctoral", "Doctoral")]

    async def hub(url, **kwargs):
        await wait_for_other("hub")
        return SimpleNamespace(success=True, redirected_url=None, links={"internal": [
            {"href": root + "careers/jobs", "text": "Jobs"},
        ]})

    monkeypatch.setattr(discovery, "_sitemap_candidates", sitemap)
    result = await discovery._collect_candidates(SimpleNamespace(arun=hub), None, root, [
        {"href": root + "careers", "text": "Careers"},
    ])
    assert both_started.is_set()
    assert {c.href for c in result} >= {root + "careers", root + "doctoral", root + "careers/jobs"}


async def test_failed_optional_hub_preserves_other_candidates(monkeypatch):
    root = "https://example.edu/"
    calls = []

    async def fetch(url, **kwargs):
        calls.append(url)
        if url.endswith("jobs"):
            raise RuntimeError("temporarily unavailable")
        return SimpleNamespace(success=True, redirected_url=None, links={"external": [
            {"href": "https://ats.example/phd", "text": "Doctoral positions"},
        ]})

    monkeypatch.setattr(discovery, "_sitemap_candidates", AsyncMock(return_value=[]))
    result = await discovery._collect_candidates(SimpleNamespace(arun=fetch), None, root, [
        {"href": root + "jobs", "text": "Jobs"}, {"href": root + "research", "text": "Research"},
    ])
    assert len(calls) == 2
    assert any(c.href == "https://ats.example/phd" for c in result)


@pytest.mark.parametrize(("destination", "count"), [("/wp-sitemap.xml", 1), ("https://evil.example/map.xml", 0)])
async def test_canonical_sitemap_redirect_is_bounded_and_stays_official(monkeypatch, destination, count):
    requested = _responses(
        monkeypatch,
        {
            "https://example.edu/sitemap.xml": (301, "", {"Location": destination}),
            "https://example.edu/wp-sitemap.xml": (200, _xml("urlset", ["https://example.edu/phd/projects"])),
        },
    )
    assert len(await discovery._sitemap_candidates("https://example.edu/")) == count
    assert len(requested) == count + 1


def test_admissions_hub_is_explored_for_departmental_studentships():
    assert discovery._hub_links([{"href": "https://example.edu/admissions/", "text": "Admissions"}]) == [
        "https://example.edu/admissions/"
    ]


def test_admissions_project_list_is_a_candidate_but_arbitrary_projects_are_not():
    links = [
        {"href": "https://example.edu/admissions/specific-projects/", "text": "Specific projects"},
        {"href": "https://example.edu/undergraduate/course-projects/", "text": "Past projects"},
    ]
    assert [c.href for c in discovery._candidates(links)] == [links[0]["href"]]


async def test_foundation_scholarship_hub_reaches_linked_application_board(monkeypatch):
    root = "https://foundation.example/"
    hub = root + "scholarships/"
    board = "https://funding.example/apply/phd-scholarships"
    crawler = SimpleNamespace(arun=AsyncMock(return_value=SimpleNamespace(
        success=True, redirected_url=None,
        links={"external": [{"href": board, "text": "Doctoral applications"}]},
    )))
    monkeypatch.setattr(discovery, "_sitemap_candidates", AsyncMock(return_value=[]))
    candidates = await discovery._collect_candidates(
        crawler, None, root, [{"href": hub, "text": "Scholarships Available"}],
    )
    assert any(c.href == board and c.referrer == hub for c in candidates)
    assert crawler.arun.await_count <= 4
