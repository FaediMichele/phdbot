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


The scholarship repair uses a source-scoped audited funding adapter through the
existing source-adapter contract. It resolves ARIA degree tabs, splits sibling
sections, preserves eligibility/stipend text, and fails visibly on changed or
ambiguous layout. Only the explicitly shared Masters/PhD annual deadline is inherited;
the targeted scholarship uses its own HFF deadline, not the university's later date.
No year or open verdict is fabricated for recurring dates. Current saved AND fresh
HTML produced three distinct records:Masters Open,PhD Open,PhD Targeted(deadline
2026-03-16). Schema preparation revalidates the source before selecting the adapter.
An isolated rollback test verified zero LLM calls and priority over missing archive
schemas at budget1.1005 unit tests/Ruff/mypy126files pass. Live canary and deployment
are tracked separately in CURRENT_STATE; no new searchable count claimed yet.


Run142 completed in53.2s: schema1/scrape3/quality3/index1, zero schema LLM calls.
The expired targeted scholarship103939 stayed out of search. PhD Open103938 was
provisional with open_status uncertainty; annual dates remained yearless. The search
check exposed a DB/index type mismatch: the initial adapter used the degree-tab type,
while the existing taxonomy correctly classifies grants as research_fellowship.
These awards require a separate university application, so the adapter now uses
research_fellowship for funding and retains Masters/PhD in the title and evidence.
The conservative classifier for generic scholarship directories is unchanged.
Temporary feedback11 holds only103938 until fresh upsert/index confirms consistency;
its original concern is clarified here rather than silently erasing the audit.
1005 unit tests/Ruff/mypy passed after this final type alignment.


Run143 completed the ordinary refresh with the same three position IDs. Live search
now exposes two provisional recurring funding schemes (Masters103937 and PhD103938),
with grant type consistent in DB/index. Targeted103939 remains expired and excluded.
Feedback11 was retracted after verification; archive feedback7–10 remains active.
These are two funding schemes with unverified current opening, not two certified
open PhD training posts. No schema regeneration or forced opportunity verdict was
needed for the final refresh. Operational receipts remain local and ignored.

September24 follow-up cohort (schedules32–34) completed as runs144–146. RCRM144
found its official vacancies board8080 but schema generation exhausted four
responses without a tool call (387.5s whole run); no positions were produced.
Saved board evidence contains clinical/service roles, not an established academic
opportunity, so no repair rerun is justified by this audit alone. IEES145 recovered
the obsolete registry path through the identity-verified root and found no listing
(77.1s). IOMT146 preserved a technical root404 failure (56.3s); an independent HTTPS
check failed hostname certificate validation. No bypass or absence-of-jobs verdict.
Live institution browsing returned zero hits for all three; completed runs unchanged.

The schema generator now allows one reminder after a response without tool calls,
then raises its existing non-retryable exhaustion error on the second consecutive
missing-tool response. Actual tool submissions reset that streak and retain the
four-attempt validation/correction budget. Regression tests cover recovery after a
reminder, four productive corrections, and interrupted missing-tool streaks. This
bounds protocol failures; it does not prove a measured reduction in wall-clock time
or decide whether a source contains opportunities. Release status is in CURRENT_STATE.

IOEW's English image-language entry was also audited through its three navigation/
content frames. Examined pages expose projects/publications/contact, no recruitment
link; the German partner is not proven to be an ATS. This limited observation does
not establish absence of vacancies. Frame support remains deferred pending evidence
of useful recall. Local receipts preserve the HTML and hashes.

MPG anthropology run147/schedule35 selected the official career landing page8081,
then extracted four navigation links (Vacancies, Job Search, Subscription, Login).
All stayed out of live search. The actual Umantis board, linked by that same official
career page, contains an Economic Experimentation guest-research programme. Audited
detail describes1–6months, normally self-funded, with discretionary support; board
lists30April/31October2026 deadlines. This is not a funded PhD vacancy.

A prompt-only isolated replay still missed Umantis and was discarded. Deterministic
source retention now includes narrowly recognized tenant-scoped Umantis Jobs boards
only with explicit official recruitment-page provenance. It preserves language and
rejects search/register/login variants; generic schema and opportunity gates remain.
The same saved HTML/model selection now retains the actual board without further
inference.1020 unit tests/Ruff/mypy pass. This proves routing on the audited sample,
not successful live extraction or searchability; inspect CURRENT_STATE for deployment
and subsequent canary. No historical run or existing opportunity verdict was changed.

Run148/schedule36 verified live discovery retention: the Umantis tenant boards were
persisted, including English8085. Budget1 schema preparation selected German8084,
which correctly deferred as ownership_unverified: the ATS does not supply the exact
employer JobPosting metadata required by the generic external-source gate. Four old
career navigation rows were refreshed; index0.148 remains DONE, not a failed run to
restart. Search-form variants selected by the model also exist; source retention
itself did not auto-admit those variants.

Umantis schema admission now re-fetches the recorded official recruitment page and
requires a current exact board link with a recruitment label. Tenant/language changes,
foreign redirects, removed links and denial pages do not verify ownership. Stored
provenance alone is insufficient, and generic quality/index checks remain. The shared
URL recognizer retains the same restricted discovery scope. Saved official HTML
passed;13 ownership regressions plus the existing suite pass.

Independent temporal regression: the guest-research detail mentions yearless April/
October deadlines beside parenthetical start dates in2026/2027. Those start dates
previously yielded a false April2027 deadline. Explicit start-date asides are now
excluded; the yearless detail abstains, while the board's fully dated October2026
window remains parseable. No year is borrowed.1036 tests/Ruff/mypy127files pass.
Live collection of English8085 is still required before claiming useful new results.

Run149/schedule37 acquired English ATS8085: schema1/scrape1/quality1/index1.
Position103951 became a provisional research_staff lead, with deadline2026-10-31
and open_status/details uncertainty. The generated schema chose the Apply-now login
URL and no description. The public title link was present in the same downloaded
HTML. Scrape now repairs only recognized Umantis application-login URLs when an
observed detail anchor matches vacancy ID, language, exact normalized title and host.
No guessed URL, extra fetch or schema generation;1043 tests/Ruff/mypy pass.

For this existing record, an audited one-row canonical-URL repair preserves103951,
first-seen data and verdict rather than inserting a second copy. Current board HTML
was fetched to verify the exact replacement and absence of a conflicting DB URL;
before-values are in umantis-detail-refresh.json. Schedule38 refreshes scrape/quality/
evidence/enrich/index without discovery/schema or deep review. Final evidence/search
verification is still pending in CURRENT_STATE; do not count the refresh as a new lead.

Run150 preserved the same103951 with its public detail URL and October2026 deadline.
Its final evidence audit failed: generic cleanup retained only the longest of several
`.content` siblings (the892-character application/contact section), dropping OurOffer.
The scoped Umantis detail cleaner now retains sibling content sections inside one
unique container on a recognized single-vacancy detail URL. It abstains on other
hosts, board URLs or multiple containers. Saved real HTML produces2424characters,
including self-funded terms, without borrowing start dates.1048 tests/Ruff/mypy pass.
Schedule39 targets only evidence/index refresh; live final verification remains in
CURRENT_STATE.150 is DONE and untouched; no additional lead claimed for this repair.
