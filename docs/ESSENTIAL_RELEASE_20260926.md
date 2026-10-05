# Essential PHDBOT baseline — 26 September 2026

The bounded release agreed on26September is ready for ordinary use. This closes
the essential baseline, not exhaustive activation of the18673-entry catalogue or
support for every recruitment site. Probable leads remain explicitly uncertain.
No claim of a verified currently open vacancy follows from mere searchability.

## Release evidence

-1104unit tests, Ruff and mypy passed before deployment. API healthy image:
 `sha256:ed09d3224642b0c86c4a54848e39d93efe66c357ab49f1dcfc1c18a0591a3907`.
-Representative source-to-search paths cover universities, research institutes and
 foundations, including TalentAdore/TalentLink, Umantis, BITE and scoped funding.
-The20-record audit across5countries found4 false/closed rows. Exact-ID feedback
 12–15 hides them in browse and semantic search. A shared provisional guard now
 excludes year-only titles without rejecting adjacent real opportunities.
-Application-submission dates are separated from reference-letter dates. Run155
 verified BITE103964 as research_staff,12October2026, same public URL and ID.
 A senior role no longer inherits PhD from mentions of supervised students.
-Run156 verified AIT103575 as a concrete PhD vacancy, preserving identity and
 details. A singular thesis invitation takes precedence over programme coursework.
-HFF recurring funding keeps separate scope from the expired neighbouring call.
 Four Imperial sample records match the official feed in title/deadline and have
 complete source descriptions available in PHDBOT.
-Real-browser check passed institution search, role/date presentation, probable
 and uncertainty labels, details, Save, reload persistence and Unsave. No JS errors.
-Final API checks passed role filters, verified/probable separation, exact feedback
 hiding in semantic search, HFF negative control and AITkind. Latest156DONE;
 no pending/running schedules at the final checkpoint.
-Schedules40–44 exercised native governor admission and durable serialization.
 Failures in individual sources did not block the three-institution cohort.

Evidence remains in ignored local directories:
`var/release-baseline-20260926/` and `exports/expansion-verification/`.
Key receipts: final-check.json, ait-kind-verification.json,
senior-canary-verification.json, imperial-feed-verification.json and
exports/expansion-verification/ui-release-check.json.
The20-record sample is purposive and does not establish a statistical error rate.

## Secondary limitations, explicitly retained

-Imperial returns a403 to the browser used to inspect its listing. The public
 feed works and supplies text/application URLs; a separate public-detail URL
 was not established. Retain the publisher's application URL, not a guessed route.
-EURAXESS59872's EXPIRED text is an inline-hidden template with expiry timestamp
 1October2026 13:16:37UTC. At audit time it is not evidence of a visible closure.
 The item remains probable/open-status uncertain; no forced open verdict.
-Rare portals, ambiguous-name activation (Rockwool), isolated source failures,
 exhaustive catalogue coverage and additional enrichment remain secondary work.
-Stable extraction and URL families do not imply complete DOM/breadcrumb modelling.
 Adaptive refresh planning and other historical architectural proposals remain
 outside this essential release.

## Recovery and handoff

See OFFLINE_HANDOFF.md for the current user guide and
archive/OFFLINE_HANDOFF_TECHNICAL_20260926.md for the dated recovery record,
tested commands and untested-control caveats. The dirty
worktree is intentionally preserved, including the user's governor integration.
No reset, remote push or broad relabel was performed. One grounded, nonmanual
AITkind correction has its prior values in ait-kind-repair.json.
The final source patch/untracked bundle and hashes are recorded locally in
var/release-baseline-20260926/checkpoint/; base commit and runtime image accompany
it. This is a recoverable local release, not a claim that changes were committed.

No new jobs are needed for acceptance of this baseline. Do not repeat completed
runs or queue collection merely to occupy a PARK window. Broader coverage can be
continued as separate useful bounded maintenance, with evidence-driven priorities.
