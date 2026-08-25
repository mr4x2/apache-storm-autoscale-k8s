# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Key Commands

```bash
# Build both autoscaler JARs (produces two fat JARs in storm-src/target/)
cd storm-src && mvn package
# → target/storm-autoscale-v1-1.0.jar     (modified v1, entry: rulebase.v1.TopologyParser)
# → target/storm-autoscale-aristo-1.0.jar  (original v1, entry: rulebase.aristo.TopologyParser)

# Start local cluster
docker compose up -d

# Deploy topology (inside nimbus container)
storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo

# Run modified-v1 autoscaler (inside nimbus container)
storm jar storm-autoscale-v1-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt

# Run original-v1 autoscaler (Group 2 comparison)
storm jar storm-autoscale-aristo-1.0.jar org.apache.storm.starter.rulebase.aristo.TopologyParser input.txt target.txt
```

```bash
# Run analysis pipeline (from analysis/)
cd analysis
python3 dynamix_analysis.py data          # validate + summarise → tables/
python3 dynamix_plots.py    data          # render figures → figures/
# ⚠ analysis/data/ is SYNTHETIC — delete before quoting any number in the paper
```

## Architecture (Short)

Two autoscaling mechanisms run simultaneously:

1. **Java rule-based autoscaler** (`storm-src/`) — runs inside Nimbus, adjusts executor/worker counts via Storm's Thrift `rebalance` API. Entry point: `rulebase/v1/TopologyParser`. Polls every 30s; triggers when spout severity ≥ 2. See [`docs/autoscaler-java.md`](docs/autoscaler-java.md).

2. **KEDA pod autoscaler** (`k8s/keda/`) — Python FastAPI service computes a weighted composite metric (worker utilization 60% + bolt capacity 20% + spout latency 20%) from Prometheus. KEDA scales the `supervisor` StatefulSet (1–7 pods) when weight > 0.75. See [`docs/autoscaler-keda.md`](docs/autoscaler-keda.md).

**Topology** (`iot-smarthome`): single spout → 8 split bolts → avg → sum/forecast → MySQL. DAG defined in `storm-src/src/main/resources/input.txt`.

**Metrics flow**: Storm UI → storm-exporter (port 8082) → Prometheus → KEDA Controller + Grafana.

## Related Projects

| Repository | Role |
|---|---|
| [fimocode/stormsmarthome](https://github.com/fimocode/stormsmarthome) | Core topology source — `com.storm.iotdata.MainTopo` and all bolts/spouts |
| [mr4x2/storm_exporter_prometheus](https://github.com/mr4x2/storm_exporter_prometheus) | Prometheus exporter; also computes and publishes `weight_scale` metric used by KEDA |

> `weight_scale` is published by `storm_exporter`, **not** by the KEDA controller FastAPI (`k8s/keda/custom-metrics/main.py`). The ScaledObject queries it directly from Prometheus.

## Docs Index

| Doc | Contents |
|---|---|
| [`plan.md`](plan.md) | **Active experiment tracker** — Phase 0 checklist, G1/G2/G3 run matrices, paper fixes |
| [`docs/architecture.md`](docs/architecture.md) | Full system diagram, component table, port reference |
| [`docs/autoscaler-java.md`](docs/autoscaler-java.md) | Java autoscaler algorithm, class structure, build |
| [`docs/autoscaler-keda.md`](docs/autoscaler-keda.md) | KEDA scaler, composite metric formula, API endpoints |
| [`docs/storm-topology.md`](docs/storm-topology.md) | Topology DAG, throughput targets, Storm config |
| [`docs/deployment-docker.md`](docs/deployment-docker.md) | Docker Compose setup, MQTT publisher, monitoring |
| [`docs/deployment-k8s.md`](docs/deployment-k8s.md) | K8s deployment steps, KEDA setup, custom images |
| [`docs/monitoring.md`](docs/monitoring.md) | storm-exporter metrics, Prometheus queries, Grafana |
| [`docs/related-projects.md`](docs/related-projects.md) | Full details on stormsmarthome and storm_exporter_prometheus |
| [`docs/aristo-versions.md`](docs/aristo-versions.md) | Aristo v1–v4 diff table + exact changes made to v1 for this repo |
| [`docs/experiments.md`](docs/experiments.md) | DynamiX paper experiment checklist (Group 1/2/3), runnable commands, PromQL, results tables, analysis pipeline + figure map |
| [`docs/g1-known-issues.md`](docs/g1-known-issues.md) | **Working checklist** — G1 data-quality problems found 2026-08-08 (throughput/latency collapse, stale load-profile constants, ARiSto no-scale-down, dynamix r1/r2 unusable); fix order included |
| [`docs/metrics-schema.md`](docs/metrics-schema.md) | Data contract v1.1 for experiment-run CSVs (columns, real PromQL for this exporter, validation); JSON twin `docs/metrics-schema.json` |
| [`analysis/README.md`](analysis/README.md) | Analysis/plotting scripts that turn run CSVs into Section V summary tables + figures F1–F6; lists 2 open blockers |
| [`artifacts/README.md`](artifacts/README.md) | Original Claude Science experiment bundle (reference copy); integrated versions live in `analysis/` and `docs/` |

## Key Files

| File | Role |
|---|---|
| `storm-src/src/main/resources/input.txt` | Topology DAG edges (autoscaler reads this) |
| `storm-src/src/main/resources/target.txt` | Throughput targets per spout |
| `k8s/keda/custom-metrics/main.py` | KEDA controller — composite metric computation |
| `k8s/keda/autoscale-keda.yaml` | KEDA ScaledObject (threshold 0.75, max 7 pods) |
| `k8s/storm-k8s.yml` | All K8s workloads (supervisor is StatefulSet) |
| `config/storm-nimbus.yaml` | Full Storm config |
| `analysis/dynamix_analysis.py` | Validates run CSVs against schema, writes `tables/group{1,2,3}_summary.csv` |
| `analysis/dynamix_plots.py` | Renders F1–F6 PNGs from summary tables + timeseries |
| `analysis/data/` | **Synthetic placeholder data only** — 42 fabricated runs; replace with real cluster exports |
| `docs/metrics-schema.json` | Machine-readable data contract; `dynamix_analysis.py` validates every CSV against this |

## Open blockers (must fix before paper results are valid)

1. **`OutputWriter` not in `rulebase/v1/`** — modified-v1 / DynamiX conditions emit no `layer=aristo` rebalance rows; F4 rebalance columns are blank for the P0 comparison. See [`docs/aristo-versions.md`](docs/aristo-versions.md) → "Not Done".
2. **`weight_scale` formula discrepancy** — draft §III writes `0.6·worker + 0.2·bolt + 0.2·latency`; the actual code (`k8s/keda/custom-metrics/main.py`) divides each signal by its threshold (0.70 / 0.50 / 100 ms) first. Reconcile the paper text with the code.
3. **KEDA pod scale-out and ARiSto worker growth are decoupled** — `FlowCheck.java:214` only grows `workers` as a side-effect of a bolt-severity trip in the same poll cycle (`changes > 0`); it never checks whether a newly-added supervisor pod (from KEDA) is sitting idle. Observed in `G1-dynamix-r1` (2026-08-04, ~22:56–23:54 segment): KEDA added a 2nd supervisor pod at `t_s=1514` but it carried 0 workers until `t_s=2239` (~12 min), fixed only by manual `storm rebalance`. Also, `cores` is hardcoded to `2` in `FlowCheck.java:51` but the deployed supervisor pod CPU limit (`k8s/storm-k8s.yml:79-80`) is `4000m` (4 cores) — the growth threshold is using the wrong constant. Fix deferred; **do not** carry manually-rebalanced runs into paper data — the poller (`storm_snapshot.py`) labels any worker-count delta `layer=aristo` regardless of whether a human or the autoscaler triggered it, so manual intervention is indistinguishable from autoscaler action in the CSV. Re-run G1-dynamix hands-off after the fix lands.
