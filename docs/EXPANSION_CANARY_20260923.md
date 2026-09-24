# Research institution expansion — 23 September 2026

The imported registry can now feed bounded, restart-safe institution jobs through
Coverage and `/v1/catalog/expansion`. Catalogue presence alone is not coverage:
15,594 institutions were added in September, but the initial September22 audit
found15,586 of that cohort still catalogued rather than explored.

## Delivered behavior

- Atomic activation and persistent scheduling, concurrent-request idempotence,
  scope revalidation before dispatch, one institution published per run.
- Recruitment hubs take priority within the existing four-visit budget; linked
  external recruitment sites and jobs subsections can be followed. Optional hub
  failure does not replay all successful visits. French recruitment labels work
  even when the URL does not resemble a jobs route.
- Exact title-anchor URLs are recovered without regenerating a schema. Dynamic
  recruitment containers can receive a six-second CSS-only rendering wait;
  source-specific rendering hints are not blindly copied with reused schemas.
- Personnel contact directories are deferred before model work and rechecked
  after seven days. Failed schemas retain their last error in durable checkpoints.
- Quality budgets prioritize newly scraped/unchecked sources over old aggregators.
- Detail cleanup tolerates descendants destroyed when page furniture is removed.
  Deadline evidence stops at a following start/interview-date label. Named jobs
  requiring a PhD are distinguished from doctoral training positions.
- Active issue feedback hides only the exact item in server-side search. Inspection
  and undo remain available; positive confirmations do not erase other dimensions.

## Measured canaries

| Institution / run | Result | Interpretation |
| --- | --- | --- |
| AIT125 | schema1, scrape30, index4;154.8s | Initial schema omitted actual detail links. |
| AIT126 | scrape30, index4;52s | Same IDs; exact links repaired without schema generation. |
| INO127 | scrape283, index0 |282 personnel profiles plus an empty-board heading; not283 opportunities. Directory source8053 held reversibly. |
| Champalimaud128 | discovery1, schema0 | Correct board found; HTML arrived before dynamic offers. |
| IOW129 | scrape2, index1 | General PhD information produced a wrong department link. Feedback5 hides103897; no institution-wide verdict. |
| Champalimaud130 | schema1, scrape9;104.8s | Real dynamic cards acquired. Quality budget1 initially hit an old aggregator; subsequently corrected. |
| AIT133 | enrich4, index3;61.1s | Full details recovered; unsolicited application classified separately. |
| Champalimaud134 | evidence2, enrich1, index3;54.6s | Three new provisional leads with details, including Learning Lab PhD. |

The specialist record103900 audit found a start date incorrectly reinterpreted as
its deadline and a PhD qualification misread as training. Its official closing date
is30 September2026 and its type is research staff. Run135 refreshed its index; default search verified both corrected fields before
feedback6 was retracted. Feedback5 on the unrelated IOW artifact remains open.
Two older aggregator hits must not be counted as new Champalimaud additions.
These are provisional leads, not a certification that every offer remains open.
GPU seconds were not measured; elapsed times are run-specific, not estimates for
complete catalogue coverage or a reconstruction of the historical Run70 ETA.

## Validation and operating limits

977 unit tests, Ruff and mypy passed. An isolated restored production backup verified
concurrent enqueue idempotence, rollback of invalid mixed batches, and fresh-source
priority with a one-source quality budget. Fresh-browser UI smoke verified feedback
hiding/inspection without mutating a report. Backups, raw evidence and operational
receipts remain local and ignored, under `backups/`, `var/expansion-20260922/` and
`exports/expansion-verification/`; deployment state belongs in CURRENT_STATE.

Activation is bounded and explicit; this does not introduce an unbounded recurring
catalogue crawl, automatic registry-release monitoring, adaptive refresh scheduling
or automatic repair of every failed source. GO FAIR and Pathliv were previewed but
not activated in this canary. Pathliv's recruitment page exposes template text;
no opportunity is inferred from that alone. Existing IMBA403 and FORTH certificate
issues remain separate technical work, without access-control/TLS bypasses.

## Follow-up — 24 September

Small repeated preview batches now rotate countries using the last durable expansion
admission per country, before falling back to alphabetical order. Cancelled jobs do
not advance rotation; the stable registry hash and within-batch country diversity
remain. An isolated restored-database transaction exercised44 countries before any
repeat, checked cancellation and explicit country filters, and rolled back its fixtures.
977 unit tests, Ruff and mypy passed again before deployment. This changes candidate
ordering only; it does not introduce automatic recurring activation.

The next automatic cohort (Albanian Academy11350, Austrian IOEW19181, Bijeljina12608)
produced no sources in runs136–138. This is a discovery outcome, not proof of no
vacancies. A direct-page audit found IOEW serves a language-selection splash with
image-only links; that navigation gap is deferred separately. Saved HTML is local.

Scoped indexing still revalidates all existing provisional records. A read-only
profile located51.2s in10,024 synchronous gate evaluations (profiling overhead included).
Cooperative traversal now yields between16 rows in the existing-index gate, candidate
gate and full metadata synchronization. All checks remain. A same-snapshot comparison
returned identical metadata for10,024 rows:41.40s synchronous versus40.64s cooperative,
with a maximum observed event-loop scheduling gap0.932s. This improves responsiveness,
not total compute.978 tests/Ruff/mypy pass; no claim of live API latency yet.


Foundation follow-up: the English `scholarship` keyword was absent from discovery
candidate/hub routing. A same-HTML replay added the actual Honor Frost scholarship
board; run141 then discovered it as source8073. That page contains recurring schemes
and an expired March2026 targeted call, so discovery alone does not establish current
eligibility. Its first schema attempt cycle failed with missing title/description
coverage; preserve that error for repair rather than replaying the four-call cycle.
The expanded selection also included scholarship-recipient archive pages: these are
not counted as opportunities. Run139's ten student names and run140's single generic
vacancies heading yielded zero indexed opportunities.

Heading-only recruitment boards now defer as `source_preflight:missing_content`,
not as a claim that no jobs exist. The guard runs after bounded rendering and abstains
on actual role text, links, structured jobs, media, forms or embedded application boards.
It preserves evidence in mislabelled navigation regions. Missing-content holds become
eligible for schema recheck after seven days. An isolated restored-DB test used saved
KMI HTML, asserted zero model calls, skipped immediate retry, retried at eight days,
and rolled back the full transaction.994 unit tests, Ruff and mypy passed. Deployment
and exact source8072 disposition must be checked in CURRENT_STATE before claiming live.


Run141 completed with index4, but audit rejected that count as useful output: two
named award-recipient biographies and two scholar navigation categories. Exact-item
feedback7–10 hides them in ordinary search (live verification0 default/4 inspection),
without a domain/family or neighbouring-deadline verdict. Scholarship source8073 is
still failed; archive sources8074/8076 were selected incorrectly. These remain repair
work, not evidence that the foundation has no funding. Missing-content protection is
now deployed and source8072 held reversibly; all its records were preserved.
