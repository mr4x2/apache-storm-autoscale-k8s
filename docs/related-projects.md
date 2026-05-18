# Related Projects

This repository is part of a research system composed of three repositories. Each one has a distinct responsibility.

---

## 1. stormsmarthome — Core Topology

**Repository:** https://github.com/fimocode/stormsmarthome

The source code for the Storm topology that this project deploys and autoscales. This is the starting point of the research — it implements the basic IoT data pipeline with no autoscaling.

### What It Does

Subscribes to an MQTT broker and processes smart home energy consumption data through a multi-window Storm topology, storing results in MySQL.

### Topology Components

| Class | Role |
|---|---|
| `MainTopo.java` | Builds and submits the topology |
| `Spout_data.java` | Subscribes to MQTT topic `iot-data`, emits tuples |
| `Spout_trigger.java` | Time-trigger spout |
| `Bolt_split.java` | Splits data into time-window buckets (1,5,10,15,20,30,60,120 min) |
| `Bolt_avg.java` | Computes rolling average per window |
| `Bolt_sum.java` | Computes sum per window |
| `Bolt_forecast.java` | Computes energy forecast per window |
| `DB_store.java` | Writes results to MySQL |

### Models

Data models exist at three granularity levels: `DeviceData`, `HouseData`, `HouseholdData` — each with corresponding `Prop` and `Notification` variants.

### Build

```bash
cp sample_env.yaml src/main/resources/config/cred.yaml
# Edit cred.yaml with MQTT broker and MySQL credentials
mvn install
```

Output: `target/Storm-IOTdata-1.0-SNAPSHOT-jar-with-dependencies.jar`

### Relationship to This Repo

This repo mounts the topology JAR into the Nimbus container:
```yaml
# docker-compose.yml
volumes:
  - ./storm-src/target/Storm-IOTdata-1.0-SNAPSHOT-jar-with-dependencies.jar:/opt/storm/lib/Storm-IOTdata-1.0.jar
```

The K8s Nimbus image `mr4x2/nimbus-k8s:v2.2` bundles it directly.

---

## 2. storm_exporter_prometheus — Prometheus Exporter

**Repository:** https://github.com/mr4x2/storm_exporter_prometheus

A Python service that scrapes the Storm UI REST API and exposes all topology metrics in Prometheus format. It is the **bridge between Storm and the entire observability + autoscaling stack**.

### What It Does

Polls `http://<STORM_UI_HOST>/api/v1/` on a configurable interval and exposes metrics on a Prometheus HTTP endpoint (default port 8082).

### Exposed Metrics

**Topology summary** (labels: `TopologyName`, `TopologyId`):

| Metric | Description |
|---|---|
| `uptime_seconds` | How long the topology has been running |
| `tasks_total` | Total task count |
| `workers_total` | Worker process count |
| `executors_total` | Total executor count |
| `assigned_mem_on_heap` / `assigned_total_mem` | Memory assigned by scheduler |
| `assigned_cpu` | CPU assigned by scheduler |

**Per-spout** (labels: `SpoutId`):

| Metric | Description |
|---|---|
| `spouts_complete_latency` | End-to-end processing latency (ms) |
| `spouts_acked` / `spouts_failed` | Throughput counters |
| `spouts_emitted` / `spouts_transferred` | Emission counters |
| `spouts_executors` / `spouts_tasks` | Parallelism |

**Per-bolt** (labels: `BoltId`):

| Metric | Description |
|---|---|
| `bolts_capacity` | Utilization ratio (executed × latency / window) |
| `bolts_execute_latency` | Avg time to run `execute()` (ms) |
| `bolts_process_latency` | Avg time from receive to ack (ms) |
| `bolts_acked` / `bolts_failed` | Throughput counters |
| `bolts_executors` / `bolts_tasks` | Parallelism |

**Cluster-level** (labels: `ClusterHost`):

| Metric | Description |
|---|---|
| `worker_cluster_total` | Total worker slots in cluster |
| `worker_cluster_used` | Worker slots currently in use |
| `supervisor_cluster_total` | Number of supervisor nodes |
| `weight_scale` | **Composite autoscale metric** (see below) |

### weight_scale — The Autoscale Signal

The exporter computes and publishes `weight_scale` directly to Prometheus. This is the metric the KEDA `ScaledObject` queries:

```python
weight_scale = ratio_worker_process * 0.6/0.7
             + (avg_bolt_capacity / 0.5) * 0.2
             + (avg_spout_complete / 100) * 0.2
```

Where:
- `ratio_worker_process` = `slotsUsed / slotsTotal`
- `avg_bolt_capacity` = average `capacity` of all `split-*` bolts (600s window)
- `avg_spout_complete` = `completeLatency` of `spout-data-iot-data` (600s window)

The KEDA `ScaledObject` queries `weight_scale{ClusterHost="nimbus-ui:8081"}` with threshold `0.75`.

### Configuration

```env
STORM_UI_HOST=nimbus:8081   # or nimbus-ui:8081 in K8s
PORT_EXPOSE=8082
REFRESH_RATE=3              # seconds between Storm UI polls
```

### Run

```bash
cp sample.env .env
docker run -d -p 8082:8082 --env-file .env mr4x2/stormexporter:v1.4.1
```

### Relationship to This Repo

- **Docker Compose** uses `mr4x2/stormexporter:v1.4.1` with `REFRESH_RATE=3`
- **Kubernetes** uses `mr4x2/stormexporter:v1.2.5` with `REFRESH_RATE=5`
- Prometheus scrapes `:8082` every 15s
- The `weight_scale` metric it publishes is the sole trigger for KEDA pod scaling

---

## Research Architecture Summary

```
fimocode/stormsmarthome          ← Topology source (core project)
        │ topology JAR
        ▼
apache-storm-autoscale-k8s       ← This repo (autoscaling layer)
  ├── storm-src/                    Java rule-based executor autoscaler
  ├── k8s/keda/                     KEDA pod autoscaler
  └── docker-compose.yml            Local dev environment
        │ metrics via REST
        ▼
mr4x2/storm_exporter_prometheus  ← Prometheus exporter + weight_scale publisher
        │ scraped by
        ▼
   Prometheus → KEDA → scale supervisor pods
```
