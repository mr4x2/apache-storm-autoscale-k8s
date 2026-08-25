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
| **BLOCKER — topology flow-control** | 🟡 code fixed, not verified | **see §Blocker 0 — gates ALL real runs** |

---

## ⚠ Blocker 0 — Topology flow-control (fix + verify before ANY real run)

**Symptom (found 2026-08-04 in the real G1 runs under `scripts/docs/experiment-results/G1/`):**
neither low nor high traffic scales like the original thesis. Under heavy load the topology
**collapses** — `complete_latency` hit **12,608 ms**, throughput fell to **0**, and this did
not recover even after ARiSto scaled workers 2→4 and KEDA scaled pods 1→3. Under low load
nothing scales (weight ≈ 0.5). Every condition tops out at the **same ~600 msg/s ceiling**,
so throughput is currently NOT a valid comparison metric.

**Root cause:** no backpressure + an unreachable setpoint + an unbounded metric.
`weight_scale ≈ latency_ms / 500` (unbounded latency term) → explodes to 25 → KEDA pegs pods
uselessly, because the bottleneck is downstream (sum/forecast/MySQL sink), not the parallel
split bolts (their capacity was only ~0.5, never maxed). Adding workers/pods can't drain a
sink bottleneck.

### Fixes applied (2026-08-04) — need redeploy + verify

| # | file | change | status |
|---|---|---|---|
| 1 | `config/storm-nimbus.yaml:268` | `topology.max.spout.pending: null → 1000` (flow control) | ✅ edited, ⏳ redeploy |
| 2 | `storm-src/src/main/resources/target.txt` | `4000 → 600` both spouts (reachable setpoint; **placeholder — calibrate**) | ✅ edited, ⏳ redeploy |
| 3 | `k8s/keda/custom-metrics/main.py:93` | clip each normalized signal to [0,1] so latency can't dominate | ✅ edited (see caveat) |

> **Fix #3 caveat:** `main.py` is NOT in the live KEDA path (see §Controller below). The
> `weight_scale` KEDA actually queries is published by **storm_exporter**
> ([mr4x2/storm_exporter_prometheus](https://github.com/mr4x2/storm_exporter_prometheus)).
> The same clip MUST be applied there for live behavior to change. The `main.py` edit only
> fixes the in-repo copy / documents the intended formula.
>
> Fixes #1 and #2 are baked into the topology at submit time → require `storm kill
> iot-smarthome` + resubmit (and rebuild the autoscaler JAR, which bundles `target.txt`).

### Why reduce target.txt (answers "I set 4000 so ARiSto runs forever")

`FlowCheck.java:199` only evaluates/scales a spout **while `target > current throughput`**;
when throughput catches the target it emits "target reached" and stops. Setting target=4000
when the lab delivers/handles only ~600 keeps that gate permanently open — but that is **not**
healthy "runs forever," it is **never converges**: the controller always believes it is
under-provisioned and thrashes toward max whenever any latency/throughput wobble bumps
severity. A reviewer reads "never reaches steady state" as an *unstable controller*, not a
feature. Also the target is a **demand/SLA setpoint** — asking for 4000 msg/s of acked
throughput is meaningless when only ~600 msg/s is ever offered/achievable.

**To get continuous, legible autoscaling (what you actually want):** ramp the *offered load*
against a *reachable* target. As load climbs each step, throughput < target keeps the gate
open, severity builds from the real load increase → scale out → throughput catches the
target → converges → next louder step reopens it = the staircase "resources track load"
figure. Severity magnitude comes from throughput-drop / latency-rise trends
(`compareSpoutStats`), NOT from the size of the target gap — so a bigger target does not
scale "harder," it only removes the converged state. Set target ≈ the load you can actually
inject/sustain (~600 now; raise it later only if publishers + a fixed sink genuinely push more).

### Controller: nothing is missing — main.py is vestigial (confirmed vs thesis §3.3.2.2)

The thesis autoscaling controller = **storm_exporter (computes `weight_scale`) + KEDA
ScaledObject with a `type: prometheus` trigger** (`autoscale-keda.yaml`: metricName
`weight_scale`, threshold 0.75, query straight from Prometheus). That pipeline **is already
deployed and working** — the real dynamix run scaled pods 1→3 through it. The FastAPI
`main.py` custom-metrics service is an earlier prototype that is **not wired into KEDA**
(the trigger is `prometheus`, not `external`), so you are NOT missing a deployment by never
applying it. The thesis formula (Bảng 3.1) is exactly `main.py`'s, and the thesis text
assumes `weight_scale ∈ ~[0,1]` (worker-dominated, latency/bolt secondary) — the 12s-latency
explosion violates that design intent, so the clip **restores** the thesis model, it does not
change it. One real config drift to note: `autoscale-keda.yaml` sets `maxReplicaCount: 7`
while the thesis specifies max 3.

### Layer-coordination tuning (2026-08-04) — "ARiSto first, pods slow & last"

Goal: the cheap/fast layer (ARiSto executors+workers) exhausts its ability before the
expensive/slow layer (KEDA pods) adds infrastructure. Symptom before tuning: pods scaled
fast, workers slow — root cause was the `weight_scale`=25 explosion (now clipped) slamming
KEDA to max instantly.

- **KEDA slowed via timing, NOT threshold** (`autoscale-keda.yaml`): `maxReplicaCount 7→3`
  (thesis), `pollingInterval 60`, `cooldownPeriod 300`, HPA `scaleUp` stabilization 300s +
  max **+1 pod / 5 min**, `scaleDown` 600s. **Threshold kept at 0.75** — raising it would
  collide with the G3 `wscale_threshold` sweep (0.65/0.85 around 0.75) and move the baseline.
- **The hierarchy is mechanical:** each supervisor pod has **4 slots** (`supervisor.slots.ports`
  6700–6703). ARiSto fills a pod's 4 slots → utilization →1.0 → weight crosses 0.75 → KEDA
  adds ONE pod (slowly) → ARiSto fills the new slots. `maxWorkers=28` ≫ slot ceiling (12 at
  3 pods), so ARiSto is slot-bound, not cap-bound — correct.
- **ARiSto "faster" lever (optional, needs JAR rebuild):** `FlowCheck.java:69` `maxSeverity
  2→1` reacts on the first bad cycle instead of two. ⚠️ increases churn; also there is an
  existing **scale-in-to-0 flap** in the real data (`rebalance_G1-dynamix-r1`: workers 2→0).
  Decide after the diagnostic run — don't stack an aggressive scale-out on an unfixed scale-in.

> ⚠️ Reminder: this shapes the pod/worker CURVES. It does not create throughput — that still
> depends on the sink bottleneck (diagnostic gate below). Tune the system, then report what it
> actually does; do not tune toward a desired conclusion.

### 🚦 Diagnostic gate — the run that decides if a paper exists

After redeploying #1–2, run **one dynamix** run at the moderate ramp **1→2→4→6 buildings,
`SPEED=100`** (≈70→140→280→420 msg/s; do NOT jump to 8 = collapse zone), 10 min/step, and check:

- [ ] latency stays **bounded** (sub-second), not 12s
- [ ] `weight_scale` stays in a **sane range** (~[0,1]), not 25
- [ ] **throughput rises and latency falls when scaling fires** ← the make-or-break test
- [ ] Recalibrate `target.txt` to the measured sustained single-worker throughput

**If throughput tracks scaling → run the full G1/G2/G3 matrix.**
**If throughput still flatlines when workers/pods increase → the sink is the bottleneck;
no autoscaler can help until it is parallelized. Fix that before spending 29 h of runs.**

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
- [X] Deploy monitoring stack (`k8s/monitoring/`)
- [X] Deploy storm-exporter; confirm `weight_scale{ClusterHost="nimbus-ui:8081"}` appears in Prometheus
- [ ] Deploy KEDA operator
- [X] Deploy topology inside nimbus: `storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo`
- [X] Start MQTT publisher on the GCE VM at 1k msg/s; confirm throughput in Grafana

### 0-B · Build both JARs and copy to nimbus

- [X] `cd storm-src && mvn package` → verify both JARs exist:
  - `target/storm-autoscale-v1-1.0.jar`
  - `target/storm-autoscale-aristo-1.0.jar`
- [X] Copy both JARs into the nimbus pod:
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
  > ✅ subdirectory layout works — `dynamix_analysis.py` glob is now recursive
- [ ] Append row to `docs/experiment-results/run_metadata.csv`
  > `run_metadata.csv` must stay in the top-level `docs/experiment-results/` (not in a subdir)

### G1 done when

- [ ] All 12 `timeseries_G1-*.csv` in place
- [ ] All 12 `rebalance_G1-*.csv` in place (header-only for static; ✓)
- [ ] `python3 analysis/dynamix_analysis.py docs/experiment-results` → no SchemaError
- [ ] `python3 analysis/dynamix_plots.py docs/experiment-results` → F1–F4 regenerated from real data
- [ ] Delete synthetic `analysis/data/` so it can't be confused with real results

### Post-experiment — window-cap the real-data comparison (§Note 3)

`dynamix` reacts slower than the fixed 30-min load ramp (pod-level KEDA scaling
+ ARiSto worker growth need time to settle), so its capture window can run
longer than static/aristo_only. Comparing full raw ranges would let that extra
tail skew the comparison — not apples-to-apples. `analysis/compare_g1_real.py`
now supports `--window-cap` to fix this (done 2026-08-05, ready to use once a
clean G1-dynamix run exists — **do not run this against the current
`G1-dynamix-r1` file**, see §Note 4).

- [ ] After a clean, hands-off G1-dynamix run replaces the concatenated one:
  `scripts/venv/bin/python3 analysis/compare_g1_real.py --window-cap auto`
  (caps every condition to the shortest condition's max `t_s`; pass a number
  of seconds instead of `auto` to force a specific window, e.g. `1800`)
- [ ] Check the printed `full max t_s` / `used for comparison` table — confirm
  which condition(s) got truncated and note it in the paper's methodology
  (dynamix's post-cap tail is legitimate content for a separate
  settling-behavior figure, just not the headline comparison numbers)
- [ ] `dynamix_analysis.py`'s schema-driven summary tables (`per_level_metrics`,
  `summarize_group1`) already implicitly cap at `load_profile_default.total_duration_s`
  (1800s, `docs/metrics-schema.json`) since they only compute within defined
  load-step windows — no separate change needed there, but this needs
  reverifying once a clean run is loaded (its `_validate_timeseries_rows`
  monotonic-`t_s` check will reject the current concatenated file, which is a
  feature: see §Note 4)

---

## G2 — ARiSto Formula Ablation

**Claim:** windowed throughput formula (modified v1) fixes the collapse-to-zero failure mode
of the original cumulative formula.
**Runs:** 3 new runs (original v1) + reuse G1-aristo_only as modified-v1 arm = **3 new runs**.
**Feeds:** F5 → paper §III.C.

> ⚠️ **Reuse requires column editing, not just copy/symlink.** `summarize_group2()` filters
> `group == "G2"`. Copied G1 files still have `group="G1"` and will be silently ignored.
> After copying, run:
> ```python
> import pandas as pd, glob
> for p in glob.glob("docs/experiment-results/G2/aristo_mod_v1/timeseries_*.csv"):
>     df = pd.read_csv(p); df["group"] = "G2"; df["condition"] = "aristo_mod_v1"; df.to_csv(p, index=False)
> for p in glob.glob("docs/experiment-results/G2/aristo_mod_v1/rebalance_*.csv"):
>     df = pd.read_csv(p); df["group"] = "G2"; df["condition"] = "aristo_mod_v1"; df.to_csv(p, index=False)
> ```

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

> ⚠️ **Same reuse column-edit rule as G2.** G1-dynamix CSVs have `group="G1"`. After copying
> to `G3/baseline/`, update `group="G3"` and `condition="baseline"` using the same Python
> snippet as above (replacing path and condition label).
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
  > ⚠ Possibly stale: `rulebase/v1/OutputWriter.java` + `TopologyConfiguration.java`
  > exist now (commit `8df90b2`), and the real `G1-dynamix-r1` capture already has
  > `layer=aristo` rows for a `workers` component (see §Note 4). Reverify against
  > current code before assuming this note's "no layer=aristo rows" premise still holds.

### §Note 3 — window-cap for the real-data comparison

`static`/`keda_only`/`aristo_only` run a fixed 30-min load ramp (`docs/runbook-G1.md`
Step 2). `dynamix` combines both layers, so KEDA pod scale-out + ARiSto worker
placement can need longer to settle — its capture window isn't guaranteed to match
the other three. `analysis/compare_g1_real.py --window-cap {auto|SECONDS}` truncates
every condition to a common `t_s` range before comparing/plotting, so the headline
numbers stay apples-to-apples; anything beyond the cap (e.g. dynamix's extra settling
time) is still in the source CSV and worth a separate supplementary figure, just not
mixed into the main comparison. `dynamix_analysis.py`'s schema-driven pipeline
(`per_level_metrics`, `summarize_group1`) doesn't need the same fix — it already only
aggregates within `load_profile_default`'s defined step windows (1800s total,
`docs/metrics-schema.json`), so a longer tail on one condition is implicitly excluded.

### §Note 4 — G1-dynamix-r1 is not usable as captured

The current `scripts/docs/experiment-results/G1/dynamix/{state,rebalance}_G1-dynamix-r1.csv`
is six concatenated poller sessions spanning 2026-08-03 23:04 → 2026-08-04 23:54 (`t_s`
resets to 1 six times), not one clean run — `dynamix_analysis.py`'s monotonic-`t_s`
check (`_validate_timeseries_rows`) will reject it as-is, which is correct behavior.
The last segment (22:56–23:54, `t_s` 0–3439) also involved a manual `storm rebalance`
to fix a supervisor pod KEDA added but ARiSto never gave workers to (see Open blocker
#3 in `CLAUDE.md`). Don't promote this file to `analysis/data/` or window-cap around
it expecting a valid result — re-run G1-dynamix r1/r2/r3 hands-off after the blocker
#3 fix lands, then apply §Note 3.
