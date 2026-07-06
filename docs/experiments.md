# DynamiX Experiment Checklist

Runnable checklist for the experiments the paper (Section V) needs. Mirrors the
Notion research log ("Bài chỗ anh Tú") Group 1 / 2 / 3 plan, mapped to this repo's
actual deploy commands, JARs, and Prometheus metrics.

> **Goal of each group**
> - **Group 1 (P0)** — 4-condition baseline. Produces the paper's core claim: *multi-level > single-level*. Section V cannot be written without it.
> - **Group 2 (P2)** — original ARiSto v1 vs modified ARiSto v1. Justifies the window-based throughput enhancement (§III.C).
> - **Group 3 (P1)** — parameter sensitivity. Justifies the 600s window / 0.75 threshold / 0.7 bolt-capacity choices.

---

## Phase 0 — Prerequisites (do before any run)

- [ ] **Add `OutputWriter` to `rulebase/v1/`** — currently only `rulebase/aristo/` logs structured rebalance records. Without matching logging in the modified v1, rebalance-count and time-to-stabilize can't be compared. *(This is the one "Not Done" blocker in [`aristo-versions.md`](aristo-versions.md).)* **⚠ This gates the P0 comparison:** the DynamiX and modified-v1 conditions use `rulebase/v1/`, so until this lands, F4 (settling + rebalance) and the `rebalance_*.csv` `layer=aristo` rows are empty for exactly the headline condition. Fallback until then: infer rebalances from step changes in `executors_total`/`workers_total`.
- [ ] Rebuild both JARs and confirm they exist:
  ```bash
  cd storm-src && mvn package
  ls target/storm-autoscale-v1-1.0.jar target/storm-autoscale-aristo-1.0.jar
  ```
- [ ] Capture the **cluster spec table** (paper §IV.B is currently empty): node count, CPU/RAM per node, Storm version, Nimbus JVM heap, KEDA version, `REFRESH_RATE`, `initialCooldownPeriod`. Save to `docs/experiment-results/cluster-spec.md`.
- [ ] Create results directory: `mkdir -p docs/experiment-results`
- [ ] Verify the monitoring stack is up (Prometheus scraping `storm-exporter`, `weight_scale` present):
  ```bash
  kubectl get pods -n storm-cluster | grep -E "prometheus|storm-exporter|grafana"
  # In Prometheus UI, confirm: weight_scale{ClusterHost="nimbus-ui:8081"} returns a value
  ```

---

## Common Harness (applies to every run)

### Load injection — the ramp pattern

Load is controlled by the **number of MQTT building publishers** (each publisher emits
at `interval = 1000 ms`; more building replicas = higher aggregate rate).

Target ramp: **1000 → 4000 → 8000 msgs/sec, hold each level 10 min.**

- [ ] Calibrate replicas→rate once (measure `sum(rate(spouts_acked[1m]))` at 1/N publishers), then for each run:
  ```bash
  # ramp up
  kubectl scale deployment mqtt-publisher -n storm-cluster --replicas=<n_for_1000>   # hold 10 min
  kubectl scale deployment mqtt-publisher -n storm-cluster --replicas=<n_for_4000>   # hold 10 min
  kubectl scale deployment mqtt-publisher -n storm-cluster --replicas=<n_for_8000>   # hold 10 min
  ```
  > If publisher isn't a scalable Deployment in your cluster, use the building compose
  > variants (`k8s/mqtt/publisher/10-building-...`, `15-building-...`) as fixed rate steps.

### Toggling each layer on/off

| Layer | ENABLE | DISABLE |
|---|---|---|
| **ARiSto** (topology) | run autoscaler JAR in nimbus (below) | kill the JAR process in nimbus; leave executor counts fixed |
| **KEDA** (infra) | `kubectl apply -f k8s/keda/autoscale-keda.yaml` | `kubectl delete -f k8s/keda/autoscale-keda.yaml` (removes ScaledObject + HPA) |

Run the ARiSto autoscaler inside nimbus:
```bash
kubectl exec -it <nimbus-pod> -n storm-cluster -- bash
cd /opt/storm/lib
# modified v1:
storm jar storm-autoscale-v1-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt | tee /tmp/aristo-run.log
# OR original v1:
storm jar storm-autoscale-aristo-1.0.jar org.apache.storm.starter.rulebase.aristo.TopologyParser input.txt target.txt | tee /tmp/aristo-run.log
```

### Reset between runs (clean state)

- [ ] Kill running autoscaler JAR; `kubectl delete -f k8s/keda/autoscale-keda.yaml`
- [ ] `kubectl scale statefulset supervisor -n storm-cluster --replicas=1`
- [ ] Kill + redeploy the topology so executor counts start from baseline:
  ```bash
  kubectl exec -it <nimbus-pod> -n storm-cluster -- storm kill iot-smarthome -w 30
  # wait for full teardown, then redeploy:
  kubectl exec -it <nimbus-pod> -n storm-cluster -- bash -lc 'cd /opt/storm/lib && storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo'
  ```
- [ ] Scale publisher back to 0, wait for queues to drain, note the wall-clock start time of the next run.

### Metrics to record every run (same set for all conditions)

| Metric | Source / PromQL |
|---|---|
| Throughput (msgs/s) over time | `sum(rate(spouts_acked{SpoutId="spout-data-iot-data"}[1m]))` |
| End-to-end latency (ms) | `spouts_complete_latency{SpoutId="spout-data-iot-data"}` |
| Bolt capacity (`capacity_max_bolt`) | `max(bolts_capacity{BoltId=~"^split-.*"})` |
| Worker utilization | `worker_cluster_used{ClusterHost="nimbus-ui:8081"} / worker_cluster_total{ClusterHost="nimbus-ui:8081"}` |
| `weight_scale` | `weight_scale{ClusterHost="nimbus-ui:8081"}` |
| Supervisor pod count | `kubectl get statefulset supervisor -n storm-cluster -o jsonpath='{.status.replicas}'` (poll) or Prometheus |
| Rebalance count + intervals | `OutputWriter` log file (Phase 0 prerequisite) |
| Time to stabilize after each load step | timestamp when throughput reaches ±5% of new steady value |

- [ ] Export each run's Prometheus range as CSV/PNG into `docs/experiment-results/<group>/<condition>/`.

---

## Group 1 — Baseline Comparison (P0, most critical)

Same IoT workload + same ramp under 4 conditions. Record the full metric set each time.

- [ ] **G1-A · Static** — fixed executor counts, no autoscaler JAR, KEDA deleted, supervisor pinned (`--replicas=3`, say). Run ramp, record.
- [ ] **G1-B · KEDA-only** — no ARiSto JAR; KEDA ScaledObject applied. Run ramp, record.
- [ ] **G1-C · ARiSto-only** — run modified v1 JAR; KEDA deleted; supervisor pinned. Run ramp, record.
- [ ] **G1-D · DynamiX (both)** — modified v1 JAR **+** KEDA applied. Run ramp, record. *(This is the main claim.)*
- [ ] Build the comparison table + throughput/latency-over-time figures across A–D.

> Deliverable: the figures and table that populate paper **Section V**.

---

## Group 2 — Algorithm Comparison (P2, already set up)

Original vs modified ARiSto v1. **Keep KEDA identical** (either both on or both off — recommend both off, so only the algorithm differs) so the delta is attributable to the throughput formula alone.

- [ ] **G2-A · Modified ARiSto v1** — `storm-autoscale-v1-1.0.jar` (window `totalAcked/600`, bolt threshold 0.7, `workers=2`, `maxWorkers=28`). Run ramp, record.
- [ ] **G2-B · Original ARiSto v1** — `storm-autoscale-aristo-1.0.jar` (cumulative throughput, threshold 0.8, `workers=1`). Run ramp, record.
- [ ] Compare: throughput stability, rebalance frequency (from OutputWriter), time-to-stabilize, and how often the spout throughput reads **0** (the concrete bug the window formula fixes — thesis Hình 3.8/3.9).

---

## Group 3 — Parameter Sensitivity (P1, reviewers will demand)

Run DynamiX (both layers) varying **one** parameter at a time; hold the others at current values.

- [ ] **Observation window**: 300 / 600 / 900 / 1200 s — edit the divisor in `rulebase/v1/FlowCheck.java` (`AckedRate = totalAcked / <window>`), `mvn package`, redeploy JAR per value. *(current = 600)*
- [ ] **weight_scale threshold**: 0.65 / 0.75 / 0.85 — edit `threshold` in `k8s/keda/autoscale-keda.yaml`, re-apply. *(current = 0.75)*
- [ ] **Bolt capacity threshold**: 0.6 / 0.7 / 0.8 — edit the capacity stop threshold in `FlowCheck.java`, rebuild, redeploy. *(current = 0.7)*
- [ ] For each value record throughput stability + rebalance frequency; assemble one sensitivity table per parameter showing why the current value is optimal.

---

## Data contract & analysis pipeline

Once runs land, the numbers and figures are produced by the code in
[`analysis/`](../analysis/) — no per-run editing. Two things fix the interface:

- **Data contract:** [`docs/metrics-schema.md`](metrics-schema.md) +
  [`docs/metrics-schema.json`](metrics-schema.json) define the exact CSV layout
  every run must emit (columns, dtypes, the real PromQL behind each column, and
  validation rules). The JSON is what the loader validates against.
- **Output location:** write each run's CSVs under
  `docs/experiment-results/<group>/<condition>/` (plus one shared
  `run_metadata.csv`), named `timeseries_<run_id>.csv` /
  `rebalance_<run_id>.csv`. `run_id` = `<group>-<condition>-r<replicate>`.

### Scripts

| script | does |
|---|---|
| `analysis/dynamix_analysis.py` | loads + schema-validates all runs, derives per-level metrics (throughput, p95/p99 latency, settling time, CoV, rebalance counts, saturation gap), writes `group{1,2,3}_summary.csv` |
| `analysis/dynamix_plots.py` | renders F1–F6 (below) |
| `analysis/make_synthetic_runs.py` | **placeholder data generator** — fabricates plausible runs so the pipeline can be dry-run before the cluster is ready. **Not part of the real workflow;** delete synthetic `data/` before quoting any result. |
| `analysis/figstyle.py` | publication figure style helper |

Run it:
```bash
cd analysis
# dry run only: python3 make_synthetic_runs.py data
python3 dynamix_analysis.py <data_dir> ../docs/metrics-schema.json   # -> summary CSVs
python3 dynamix_plots.py    <data_dir> ../docs/metrics-schema.json   # -> figures
```
With real data, point `<data_dir>` at `../docs/experiment-results`. A file that
violates the contract raises `SchemaError` naming the offending run/column.

### Figures → paper section

| fig | shows | feeds |
|---|---|---|
| **F1** | throughput vs offered load, timeseries per condition | G1 → §V |
| **F2** | p95 latency (bar + CDF) across conditions | G1 → §V |
| **F3** | resource footprint (supervisor pods + executors) | G1 → §V |
| **F4** | settling time + rebalance counts | G1 → §V |
| **F5** | ARiSto formula ablation (windowed vs cumulative) | G2 → §III.C |
| **F6** | parameter sensitivity (window / wscale / bolt-cap) | G3 → §V param justification |

F1–F4 + the Group 1 table are what make **Section V** writable (the P0 gap).

> **Two P0 caveats surfaced from the code (fix before trusting F4 / rebalance columns):**
> 1. **`OutputWriter` is not in `rulebase/v1/`** (Phase 0 blocker) — until it is,
>    the modified-v1 / DynamiX runs emit no `layer=aristo` rebalance rows, so F4
>    and the rebalance columns are blank for exactly the headline condition.
> 2. **`weight_scale` formula in the draft ≠ the code.** The code divides each
>    signal by its threshold (0.70 / 0.50 / 100 ms) before weighting; the draft
>    §III writes raw-ratio weights. Reconcile the paper text with
>    `k8s/keda/custom-metrics/main.py` (see `docs/metrics-schema.md` §4).

---

## Results Tables (fill in)

### Group 1
| Condition | Avg throughput | p95 latency | Rebalances | Max supervisors | Time-to-stabilize (per step) |
|---|---|---|---|---|---|
| A Static | | | | | |
| B KEDA-only | | | | | |
| C ARiSto-only | | | | | |
| D DynamiX | | | | | |

### Group 2
| Version | Avg throughput | Latency | Rebalances | Spout throughput = 0 events | Time-to-stabilize |
|---|---|---|---|---|---|
| Modified v1 (window) | | | | | |
| Original v1 (cumulative) | | | | | |

### Group 3
| Parameter | Value | Throughput stability | Rebalance freq | Chosen? |
|---|---|---|---|---|
| Window (s) | 300 / 600 / 900 / 1200 | | | 600 |
| weight_scale threshold | 0.65 / 0.75 / 0.85 | | | 0.75 |
| Bolt capacity threshold | 0.6 / 0.7 / 0.8 | | | 0.7 |

---

## Priority order (from Notion log)

1. **P0** — Phase 0 prerequisites, then Group 1 (4-condition), then write Section V.
2. **P1** — Group 3 sensitivity; add parameter-justification paragraphs.
3. **P2** — Group 2 algorithm comparison; scale-down / cluster-spec notes.
