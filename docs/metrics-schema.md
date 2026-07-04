# DynamiX Experiments — Metrics Data Contract (v1.1)

Fixes the **exact CSV layout** every experiment run must produce, so
`analysis/dynamix_analysis.py` and `analysis/dynamix_plots.py` consume run
output with **no per-run editing**. The runbook part of
[`experiments.md`](experiments.md) tells you *how to run* each condition; this
contract tells you *what each run must emit*.

Machine-readable version: [`metrics-schema.json`](metrics-schema.json) — the
loaders validate against it. If the two disagree, the JSON wins.

> **v1.1 change:** PromQL sources below are pinned to this repo's actual
> exporter (`mr4x2/stormexporter`) and KEDA controller
> (`k8s/keda/custom-metrics/main.py`), verified against
> [`monitoring.md`](monitoring.md). Earlier draft used generic
> `storm_topology__*` placeholder names — those were wrong for this stack.

---

## 0. Directory layout

```
docs/experiment-results/
  run_metadata.csv                 # one shared file, one row per run_id (appended)
  <group>/<condition>/
    timeseries_<run_id>.csv        # one per run
    rebalance_<run_id>.csv         # one per run (header-only allowed for static)
```

`run_id` convention: `<group>-<condition>-r<replicate>`
e.g. `G1-dynamix-r1`, `G1-static-r3`, `G2-aristo_orig_v1-r2`, `G3-window_s=900-r1`.
Condition names match the JARs / toggles in [`experiments.md`](experiments.md).

---

## 1. `timeseries_<run_id>.csv` — sampled every 15 s

One row per 15 s sample, from load-driver start (`t_s = 0`) to end.

| column | meaning | real source (this repo) |
|---|---|---|
| `run_id`, `condition`, `group` | identifiers | assigned |
| `t_s` | seconds since load start, 0-aligned across replicates | driver clock |
| `offered_load_msgs_per_s` | load setpoint (publisher-replica ramp) at *t* | driver |
| `throughput_acked_per_s` | fully-acked tuples/s (primary throughput) | `sum(rate(spouts_acked{SpoutId="spout-data-iot-data"}[1m]))` |
| `emitted_per_s` | downstream-processed proxy | `sum(rate(bolts_acked{BoltId=~"^split-.*"}[1m]))` † |
| `complete_latency_ms` | spout end-to-end tuple-tree latency | `spouts_complete_latency{SpoutId="spout-data-iot-data"}` |
| `capacity_max_bolt` | hottest split bolt capacity (busy fraction) | `max(bolts_capacity{BoltId=~"^split-.*"})` |
| `executors_total` | total executors in the topology | Storm REST `/api/v1/topology/:id` ‡ |
| `workers_total` | workers in use | `worker_cluster_used{ClusterHost="nimbus-ui:8081"}` |
| `supervisor_pods` | Running Supervisor pods | `kubectl` (command §5) |
| `weight_scale` | composite trigger score (null for static) | `weight_scale{ClusterHost="nimbus-ui:8081"}` |
| `cpu_util_ratio` | mean supervisor CPU/limit (optional) | cAdvisor; null if absent |

† **The exporter has no spout-emitted counter.** `mr4x2/stormexporter` exposes
`spouts_acked` / `bolts_acked` (counters), `bolts_capacity`,
`spouts_complete_latency`, `worker_cluster_used/total`. Use bolt-acked as the
emitted proxy, or add an emitted metric to the exporter if you need true emit
rate. The **CSV column name never changes** — only the PromQL behind it.

‡ **Not exposed by the exporter.** `executors_total` / `workers_total` (topology
count, not cluster workers) come from Storm's UI REST API
`/api/v1/topology/summary`. Poll it directly; don't expect a Prometheus series.

---

## 2. `rebalance_<run_id>.csv` — one row per scaling action

Two producers merged into one file:

- **ARiSto layer** (`layer=aristo`): topology executor/worker rebalances,
  parsed from the autoscaler's `OutputWriter` log lines.
  > ⚠️ **`OutputWriter` is not yet wired into `rulebase/v1/`** (see
  > [`aristo-versions.md`](aristo-versions.md) → "Not Done", and Phase 0 in
  > [`experiments.md`](experiments.md)). Until it is, the **modified-v1 / DynamiX**
  > runs cannot emit `layer=aristo` rows, so rebalance-count and
  > time-to-stabilize for the P0 comparison will be blank. This is the first
  > blocker to clear. Fallback: infer rebalances from step changes in
  > `executors_total` / `workers_total` (less precise).
- **KEDA layer** (`layer=keda`): Supervisor pod scale events from
  `kubectl get events` / KEDA operator log. `component=supervisor`.

`action ∈ {scale_out, scale_in}`. For **static**, header only, no rows (valid).

---

## 3. `run_metadata.csv` — one row per run

`params_json` carries the knobs (`window_s`, `wscale_threshold`,
`bolt_cap_threshold`, `aristo_jar`, `keda_enabled`, `cooldown_s`);
`cluster_spec` carries the hardware/software (feeds the cluster-spec table the
review asked for — currently paper §IV.B is empty). `warmup_s` (default 120) is
the leading interval discarded before steady-state statistics.

---

## 4. The `weight_scale` composite (as implemented in this repo)

Published by the exporter; **not** the draft's abstract formula. From
`k8s/keda/custom-metrics/main.py` and README:

```
weight_scale = 0.6 * (worker_utilization / 0.70)   # worker_used / worker_total, dominant term
             + 0.2 * (bolt_capacity      / 0.50)   # avg split-bolt capacity
             + 0.2 * (spout_latency       / 100ms) # spout complete latency
```

- Scale-**out**: KEDA scales the `supervisor` StatefulSet (1→7 pods) when
  `weight_scale > 0.75` (`threshold` in `k8s/keda/autoscale-keda.yaml`).
- `initialCooldownPeriod: 300` s guards flapping.
- **Scale-in / scale-down** (review flagged as under-documented): KEDA removes
  pods when the metric stays below threshold; note the **modified ARiSto v1 has
  no executor scale-down** (only v3/v4 do — see `aristo-versions.md`). State
  this limitation in the paper's scale-down paragraph rather than implying
  symmetric down-scaling at the topology layer.

> The draft §III writes the weights as fractions of raw ratios
> (0.6·worker + 0.2·bolt + 0.2·latency). The code divides each signal by its
> threshold (0.70 / 0.50 / 100 ms) first. **Reconcile the paper text with the
> code** — the normalisation is why the trigger fires at 0.75.

---

## 5. Collection commands (real endpoints)

**Supervisor pod count (per sample):**
```bash
kubectl get statefulset supervisor -n storm-cluster -o jsonpath='{.status.replicas}'
# or:
kubectl get pods -n storm-cluster -l app=supervisor \
  --field-selector=status.phase=Running -o name | wc -l
```

**Prometheus range export (post-run bulk, preferred):**
```bash
curl -sG 'http://prometheus.storm-cluster.svc.cluster.local:9090/api/v1/query_range' \
  --data-urlencode 'query=sum(rate(spouts_acked{SpoutId="spout-data-iot-data"}[1m]))' \
  --data-urlencode "start=<run_start_epoch>" \
  --data-urlencode "end=<run_end_epoch>" \
  --data-urlencode 'step=15s'
```
Loop the query set (throughput / latency / capacity / worker-util / weight_scale)
and join on timestamp into `timeseries_<run_id>.csv`.

**Executors/workers (post-run or polled):** Storm UI REST
`GET http://nimbus-ui:8081/api/v1/topology/summary` → topology `executorsTotal`,
`workersTotal`.

**KEDA pod events (post-run):**
```bash
kubectl get events -n storm-cluster --field-selector involvedObject.kind=Pod -o json \
  | jq '.items[] | select(.reason|test("Scaled|Started|Killing"))'
```

---

## 6. Validation

`dynamix_analysis.load_*()` validate every file against
`metrics-schema.json`: required columns present + coercible dtype;
`condition ∈` the group's allowed set; `t_s` monotonic with sample gaps ≤ 2×
period; `run_id` present in `run_metadata.csv`. A bad export raises with the
offending column/row before it can reach a figure.
