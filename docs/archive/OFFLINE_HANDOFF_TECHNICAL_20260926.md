# Offline handoff — 26 September 2026

## Essential baseline completed — 2026-09-26T19:23:25.521992+02:00

Governor NORMAL. Essential release scope agreed26September is complete and usable;
not exhaustive registry coverage or future/secondary features. See
ESSENTIAL_RELEASE_20260926.md. Current imageed09d3224642b0c86c4a54848e39d93efe66c357ab49f1dcfc1c18a0591a3907 healthy.
1104tests/Ruff/mypy PASS; realbrowser search/uncertainty/details/save-reload-unsave PASS.
FinalAPIchecks PASS, var/release-baseline-20260926/final-check.json.
Latest schedule44/run156 DONE; noactivequeue.43/155 and earlierDONE preserved.

AIT103575 one grounded nonmanualkind correctedprogramme→vacancy using fresh public
HTML and shared singular-PhD-project rule. SameID,PhD type,dates/verdict unchanged.
Receiptait-kind-repair.json containsbeforevalues; ait-kind-verification.json proves
livekindvacancy. No bulkupdate. Allprior userwork andfeedback12–15 preserved.

Imperial4sampleitems verifiedagainstofficialfeed: exacttitle/deadline andfullapptext.
Browser listing403, no invented publicdetailURL; publisherapplicationURL retained.
EURAXESS59872 EXPIRED is inlinehidden template withfutureexpiry2026-10-01T13:16:37Z;
not proof of currentvisibleclosure. Remainsprobable/open-statusuncertain.
These are documentedlimitations, not unresolved fabricated opportunityfacts.
Initial20recordaudit findings resolved/excluded or explicitly qualified; no
statisticalaccuracyclaim and no claimallcatalogueentitiesactivated.

Localcheckpoint bundle preservestrackedpatch+newsource/docs/tests withhashes/baseHEAD,
no commit/reset/push. No acceptancejobsremain. Futuremaintenance may expandcoverage
but do not repeatcompletedcanaries. Heartbeat remainsPAUSED; no governorquotaqueries.

## Senior-role canary complete — 2026-09-26T07:47:42.724451+02:00

Schedule43/run155 DONE; verification passed: same103964/publicURL, research_staff,
application deadline2026-10-12, live search[103964,103962], probable flagsopen_status/details.
Receipt var/release-baseline-20260926/senior-canary-verification.json. Do not repeat.
1100tests/Ruff/mypy passed; runtimeb3d48723b6aa32cbe43b628b754ae66001a9216e886e379832aada206262c208.
Governor WATCH: bounded follow-up diagnosis of existing ImperialTalentLink feed
underway (no newmodels/runs). ExistingadapterusesapplicationUrl fallback; need
observedpublicdetailroute. Keep currentIDs/dates/evidence, do not replaceURLs blindly.

## Newer checkpoint — 2026-09-26T07:46:06.134526+02:00

Senior-role fix is tested and released (1100tests/Ruff/mypy). Healthy image
b3d48723b6aa32cbe43b628b754ae66001a9216e886e379832aada206262c208.
Schedule43/run155 is active, evidence1/index20 for103964, governed and idempotently
recorded. This supersedes the earlier warning not to enrich that record: the
classification fix has now passed its real-HTML preflight. Verify existing job43;
do not start another run. Receipt senior-canary.json and verification script
var/release-baseline-20260926/verify-senior-canary.py. Expected research_staff,
12October2026deadline, sameID/publicURL. Other audit blockers remain.

## Latest checkpoint — 2026-09-26T07:39:15.379242+02:00

This section supersedes the earlier active-queue snapshot below. Schedules40–42
and runs152–154 are DONE, latest154; active queue empty. Healthy image now
sha256:0e15f0b9860b3b50d5f5dbd789a59b6a4824db5920dac78a5fa4b3a531113760.
1096 tests/Ruff/mypy passed; test log /tmp/phdbot-audit-tests-20260926.log.
See RELEASE_AUDIT_20260926.md for20-record audit findings, four exactID hides,
remaining Imperial URL/AITkind/EURAXESS conflict issues and next work.
Do NOT enrich/index MPI group-leader103964 before fixing senior-role precedence:
offline classifier currently calls itphd from context, although it is a senior job.
No new unattended jobs: dependent work needs that review, not speculative retries.
Existing status commands below were retested; stop/resume/cancel still not invoked.

Prepared for the user-approved essential release target of 3 October; see
RELEASE_BASELINE_20260926.md. This is a runnable worktree checkpoint, not a claim
that the complete release audit has passed. Existing user scheduler/compose/AGENTS
changes and new adapter changes are preserved together, without a reset.

## Working version and evidence

API image `sha256:ba30acccc68659efd786ad527eefc261927ebd88db1e5bf1f946dfb49dd7ef00`
was deployed with the idle guard and observed healthy at 02:05:50 CEST.
1084 unit tests, Ruff and mypy passed before deployment. Full test output:
`/tmp/phdbot-release-tests-20260926.log`. No schema migration or bulk data repair.
BITE live adapter check returned two actual psychiatry public URLs, without an
LLM. It is now deployed; complete pipeline/search validation is still pending.
Umantis run151 is DONE and must not be repeated.

## Durable work

- Schedule40 / run152: MPI Psychiatry19762, running at the launch checkpoint.
- Schedule41: Research and Innovation Foundation9383, waiting for pipeline.
- Schedule42: CREAF16890, scheduled independently.
- Rockwool9164 was NOT activated: ambiguous name scope. Defer ID-scope repair;
  do not bypass the guard. Receipt records the 409 response.

Each job has discovery1/schema2/scrape2/quality2/index150, max_pages2, no deep
review/enrich, governor_plan checked by the native scheduler at dispatch.
Central rough estimate600seconds per job (30minutes for three admitted jobs).
Comparable completed runs144–147 took56–387seconds. Compare actuals on return;
this is not a wall-clock guarantee. Expiry is recorded separately in each receipt.
HTTP/model timeouts and retry budgets bound operations; there is no aggregate
wall-clock kill timer. Pipelines are serialized, use local Ollama GPU, and suspend
when the system sleeps. No model/cloud route is needed for these prepared jobs.
Verified runtime routes: ollama/gpt-oss:20b and ollama/nomic-embed-text, both at
http://ollama:11434. Public website/search requests still require Internet access.

Receipts: `var/release-baseline-20260926/job-*.json`, including purpose, exact
request, expiry, expected output, authorization, resource limits and commands.
Queue ends at this representative evidence milestone: further repairs depend on
its results. Do not schedule speculative repeat runs or fill GPU idle time.

## Commands and their verification status

Run from `/home/giaaaacomo/Progetti/PHDBOT`. These READ commands were exercised:

```sh
curl -fsS http://127.0.0.1:8003/v1/pipeline/status
curl -fsS 'http://127.0.0.1:8003/v1/schedules?active_only=true'
docker inspect phdbot-api-1 --format '{{.Image}} {{.State.Health.Status}}'
```

The activation script `.venv/bin/python var/release-baseline-20260926/queue.py`
was exercised and created schedules40–42. It preserves receipts and the API
preserves existing institution schedules. Do NOT rerun as a generic Start command:
inspect existing IDs/results first. Failed or interrupted work uses Resume on the
same run when explicitly recoverable; DONE runs remain untouched.

These control routes exist in the inspected API code, but were NOT exercised in
this handoff to avoid stopping real work:

```sh
curl -fsS -X POST http://127.0.0.1:8003/v1/pipeline/stop
curl -fsS -X POST http://127.0.0.1:8003/v1/pipeline/resume
curl -fsS -X POST http://127.0.0.1:8003/v1/schedules/42/cancel
```

Check the current run/job ID before any control operation. The example cancel
ID42 is only appropriate if that exact job is still pending and cancellation is
intended. Stop preserves pipeline checkpoints; no new Start after interruption.

## Dependencies and recovery

Existing Docker Compose API, PostgreSQL5433, Qdrant6333 and Ollama11434 are needed.
Governor state directory is mounted read-only; stale/missing state or manual PARK
keeps planned jobs pending. Quota-only PARK can admit them. No polling daemon or
second scheduler was added.

Prior restorable backup: `backups/pre-expansion-20260922.dump`, SHA256
fb7ca8a1524b29884371a2adb818ee15dc9e68643ddb5c5c0e81e20072cd6376.
Its isolated restore was verified earlier; this handoff did not repeat restoration.
For scheduler rollback see GOVERNOR_SCHEDULER.md. Cancel unstarted governed jobs
before reverting to code without admission support; never deploy over a live run.
Do not restore an old DB merely to roll back code and lose current results.

## Resume priorities

Inspect schedules40–42 and actual source choices once at a meaningful checkpoint.
Validate live searchable results and keep navigation, senior roles and PhD places
distinct. Psychiatry application deadline12October differs from references19October;
current deterministic parser abstains, so a missing deadline needs explicit
uncertainty. Do not adopt API endsOn as the application deadline.
Then continue the 20-record representative release audit, defer isolated failures,
and update this handoff with actual durations and concrete next useful jobs.
