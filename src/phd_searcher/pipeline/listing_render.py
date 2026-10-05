"""Bounded rendering hints for asynchronously populated recruitment lists."""

from __future__ import annotations

import re
from collections.abc import Mapping

from bs4 import BeautifulSoup

_SAFE_CLASS = re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]{0,100}\Z")
_WAIT_SELECTOR = re.compile(r"\.[a-zA-Z_][a-zA-Z0-9_-]{0,100} > \* a\[href\]\Z")


class ListingRenderError(RuntimeError):
    """A dynamic list did not become observable; not evidence of no vacancies."""


def listing_render_selector(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    if not any(
        re.search(r"\b(recruitment|open positions|job opportunities|vacancies)\b", h.get_text(" ", strip=True), re.I)
        for h in soup.find_all(["h1", "h2", "h3"])
    ):
        return None
    for node in soup.find_all(["div", "ul"], class_=True):
        for token in node.get_attribute_list("class"):
            if not isinstance(token, str) or not _SAFE_CLASS.fullmatch(token):
                continue
            parts = set(token.lower().split("-"))
            if not ({"list", "entry", "wrapper"} <= parts or {"job", "list"} <= parts or {"vacancy", "list"} <= parts):
                continue
            parent = node.parent
            if parent is not None and parent.find(
                class_=re.compile(r"loading|load-more|loadmore", re.I)
            ) is not None and len(soup.select(f".{token}")) == 1:
                return f".{token} > * a[href]"
    return None


def render_wait_options(schema: Mapping[str, object]) -> dict[str, object]:
    selector = schema.get("render_wait_for")
    if isinstance(selector, str) and _WAIT_SELECTOR.fullmatch(selector):
        return {"wait_for": f"css:{selector}", "wait_for_timeout": 6000}
    return {}
