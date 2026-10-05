"""Observe an official embedded BITE board without reconstructing its JS filters.

Only a single complete response is supported. Truncated/paginated widgets fail
explicitly instead of silently importing a partial or broader tenant feed.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from playwright.async_api import Response, async_playwright

_API = "https://jobs.b-ite.com/api/v1/postings/search"
_LOADER = "https://static.b-ite.com/jobs-api/loader-v1/api-loader-v1.min.js"
_MARKER = re.compile(r"[a-z0-9_-]{1,100}:[a-z0-9_-]{1,100}")


def bite_listing(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select("[data-bite-jobs-api-listing]")
    if len(nodes) != 1 or not soup.find("script", src=_LOADER):
        return None
    marker = nodes[0].get("data-bite-jobs-api-listing")
    return marker if isinstance(marker, str) and _MARKER.fullmatch(marker) else None


def _public_url(url: str) -> bool:
    try:
        p = urlsplit(url)
        return bool(p.scheme == "https" and p.hostname and "." in p.hostname
                    and not p.username and not p.password and p.port in {None, 443}
                    and not p.fragment)
    except ValueError:
        return False


def bite_items(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("page"), dict):
        raise RuntimeError("BITE: missing pagination evidence")
    page = payload["page"]
    total = page.get("total")
    # BITE omits jobPostings for an empty, scoped board. Both official
    # language variants were observed returning {"page": {"offset": 0,
    # "total": 0}, "fields": ...} with HTTP 200.
    jobs = [] if total == 0 and "jobPostings" not in payload else payload.get("jobPostings")
    if (not isinstance(jobs, list) or type(total) is not int or total < 0
        or type(page.get("offset")) is not int or page["offset"] != 0
        or len(jobs) != total or total > 1000):
        raise RuntimeError("BITE: incomplete or unsupported pagination")
    items: list[dict[str, object]] = []
    seen: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise RuntimeError("BITE: invalid job row")
        title, url = job.get("title"), job.get("url")
        if (not isinstance(title, str) or not title.strip() or not isinstance(url, str)
            or not _public_url(url) or not re.fullmatch(r"/jobposting/[a-zA-Z0-9-]+/?", urlsplit(url).path)
            or url in seen):
            raise RuntimeError("BITE: missing, invalid or duplicate public detail")
        seen.add(url)
        # endsOn/startsOn are display windows, NOT application/start dates.
        # Keywords can include PhD students supervised by a senior hire.
        items.append({"title": title.strip(), "url": url, "language": job.get("locale") or ""})
    return items


def _matching_response(response: Response, source_url: str) -> bool:
    if response.url != _API or response.request.method != "POST":
        return False
    try:
        request = response.request.post_data_json
        return bool(isinstance(request, dict) and request.get("origin") == source_url
                    and response.request.frame.url == source_url)
    except Exception:
        return False


async def fetch_bite_page(source_url: str, marker: object, page_number: int) -> list[dict[str, object]]:
    if not _public_url(source_url) or not isinstance(marker, str) or not _MARKER.fullmatch(marker) or page_number < 0:
        raise RuntimeError("BITE: invalid admitted board")
    if page_number > 0:
        return []  # Page zero must prove it contains the entire scoped feed.
    async with asyncio.timeout(40), async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = await browser.new_page()
            async with page.expect_response(lambda r: _matching_response(r, source_url), timeout=15000) as pending:
                main = await page.goto(source_url, wait_until="domcontentloaded", timeout=20000)
            response = await pending.value
            if main is None or main.status != 200 or page.url != source_url or response.status != 200:
                raise RuntimeError("BITE: unavailable or redirected official board")
            html = await page.content()
            tenant, listing = marker.split(":")
            soup = BeautifulSoup(html, "html.parser")
            if (bite_listing(html) != marker or not soup.find(
                "script", src=f"https://cs-assets.b-ite.com/{tenant}/jobs-api/{listing}.min.js",
            )):
                raise RuntimeError("BITE: changed or ambiguous official widget")
            return bite_items(await response.json())
        finally:
            await browser.close()
