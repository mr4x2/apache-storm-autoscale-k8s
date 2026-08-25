# G1 Known Issues — must fix/verify before trusting results for the paper

Working list of data-quality problems found while auditing real G1 captures
(2026-08-08 session). None of these are fixed yet. Re-check this list before
re-running G1 or before citing any G1 number in the paper.

---

## 1. Throughput/latency collapse to zero — BLOCKS any throughput/latency chart

**Symptom:** `throughput_acked_per_s` reads exactly `0.0` for a large fraction of
samples in every condition, interspersed with isolated single-sample spikes
(600–1000+ msg/s) that don't sustain. `complete_latency_ms` shows the same
pattern plus one large spike (~14,000 ms) under `dynamix-r3`.

**Measured, static/aristo_only/dynamix r3, first 30 min window:**

| condition | zero-throughput samples | max single-sample spike |
|---|---|---|
| static | 50/121 (41%) | 582 msg/s |
| aristo_only | 76/121 (63%) | 603 msg/s |
| dynamix | 51/121 (42%) | 1057 msg/s |

**Most important clue:** all three conditions read **exactly zero for the first
~11–12 minutes**, regardless of autoscaler config (including `static`, which has
no autoscaler at all). Since it's condition-independent, the cause is upstream of
ARiSto/KEDA entirely. Candidate causes, not yet checked:
- Topology/MQTT warm-up lag (spout not actually consuming yet when the ramp starts)
- The `sum(rate(spouts_acked{...}[1m]))` query (`scripts/export_run.py` `QUERIES`)
  reading near-zero while its 1-minute window is still mostly pre-run
- Publisher→broker→spout connection delay specific to how the load ramp starts
  (`docs/runbook-G1.md` Step 2)

**Do not** chart throughput or latency — individually or together — until this is
understood. They share the same root cause (a zero-throughput stretch is *why*
latency reads 0 there too), so showing one without the other to avoid an
unflattering result is not a formatting choice, it's selective reporting of two
symptoms of the same event.

Diagnostic (not publication) chart: `analysis/g1_throughput_diagnostic.py` →
`analysis/figures/G1_throughput_DIAGNOSTIC_do_not_use_in_paper.png`.

---

## 2. `offered_load_msgs_per_s` is fabricated in every captured CSV, not measured

`scripts/export_run.py`'s `LOAD_STEPS` constant is hardcoded to the *old*
`1000/4000/8000 msg/s @ 600s each` profile and stamps that label onto every row
by `t_s`, regardless of what was actually run. Real load is now
`200→500→900 msg/s` via publisher-count staging
(`600/600/1600s`, `docs/runbook-G1.md`). `throughput_acked_per_s` and
`complete_latency_ms` ARE real Prometheus measurements — only `offered_load_msgs_per_s`
is wrong.

**Fix:** update `LOAD_STEPS` in `scripts/export_run.py` to match the real runbook
profile before the next export.

## 3. `docs/metrics-schema.json`'s `load_profile_default` is the same stale profile

Same root cause as #2, different file. `per_level_metrics()` /
`summarize_group1()` in `analysis/dynamix_analysis.py` window real data against
this profile — currently wrong load-step boundaries for real G1 runs.

**Fix:** update `load_profile_default` (steps + `total_duration_s`) to
`200/500/900 msg/s`, `600/600/1600s`, `2800s` total.

## 4. `cores=2` hardcoded in `FlowCheck.java:51` vs. real 5.5-core Supervisor limit

Already tracked as **CLAUDE.md Open blocker #3**. Table II (§IV.B draft) confirms
the real Supervisor CPU limit is `5500m` (5.5 cores) — worse mismatch than
originally estimated (was compared against 4000m earlier). Feeds the
`(threads+changes)/(cores*workers) > 2` worker-growth threshold in `FlowCheck.java:214`.

## 5. ARiSto has no worker/executor scale-down path

Confirmed 2026-08-08: `rulebase/v1/FlowCheck.java` only ever does `++workers` and
`+1` executor — no decrement path anywhere. Any observed *decrease* in
`workers_total`/`executors_total` within a single run is therefore not a real
ARiSto decision (most likely a Storm worker-process crash/restart blip), whatever
the `rebalance_*.csv`'s `layer=aristo, action=scale_in` heuristic label says —
that label is assigned purely by "which count changed," not by reading ARiSto's
actual decision log (`storm_snapshot.py`'s `derive_rebalances()`).

**Applied:** `analysis/g1_behavior_figure.py` now normalizes `workers_total`/
`executors_total` to a running maximum. `supervisor_pods` is left unmodified
(KEDA's ScaledObject has a genuine scale-down policy).

**Still open:** the crash/restart-blip explanation is inferred, not directly
confirmed. Check Storm supervisor/worker logs for the affected windows
(e.g. `aristo_only-r3` t≈1044-1092s, `dynamix-r3` t≈1476-1525s and t≈1609-1658s)
before treating it as settled.

## 6. `aristo_only`'s measured Supervisor pod count sits flat at 1, not the protocol-fixed 3

`docs/runbook-G1.md` condition C (`aristo_only`) specifies
`kubectl scale statefulset supervisor --replicas=3`, but the real captured
`supervisor_pods` telemetry for `aristo_only-r3` (and by extension possibly
r1/r2) shows a constant `1` for the entire run. Either the scale step wasn't
actually applied for that capture, or the telemetry doesn't reflect real replica
count for this condition.

**Fix:** verify the scale step was run before the next `aristo_only` capture;
check `kubectl get statefulset supervisor -n storm-cluster` mid-run next time.

## 7. `dynamix-r1` and `dynamix-r2` are multi-session-concatenated, not usable

`state_G1-dynamix-r1.csv` / `rebalance_*.csv` contain **11 concatenated poller
sessions** spanning 2026-08-03 through 2026-08-08 (`t_s` resets to 1 eleven
times). `dynamix-r2` has 2 sessions, with the first spanning an anomalous ~3
hours (should be ~47 min). Only `dynamix-r3` is a single clean session and was
used for the current behavior figure. Also carries the original manual-rebalance
taint documented in memory (`g1-dynamix-r1-manual-intervention.md`) and
**CLAUDE.md Open blocker #3**.

**Fix:** re-run `dynamix` r1 and r2 hands-off, one poller session per run, no
manual intervention, before using them for anything beyond illustration.

---

## What's currently usable

- `static` r1/r2/r3 — clean, single-session, no issues found.
- `aristo_only` r1/r2/r3 — clean, single-session (modulo #5, #6 above).
- `dynamix` r3 only — clean, single-session (modulo #5 above). r1/r2 excluded (#7).
- `keda_only` r1 — still running as of 2026-08-08, not yet complete.

## Suggested order of attack

1. #1 (throughput/latency collapse) — highest leverage, blocks all performance
   charts, condition-independent so likely one root cause.
2. #2 + #3 together (same fix pattern, two files) — cheap, unblocks trustworthy
   `offered_load` reporting and correct per-level windowing.
3. #6 — cheap, just needs verifying the scale step ran.
4. #7 — re-run dynamix r1/r2 once #1 is understood (no point re-running into the
   same collapse).
5. #4 / CLAUDE.md blocker #3 — code fix, do before the next full G1 pass.
