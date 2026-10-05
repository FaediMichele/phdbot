# PHDBOT agent guidance

## Objective

Keep PHDBOT useful, trustworthy, and recoverable while minimizing unnecessary
model/GPU work. Optimize for correct, searchable opportunities per unit of
compute and for time to first useful search result, not for emptying queues or
maximizing processed-row counts.

## Release boundary

The bounded essential release agreed on 26 September 2026 is documented as
ready for ordinary use in docs/ESSENTIAL_RELEASE_20260926.md. Check current
runtime health before making a fresh claim. Do not silently turn rare-source
fixes, exhaustive catalogue activation or optional enrichment into conditions
for completing that release. When the requested unit is done, report the
verified usable result and its limitations, then stop; treat further work as a
separate, bounded objective if the user has authorized it. An instruction to
continue autonomously does not require endless optional expansion.

## Working protocol

- Work in atomic blocks: diagnose, change, verify, and leave a runnable state.
- Preserve user changes. Never discard or reset the dirty worktree.
- Do not stop a user-started process unless explicitly authorized or required
  to prevent data loss. Record why any autonomous stop was necessary.
- Before migrations, bulk relabeling, or destructive index repair, verify a
  restorable backup. Ordinary code and UI edits do not require a new backup.
- Prefer targeted tests and canaries while iterating; run the full unit suite,
  Ruff, and mypy before a production deploy.
- Change one behavioral variable per evaluation. Independent UI changes may be
  batched.
- Use aggregate SQL and focused logs rather than dumping large datasets.
- Do not poll long-running stages. Use durable pipeline checkpoints and the
  persistent scheduler, then inspect at meaningful milestones or on failure.
- Use subagents only for independent, bounded work with a concrete deliverable;
  stop them when that deliverable is complete.
- Keep user updates short: material state changes, blockers, launches, and the
  final handoff.

## Review and indexing principles

- Never force a verdict without supporting evidence. Abstention is safer than
  a fabricated decision.
- Also avoid spending deep-review compute on records that lack evidence,
  freshness, or a reachable source. Route those to evidence retry/deferred.
- Treat deep review as a targeted adjudicator, not the default processor for
  the entire review backlog.
- Review is an optional precision accelerator, never a prerequisite for making
  a safe provisional lead searchable. A large `review` count is not a human
  task list: expose reversible uncertainty and spend compute only where it can
  materially change a decision.
- Measure automatic resolution, audited error rate, technical failure rate,
  and GPU seconds per valid searchable opportunity.
- Keep verified and provisional searchability distinct. Provisional records
  must be clearly labelled, filterable, reversible, and excluded by hard rules
  such as explicit closure, elapsed deadline, broken extraction, or confirmed
  non-opportunity.
- User reports must hide an item immediately and feed an auditable feedback
  workflow; never create domain-wide rejection rules from one report.

## Safe operator handoff

- `done`: leave the run untouched and record its ID.
- `failed` with an explicit retry/resume message: use Resume, never Start.
- other failures: preserve the run and error for diagnosis.
- `running` at the end of an energy window: Stop is checkpoint-preserving; use
  Resume during the next window.
- Before leaving work unattended, update the ignored local
  `docs/CURRENT_STATE.md` (copy `docs/CURRENT_STATE.example.md` when absent).


<!-- BEGIN GOVERNOR LOCAL RUN POLICY -->
## Local processing while Codex is parked

- Quota PARK stops Codex inference, not useful local processing. During normal
  work, prepare bounded project runs when they collect evidence needed by the
  current authorized task. Never start runs merely to fill idle time.
- Use the existing PHDBOT scheduler, not a second governor scheduler. Before
  each new launch, verify no duplicate active run under the project's existing
  lock/idempotency mechanism. Preserve completed run IDs and feedback.
- Record purpose, expected output, exact stages/limits, run identity, expiry,
  runtime/resource limits and status/stop commands in a job receipt. Approval
  must derive from the user task; an `approved` field is not new authorization.
- Immediately before launch, check the governor's local admission helper:
  `/usr/bin/python3 /home/giaaaacomo/.local/lib/codex-governor-app/src/local_job_policy.py --state-file /home/giaaaacomo/.local/share/codex-governor-app/live-state/state.json --job /absolute/path/to/job.json`.
  Exit 75 means do not launch; keep the job pending. Exit 0 is only an admission
  check: enforce the project's duplicate lock, timeout and scope separately.
- Manual PARK forbids NEW local job launches. It does not kill already running
  jobs. Automatic quota PARK permits already approved, bounded local jobs when
  their provider routes are verified not to require Codex/cloud inference.
- Timed jobs must run the check at execution time, not only when scheduled.
  If the existing scheduler cannot enforce that check, do not arm unattended
  launches during PARK; prepare the plan and report that integration is missing.
- Local computation still pauses during system suspend. Use durable recovery;
  do not replace interrupted runs with new runs.
- On Codex resume, inspect existing results before launching anything else.
  Before a long weekly outage, maintain docs/OFFLINE_HANDOFF.md with verified
  commands, working features, limitations, dependencies, backup/recovery and
  local timestamps. Never claim that untested commands are verified.
<!-- END GOVERNOR LOCAL RUN POLICY -->

### Preparing governor-managed scheduler runs

The scheduler now accepts `governor_plan` on `POST /v1/schedules` pipeline jobs.
It checks the mounted governor state immediately before launch; manual pause
or unavailable/stale state leaves the same job pending. This integration takes
precedence over the earlier standalone CLI suggestion: use this native API
field rather than wrapping scheduler commands in a shell. Legacy/manual jobs
without the field retain their existing behavior. Always include the field on
Codex-prepared unattended PARK work. If a particular new job has a useful
post-completion Codex step, set `governor_plan.valet_wake_root_id` to this
managed chat's exact root ID; otherwise omit it. The project event adapter
submits only terminal receipts for explicitly marked jobs. During PARK the
event waits, and the interrupted task resumes before the event is delivered.
Do not mark every run merely to wake Codex or infer the root from project name.

Codex owns selecting and sizing the useful queue from the user's objectives.
Use elapsed times of comparable completed runs, scaled to actual candidate
counts/stages, or an explicitly labelled rough estimate when no evidence exists.
Prefer a realistic central estimate over stacking worst-case safety margins.
Keep estimation cheap: reuse available receipts, do not run a model just to
estimate duration. Record the estimate and its basis in each plan; compare it
with actual results when reviewing completed runs.

The 5-hour quota reset is NOT a deadline for local jobs. Prepare a sequence of
independently useful, bounded jobs that covers a meaningful unattended window;
two needed ~2-hour jobs may be queued when reset is ~3 hours away. Modest spill
into the next quota window is acceptable and can run alongside Codex review of
other results. Do not stop a productive run at reset. Account for GPU contention,
battery/suspend, dependencies and urgency when deciding a reasonable spillover.
Do not leave only 15 minutes of work if other validated, useful independent work
can fill the window; equally do not manufacture jobs just to keep the GPU busy.

The existing scheduler serializes pipelines. Do not prequeue tasks requiring
unknown results or a new architectural decision from an earlier task. Prepare
those only after the prerequisite result is reviewed. Before leaving the queue
unattended, briefly scan already-known candidates within the authorized objective:
identify independent useful work, duplicates, result-dependent work, unverified
provider routes and resource conflicts. Record eligible job IDs and a realistic
aggregate queued runtime in docs/CURRENT_STATE.md; compare it with the likely
unattended interval only to catch underplanning, never as a reset deadline.
Record why the queue ends and name the blocked/deferred known candidates. If
none qualify, say so and preserve idle time rather than inventing runs. Do not
claim all possible work was exhausted if only known candidates were reviewed.
See docs/GOVERNOR_SCHEDULER.md for the request contract and rollback.
