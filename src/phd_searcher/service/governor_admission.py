"""Local, quota-free admission for explicitly governor-managed schedules."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from pydantic import ValidationError

from phd_searcher.typedef.schedule import GovernorPlan


def governor_block_reason(raw: object) -> str | None:
    """None permits launch; a reason keeps the durable job pending.

    Duration is a planning estimate, never a deadline tied to account reset.
    Existing pipeline locks still own exclusion and crash-safe run identity.
    """
    try:
        plan = GovernorPlan.model_validate(raw)
        path = os.environ.get("PHDBOT_GOVERNOR_STATE_FILE")
        if not path:
            return "governor: state file not configured"
        state = json.loads(Path(path).read_text())
        now = time.time()
        if not isinstance(state, dict):
            return "governor: invalid state"
        stamp = state.get("updated_at")
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not 0 <= now - stamp <= 30:
            return "governor: stale state"
        if state.get("manual_park"):
            return "governor: manual pause blocks new local runs"
        if not state.get("enabled") or state.get("mode") not in {"NORMAL", "CONSERVE", "WATCH", "PARK", "RESUME"}:
            return "governor: controller unavailable"
        if plan.cwd not in state.get("pilot_projects", []):
            return "governor: project not enrolled"
        if plan.expires_at.timestamp() <= now:
            return "governor: plan expired; review required"
        if state.get("mode") == "PARK" and (state.get("park") or {}).get("reason") not in {
            "dynamic safety reserve",
            "hard quota exhaustion",
        }:
            return "governor: PARK is not quota-only"
    except (OSError, ValueError, TypeError, AttributeError, ValidationError):
        return "governor: plan/state unavailable; no launch"
    return None
