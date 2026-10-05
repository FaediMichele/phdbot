# PHDBOT

PHDBOT finds research and higher-education opportunities across European universities,
research institutes, centres and foundations. It collects vacancy pages, extracts
opportunities and provides search, institution browsing, review history and exports.
The [essential release](docs/ESSENTIAL_RELEASE_20260926.md) is usable; catalogue
activation and rare portal coverage continue incrementally.

The local stack uses FastAPI, PostgreSQL, Qdrant and Ollama. Collection and indexing
can use provisional leads without waiting for optional deep review. A search result
is a lead to check at its official source, especially when marked **Probable**.

The institution catalog has two explicit tiers: `core` universities obtained from the Wikidata
university hierarchy, and conservatively admitted `specialist` institutions (such as universities
of applied sciences, art/design academies and conservatories). Specialist records must belong to
higher education, have an official website and minimum public documentation, and expose a ROR or
WHED identifier; individually verified institutions can be maintained as curated exceptions.
Audited official vacancy portals can likewise be kept in a small curated-source registry when
generic discovery misses them; they complement normal discovery rather than replacing it.
An additional conservative `research` tier covers research institutes/centres with an official
website, ROR identifier and minimum public documentation. ISTI-CNR and FBK are curated seeds.

## Quickstart

Requirements: Docker with Compose and NVIDIA GPU support for the local Ollama
container, Python 3.13 and `uv` for host-side development. Copy `.env.example`
to `.env` only on first setup and adjust local settings. Compose reuses an
external `ollama_ollama` model volume; on a new machine, create it with
`docker volume create ollama_ollama` before `make run`. The first Ollama start
downloads the configured language and embedding models and can take much longer
than subsequent starts. The optional Open WebUI profile also needs its external
`ollama_ollama-webui` volume. See the [operator handoff](docs/OFFLINE_HANDOFF.md)
for an existing installation's use and recovery.

```bash
make setup          # uv sync (main + integration), enable git hooks
make run            # API, PostgreSQL, Qdrant and local Ollama (API on :8003)
make migrate        # migrations, if needed; API startup also applies them
make test-unit      # unit tests
make stop           # stop the stack; persistent Docker volumes remain
```

Open <http://localhost:8003/>. `GET /health` checks API availability. To inspect
an existing installation without starting new work:

```bash
docker compose ps
curl -fsS http://127.0.0.1:8003/v1/pipeline/status
curl -fsS http://127.0.0.1:8003/v1/pipeline/thermal
curl -fsS http://127.0.0.1:8003/v1/schedules
```

### What to do in the browser

1. **Search** with a phrase or choose an institution and leave the phrase empty
   to browse its indexed opportunities. Filter by role, country, deadline,
   compensation and verification. **Verified** has a final accepted verdict;
   **Probable** is explicitly uncertain and can be hidden with the verification
   filter. The uncertainty tiers are heuristics, not calibrated probabilities.
2. Open a result and follow its official vacancy link. Save useful items in the
   **Saved** tab, including its deadline calendar. Saved items live in this
   browser's local storage; use HTML/PDF/CSV/JSON export for a portable copy.
3. Report an incorrect result from its detail view. This hides that result in
   the current search and records reversible, auditable feedback about that
   specific item. One report does not reject a whole institution or URL family.
4. Use **Coverage** to see which institutions are merely catalogued, which have
   sources or extracted records, and which have searchable results. These counts
   measure different steps; an extracted row is not necessarily a current vacancy.
5. Use **Pipeline** and **Schedules** to collect new sources or refresh selected
   ones. A useful first pass is discovery → schema → scrape → quality → index.
   Review, evidence, second review and enrichment are optional precision passes.
   The scheduler persists across API/host restarts and serializes pipeline runs.
   Stop keeps a checkpoint; Resume continues the same run. Inspect a failed run
   before deciding whether to resume it. Do not start a duplicate for an already
   queued institution.

The [operator guide](docs/OFFLINE_HANDOFF.md) covers daily use and recovery;
[catalogue population](docs/CATALOG_POPULATION_20260928.md) explains expansion
beyond the original universities. The catalogue contains more institutions than
have been processed; adding an institution to the catalogue alone does not make
its opportunities searchable. Discovery also checks jobs/careers pages and
external recruitment hosts, whose ownership and listing scope must be verified.

### Thermal protection on the local machine

On this Compose installation, the CPU watcher samples the host's kernel CPU
sensor every 5 seconds. At or above 95 °C for 60 seconds it holds new pipeline
work at safe checkpoints; 102 °C requests a hold immediately at the next safe
boundary. It resumes after 30 seconds at or below 85 °C. Startup and lost sensor
readings also hold work until a fresh cool interval is observed. An in-flight
network/model request can finish before the hold, so this is not firmware-level
emergency protection. It reads CPU temperature only; GPU and disk temperatures
remain outside this watcher. The API status and Pipeline tab show its state.
Supported Linux CPU sensor drivers are `k10temp`, `coretemp` and `zenpower`.
Check the thermal endpoint on another machine before collecting data: an
unsupported or inaccessible sensor deliberately holds work. The watcher can be
disabled explicitly with `PHDBOT_THERMAL_ENABLED=false` when providing another
monitoring arrangement. These thresholds are the current laptop configuration,
not a hardware-independent temperature recommendation.

Actual pauses and critical readings are logged in `exports/thermal-events/`.
For this installation, `make thermal-events-install` installs a local user timer
that forwards pause and critical observations to desktop notifications and the
existing paired Valet outbox. During Codex PARK the chat notification waits for
resume; a local desktop notification can still appear. Once ordinary behaviour
is established, set `PHDBOT_THERMAL_NOTIFY_PAUSES=false` in `.env` to retain
pause logs without routine notifications; critical notifications stay enabled.
The timer also writes bounded 10-second samples during active or thermally held
runs in `var/thermal/samples-YYYYMMDD.jsonl` for measuring behaviour. Temperature
thresholds are Compose environment variables; see `docker-compose.yaml`.
Temporary CPU-budget experiments are optional: `scripts/thermal_cpu_trial.py`
uses an explicitly prepared local lease in `var/thermal/cpu-trial.json` to limit
only the original PHDBOT Ollama container. The same thermal timer restores its
previous positive budget at the registered wave's completion or lease expiry
(at most six hours), and preserves competing operator changes. Trials starting
from an unlimited budget are rejected: Docker ignores `--cpus 0` during update.
Legacy leases in that situation enter `recovery_required`; restoring the exact
unlimited configuration requires an explicitly authorized container recreation. It never launches jobs.
The timer and Docker access must remain available for automatic restoration;
a restart resumes lease reconciliation. No adaptive CPU throttling is enabled
by default, and a lower CPU budget has not yet been shown to improve throughput.

## Control panel (GUI)

With the stack up (`make run`), open <http://localhost:8003/> — a single-page local admin UI
served by the API itself (no extra container). Tabs: **Pipeline** (live status + start/stop/resume
controls), **Coverage** (per-institution counts + totals), **Review** (reversible manual and
automatic screening), **Search** (semantic search, detail and portable export), **Saved**
(browser-local shortlist and calendar), and **Macros**
(saved refresh → search → export workflows). It just calls the JSON endpoints below over the
same origin.

`POST /v1/search {"query": "...", "country": "IT?", "university": "?", "deadline_after": "?"}` → semantic hits.
`GET /v1/positions/{id}`, `POST /v1/positions/{id}/detail-refresh`,
`GET /v1/universities` (coverage), `GET /health` for probes.

The optional precision cascade after `quality` is `review → evidence → review2 → enrich`. `quality`
detects malformed URLs, markup/script fragments, navigation and systematically broken extraction
sources without deleting scraped rows; source quarantines are visible in Coverage and are released
for normal triage if a later extraction becomes healthy. `review` is a fast first pass through a
validated LLM tool call (never free-form structured output). Its evidence must be a quote actually
present in the supplied text; automatic approval requires confidence ≥ 0.90 and automatic
rejection ≥ 0.97. Candidates with less than 200 normalized characters of attributable text bypass
the model and go straight to evidence retrieval, so GPU time is not spent judging an empty dossier.

Only the unresolved residue enters `evidence`, which fetches the detail page without changing the
verdict. URL fragments use only their attributable inline excerpt: an HTTP fetch cannot identify a
`#fragment` and must never assign the whole shared page to several positions. `review2` then
independently extracts vacancy/open-status/type facts, validates verbatim evidence and composes the
final status deterministically. It uses the configured local model, one dossier at a time, with a
bounded high-reasoning first pass and short corrective tool passes; there is no cloud judge.
The fallback states remain distinct: a genuinely insufficient source is `source_unusable`, a
structurally valid but unsupported model verdict is quarantined as `grounding_failure`, malformed
tool output stays retryable as `tool_error`, and only evidence-rich residual ambiguity becomes
`human_review`. The rejected model payload is kept in the audit but is never applied. Finally,
`enrich` completes details for eligible items. Every model/manual verdict is
appended to `review_attempts`, while the current verdict stays on the position; manual decisions
always win and survive future refreshes. The audit trail is available at
`GET /v1/positions/{id}/review-attempts`.
The shared position taxonomy includes PhD, Master/MPH, medical doctorate, internships/traineeships,
assistantships, fellowships, postdocs, research staff and faculty roles; every type is available in
the Search filters and portable exports.

Search results can be downloaded as a standalone interactive HTML report, printable PDF, CSV or
JSON. HTML embeds the selected query, filters, result details and client-side filtering, so the
recipient does not need a running PHDBOT instance.

To browse an institution without semantic ranking, select one or more institutions and leave the
query empty. This lists matching indexed opportunities without embeddings or a relevance threshold;
date, type, compensation and verification filters still apply. The score is absent (`null` in the
API), and default ordering is by catalog ID. Coverage's extracted count is not a count of searchable
openings, so it need not equal browse totals. Saved shortlists and exports support both search modes.

Search has two explicit verification modes. `verified_only` returns final accepted records;
`include_probable` also returns unresolved records that pass hard currentness, source-quality and
non-opportunity exclusions. Probable hits carry explicit heuristic uncertainty tiers (15% grounded,
35% opening status unverified, 60% strong role title with incomplete details); these are audit
levels rather than claimed statistical probabilities. Users can filter and sort by maximum
uncertainty, while the stored review verdict remains unchanged. The GUI can report a bad result to
an append-only audit queue, hide it locally and retract the report, or positively confirm that an
item is a real opportunity. Feedback snapshots the versioned URL family and its extraction context.
Only repeated independent opportunity/non-opportunity labels can produce a visible family prior;
that prior may raise uncertainty but never verifies, rejects or closes an individual sibling. A
single report therefore never creates a global rejection rule, and `closed` is an item-level
availability observation rather than evidence that the family contains fake opportunities.

Each newly collected position records an immutable `first_seen_at` and a scrape-owned
`last_seen_at` (the historical `scraped_at` API field remains as a compatibility alias). Search,
details and portable exports identify when PHDBOT first pulled and last checked the source. Legacy
records keep an unknown first-seen value instead of receiving a fabricated migration date.
Opening a missing or recognizably noisy legacy detail queues an idempotent, attributable refetch;
the existing text remains available until the replacement succeeds. An unlimited detail-enrichment
run also pays down at most 25 high-value legacy captures, so cleanup never turns into an implicit
archive-wide crawl.

The GUI's recommended **Collect & publish** action refreshes universities and sources, scrapes,
applies hard quality rules and indexes position results before enriching the separate institution
index, without waiting for model review. Fast review, evidence retrieval, deep review and detail enrichment remain optional,
bounded precision passes. This keeps time to first useful result independent from the size of the
review pool; that pool is not a mandatory human inbox.

Macros persist a search, pipeline parameters, export formats and a destination below `exports/`.
They can optionally wait for an incremental full refresh before searching and exporting. Macro
runs and pipeline IDs live in PostgreSQL and are recovered after an API restart. A synchronized or
network-shared `exports/` directory can be used as a zero-credential Drive/Nextcloud hand-off.

Pipeline configurations and saved macros can also be scheduled as persistent one-shot jobs from
the GUI. Local input is interpreted explicitly as `Europe/Rome` (including daylight-saving time),
then stored as UTC. `GET/POST /v1/schedules`, `GET /v1/schedules/{id}` and
`POST /v1/schedules/{id}/cancel` expose the same state. Due jobs survive API or host restarts,
wait if another pipeline owns the cluster-wide lock, and are attached idempotently to exactly one
pipeline or macro run. Scheduled pipelines also retry explicit transient failures at most three
times (15-minute cooldown for rate limits, 5 minutes for other known temporary failures); unknown
or persistent errors remain failed and visible for diagnosis.

## Running the pipeline

With the stack up (`make run`; migrations are applied automatically at API startup), run the
scrape stages in the API container (the image bundles Playwright Chromium for the crawl stages):

```bash
make pipeline args="universities"
make pipeline args="discovery --limit 20"
make pipeline args="schema --limit 20"
make pipeline args="scrape"
make pipeline args="quality"
make pipeline args="review"
make pipeline args="evidence"
make pipeline args="review2"
make pipeline args="enrich"
make pipeline args="index"
```

Or drive and monitor it over HTTP without the CLI: `POST /v1/pipeline/start`, `/stop`, `/resume`,
and `GET /v1/pipeline/status` (which stage is running, per-stage average time, ETA). Limits are
independent, for example:

```json
{
  "stages": null,
  "limits": {
    "universities": 50,
    "discovery": 50,
    "schema": 50,
    "scrape": 20,
    "quality": 20,
    "review": 200,
    "evidence": 200,
    "review2": 200,
    "enrich": 200,
    "index": 1000
  },
  "max_pages": 25,
  "name": null
}
```

Run checkpoints and retry/backoff state are persisted in PostgreSQL. `Resume` keeps the same run
and continues from the completed country/university/listing/page/batch instead of restarting the
whole current stage. Successful scrape pages and index batches are committed before advancing the
cursor, so repeating a page after a crash remains safe and idempotent. The status reports active
processing time rather than wall-clock age: stopped/failed intervals are excluded, and a durable
worker heartbeat avoids counting offline time after a crash or power loss.

Schema generation first tries already accepted schemas from the same host and listing kind, but
reuses one only after it passes the normal validation against the current target HTML. A failed
four-step tool-feedback exchange is not replayed wholesale; only transport failures retain the
outer retry budget. This avoids repeated local-model work without trusting a schema blindly.

Limits are per-stage budgets: `scrape` and `quality` count listing sources, `review` and `review2`
count candidate positions, while `evidence` and `enrich` count detail pages. Leaving a limit empty
means all remaining work for that stage. A completed first-pass verdict is not recomputed merely
because a newer run starts; versioned status and append-only attempts make the cascade idempotent.

A local LLM on the host is reachable from containers as `http://host.docker.internal:<port>`
(set `PHD_SEARCHER__LLM__API_BASE` / `PHD_SEARCHER__EMBEDDING__API_BASE`). The `.env`
`localhost` URLs only apply to host-side tooling (`make migrate`, `uv run phd ...`); compose
overrides them for the container.

## Data resilience and bootstrap

Git stores the application, migrations and reproducible configuration—not live
PostgreSQL/Qdrant data. Operational backups may contain source text, contact
details, audit evidence and user configuration, so they belong in encrypted
private storage. A future public fast-start dataset must instead be generated
by an allowlisted, privacy-minimizing export and published as a versioned
release artifact rather than committed to repository history. See
[docs/DATA_BACKUP_AND_BOOTSTRAP.md](docs/DATA_BACKUP_AND_BOOTSTRAP.md).

## Configuration

Env vars, prefix `PHD_SEARCHER__`, nested with `__`. See `.env.example`.

## Layout

- `src/phd_searcher/main.py` — the module-level FastAPI app (`hypercorn phd_searcher.main:app`). Pipeline control (start/stop/resume) is Postgres-mediated, so the server is safe to run with multiple workers (`WEB_CONCURRENCY`).
- `config/` — pydantic-settings. `typedef/` — request/response models + shared types (pure data). `dependency/` — injector modules. `engine/` — `ModelHelper` (litellm) + prompt rendering. `service/` — business logic. `apis/v1/` — routes. `database/` — SQLAlchemy models + Alembic.
- `tests/unit/` — fast, mocked. `tests/integration/` — separate uv project, spins docker compose.
- `Makefile` — dev tasks.

Thermal tuning: the [measured CPU-budget comparison](docs/THERMAL_TRIAL_20261005.md)
and [hardware-specific research and proposed next test](docs/THERMAL_OPTIONS_20261005.md)
distinguish verified recovery from untested power-management options.
