# Backup and first pipeline performance validation — 4 October 2026

## Verified baseline and scope

User authorized protecting current data and improving catalogue throughput on
3 October. The essential release remains separate and ready for ordinary use.
At20:32 on3 October the API was healthy, latest run2918 DONE, no active schedules.
18,673 institutions,65,732 positions,8,646 listing pages and2,889 pipeline runs
were stored.12,839 institutions remained `catalogued`. Applying the historical
133.5s/job uniformly would mean about19.8 days of continuous initial acquisition;
this is a naive projection, not a measured duration or a repeat-refresh target.
A one-week initial pass at that population would require about47s per institution.
The changes below alone do not establish that throughput.

## Backup completed and PostgreSQL restore tested

Directory: `backups/data-20261003-2032/` (about791MiB, local disk, private permissions).
Manifest includes SHA-256, sizes, timestamps and source/restored counts.

- `postgres.dump`: custom-format dump of app. Restored with pg_restore
  `--exit-on-error --no-owner` into a new isolated database
  `phdbot_verify_20261003_2032` in the existing PostgreSQL container. All restore
  operations succeeded; counts of universities, positions, listing_pages,
  pipeline_runs and scheduled_jobs matched. Only that temporary database was
  dropped after success. Production app was never restored or overwritten.
- Eight Qdrant collection snapshots and alias metadata. Archives are readable,
  SHA-256 recorded. A Qdrant restore was **not** tested. Their server-side
  snapshots were retained. PostgreSQL/Qdrant are not a distributed atomic dump;
  collection pipelines were idle throughout acquisition.
- `project-state.tar.gz`: source, scripts, docs, tests, dependency manifests,
  compose config, AGENTS and catalogue/wave receipts. Does not include `.env`
  secrets, Ollama model weights, all local caches/exports or a filesystem image.

Exact executed backup/verification procedure is preserved in
`var/performance-20261003/backup.py`. It uses a fixed new output directory and
must not be rerun as a refresh command. To verify restore again, use a **new**
isolated database name and the existing dump; never target `app` for a test.
The copy remains on the same machine; it does not protect against disk loss.

## Changes and measurements

1. Discovery reads sitemap HTTP data while the existing sequential jobs-hub
   traversal runs. Maximum sitemap/hub requests, candidate order, provenance,
   redirects and external ATS navigation remain bounded as before. TaskGroup
   cancels sibling work on failure/cancellation. No concurrent GPU pipelines.
2. A representative live probe exposed social share actions containing the jobs
   URL in query parameters. They entered model candidates and consumed hub
   visits. Discovery now excludes known share endpoints and non-HTTP schemes;
   ordinary ATS links, query-based listings and real LinkedIn job URLs remain.
   This is shared action filtering, not an institution allowlist.
3. Previously prepared BITE fix was also deployed: missing jobPostings is empty
   only with validated offset0,total0. Nonempty/truncated payloads still fail.

Read-only probe used real Crawl4AI requests, no model, no database writes:
`var/performance-20261003/probe_io.py`, result `io-profile.json`.
INP: sitemap2.803s, hubs3.276s, collection wall3.287s vs component sum6.079s.
IPS: sitemap0.476s, hubs4.250s, wall4.257s vs sum4.726s.
Component sums estimate serial cost from the same concurrent execution; they
are **not** a separate controlled before/after measurement of the full pipeline.
On the captured IPS candidate list, the second filter removed7 share/action
links out of12; INP retained all16. No whole-pipeline speedup is claimed yet.

Final checks before deploy:1,117 unit tests passed, full Ruff and mypy129 files
passed. Both changes are in healthy API image
`sha256:030eb5463665cdf5adb21469547c81d8e0272f60c8b4a785a08bb49717292ce2`.
Rollback image: `phd-searcher:before-discovery-overlap-20261003`. Rebuild/recreate
was limited to API while no run or queued job was active. No migrations.

## Autonomous validation cohort

Prepared3 October, actually queued4 October at00:58. Durable plan:
`var/performance-20261003/canary-plan.json`.
60 new institutions:30 education,30 facility,14 countries. Existing inventory
eligibility, shared hosts, sources, jobs and live exact ILIKE name scope checked.
47 ambiguous candidates were skipped before enqueue; endpoint remains authoritative.
No completed institution/run was intentionally reprocessed.

Schedules2779–2838, all60 accepted once through native expansion endpoint.
At00:58:55:2779 RUNNING as2919;7WAITING_PIPELINE;52SCHEDULED.
Provider verification: ollama/gpt-oss:20b and ollama/nomic-embed-text at
http://ollama:11434. Native governor_plan admission applies at actual launch.
Per job: discovery1/schema3/scrape3/quality3/index150,max_pages3.
No evidence/review/review2/enrich. Expiry2026-10-05T20:41:23+02:00 concerns new
launches; existing retry/request bounds and pipeline lock remain enforced.
Central estimate8,220s (~2.28h), based on wave2.5 education129.8s/facility143.4s
means in equal proportions, with no assumed speed gain. Suspend/admission can delay it.
Only2838 carries the bound chat wake; verify every ID at the event because final
ID is not a completion barrier. Valet timer verified active.

Known work deferred: larger catalogue waves depend on measured cost and yield;
BITE1736/run1867 technical recovery needs Resume of that same run (currently
not resumed); historic manual stops stay untouched. Evidence/source ownership
repairs need scoped samples. Do not mass-review/reconcile28k records. Further
catalogue entries have not been exhaustively reviewed. Two hours of bounded,
useful validation was selected without treating quota reset as a deadline.

Next checkpoint: aggregate all60 outcomes, timing by cohort and discovery
outcome, source/position yield and failure reasons. Cohorts differ from historical
wave2.5, so a change in average alone is not causal proof. Before riskier model
or concurrency changes, add durable per-stage timing/model-call measurements;
prioritize repeated model work, job overhead and known adapter reuse according
to observed cost. Keep acquisition of new sources separate from recurring
refresh of known sources; first-pass catalogue timing is not the refresh SLA.

## Reconciliation note

An old preparation helper had an unguarded asyncio.run(main()) at import. During
preparation it rewrote the old wave2.5 manifest with duplicate receipt entries,
while reusing the same1100 existing schedules. Database verification remained
2778 total jobs, max2778,zero active: no pipeline or schedule was duplicated.
The original manifest was restored byte-for-byte from the fresh project backup;
the unintended file was retained under var/performance-20261003 for audit.
The new helper strips that entrypoint before loading preparation functions.
Do not import/execute historical queue scripts casually.

## Canary result and next measurement, 02:55 on 4 October

Final consistent snapshot: `var/performance-20261003/canary-final-check.json`;
report: `canary-final-report.json`. All60 schedules and runs DONE, none active or
failed. Mean118.3s, median85.6s; discovery21done/29no_listing/10failed.
41 sources at19 institutions,128 position rows and15 current SQL indexed
markers at5 institutions. Different institutions from wave2.5 make timing
comparison descriptive, not causal. Markers do not certify unique searchability.

Per-stage and discovery/schema model-request wall time/count/failure counters
are now persisted under each stage checkpoint's `performance` key. They survive
Resume, with best-effort writes that do not change pipeline outcomes. These
measure HTTP wall time, not actual GPU occupancy. Deployment passed1,118 unit
tests, Ruff and mypy129 files. Healthy image:
`sha256:40fd893f6bd1869b3f91ed75c8d67206dc64e589b69522bb42aaade477a43200`;
rollback tag: `phd-searcher:before-timing-20261004`.

The next bounded cohort is100 new institutions,50 education/50 facility, from
12 countries: schedules2839–2938, plan
`var/performance-20261003/timing-profile-plan.json`. At02:55 one was running
as run2979, seven waiting,92 scheduled. Only2938 requests a Valet wake.
Identical stages and limits to canary; central estimate11,830 seconds (~3.29h)
from its118.3s/job measured mean. This cohort's purpose is to identify dominant
stage/model cost while adding eligible sources. Larger waves and structural
speed changes await its result. Fifty ambiguous name-scope candidates were
excluded before scheduling; no completed job was knowingly repeated.

## Exact-snapshot index cache and field validation, 06:17 on 4 October

All100 profile schedules and runs are DONE. Mean126.4s, median88.6s/job;
104 sources at38 institutions and29 current SQL indexed markers at11
institutions. Stage profile measured5,006.2s total in index (~50.1s/job),
3,867.9s in schema (3,571.3s in93 model HTTP requests),2,244.7s in discovery,
172.9s in scrape and29.5s in quality. A zero-yield institution still paid
almost49s for index. The hot path revalidated10,186 existing indexed records
for every institution.

Read-only cProfile on1,000 indexed rows attributed6.17s CPU to verification
and0.16s to loading the sample. A bounded process-local cache now reuses a
gate result only for an identical snapshot of all persisted position/source
fields on the same local date. It stores only SHA-256 keys and immutable
results, expires at date change and on restart. Edits to evidence, source
quality, closure or screening status force fresh evaluation; eviction only
costs another evaluation.

Read-only comparison of old, cold-cache and warm-cache gates on all10,186 real
indexed records found zero different decisions. Times:46.27s old,46.58s cold,
0.67s warm. This is a component result; the projected whole-pipeline saving
is about45.6s/job, pending the next cohort. Final checks:1,127 unit tests,
Ruff and mypy129 files passed. Healthy API image:
`sha256:eea99b17e0861294a90467bf2c667ccc2ec2f14bc14352236fccad5ef8073e48`;
rollback tag:`phd-searcher:before-verification-cache-20261004`.

Validation plan:`var/performance-20261003/cache-validation-plan.json`.
200 unique new institutions,100 per group,20 countries, schedules2939–3138
accepted once. At06:17 all200 were queued, with none observed started. Only
3138 requests a Valet wake; inspect every manifest ID at its event. Same five
stages and limits as the100-job profile. Central estimate16,200s/4.5h uses the
measured component saving; it is a projection. Larger scale and schema/model
changes await this whole-pipeline result. No additional work was queued to
fill idle time.

## Completed cache cohort and next bounded acquisition, 10:49 on 4 October

The untrusted receipt for schedule3138 was verified against schedule3138/run3275
and a consistent DB snapshot. All200 schedules2939–3138 and runs are DONE;
global queue was empty before the next launch. Snapshot:
`var/performance-20261003/cache-validation-event.json`; aggregate report:
`cache-validation-report.json`. Mean82.7s and median27.4s/job versus126.4s
and88.6s in the preceding 100-job cohort. Different institutions mean the
whole-job difference is descriptive. The repeated index stage fell from
50.06s to4.03s/job; the new existing-verification substep averaged1.24s,
median0.85s, with one47.76s cold run. This is consistent with the read-only
component validation and a large real index-stage saving.

Stage totals across200 jobs: discovery4,054.2s, schema9,796.8s,
scrape328.0s, quality61.8s, index805.1s. Schema model HTTP calls numbered217
and consumed9,198.4s; discovery model calls numbered120 and consumed698.4s.
The schema stage is now the main throughput bottleneck. The cohort added227
listing pages at67 institutions,448 position rows, and51 current SQL indexed
markers at22 institutions. Discovery:74done,98no_listing,28failed. These
markers are not a distinct verified searchable opportunity count. Facility
institutions produced40 markers in14/100 institutions and mean98.1s/job;
education produced11 markers in8/100 and mean67.3s/job. Yield differences
may reflect cohort mix and should guide sampling, not create a global source
verdict.

A bounded next tranche takes500 previously unprocessed research facilities,
26 countries,500 unique hosts/IDs, after live duplicate and exact name-scope
checks. Forty-five ambiguous names were skipped. Plan and helper:
`var/performance-20261003/research-facility-wave-plan.json` and
`queue_research_facilities.py`. The first POST failed422 on a decimal
estimated_seconds; DB max ID remained3138, so no job was created. The helper
was corrected to integer98 and500 schedules3139–3638 were accepted once.
At10:49:1running,15waiting_pipeline,484scheduled,zero failed. Native governor
plan is present on all500; only3638 asks Valet to wake this root. Same
five-stage limits as the cache cohort; no review/evidence/enrichment. Central
estimate49,050s (~13.6h) uses the100-facility measured mean98.1s and is not
a deadline. The scheduler keeps serial execution and durable recovery.

Further facility/education activation and schema change deployment wait for
this tranche's representative results or a separately validated improvement.
Known independent candidates were reviewed in CURRENT_STATE; the queue stops
at500 because larger selection and model changes need another cost/yield
decision, not because all catalogue work is exhausted.
