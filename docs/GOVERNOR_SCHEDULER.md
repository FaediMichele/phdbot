# Governor-managed local schedules

Opt in through `governor_plan` on POST `/v1/schedules`; no new DB migration.
The plan is persisted in the existing payload and exposed by schedule GETs.
Example shape (fill actual scope, estimated duration and future timestamps):

```json
{
  "target": "pipeline",
  "run_at": "2026-09-25T15:00:00+02:00",
  "pipeline": {"stages": ["index"], "limits": {"index": 20}},
  "governor_plan": {
    "cwd": "/home/giaaaacomo/Progetti/PHDBOT",
    "objective": "State the missing result needed by the authorized task",
    "expected_result": "State the measurable output and where it is recorded",
    "estimated_seconds": 7200,
    "estimate_basis": "Explain comparable runs, volume scaling or rough estimate",
    "expires_at": "2026-09-26T15:00:00+02:00",
    "approved": true,
    "requires_codex": false,
    "provider_routes_verified": true
  }
}
```

This is a shape example, NOT an approved job or benchmark for indexing20 records.
Dates must be chosen at planning time; expiry concerns starting a stale plan,
not stopping an active job. Flags record checks made by the planner; they do not
constitute independent authorization or a network sandbox.

At dispatch, a plan-bearing job reads PHDBOT_GOVERNOR_STATE_FILE. Manual PARK,
state older than30 seconds, missing project enrollment, expired plan, unknown
PARK cause or controller failure -> waiting_pipeline with a reason, no new run.
Quota-only PARK allows work. Pipeline exclusion and scheduled_job_id remain
owned by PipelineRunner. No new model call, quota poll or daemon is introduced.
Waiting for the governor or another pipeline does not consume execution retries.
Existing/manual schedules without a plan keep existing semantics. Direct manual
pipeline starts are not intercepted by this scheduler-specific integration.

Codex should prepare several useful independent runs when warranted, recording
realistic estimated_seconds and estimate_basis. Use central timings of comparable
runs and scale to work volume. No reset-time cutoff is enforced. A two-hour run
can start shortly before reset and finish later; do not kill it at quota renewal.
Queue length is determined by useful available work and acceptable resource
occupation, not by filling time at all costs. GPU pipelines remain sequential.
Dependencies requiring reasoning are reviewed after completion, not blindly chained.

The compose API mounts only the controller state directory read-only (directory
mount preserves atomic updates). Override PHDBOT_GOVERNOR_STATE_DIR for another
host. Without a readable state, planned governed jobs remain pending.

Rollback: retain prior image tagged phd-searcher:before-governor-scheduler-20260925.
Do not roll back while governed schedules are pending: the old scheduler would
ignore their plan field. First cancel such unstarted jobs through the normal API
and record their plans; ensure no run is active. Restore the compose file backup,
retag the prior image to phd-searcher:dev and recreate only api without rebuilding.
No DB restoration is necessary; keep completed runs and feedback intact.

Catalog activation also accepts optional `governor_plan` on
`POST /v1/catalog/expansion`, using the same contract. It is copied into each
new institution schedule inside the activation transaction. Duration estimates
apply to each individual job. Repeated activation preserves the original schedule
and plan; it does not replace them or create duplicate runs. Existing UI/manual
requests without the field retain their behavior.

## Optional Valet completion wake

For a newly scheduled job that should wake the same governed root after a durable
terminal result, set `governor_plan.valet_wake_root_id` to that root's exact ID.
Omit it for exploratory/maintenance jobs that do not need a model continuation.
The host-side Valet adapter reads only terminal schedule receipts, verifies the
project/root pairing again and submits a fixed, idempotent event to the existing
Valet outbox. It cannot send project-chosen prompt text. During quota or manual
PARK, the event waits; an interrupted user turn resumes first. A failure or
uncertain delivery requires attention rather than a blind retry. The field does
not alter the scheduler's job execution or governor admission.

### Completion of a whole wave

The numerically last schedule can finish before earlier schedules. Its wake is
only evidence about that job. For a bounded cohort of 1-100 schedules, the
optional local `scripts/wave_event_bridge.py` reads explicitly registered IDs
and publishes one terminal receipt after all IDs are done, failed or cancelled.
It uses the existing paired Valet outbox; it never launches or retries pipelines.

`make wave-events-install` installs its one-minute user timer. Register a file
`var/wave-watches/wave-NAME.json` with `event_id` (starting `wave-`), a unique
`schedule_ids` list, the exact `valet_wake_root_id`, and `delivered:false`.
The root must match the existing pairing. Receipts live in `var/valet-events/`;
delivery is durable and idempotent. A missing/active schedule produces no wake.
An uncertain outbox submission needs inspection, not a new event ID.

This observer was installed and exercised against an active 20-job cohort on
4 October; terminal aggregation and failure/cancellation rules have unit tests.
The first real whole-wave terminal delivery remains to be observed.
