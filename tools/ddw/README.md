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

### Paired schema experiment

The optional schema operation uses Crawl4AI 0.9.2's complete CSS validator and
preprocessor, plus frozen pure PHDBOT preflight/adapter/reuse functions. Provenance
is in `src/phd_searcher/ddw/reference/provenance.json`; the actual runtime helpers
were checked locally against these copies. Original production modules are unchanged.
It accepts at most 20 hash-checked snapshots and same-host/kind cache candidates.
The benchmark cohort contains 16 sanitized public snapshots, including historical
static/rendered pairs and three bounded public captures. It is a selected diagnostic
cohort, not a sample estimating prevalence across the catalogue. The three new
captures are ETH, FBK and ISTI; the remaining material is historical. Sanitization
preserved all measured preflight decisions and extracted items.

```sh
python -m pip install -r tools/ddw/schema-requirements.txt
PYTHONPATH=src python -m phd_searcher.ddw.schema_probe tests/ddw/snapshots/manifest.json result.json
PYTHONPATH=src python tools/ddw/schema_experiment.py tests/ddw/snapshots/manifest.json /tmp/schema-study-new
```

Use a fresh directory for each benchmark. The first command's finalized receipt
can be replayed without revalidation. Input identity and implementation version
must match. This bounded schema operation is a development harness, not a general
remote service: no production import, HTTP, database, rendering or model calls.
The benchmark imposes a 90-second subprocess timeout and compares serial execution
with at most two processes. It does not claim cross-host leases or general recovery.

Baseline includes existing preflight, BITE/funding routes and the current same-host
schema pool. Hosted comparison uses exact frozen source; `--live-baseline` locally
uses the actual current PHDBOT reuse helper. Prepared model input uses the production
compaction parameters and is produced only for unresolved generation candidates.
All fields and exact prepared input are compared, not just the acceptance boolean.
Ancillary LiteLLM pricing-map downloads are disabled in the experimental process;
no production environment is changed. Initial dependency installation needs network.

`audit.json` separately fixes public-DOM/manual title-link expectations. It is not
a PhD eligibility/opening audit. BITE postings are not fetched; generation candidates
remain conditional on rendering, ownership and due-state. The harness does not
represent full crawl/scrape/normalization/quality/index execution. A structurally
accepted schema can still return navigation or an application-login link, and
existing downstream repairs are outside that raw-extraction comparison.

The summary records baseline median, child startup/end-to-end, compute, hash/JSON
verification and compressed payload sizes. Transfer bytes are measured; they are
not network latency, model savings or full-pipeline acceleration. Additional reuse
and avoided-generation counters are computed against the already optimized baseline.
No infrastructure expansion is justified merely by moving identical cheap work.

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
