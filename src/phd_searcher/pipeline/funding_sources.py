"""Audited inline funding sections; no inferred intake year or open verdict."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

HONOR_FROST_SCHOLARSHIPS_URL = "https://honorfrostfoundation.org/grants-offered/scholarships/"
FUNDING_URLS = frozenset({HONOR_FROST_SCHOLARSHIPS_URL})
_SHARED_DEADLINE = re.compile(r"deadline for all Masters and PhD scholarship applications", re.I)
_LOCAL_DEADLINE = re.compile(r"Application deadline for HFF scholarship:\s*([^()]+)", re.I)


def funding_items(html: str, source_url: str) -> list[dict[str, object]]:
    """Separate degree tabs and sibling sections before assigning any dates.

    Only the explicitly shared Masters/PhD deadline is inherited. A targeted
    scholarship keeps its own HFF deadline, not the host university's date.
    Recurring dates remain raw evidence; normalization does not invent a year.
    Layout ambiguity raises rather than reporting an empty successful scrape.
    """
    if source_url not in FUNDING_URLS:
        raise RuntimeError("untrusted funding source URL")
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    if main is None:
        raise RuntimeError("funding main region missing")
    shared = [h.get_text(" ", strip=True) for h in main.select("h2, h3, p")
              if _SHARED_DEADLINE.search(h.get_text(" ", strip=True))]
    if len(shared) != 1:
        raise RuntimeError("shared Masters/PhD deadline missing or ambiguous")
    items: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    degrees: set[str] = set()
    for pane in main.select('[role="tabpanel"]'):
        label_id = pane.get("aria-labelledby")
        labels = main.find_all(id=label_id) if isinstance(label_id, str) else []
        if len(labels) != 1 or labels[0].get("aria-controls") != pane.get("id"):
            raise RuntimeError("funding tab label association changed")
        degree = labels[0].get_text(" ", strip=True)
        if degree == "Diplomas & Minors":
            continue  # Outside the supported Masters/doctoral scholarship scope.
        if degree not in {"Masters", "PhD"} or degree in degrees:
            raise RuntimeError("funding degree tabs changed or duplicated")
        degrees.add(degree)
        bodies = pane.select(".awb-tab-pane-inner")
        if len(bodies) != 1:
            raise RuntimeError("funding tab body missing or ambiguous")
        body = bodies[0]
        headings = body.find_all("h2", recursive=False)
        if not headings or len(headings) != len(body.find_all("h2")):
            raise RuntimeError("funding section boundaries changed")
        for heading in headings:
            title = heading.get_text(" ", strip=True)
            key = (degree, title)
            if title not in {"Open Scholarships", "Targeted Scholarships"} or key in seen:
                raise RuntimeError("funding section title changed or duplicated")
            seen.add(key)
            blocks: list[Tag] = []
            for sibling in heading.next_siblings:
                if not isinstance(sibling, Tag):
                    continue
                if sibling.name == "h2":
                    break
                blocks.append(sibling)
            texts = [block.get_text(" ", strip=True) for block in blocks]
            description = "\n\n".join(text for text in texts if text)
            if len(description) < 100:
                raise RuntimeError("funding section evidence missing")
            if title == "Targeted Scholarships":
                deadline_blocks = [text for text in texts if _LOCAL_DEADLINE.search(text)]
                if len(deadline_blocks) != 1 or "deadline to the University" in deadline_blocks[0]:
                    raise RuntimeError("targeted funding deadline missing or ambiguous")
                match = _LOCAL_DEADLINE.search(deadline_blocks[0])
                assert match is not None
                deadline = match.group(1).strip()
            else:
                deadline = shared[0]
                description += "\n\n" + deadline
            items.append({
                "title": f"{degree} — {title}",
                # No arbitrary first hyperlink: standard synthetic identity is
                # stable by source + distinct title and retains inline evidence.
                "description": description,
                "deadline": deadline,
                "position_type": "phd" if degree == "PhD" else "masters_mph",
                "language": "en",
            })
    if degrees != {"Masters", "PhD"}:
        raise RuntimeError("funding degree tabs missing")
    return items
