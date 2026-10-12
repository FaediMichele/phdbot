# PHDBOT DDW v1 experiment

A portable deterministic executor for **explicitly assigned** public HTML pages.
It has no PHDBOT database connection, model inference, scheduler, deployment or
canonical publication capability. The CI experiment uses only synthetic HTML;
successful CI is not evidence of production throughput or live-site compatibility.

## Install and run

Python 3.13 and the three pinned lightweight dependencies are sufficient. From
the repository root (or an extracted `worker.zip`):

```sh
python -m pip install -r tools/ddw/requirements.txt
PYTHONPATH=src python -m phd_searcher.ddw.worker run task.json --spool output
```

The archive includes the worker and the existing pure `schema_quality` module;
no application settings or production dependencies are loaded. Linux is validated;
the code uses portable subprocess/file APIs but Windows/macOS are not yet tested.
Set PYTHONPATH using the equivalent shell syntax on Windows. Unix children also
have a 512 MiB address-space cap and a CPU-time limit; on Windows only the parent
deadline and input/output caps apply. Do not claim equivalent memory isolation.

`--allow-network` explicitly enables assigned HTTPS fetches. URLs must be in the
task's host allowlist. All DNS answers must be globally routable; the connection
is pinned to a validated IP with hostname TLS verification. No redirects, proxies,
credentials, cookies, browser rendering or discovered-link traversal. Non-200,
compressed or non-HTML responses are errors. Requests are serial with a one-second
gap in network mode. The operator must approve public URLs, schemas and applicable
site access policy; a hash or allowlist does not establish that authorization.
The initial workflow never enables network fetching.

## Task and result contract

The JSON task contains exactly:

- `version: 1`, `cycle`: stable refresh/assignment label, `expires_at`: timezone-aware ISO timestamp.
- `timeout_seconds`: 0.05–10 per page, including child startup; total execution budget 60 seconds.
- `allowed_hosts`: at most 8 explicitly approved hostnames.
- `pages`: 1–8 unique URLs, each with `url`, `schema`, `schema_sha256`.
  Fixture pages also include UTF-8 `html` and `html_sha256`.

`schema_sha256` hashes canonical JSON (sorted keys, compact separators, UTF-8,
no NaN). The schema supports `baseSelector`, optional `name`, `fields` and
`baseFields`. Fields use `name`, CSS `selector`, and `type` text or attribute
with `attribute`. Unsupported nested/regex/transformation/rendering features are
rejected, never silently approximated. Base fields operate on the repeated node;
ordinary fields select descendants. This is a bounded subset, not full Crawl4AI
compatibility. Existing PHDBOT structural schema checks are reused unchanged.
Title is required. Zero matches is an extraction error, never a no-vacancies verdict.

Limits: 1 MB HTML/page; at most 500 items and 16 fields; 20,000 characters/value;
4 MB output/page. The task is fully supplied before work starts. Byte-identical
canonical input gives the same `work_key` (SHA-256), independent of attempt or
machine. Preserve the original task on retry; a new cycle/input is new work.

The spool is `output/<work_key>/<attempt>/`. Attempts are explicit integers 1–3,
with no automatic retry. A local exclusive claim prevents overlapping attempts
for the same work in the same spool; it is not a cross-machine lease. Atomic files
record task, per-page body bytes/base64, hashes, extracted values, observation
time and receipt. Receipt states: running, complete, partial, interrupted, expired.
Only all-successful pages yield complete. CLI returns 0 for complete, 2 for other
final outcomes. Each final page accounts for success, error, timeout or unprocessed.

Replaying a finalized attempt verifies and returns it without execution. A new
explicit attempt preserves earlier receipts. SIGTERM/KeyboardInterrupt stops the
in-flight child and records interruption. SIGKILL/power loss may leave an active
claim and running receipt: fail closed, inspect that execution has ended, remove
only that work's stale empty `active` directory, then choose the next attempt.
Do not overwrite the unfinished receipt or steal a claim automatically.

```sh
PYTHONPATH=src python -m phd_searcher.ddw.worker verify output/WORK_KEY/1 WORK_KEY
PYTHONPATH=src python -m phd_searcher.ddw.worker run task.json --spool output --attempt 2
```

Verification checks assignment identity, hashes and completeness; it does not
authenticate a remote worker, establish freshness at import time or prove a
website's assertions. Results are observations, not opportunity/closure verdicts.
The caller must retain its expected work key. A production importer and assignment
authority are outside this experiment. Treat spool and inputs as trusted local
paths; do not share a writable spool with untrusted users.

## CI and artifacts

```sh
PYTHONPATH=src python -m unittest discover -s tests/ddw -v
PYTHONPATH=src python tools/ddw/experiment.py /tmp/ddw-experiment
```

The second command is repository-only and creates a synthetic assignment,
executes and replays it, verifies its result, and builds `worker.zip`,
`experiment.json`, receipts and `checksums.json`. Packaging uses an explicit
source allowlist. No .env, database, project logs or private documentation enter
the artifact. The GitHub workflow records the exact source SHA, pins official
actions to commit SHAs, uses read-only contents permission, a five-minute timeout,
one concurrent run per branch and three-day artifact retention. It runs on pushes
to `experiment/ddw-v1`; manual dispatch becomes available after the workflow is
present on the default branch. No cron, privileged self-hosted runner or production
deployment is configured.

Download a successful run's artifact, check all file hashes and its source SHA
before installation. Keep prior extracted versions in separate directories for
manual rollback. Dependency pins aid repeatability; offline dependency bundles,
release signatures/attestations, automatic updates and production imports are
future work. Checksums provide integrity, not authenticity on their own.
