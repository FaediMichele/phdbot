"""Recognize scoped Umantis HTML boards and revalidate their official links."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from phd_searcher.pipeline.workday import recruitment_referrer


def umantis_board(url: str) -> bool:
    """No search forms, accounts, subscriptions or unscoped tenant roots."""
    try:
        parsed = urlsplit(url)
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        return bool(
            parsed.scheme == "https" and not parsed.username and not parsed.password
            and parsed.port in {None, 443} and not parsed.fragment
            and re.fullmatch(r"recruitingapp-[0-9]+\.de\.umantis\.com", parsed.hostname or "")
            and re.fullmatch(r"/Jobs/[0-9]+/?", parsed.path)
            and set(query) <= {"lang"}
            and (not query or (len(query["lang"]) == 1 and re.fullmatch(r"[a-z]{3}", query["lang"][0])))
        )
    except ValueError:
        return False


async def verified_umantis_link(
    crawler: AsyncWebCrawler, config: CrawlerRunConfig, referrer: object,
    website: str, target: str,
) -> bool:
    """Stored provenance alone is insufficient; require today's exact board link."""
    if not umantis_board(target) or not isinstance(referrer, str) or not recruitment_referrer(referrer, website):
        return False
    proof = await crawler.arun(referrer, config=config)
    final = proof.redirected_url or referrer
    status = proof.redirected_status_code or proof.status_code
    if not proof.success or status is None or not 200 <= status < 300 or not recruitment_referrer(final, website):
        return False
    soup = BeautifulSoup(proof.html or "", "html.parser")
    return any(
        urljoin(final, str(a.get("href", ""))) == target
        and re.search(r"\b(jobs?|vacancies|openings|positions|stellenangebote)\b", a.get_text(" ", strip=True), re.I)
        for a in soup.select("a[href]")
    )


def repair_umantis_detail_urls(
    items: list[dict[str, object]], html: str, source_url: str,
) -> list[dict[str, object]]:
    """Use an observed title link for the same vacancy, never synthesize a URL."""
    if not umantis_board(source_url):
        return items
    origin = urlsplit(source_url)
    links: dict[tuple[str, str, str], set[str]] = {}
    for anchor in BeautifulSoup(html, "html.parser").select("a[href]"):
        url = urljoin(source_url, str(anchor.get("href", "")))
        parsed = urlsplit(url)
        match = re.fullmatch(r"/Vacancies/([0-9]+)/Description/([0-9]+)", parsed.path)
        if (match and parsed.scheme == origin.scheme and parsed.netloc == origin.netloc
                and not parsed.query and not parsed.fragment):
            title = " ".join(anchor.get_text(" ", strip=True).casefold().split())
            links.setdefault((match[1], match[2], title), set()).add(url)
    repaired = []
    for item in items:
        current = urlsplit(urljoin(source_url, str(item.get("url") or "")))
        match = re.fullmatch(r"/Vacancies/([0-9]+)/Application/CheckLogin/([0-9]+)", current.path)
        title = " ".join(str(item.get("title") or "").casefold().split())
        if (match and title and current.scheme == origin.scheme and current.netloc == origin.netloc
                and not current.query and not current.fragment):
            targets = links.get((match[1], match[2], title), set())
            if len(targets) == 1:
                item = {**item, "url": next(iter(targets))}
        repaired.append(item)
    return repaired
