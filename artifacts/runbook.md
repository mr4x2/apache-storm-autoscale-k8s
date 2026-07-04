# DynamiX Autoscaling — Experiment Runbook

**Scope.** Concrete, copy-paste-level procedures for the three experiment groups
required to complete the DynamiX paper (Sections V–VI). Each group states the
**claim it tests**, the **procedure**, and the **figures/tables it feeds**. All
runs emit the CSVs defined in `metrics_schema.md` / `metrics_schema.json`; the
analysis (`dynamix_analysis.py`) and plotting (`dynamix_plots.py`) code consumes
those files unchanged.

This runbook is written against the system in the thesis (`datn-tuda2.pdf`) and
the DynamiX draft: Apache Storm on Kubernetes, topology-level scaling by ARiSto
(executors / worker processes), infrastructure-level scaling of Supervisor pods
by KEDA→HPA, monitored by Storm-Exporter → Prometheus → Grafana.

> **Priority (from the review log "Bài chỗ anh Tú").**
> **P0 — Group 1** (this is what makes Section V writable) + de-Vietnamise the
> draft. **P1 —** controller-interaction section (largely done in draft §III.D),
> **Group 3**, cloud–fog framing. **P2 — Group 2**, `weight_scale` justification,
> scale-down paragraph, ARiSto-v1 + cluster-spec table.

---

## 0. Prerequisites & fixed harness (shared by all groups)

### 0.1 Cluster (record the real values into `run_metadata.cluster_spec`)

| item | value (fill in) |
|---|---|
| Kubernetes | version, node count, per-node vCPU / RAM |
| Storm | version, Nimbus / UI / Supervisor images |
| Supervisor StatefulSet | slots per Supervisor, initial replicas, CPU/mem requests+limits |
| ZooKeeper | replicas |
| Data path | MQTT broker (e.g. Mosquitto/EMQX), MySQL sink |
| Monitoring | Storm-Exporter build, Prometheus scrape interval (set = 15 s), Grafana |

> This table is also the **cluster-spec table** the review asked the paper to add.
> Fill it once; it is identical across every run in the campaign except where a
> group deliberately varies it.

### 0.2 Topology under test

The smart-home ingestion topology from the thesis (MQTT spout → parse/enrich
bolts → aggregation bolt → MySQL sink). Pin the **initial** parallelism
(executors per component, worker count) and record it; every condition starts
from the same initial topology so differences are attributable to the scaler,
not the starting point.

### 0.3 Load driver — `ramp_1k_4k_8k_10min` (the standard profile)

A publisher that pushes synthetic smart-home sensor messages into the MQTT
broker at a controlled rate:

| step | rate (msg/s) | duration |
|---|---|---|
| 1 | 1000 | 10 min (600 s) |
| 2 | 4000 | 10 min (600 s) |
| 3 | 8000 | 10 min (600 s) |

Total **30 min** per run. `t_s = 0` at step-1 start. The **first 120 s** of the
run (`warmup_s`) are discarded from steady-state statistics. Use the same seeded
message generator for every run so payload distribution is constant.

> Rationale for the step ramp (not a smooth ramp): each 10-min plateau gives the
> scaler time to reach a new steady state, so we can measure **settling time**
> and **steady-state stability** per load level — the two metrics that separate
> the conditions.

### 0.4 Replicates

**n = 3** per condition. Analysis reports mean ± 95% CI across replicates; plots
show the mean trace with replicate spread. Randomise run order across conditions
to avoid time-of-day / warm-cache confounds.

### 0.5 Metric collection

Prometheus scrape interval **= 15 s** (matches the CSV sample period). Export
per-run with `scripts/export_prom.sh <run_id> <start_epoch> <end_epoch>` (loops
the queries in `prometheus/queries.env`, joins on timestamp → `timeseries_<run_id>.csv`).
Parse ARiSto + KEDA scaling actions into `rebalance_<run_id>.csv`. Append one row
to `run_metadata.csv`. **Verify the exporter metric names once** (§metrics_schema
§1 note) before the first real run.

---

## Group 1 — 4-condition baseline comparison  **(P0, most critical)**

### Claim under test
> Coordinated multi-level autoscaling (DynamiX) sustains higher and more stable
> throughput with lower tail latency under a rising workload than (a) no scaling,
> (b) infrastructure-only scaling, or (c) topology-only scaling.

### The four conditions

| condition | ARiSto (topology) | KEDA (infra pods) | what it isolates |
|---|---|---|---|
| `static`      | **off** — fixed executors/workers | **off** — fixed Supervisor replicas | no-elasticity floor |
| `keda_only`   | **off** | **on** | infra scaling without topology rebalance |
| `aristo_only` | **on**  | **off** — fixed Supervisor replicas | topology scaling without more nodes |
| `dynamix`     | **on**  | **on**  | full coordinated system |

All four run the **same topology, same load profile, same cluster**. Only the
two switches above change.

### How to set each switch

**ARiSto ON/OFF (topology layer):**
- **ON** — deploy the autoscaler side-car/job with the modified-v1 JAR
  `storm-autoscale-v1-1.0.jar`, baseline knobs `window_s=600`,
  `wscale_threshold=0.75`, `bolt_cap_threshold=0.7`, `cooldown_s=300`.
  Record the JAR name in `run_metadata.aristo_jar`.
- **OFF** — do not deploy the autoscaler. Topology parallelism stays at the
  initial values for the whole run.

**KEDA ON/OFF (infrastructure layer):**
- **ON** — apply the `ScaledObject` targeting the Supervisor StatefulSet
  (trigger = the `weight_scale`/Prometheus metric, per draft §III.D; scale-out
  only, `cooldownPeriod` = 300 s, `minReplicaCount` = initial, `maxReplicaCount`
  = campaign cap).
  ```bash
  kubectl apply -f k8s/keda/supervisor-scaledobject.yaml -n <ns>
  ```
- **OFF** — remove it and pin replicas:
  ```bash
  kubectl delete scaledobject supervisor-scaler -n <ns> --ignore-not-found
  kubectl scale statefulset supervisor -n <ns> --replicas=<initial>
  ```

**`static` fixed sizing.** Choose the fixed executor/worker counts and Supervisor
replica count = the *initial* values (not the peak). The point of `static` is to
show what happens when the system cannot grow into the 4k/8k steps.

### Procedure (per run — repeat ×3 per condition, 12 runs total)

1. Reset cluster to initial topology + initial Supervisor replicas; confirm all
   pods Running and Storm UI shows the topology ACTIVE with initial parallelism.
2. Set the two switches for the condition (above). For `dynamix`/`aristo_only`,
   confirm the autoscaler pod is up and reading metrics; for `dynamix`/`keda_only`,
   confirm the `ScaledObject` is `READY=True` (`kubectl get scaledobject -n <ns>`).
3. Start Prometheus range recording / note `start_epoch`.
4. Launch the load driver with `ramp_1k_4k_8k_10min`. Hold for the full 30 min.
5. On completion, note `end_epoch`, stop the driver.
6. Export: `scripts/export_prom.sh <run_id> <start_epoch> <end_epoch>` →
   `timeseries_<run_id>.csv`; parse scaling logs → `rebalance_<run_id>.csv`;
   append `run_metadata.csv`.
7. Tear down / reset before the next run.

`run_id`s: `G1-static-r{1,2,3}`, `G1-keda_only-r{1,2,3}`,
`G1-aristo_only-r{1,2,3}`, `G1-dynamix-r{1,2,3}`.

### Metrics computed (by `dynamix_analysis.py`)
- **Throughput**: mean acked/s per load level; **CoV** (stability) per level.
- **Latency**: p50 / p95 / p99 complete-latency per load level.
- **Settling time**: seconds after each load step to return within ±5 % of the
  new post-step steady-state throughput (static may never settle at 8k → censored).
- **Rebalance count**: ARiSto rebalances and KEDA pod events over the run.
- **Resource trajectory**: `supervisor_pods`, `executors_total` vs time.
- **Saturation gap**: offered − acked at the 8k level (how much load is dropped).

### Figures/tables this group feeds
- **Fig F1** — throughput vs time, 4 conditions overlaid, load steps shaded (headline figure).
- **Fig F2** — p95 latency per condition (bar) + latency CDF.
- **Fig F3** — supervisor-pod and executor trajectories vs time.
- **Fig F4** — settling time & rebalance count, grouped bars.
- **Table T1** — per-condition steady-state throughput (mean±CI), CoV, p95 latency, settling time, rebalances. → `group1_summary.csv`.

---

## Group 2 — ARiSto throughput-formula ablation  **(P2)**

### Claim under test
> The modified throughput formula (windowed rate over a 600 s observation window)
> corrects the failure mode of the original ARiSto v1 formula (cumulative-average
> throughput collapsing toward 0), producing correct scaling decisions.

Background: the thesis shows the original ARiSto v1 cumulative-throughput formula
degenerating to ~0 (thesis Hình 3.8–3.10), which suppresses scale-out. The
modified v1 uses a windowed rate. Group 2 isolates **only that change**.

### The two conditions

| condition | JAR (`run_metadata.aristo_jar`) | throughput formula |
|---|---|---|
| `aristo_orig_v1` | `storm-autoscale-aristo-1.0.jar` | original cumulative average |
| `aristo_mod_v1`  | `storm-autoscale-v1-1.0.jar`     | windowed rate (600 s) |

**Everything else identical**, and identical to the Group 1 `aristo_only`
condition: **KEDA OFF**, Supervisor replicas pinned to initial, same topology,
same `ramp_1k_4k_8k_10min` load, same baseline knobs. This is deliberately the
Group 1 harness with only the JAR swapped — reuse those scripts.

> Note: `G1-aristo_only` **is** `aristo_mod_v1` under this design. You may reuse
> the Group 1 `aristo_only` runs as the `aristo_mod_v1` arm and only add the
> `aristo_orig_v1` runs — saving 3 runs. If you do, copy those `run_id`s under
> `G2-aristo_mod_v1-r*` (or symlink) so Group 2 analysis sees both arms.

### Procedure (×3 per condition, 6 runs — or 3 new if reusing G1)
Identical to Group 1 §Procedure, KEDA OFF, swapping only the autoscaler JAR.
`run_id`s: `G2-aristo_orig_v1-r{1,2,3}`, `G2-aristo_mod_v1-r{1,2,3}`.

### Metrics of interest
- **Computed throughput signal** the scaler *sees* (log it from the autoscaler) —
  expected to collapse toward 0 for `aristo_orig_v1` at higher load, stay correct
  for `aristo_mod_v1`. This directly reproduces the thesis Hình 3.8–3.10 story.
- Resulting **rebalance count** and **actual acked throughput** — the original
  formula under-scales, so actual throughput and rebalances are lower.

### Figures/tables
- **Fig F5** — modified vs original: (top) scaler-computed throughput signal vs
  time; (bottom) actual acked throughput vs time. Shows the formula bug and its
  fix on one canvas. → also `group2_summary.csv` (rebalances, mean acked, under-scale flag).

---

## Group 3 — Parameter sensitivity  **(P1)**

### Claim under test
> DynamiX's behaviour is understood and defensible across its main knobs; the
> chosen baseline (`window_s=600`, `wscale_threshold=0.75`, `bolt_cap_threshold=0.7`)
> is a sensible operating point (throughput stability vs rebalance churn trade-off).

### Design — one-factor-at-a-time (OFAT) from the baseline

Baseline operating point: **`window_s=600`, `wscale_threshold=0.75`,
`bolt_cap_threshold=0.7`**, full DynamiX (ARiSto + KEDA ON). Vary **one** knob at
a time; hold the other two at baseline.

| swept parameter | values | # runs (×3 replicates) |
|---|---|---|
| `window_s` (observation window) | 300, **600**, 900, 1200 | 4 × 3 = 12 |
| `wscale_threshold` (scale-out trigger) | 0.65, **0.75**, 0.85 | 3 × 3 = 9 |
| `bolt_cap_threshold` (bolt capacity) | 0.6, **0.7**, 0.8 | 3 × 3 = 9 |

The baseline point (600 / 0.75 / 0.7) is shared across all three sweeps — run it
**once** (3 replicates) and reuse; that removes 6 duplicate runs. Net new runs:
(4−1)+(3−1)+(3−1) = 7 points × 3 = **21 runs**, plus the shared baseline 3 = 24.

`run_id` convention: `G3-window_s=300-r1`, `G3-wscale_threshold=0.85-r2`,
`G3-bolt_cap_threshold=0.6-r3`, and the shared `G3-baseline-r{1,2,3}`.

### Config injection (how to set a knob without rebuilding the JAR)

The autoscaler reads its knobs from environment / ConfigMap (recommended so a
sweep is a redeploy, not a rebuild):

```yaml
# k8s/aristo/autoscaler-config.yaml  (ConfigMap)
data:
  ARISTO_WINDOW_S:          "600"
  ARISTO_WSCALE_THRESHOLD:  "0.75"
  ARISTO_BOLT_CAP_THRESHOLD:"0.70"
  ARISTO_COOLDOWN_S:        "300"
```
```bash
# set one knob for a sweep point, then restart the autoscaler pod
kubectl set env deployment/aristo-autoscaler -n <ns> ARISTO_WINDOW_S=900
kubectl rollout restart deployment/aristo-autoscaler -n <ns>
```
The `wscale_threshold` also feeds the KEDA `ScaledObject` trigger `threshold`;
keep them consistent by templating both from the same value
(`k8s/render.sh <window_s> <wscale_threshold> <bolt_cap_threshold>`).

### Procedure (per sweep point, ×3)
Same as Group 1 `dynamix`, but set the swept knob via the ConfigMap/env before
starting the load driver. Record the full knob set in `run_metadata.params_json`.

### Metrics of interest (per sweep point)
- **Throughput stability** = coefficient of variation (CoV) of steady-state
  acked/s at the 8k level (lower = more stable).
- **Rebalance frequency** = total scaling actions / run (lower = less churn).
- **Mean steady-state throughput** and **p95 latency** (the knob shouldn't cost
  performance).
- The trade-off: small `window_s` / low threshold → reactive but churny; large
  window / high threshold → stable but slow to respond. The baseline should sit
  near the knee.

### Figures/tables
- **Fig F6** — 3 stacked panels (one per knob): x = knob value, dual signal =
  throughput CoV (stability) and rebalance frequency, baseline value marked. → `group3_summary.csv`.

---

## Master run matrix

| group | condition / sweep point | replicates | run_ids | new runs |
|---|---|---|---|---|
| G1 | static | 3 | `G1-static-r{1,2,3}` | 3 |
| G1 | keda_only | 3 | `G1-keda_only-r{1,2,3}` | 3 |
| G1 | aristo_only | 3 | `G1-aristo_only-r{1,2,3}` (= G2 aristo_mod_v1) | 3 |
| G1 | dynamix | 3 | `G1-dynamix-r{1,2,3}` | 3 |
| G2 | aristo_orig_v1 | 3 | `G2-aristo_orig_v1-r{1,2,3}` | 3 |
| G2 | aristo_mod_v1 | 3 | (reuse G1-aristo_only) | 0 |
| G3 | baseline 600/0.75/0.70 | 3 | `G3-baseline-r{1,2,3}` | 3 |
| G3 | window_s ∈ {300,900,1200} | 3 each | `G3-window_s=<v>-r*` | 9 |
| G3 | wscale_threshold ∈ {0.65,0.85} | 3 each | `G3-wscale_threshold=<v>-r*` | 6 |
| G3 | bolt_cap_threshold ∈ {0.6,0.8} | 3 each | `G3-bolt_cap_threshold=<v>-r*` | 6 |
| | | | **Total new runs** | **39** |

At 30 min/run + reset overhead (~15 min), budget ≈ 39 × 45 min ≈ **29 h** of
cluster time. Prioritise **G1 (12 runs, ~9 h)** first — it alone unblocks
Section V.

---

## Mapping to the review log (what each item discharges)

| review item (priority) | discharged by |
|---|---|
| Run 4-condition comparison → write Section V (**P0**) | Group 1 → F1–F4, T1 |
| De-Vietnamise draft + English figure labels (**P0**) | separate draft-edit pass (not an experiment) |
| Controller-interaction / concurrent-rebalance safety (**P1**) | draft §III.D (done) + cooldown/serialisation described in metrics_schema §4 & G1 KEDA setup |
| Parameter justification / sensitivity (**P1**) | Group 3 → F6, T3 |
| Cloud–fog vs cloud-only framing (**P1**) | cluster-spec table §0.1 makes the real deployment explicit |
| `weight_scale` weight justification (**P2**) | Group 3 `wscale`/`bolt_cap` sweeps + §4 definition |
| Scale-down description (**P2**) | metrics_schema §4 hysteresis + rebalance_events `scale_in` rows quantify it |
| ARiSto version = v1 (**P2**) | Group 2 makes v1 explicit; `run_metadata.aristo_jar` records it |
| Cluster-spec table (**P2**) | §0.1 |
