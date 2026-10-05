# Progressive population of the imported catalogue — 28 September 2026

User authorization at21:04: plan and perform collection from the new catalogue.
This is an active population objective, separate from the completed essential
software release. It is not complete when the first wave is queued or finished.

## Baseline and completion criterion

At21:05 the imported ROR catalogue had15,594 institutions:15,569 still catalogued,
25 already activated,23 with discovered sources,20 with stored positions and13
with indexed markers. Indexed markers are not a count of unique open vacancies.
Of the unactivated snapshot,12,749 are research-tier and2,820 core-tier.

Keep the fixed snapshot in var/catalog-population-20260928/inventory.json.
Each institution must eventually have a recorded acquisition outcome or an
explicit unresolved/deferred reason. Successful sources may publish immediately;
failed/empty/ambiguous sources must not block the rest. A bounded pass through
three sources does not establish complete institutional recall. Report source
coverage gaps separately from institution admission and from searchable results.

## Execution plan

1. Inventory: completed, read-only. No registry reimport or bulk activation.
   Snapshot records15,569 rows. Initial operational holds:1,372 shared catalogue
   hosts,71 outside the configured European activation scope,4 with sources/jobs,
   3 names containing SQL scope wildcards. Two additional ambiguous names were
   found while checking selected candidates. These are deferrals, not rejections
   or evidence of no vacancies.14,087 other records remain unreviewed.
2. First wave:30 independent institutions selected (20 ROR facilities,5 nonprofits,
   5 education entries) across20countries. Registry type determines exploration
   order only; it does not establish job relevance. Rotate countries, use a stable
   ROR hash, and recheck exact name scope. Candidates have distinct catalogue hosts,
   no sources and no prior noncancelled expansion job at snapshot time.
3. Enqueue via existing POST /v1/catalog/expansion, at most10 IDs per request,
   max_sources3/max_pages3 and governor_plan. Each institution gets its own durable
   discovery1/schema3/scrape3/quality3/index150 job. No review, enrichment or global
   rerun. Preserve local scheduler exclusion, recovery and idempotency.
4. Review the first wave at a meaningful completion/failure milestone. Save job/run
   IDs, elapsed timings, sources discovered vs processed, technical failures,
   actual live search samples, duplicates and uncertainty. Separately record real
   no-vacancy evidence and collection failures. Do not infer zero opportunities
   from zero extracted rows or propagate closure between neighbouring adverts.
5. Continue later waves from the same snapshot, refreshing only admission state
   before enqueue. Adjust wave sizes to measured cost and yield. Prioritize common
   recoverable failures separately; defer rare portal repairs. Existing-source
   entries need scoped collection, ambiguous names need explicit ID scoping,
   shared hosts need ownership review, and71 cross-border entries need a scope
   decision/implementation. Do not silently omit these from the population report.

## First-wave resources and queue stop rule

Rough central estimate360s per institution,30 jobs=10,800s (3h). Comparable
three-source jobs157/158 took238/433s; the heterogeneous wave is not a throughput
benchmark and future total completion ETA is not established. Measure actuals
before extrapolating15k entries. One serialized pipeline/GPU; existing HTTP/model
retry/output limits. No aggregate hard kill timer. Suspend pauses processing;
recover the same run. Use local Ollama routes only and verify runtime provider
model/base before enqueue. Expire admission plans24h after preparation, not jobs
already running. A quota reset is not a runtime deadline.

The intended unattended interval is not specified. Three hours provides useful
independent work for this first measured wave; do not stretch or truncate it to
match a quota reset. Stop the prepared queue after30: reviewing this more diverse
wave is necessary before choosing scale/cost for the next one. The14,087 unreviewed
records are not claimed exhausted. Known CISPA link/duplicate refinements and
historic failed/no_listing institutions remain separate repair work. Completed
GEOMAR/CISPA runs157–159 must not be repeated.

## Durable receipts and safe resumption

- inventory.json and wave1-candidates.json under var/catalog-population-20260928/.
- Record request, accepted schedule/run IDs, timestamps, provider checks, duration
  basis, authorization, status/stop/cancel instructions in wave1-jobs.json BEFORE
  leaving the queue unattended. No current job IDs until the scheduler accepts.
- Before initial enqueue, inspect active jobs once. If resuming a partial enqueue,
  reconcile by expansion_institution_id and reuse existing schedules. Never require
  an empty queue when it contains this wave's own jobs; never duplicate them.
- Use native governor_plan admission, not a separate scheduler or quota polling.
- After enqueue, read each accepted schedule once to distinguish queued/running;
  report once, then inspect only at a meaningful completion/failure milestone.

## Wave 1 armed — 29 September 2026, 01:40

Native PHDBOT scheduler accepted IDs48–77 for the30 reviewed candidates, three
batches of10. Receipt: var/catalog-population-20260928/wave1-jobs.json. At the
post-acceptance snapshot every job was scheduled; no start was confirmed.
Estimated useful queued runtime10,800s (~3h). The queue ends after this wave
because further wave size and priority depend on measured yield and failure types.
Retain the job IDs and inspect at a meaningful completion/failure milestone.
