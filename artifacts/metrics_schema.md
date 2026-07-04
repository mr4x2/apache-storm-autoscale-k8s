# DynamiX Experiments — Metrics Data Contract (v1.0)

This document fixes the **exact CSV layout** every experiment run must produce.
The runbook (`runbook.md`) tells you *how to run* each experiment; this contract
tells you *what data each run must emit* so that `dynamix_analysis.py` and
`dynamix_plots.py` consume the files with **no per-run editing**.

The machine-readable version is `metrics_schema.json` (used by the loaders for
validation). If the two ever disagree, the JSON wins.

---

## 0. Directory layout

```
data/
  run_metadata.csv                 # one shared file, one row per run_id (appended)
  timeseries_<run_id>.csv          # one per run
  rebalance_<run_id>.csv           # one per run (header-only allowed for static)
```

`run_id` convention: `<group>-<condition>-r<replicate>`
e.g. `G1-dynamix-r1`, `G1-static-r3`, `G2-aristo_mod_v1-r2`, `G3-window_s=900-r1`.

---

## 1. `timeseries_<run_id>.csv` — sampled every 15 s

The heartbeat of every run. One row per 15 s sample, from load-driver start
(`t_s = 0`) to end. Columns (see JSON for dtypes/units):

| column | meaning | how to collect |
|---|---|---|
| `run_id`, `condition`, `group` | identifiers | assigned |
| `t_s` | seconds since load start, 0-aligned across replicates | driver clock |
| `offered_load_msgs_per_s` | load-driver setpoint at time *t* | driver |
| `throughput_acked_per_s` | fully-acked tuples/s (the primary throughput metric) | `sum(rate(storm_topology__acked[1m]))` |
| `emitted_per_s` | emitted tuples/s | `sum(rate(storm_topology__emitted[1m]))` |
| `complete_latency_ms` | spout complete-latency (end-to-end tuple-tree) | `storm_topology__complete_latency` |
| `capacity_max_bolt` | Storm capacity of the hottest bolt (≈ busy fraction) | `max(storm_topology__capacity)` over bolt executors |
| `executors_total` | total executors in the topology | Storm REST topology summary / `storm_topology__executors` |
| `workers_total` | worker processes | Storm REST `workersTotal` |
| `supervisor_pods` | Running Supervisor pods | `kubectl get pods` (command below) |
| `weight_scale` | ARiSto/KEDA composite trigger score (null for static) | computed, see §4 |
| `cpu_util_ratio` | mean supervisor CPU/limit (optional) | cAdvisor; null if absent |

> **Metric-name note.** Storm-Exporter flattens Storm's MBeans; exact metric
> names depend on the exporter build (`storm_topology__acked`,
> `storm__topology__acked`, or a `topologyStats`-prefixed variant). Verify the
> real names once with `curl <exporter>:<port>/metrics | grep -i acked` and pin
> them in `prometheus/queries.env` (template shipped in the runbook). The
> **column names in the CSV never change** — only the PromQL behind them.

## 2. `rebalance_<run_id>.csv` — one row per scaling action

The scaling-decision log. Two producers merged into one file:

- **ARiSto layer** (`layer=aristo`): topology executor/worker rebalances, parsed
  from the autoscaler's `OutputWriter` log. Fields: which component, old→new
  parallelism, and the trigger value.
- **KEDA layer** (`layer=keda`): Supervisor pod scale events, from
  `kubectl get events` / the KEDA operator log. `component=supervisor`.

`action ∈ {scale_out, scale_in}`. For the **static** condition this file has a
header and no rows (valid and expected).

## 3. `run_metadata.csv` — one row per run

Campaign-level ledger. `params_json` carries the knob settings
(`window_s`, `wscale_threshold`, `bolt_cap_threshold`, `aristo_jar`,
`keda_enabled`, `cooldown_s`); `cluster_spec` carries the hardware/software the
run executed on (feeds the cluster-spec table the review asked for). `warmup_s`
(default 120) is the leading interval discarded before steady-state statistics.

---

## 4. The `weight_scale` composite (as defined in the DynamiX draft, §III)

```
weight_scale = 0.6 * worker_util_ratio      # busy-worker fraction (dominant term)
             + 0.2 * bolt_capacity           # capacity_max_bolt, clamped to [0,1]
             + 0.2 * latency_norm            # complete_latency / latency_SLA_target
```

- Scale-**out** fires when `weight_scale > wscale_threshold` (baseline 0.75) for
  a sustained observation window (baseline 600 s).
- Scale-**in** (the review flagged this as under-documented — see runbook §G1
  and the paper's scale-down paragraph): fires when `weight_scale` stays below a
  lower hysteresis band (e.g. `wscale_threshold - 0.25`) for the window, subject
  to the `cooldown_s` (300 s) guard that also serializes the two controllers.
- `latency_norm` uses the SLA target recorded in `run_metadata.params_json`
  (`latency_sla_ms`); if absent, analysis normalises by the run's own
  steady-state p50 and flags the column as relative.

---

## 5. Collection commands (reference)

**Supervisor pod count (per sample):**
```bash
kubectl get pods -n <ns> -l app=supervisor \
  --field-selector=status.phase=Running -o name | wc -l
```

**Prometheus range query (post-run bulk export, preferred over per-sample curl):**
```bash
# one metric, whole run, 15s step -> CSV column
curl -sG 'http://<prom>:9090/api/v1/query_range' \
  --data-urlencode 'query=sum(rate(storm_topology__acked[1m]))' \
  --data-urlencode "start=<run_start_epoch>" \
  --data-urlencode "end=<run_end_epoch>" \
  --data-urlencode 'step=15s'
```
A helper (`scripts/export_prom.sh`, described in the runbook) loops the query set
in `prometheus/queries.env` and joins them on timestamp into
`timeseries_<run_id>.csv`. This decouples collection from Grafana and makes runs
reproducible from Prometheus TSDB alone.

**ARiSto rebalance events (post-run):** grep the autoscaler pod log for the
`OutputWriter` rebalance lines and map to the `rebalance_*` columns.

**KEDA pod events (post-run):**
```bash
kubectl get events -n <ns> --field-selector involvedObject.kind=Pod \
  -o json | jq '...'   # filter Scaled/Started/Killing on supervisor pods
```

---

## 6. Validation

`dynamix_analysis.load_timeseries()` / `load_rebalance()` / `load_metadata()`
validate every file against `metrics_schema.json`:
- all required columns present, correct dtype (coercible),
- `condition` ∈ allowed set for the group,
- `t_s` monotonic non-decreasing, sample gaps ≤ 2× sample period,
- `run_id` present in `run_metadata.csv`.

A file that fails validation raises with the specific column/row, so a
mis-exported run is caught before it reaches a figure.
