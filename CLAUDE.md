# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Key Commands

```bash
# Build autoscaler JAR
cd storm-src && mvn package

# Start local cluster
docker compose up -d

# Deploy topology (inside nimbus container)
storm jar Storm-IOTdata-1.0.jar com.storm.iotdata.MainTopo

# Run Java autoscaler (inside nimbus container)
storm jar storm-autoscale-1.0.jar org.apache.storm.starter.rulebase.v1.TopologyParser input.txt target.txt
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
| [`docs/architecture.md`](docs/architecture.md) | Full system diagram, component table, port reference |
| [`docs/autoscaler-java.md`](docs/autoscaler-java.md) | Java autoscaler algorithm, class structure, build |
| [`docs/autoscaler-keda.md`](docs/autoscaler-keda.md) | KEDA scaler, composite metric formula, API endpoints |
| [`docs/storm-topology.md`](docs/storm-topology.md) | Topology DAG, throughput targets, Storm config |
| [`docs/deployment-docker.md`](docs/deployment-docker.md) | Docker Compose setup, MQTT publisher, monitoring |
| [`docs/deployment-k8s.md`](docs/deployment-k8s.md) | K8s deployment steps, KEDA setup, custom images |
| [`docs/monitoring.md`](docs/monitoring.md) | storm-exporter metrics, Prometheus queries, Grafana |
| [`docs/related-projects.md`](docs/related-projects.md) | Full details on stormsmarthome and storm_exporter_prometheus |

## Key Files

| File | Role |
|---|---|
| `storm-src/src/main/resources/input.txt` | Topology DAG edges (autoscaler reads this) |
| `storm-src/src/main/resources/target.txt` | Throughput targets per spout |
| `k8s/keda/custom-metrics/main.py` | KEDA controller — composite metric computation |
| `k8s/keda/autoscale-keda.yaml` | KEDA ScaledObject (threshold 0.75, max 7 pods) |
| `k8s/storm-k8s.yml` | All K8s workloads (supervisor is StatefulSet) |
| `config/storm-nimbus.yaml` | Full Storm config |
