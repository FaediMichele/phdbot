"""Cheap source checks before schema/model work. No verdict about individual jobs."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

_ERROR_HEADINGS = {
    "not found",
    "page not found",
    "404",
    "404 not found",
    "404 page not found",
    "page introuvable",
    "seite nicht gefunden",
}
_NO_OPENINGS = re.compile(
    r"^(?:at the moment[, ]+)?(?:there are|we have)\s+(?:currently\s+)?no\s+"
    r"(?:open\s+)?(?:job openings|job vacancies|open positions|vacancies|positions)"
    r"\s*[.!](?:\s|$)",
    re.I,
)


def _fold(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold()))


def _json_objects(value: object) -> Iterator[dict[str, object]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _json_objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _json_objects(nested)


def employer_evidence(html: str, institution: str) -> bool:
    """External ATS allowed when structured JobPosting names the exact employer.

    An arbitrary mention/link or an Organization unrelated to hiring isn't proof.
    Absent evidence defers the source, it does not reject the institution/jobs.
    """
    soup = BeautifulSoup(html, "html.parser")
    matched = False
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.get_text())
        except ValueError:
            continue
        for obj in _json_objects(payload):
            types = obj.get("@type", [])
            types = [types] if isinstance(types, str) else types
            employer = obj.get("hiringOrganization")
            if isinstance(types, list) and "JobPosting" in types:
                if (
                    not isinstance(employer, dict)
                    or not _fold(institution)
                    or _fold(str(employer.get("name", ""))) != _fold(institution)
                ):
                    return False  # Mixed-employer aggregators are not this institute's board.
                matched = True
    return matched


def page_state(html: str, status: int | None = None) -> str | None:
    if status in {404, 410}:
        return "unavailable"
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find(id="content") or soup
    heading = main.find("h1")
    if heading is not None and _fold(heading.get_text(" ", strip=True)) in _ERROR_HEADINGS:
        return "unavailable"
    # Contradictory positive evidence means abstain, not hide a mixed page.
    if '"JobPosting"' in html or any(
        re.search(r"\b(phd|postdoctoral|doctoral|researcher|professor)\b", a.get_text(" ", strip=True), re.I)
        for a in main.find_all("a", href=True)
    ):
        return None
    for block in main.find_all(["p", "h1", "h2"], limit=15):
        text = " ".join(block.get_text(" ", strip=True).split())
        if _NO_OPENINGS.search(text):
            return "empty"
    return None


_LISTING_HEADINGS = frozenset({
    "jobs", "vacancies", "current vacancies", "open positions", "job opportunities",
    "actuele vacatures", "vacatures", "stellenangebote", "offres d emploi",
})


def listing_body_missing(html: str) -> bool:
    """Observe a heading-only board after rendering, without claiming no jobs.

    Require an explicit main region and recruitment heading. Any remaining
    text, application link, structured job or embedded/media content makes us
    abstain. Deferred sources are retried; no vacancy verdict is inherited.
    """
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find(id="content")
    if main is None or re.search(r"jobposting", html, re.I):
        return False
    # Some sites misuse navigation/aside regions for their real job cards.
    # Preserve recognizable role evidence and embedded boards before cleanup.
    if main.select_one("iframe, embed, object, canvas, form") or re.search(
        r"\b(?:ph[.\s]?d|doctoral|postdoc(?:toral)?|professor|researcher|fellowship)\b",
        main.get_text(" ", strip=True), re.I,
    ):
        return False
    for node in main.select("nav, aside, header, footer, script, style"):
        if not node.decomposed:
            node.decompose()
    headings = [h for h in main.find_all(["h1", "h2"]) if _fold(h.get_text(" ", strip=True)) in _LISTING_HEADINGS]
    if not headings:
        return False
    # A heading itself may link to an actual external board: keep that route.
    if main.select_one("a[href], iframe, embed, object, img, canvas, form, input, button, select, textarea"):
        return False
    for heading in headings:
        heading.decompose()
    return not main.get_text(" ", strip=True)


class SchemaDeferredError(Exception):
    """A recorded preflight disposition, not an LLM/transport failure."""


def staff_directory_evidence(html: str) -> bool:
    """Defer repeated contact profiles, never infer a vacancy verdict from names.

    Require repeated office labels AND personal email evidence in their blocks.
    A mixed board with recruitment links or structured jobs must be left alone.
    """
    soup = BeautifulSoup(html, "html.parser")
    if '"JobPosting"' in html or any(
        re.search(
            r"\b(phd|postdoctoral|doctoral|researcher|professor|apply|vacancy|"
            r"bewerben|dottorato|assegno|borsa)\b",
            a.get_text(" ", strip=True), re.I,
        )
        for a in soup.find_all("a", href=True)
    ):
        return False
    blocks: set[int] = set()
    for label in soup.find_all(["b", "strong"]):
        if _fold(label.get_text(" ", strip=True)) not in {
            "main office laboratory", "office", "office location", "ufficio",
        }:
            continue
        block = label.parent
        if block is None:
            continue
        if re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", str(block), re.I):
            blocks.add(id(block))
    return len(blocks) >= 3
