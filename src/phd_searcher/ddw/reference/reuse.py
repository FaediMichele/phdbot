from __future__ import annotations

import json
from copy import deepcopy
from urllib.parse import urlsplit

from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from .schema_quality import repair_base_anchor_url_schema, schema_quality_issues


def _schema_cache_key(url: str, kind: str) -> tuple[str, str] | None:
    """Scope schema reuse to the same host and listing kind.

    A schema is never trusted from the key alone: it still has to validate
    against the target page HTML before reuse.  The key only bounds the cheap
    candidate set and prevents cross-tenant/domain reputation leakage.
    """
    try:
        host = urlsplit(url.strip()).hostname
    except ValueError:
        return None
    if not host:
        return None
    return kind, host.casefold().rstrip(".")

def _validated_reusable_schema(
    html: str,
    schemas: list[dict[str, object]],
    *,
    expected_fields: list[str],
) -> dict[str, object] | None:
    """Return the first cached schema that passes the normal target-page gate."""
    for raw_schema in schemas:
        schema = repair_base_anchor_url_schema(raw_schema)
        schema.pop("render_wait_for", None)  # Render hints belong to the observed page.
        if schema_quality_issues(schema):
            continue
        try:
            validation = JsonCssExtractionStrategy._validate_schema(
                schema,
                html,
                "CSS",
                expected_fields=expected_fields,
            )
        except (TypeError, ValueError):
            continue
        if validation["success"]:
            return schema
    return None

def _remember_schema(
    cache: dict[tuple[str, str], list[dict[str, object]]],
    key: tuple[str, str] | None,
    schema: dict[str, object],
) -> None:
    if key is None:
        return
    candidates = cache.setdefault(key, [])
    fingerprint = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    if all(
        json.dumps(item, sort_keys=True, separators=(",", ":")) != fingerprint
        for item in candidates
    ):
        candidates.append(deepcopy(schema))
