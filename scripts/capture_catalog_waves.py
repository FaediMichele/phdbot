"""One read-only, consistent snapshot; no pipeline/model/index side effects."""
import argparse
import json
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--container', default='phdbot-postgres-1')
    args = parser.parse_args()
    ids = set()
    for path in args.plan:
        plan = json.loads(path.read_text())
        for entry in plan['jobs'].values():
            if entry.get('status') == 'accepted':
                ids.update(entry['schedule_ids'])
    if not ids or any(type(i) is not int or i <= 0 for i in ids):
        parser.error('plans must contain positive accepted schedule IDs')
    sql = """
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '45s';
SET LOCAL TIME ZONE 'Europe/Rome';
WITH jobs AS (
 SELECT j.id, j.state, j.pipeline_run_id, j.attempts, j.error,
 j.payload->>'expansion_institution_id' AS institution_id,
 j.payload->'_governor_plan'->>'objective' AS objective,
 j.payload->'_governor_plan'->>'valet_wake_root_id' AS wake_root,
 j.started_at, j.finished_at, r.state AS run_state,
 r.active_elapsed_seconds, r.started_at AS run_started_at, r.finished_at AS run_finished_at,
 r.stages_done, r.checkpoints->'discovery' AS discovery,
 r.checkpoints->'schema' AS schema, r.checkpoints->'scrape' AS scrape,
 jsonb_build_object(
  'discovery',r.checkpoints->'discovery'->'performance',
  'schema',r.checkpoints->'schema'->'performance',
  'scrape',r.checkpoints->'scrape'->'performance',
  'quality',r.checkpoints->'quality'->'performance',
  'index',r.checkpoints->'index'->'performance'
 ) AS performance,
 u.name, u.country, u.discovery_status, u.website_url,
 u.registry_metadata->'types' AS registry_types
 FROM scheduled_jobs j LEFT JOIN pipeline_runs r ON r.id=j.pipeline_run_id
 LEFT JOIN universities u ON u.id=(j.payload->>'expansion_institution_id')::int
 WHERE j.id IN (__SCHEDULE_IDS__)
), sources AS (
 SELECT l.id, l.university_id, l.url, l.source, l.schema_status,
 l.quality_status, l.quality_reason, l.extraction_schema->>'adapter' AS adapter,
 l.last_scraped_at, l.discovered_at
 FROM listing_pages l WHERE l.university_id IN (SELECT institution_id::int FROM jobs)
), outcomes AS (
 SELECT p.university_id, p.listing_page_id, p.position_type, p.opportunity_kind,
 p.screening_status, p.review_state, p.routing_reason,
 count(*) AS rows, count(*) FILTER(WHERE p.indexed_at IS NOT NULL) AS indexed_markers,
 count(*) FILTER(WHERE p.is_active AND (p.deadline IS NULL OR p.deadline >= CURRENT_DATE)) AS active_current,
 count(*) FILTER(WHERE p.indexed_at IS NOT NULL AND p.is_active AND (p.deadline IS NULL OR p.deadline >= CURRENT_DATE)) AS current_indexed_markers
 FROM positions p WHERE p.university_id IN (SELECT institution_id::int FROM jobs)
 GROUP BY 1,2,3,4,5,6,7
)
SELECT json_build_object('captured_at',clock_timestamp(),'as_of',CURRENT_DATE,
 'jobs',(SELECT json_agg(jobs ORDER BY id) FROM jobs),
 'sources',(SELECT json_agg(sources ORDER BY id) FROM sources),
 'outcomes',(SELECT json_agg(outcomes) FROM outcomes));
ROLLBACK;
"""
    result = subprocess.run(
        ['docker', 'exec', '-i', args.container, 'psql', '-U', 'app', '-d', 'app',
         '-X', '-qAt', '-v', 'ON_ERROR_STOP=1'],
        input=sql.replace("__SCHEDULE_IDS__", ",".join(map(str, sorted(ids)))), text=True, capture_output=True, check=True, timeout=60,
    )
    data = json.loads(result.stdout)
    args.output.write_text(json.dumps(data, ensure_ascii=False))
    print({key:len(data[key] or []) for key in ('jobs','sources','outcomes')})


if __name__ == "__main__":
    main()
