# Thermal CPU-budget trial, 5 October 2026

Both twenty-institution cohorts completed once. All cooling pauses resumed
without a manual restart. The CPU4 trial produced no critical102°C event.

| Measure | Baseline | Ollama4-CPU budget |
| --- | ---: | ---: |
| Cohort size |20|20|
| Wall runtime |26m53|44m55|
| Cooling pauses |3|4|
| Cooling seconds |247.21|257.35|
| Peak sampled CPU °C |100.5|100.125|
| Sources stored |20|43|
| Schema generations |10|17|
| Current SQL indexed markers |5|4|

Different institutions and workloads confound the time comparison; the trial
cannot establish a causal slowdown or speedup. The temperature/pause results
do not justify enabling a permanent four-CPU cap. Keep the thermal pause guard
and notification hooks; prioritize reducing avoidable schema generation.
SQL indexed markers are not certified unique open vacancies.

The real trial exposed a rollback defect missed by mocked Docker tests:
`docker update --cpus 0` returns success but does not remove an existing limit.
The [Moby update implementation](https://github.com/moby/moby/blob/v28.5.1/container/container_unix.go)
only changes NanoCPUs when the incoming value is nonzero. The installed engine
also rejects `--cpus=-1`. New trials from an unlimited budget now fail before
mutation. Legacy leases record recovery_required without looping or claiming
successful restoration. Exact cleanup requires authorized recreation of the
idle Ollama container with its persistent model volume retained.

Artifacts are local and ignored: var/thermal-20261004/final-*.json and
var/thermal-20261005/final-*.json. Final trial schedules3659–3678, runs3799–3818.
