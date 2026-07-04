# DynamiX Experiment Plan

**Goal:** run 39 cluster experiments → populate `docs/experiment-results/` → re-run
`analysis/dynamix_analysis.py` + `analysis/dynamix_plots.py` → real F1–F6 figures →
write paper Section V.

Total new runs: 39 × ~45 min (run + reset) ≈ **29 h** of cluster time.

---

## Status

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — cluster + prereqs | 🔲 not started | must finish before G1 |
| G1 — 4-condition baseline | 🔲 not started | starts tomorrow |
| G2 — formula ablation | 🔲 not started | |
| G3 — parameter sensitivity | 🔲 not started | |
| Paper fix — weight_scale formula | 🔲 not started | see §Note 1 |
| Paper fix — OutputWriter in v1 | 🔲 not started | see §Note 2 |

---

## Phase 0 — Prerequisites (complete today, before G1)

### 0-A · Deploy GKE cluster + Storm stack

- [x] Create GKE Standard cluster (3–5 × `e2-standard-4`, cluster-autoscaler max 8 nodes)
- [x] Create GCE VM (`e2-medium` + 50 GB persistent disk) for MQTT publisher + DEBS dataset
- [X] Apply K8s manifests in order:
  ```bash
  kubectl create -f k8s/storm-ns.yml
  kubectl create -f k8s/storm-svc.yml
  kubectl create -f k8s/storm-pv.yml
  kubectl create -f k8s/storm-pvc.yml
  kubectl create -f k8s/storm-k8s.yml
  ```
- [ ] Deploy monitoring stack (`k8s/monitoring/`)
- [ ] Deploy storm-exporter; confirm `weight_scale{ClusterHost="nimbus-ui:8081"}` appears in Prometheus
- [ ] Deploy KEDA operator
- [ ] Deploy topology inside nimbus: `storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo`
- [ ] Start MQTT publisher on the GCE VM at 1k msg/s; confirm throughput in Grafana

### 0-B · Build both JARs and copy to nimbus

- [ ] `cd storm-src && mvn package` → verify both JARs exist:
  - `target/storm-autoscale-v1-1.0.jar`
  - `target/storm-autoscale-aristo-1.0.jar`
- [ ] Copy both JARs into the nimbus pod:
  ```bash
  kubectl cp target/storm-autoscale-v1-1.0.jar \
    <nimbus-pod>:/opt/storm/lib/ -n storm-cluster
  kubectl cp target/storm-autoscale-aristo-1.0.jar \
    <nimbus-pod>:/opt/storm/lib/ -n storm-cluster
  ```

### 0-C · Record cluster spec (fills paper §IV.B)

Fill this and save to `docs/experiment-results/cluster-spec.md`:

| item | value |
|---|---|
| GKE version | |
| Node type / count | |
| vCPU per node | |
| RAM per node | |
| Storm version | |
| Nimbus JVM heap | |
| Supervisor slots | |
| KEDA version | |
| Storm-exporter image | |
| Prometheus scrape interval | set to 15 s |
| KEDA cooldown | 300 s |

### 0-D · Calibrate MQTT load (publisher → msgs/s)

The publisher's `-s <n>` flag sets msgs/s. Verify once:
- [ ] Run publisher at `-s 1000`, confirm `sum(rate(spouts_acked{SpoutId="spout-data-iot-data"}[1m]))` ≈ 1000 in Prometheus
- [ ] Repeat for `-s 4000` and `-s 8000`

### 0-E · OutputWriter decision (see §Note 2)

**Decision needed:** implement OutputWriter in `rulebase/v1/` (2–3 h) or use fallback.

- [ ] **Option A — implement now** (recommended if time allows): port `OutputWriter.java` +
  `TopologyConfiguration.java` from `rulebase/aristo/` into `rulebase/v1/`, wire into
  `FlowCheck.rebalanceInit()`, rebuild JAR. Enables precise `rebalance_*.csv` rows for
  all conditions.
- [ ] **Option B — use fallback for G1**: proceed without OutputWriter. After each run,
  infer ARiSto rebalances from step changes in `executors_total` and `workers_total` in
  the timeseries. F4 rebalance bars will be approximate. Implement OutputWriter before G2.

### 0-F · Verify analysis pipeline with synthetic data

- [ ] Confirm Python deps: `pip install pandas numpy matplotlib`
- [ ] `cd analysis && python3 dynamix_analysis.py data` → no SchemaError
- [ ] `python3 dynamix_plots.py data` → F1–F6 regenerated without errors
- [ ] Prometheus PromQL: verify real metric names match `docs/metrics-schema.md` v1.1:
  ```bash
  curl http://<storm-exporter>:8082/metrics | grep -iE "spouts_acked|bolts_capacity|weight_scale|worker_cluster"
  ```

---

## G1 — 4-Condition Baseline Comparison

**Claim:** DynamiX (both layers) sustains higher throughput + lower latency than any single layer.
**Runs:** 4 conditions × 3 replicates = **12 runs**, ~9 h.
**Feeds:** F1, F2, F3, F4, Table T1 → paper Section V.

### Run matrix

| run_id | condition | ARiSto JAR | KEDA | JAR flag |
|---|---|---|---|---|
| G1-static-r{1,2,3} | static | off | off | — |
| G1-keda_only-r{1,2,3} | keda_only | off | on | — |
| G1-aristo_only-r{1,2,3} | aristo_only | `storm-autoscale-v1-1.0.jar` | off | — |
| G1-dynamix-r{1,2,3} | dynamix | `storm-autoscale-v1-1.0.jar` | on | — |

Randomise run order across conditions to avoid warm-cache bias.

### Per-run procedure

- [ ] Reset cluster to initial state:
  ```bash
  # Kill autoscaler if running
  kubectl delete -f k8s/keda/autoscale-keda.yaml --ignore-not-found
  kubectl scale statefulset supervisor -n storm-cluster --replicas=2
  kubectl exec -it <nimbus-pod> -n storm-cluster -- storm kill iot-smarthome -w 30
  # wait ~60s then redeploy topology
  kubectl exec -it <nimbus-pod> -n storm-cluster -- bash -lc \
    'cd /opt/storm/lib && storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo'
  ```
- [ ] Set condition switches (ARiSto on/off, KEDA on/off) per run matrix above
- [ ] Note `start_epoch=$(date +%s)`
- [ ] Start load ramp on the publisher VM:
  ```bash
  node index.js -f /data/house-1.csv -s 1000 -b <mqtt-broker-ip>  # hold 10 min
  # after 10 min:
  node index.js -f /data/house-1.csv -s 4000 -b <mqtt-broker-ip>  # hold 10 min
  # after 10 min:
  node index.js -f /data/house-1.csv -s 8000 -b <mqtt-broker-ip>  # hold 10 min
  ```
- [ ] After 30 min: note `end_epoch=$(date +%s)`
- [ ] Export timeseries (loop Prometheus `query_range` per metric, join on timestamp):
  ```bash
  # example for one metric:
  curl -sG 'http://<prometheus>:9090/api/v1/query_range' \
    --data-urlencode 'query=sum(rate(spouts_acked{SpoutId="spout-data-iot-data"}[1m]))' \
    --data-urlencode "start=$start_epoch" \
    --data-urlencode "end=$end_epoch" \
    --data-urlencode 'step=15s'
  ```
  Full metric list in `docs/metrics-schema.md §1`.
- [ ] Save `timeseries_<run_id>.csv` + `rebalance_<run_id>.csv` to
  `docs/experiment-results/G1/<condition>/`
- [ ] Append row to `docs/experiment-results/run_metadata.csv`

### G1 done when

- [ ] All 12 `timeseries_G1-*.csv` in place
- [ ] All 12 `rebalance_G1-*.csv` in place (header-only for static; ✓)
- [ ] `python3 analysis/dynamix_analysis.py docs/experiment-results` → no SchemaError
- [ ] `python3 analysis/dynamix_plots.py docs/experiment-results` → F1–F4 regenerated from real data
- [ ] Delete synthetic `analysis/data/` so it can't be confused with real results

---

## G2 — ARiSto Formula Ablation

**Claim:** windowed throughput formula (modified v1) fixes the collapse-to-zero failure mode
of the original cumulative formula.
**Runs:** 3 new runs (original v1) + reuse G1-aristo_only as modified-v1 arm = **3 new runs**.
**Feeds:** F5 → paper §III.C.

> Note: G1-aristo_only runs **are** the G2-aristo_mod_v1 arm. Copy or symlink those CSVs
> under `G2/aristo_mod_v1/` so the analysis script sees both arms.

### Run matrix

| run_id | JAR | formula |
|---|---|---|
| G2-aristo_orig_v1-r{1,2,3} | `storm-autoscale-aristo-1.0.jar` | cumulative average |
| G2-aristo_mod_v1-r{1,2,3} | reuse G1-aristo_only | windowed 600 s |

Procedure: identical to G1, KEDA off, swap only the JAR.

### G2 done when

- [ ] 3 `timeseries_G2-aristo_orig_v1-r*.csv` collected
- [ ] G1-aristo_only CSVs symlinked/copied under `G2/aristo_mod_v1/`
- [ ] F5 renders from real data

---

## G3 — Parameter Sensitivity

**Claim:** baseline values (window=600 s, wscale=0.75, bolt-cap=0.7) sit at the knee of the
stability-vs-churn trade-off.
**Runs:** 7 sweep points × 3 replicates + 3 shared baseline = **24 runs** (reuse G1-dynamix as
baseline arm).
**Feeds:** F6, Table T3 → paper §V.

### Sweep matrix

| sweep | values | new runs |
|---|---|---|
| `window_s` | 300, 900, 1200 (baseline 600 = reuse G1-dynamix) | 9 |
| `wscale_threshold` | 0.65, 0.85 (baseline 0.75 = reuse G1-dynamix) | 6 |
| `bolt_cap_threshold` | 0.6, 0.8 (baseline 0.70 = reuse G1-dynamix) | 6 |
| | **Total new** | **21** |

How to change each knob without rebuilding (for wscale threshold only):
- `wscale_threshold`: edit `threshold` in `k8s/keda/autoscale-keda.yaml`, re-apply
- `window_s` + `bolt_cap_threshold`: edit `FlowCheck.java` (`totalAcked/600` divisor,
  `boltStats.getCapacity() > 0.7` threshold), `mvn package`, copy new JAR into nimbus

### G3 done when

- [ ] 21 new `timeseries_G3-*.csv` collected
- [ ] F6 renders from real data

---

## Paper fixes (parallel with experiments)

### Fix 1 — weight_scale formula (§Note 1)

**What the code does** (`k8s/keda/custom-metrics/main.py`, line 94):
```
weight_scale = 0.6 × (worker_util / 0.70)
             + 0.2 × (bolt_capacity / 0.50)
             + 0.2 × (spout_latency / 100 ms)
```
Worker is also divided by its threshold (0.70) — this is NOT in the paper's §III.D text.
The paper implies worker_util enters raw.

**But `main.py` is not in the KEDA signal path.** `autoscale-keda.yaml` uses
`type: prometheus`, querying `weight_scale` from Prometheus, which is published by
`storm_exporter` (not `main.py`). The authoritative formula is in the storm_exporter
source ([mr4x2/storm_exporter_prometheus](https://github.com/mr4x2/storm_exporter_prometheus)).

- [ ] Check storm_exporter source to get the exact formula it computes for `weight_scale`
- [ ] If storm_exporter matches `main.py` (divides worker by 0.70): update paper §III.D to
  add `/0.70` for the worker term and explain it's normalisation to threshold
- [ ] If storm_exporter matches the paper (raw ratio): fix `main.py` to match (cosmetic — it
  isn't used by KEDA anyway), no paper change needed
- [ ] Either way: note in §III.D that the KEDA trigger threshold is 0.75 (in
  `autoscale-keda.yaml`), not 0.7 (the dead constant in `main.py`)

### Fix 2 — OutputWriter in rulebase/v1/ (§Note 2)

- [ ] Port `OutputWriter.java` + `TopologyConfiguration.java` from `rulebase/aristo/` into
  `rulebase/v1/`
- [ ] Wire into `FlowCheck.rebalanceInit()`: write structured record (timestamp, workers,
  executors, avg throughput, avg latency) on each rebalance
- [ ] Rebuild `storm-autoscale-v1-1.0.jar`, re-copy into nimbus
- [ ] Required before G2 (the ablation comparison needs rebalance-count from both JARs)

### Fix 3 — Remove Vietnamese text from paper draft

- [ ] §III.C opening note (Vietnamese): "Phần này phải bổ sung thêm sơ đồ..."
- [ ] Translate/finalise all figure labels and captions to English

---

## Notes

### §Note 1 — weight_scale discrepancy detail

`main.py` is deployed (`k8s/keda/custom-metrics/autoscale-controller-deployment.yml`) but
its `/isActive` endpoint uses threshold `0.7` while the ScaledObject uses `0.75`.
More importantly, the ScaledObject is `type: prometheus` (not `type: external`), so it
reads `weight_scale` from Prometheus — computed by storm_exporter — and never calls
`main.py`'s endpoints. `main.py` appears to be an earlier prototype of the scaler that
was superseded when the storm_exporter was extended to publish `weight_scale` directly.
The paper description should match storm_exporter, not `main.py`.

### §Note 2 — OutputWriter absence in rulebase/v1/

`rulebase/aristo/` has `OutputWriter.java` + `TopologyConfiguration.java` (ported from
Aristo v3/v4). `rulebase/v1/` has neither. Until OutputWriter is added:
- `rebalance_G1-dynamix-*.csv` and `rebalance_G1-aristo_only-*.csv` will have no
  `layer=aristo` rows — only KEDA events (for dynamix) or nothing (for aristo_only).
- F4 (rebalance count by layer) will be incomplete for the two headline conditions.
- Fallback: infer ARiSto rebalances from step-changes in `executors_total` column of
  the timeseries. Less precise but sufficient for G1.
