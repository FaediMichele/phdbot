# Essential release audit — 26 September 2026, 07:38 CEST

Latest disposition: essential baseline accepted after follow-ups. See
ESSENTIAL_RELEASE_20260926.md and final-check.json. The initial findings below
are historical; they are not the current unresolved-blocker list.

Release audit is NOT yet passed. This is a purposive sample, not a statistical
accuracy estimate. Twenty records cover FI,GB,PT,AT,DE, universities, foundations
and institutes. Saved evidence/HTML and row-level findings are in ignored
`var/release-baseline-20260926/audit/reviewed-evidence.json`.

## Completed cohort and timing

Schedules40–42 / runs152–154 all DONE:83s,260s,120s (463s total) versus estimated
600s each. No retries or replacement runs started. Run152 extracted13 items from
two BITE language boards; live search contains103962, a student assistantship.
The English group-leader job103964 remains excluded as typeother, not a PhD lead.
Run153's2022 internship stays expired; run154'sfour person profiles stay excluded.
Rockwool ambiguous-name activation remains deferred, without bypassing the guard.

## Audit findings and actions

- Publication-year rows22188/22187/22186 were not opportunities. Feedback12/13/14
  hides only those records; the underlying recruitment page is not rejected.
-22351 now says no open positions; informal contact is not an open vacancy.
  Feedback15 hides this exact record. Live Turku search verified all four absent.
- Four Imperial feed records103067/103065/103053/103050 route to application
  shells with no readable detail. Do not label these non-opportunities: recover
  an observed public detail route and verify identity/deadline before sign-off.
- AIT103575 is a real PhD thesis vacancy but remains kindprogramme. Resolve this
  classification mismatch with evidence; do not treat a title alone as a programme.
- EURAXESS59872 has a future deadline and STATUS:EXPIRED. Keep uncertainty; neither
  a positive nor a definitive closed verdict follows from this conflict alone.
- HFF103937/103938 are recurring scoped funding schemes. The16March2026 expiry
  belongs to the neighbouring targeted call. Revalidated funding adapter sections;
  no date/year/open-window propagation to the recurring schemes.
- Remaining observed details support role identity; missing open status remains
  provisional. Umantis visiting programme is normally self-funded, not fundedPhD.

## Released fixes, independently evaluated

1. Application-submission deadline wording now parses12Oct2026 while reference
   letters19Oct2026 (or earlier dates/another year) are excluded from that clause.
   No year borrowing from references. Real saved BITE HTML verifies12Oct.
2. Provisional index rejects four-digit-only extracted titles even when shared
   recruitment prose would otherwise rescue them. Real titles containing a year
   remain eligible; records are retained for repair, not deleted.

1096 unit tests, Ruff, mypy passed. Guarded deployment is healthy:
`sha256:0e15f0b9860b3b50d5f5dbd789a59b6a4824db5920dac78a5fa4b3a531113760`.

## Next bounded work and queue decision

Offline preflight discovered classify_position(group-leader title, full body,
other) currently returnsphd because the senior job describes students supervised.
Do NOT enrich/index103964 until title/role precedence is repaired and tested.
The current public search still contains only assistant103962 for that institute.

Prioritize this reusable role fix and Imperial detail routing, then AITkind and
EURAXESS conflict adjudication. Preserve20-record evidence and recheck only changed
cases. No new unattended queue was armed: next repairs require code/evidence
review, and no validated dependent refresh should run before those decisions.
Governor WATCH requested completion of current useful unit and checkpoint.

## Senior-role repair follow-up

The shared title classifier now recognizes research/scientific group leaders and
heads as research_staff, and generic group-leader titles no longer inherit PhD
from body mentions of supervised students. Actual PhD titles and explicit operator
types are preserved. The real saved BITE detail passes;1100 unit tests/Ruff/mypy
pass. One governed evidence1/index20 canary is prepared for existing103964, using
the normal detail-refresh API. Receipt senior-canary.json; inspect the durable
schedule then run verify-senior-canary.py once after completion. No new discovery,
schema generation, model review or duplicate position is needed.

Canary43/run155 completed:103964 is searchable as research_staff,12October2026,
same identity/public URL, probable(open_status/details). No duplicate lead.
