import re

from bs4 import BeautifulSoup

_LOADER = "https://static.b-ite.com/jobs-api/loader-v1/api-loader-v1.min.js"

_MARKER = re.compile(r"[a-z0-9_-]{1,100}:[a-z0-9_-]{1,100}")

def bite_listing(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select("[data-bite-jobs-api-listing]")
    if len(nodes) != 1 or not soup.find("script", src=_LOADER):
        return None
    marker = nodes[0].get("data-bite-jobs-api-listing")
    return marker if isinstance(marker, str) and _MARKER.fullmatch(marker) else None
